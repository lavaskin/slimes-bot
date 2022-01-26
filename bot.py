import asyncio
import json
import math
import numbers
import sys
import os
from os.path import exists
import random
import discord
from discord.ext import commands
from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore


##########################################
# Globals Setup (I know globals are bad) #
##########################################

# Load in JSON Files
keyFile = open('./other/auth.json', 'r')
keys = json.loads(keyFile.read())
dbCred = credentials.Certificate('./other/firebase.json')
descFile = open('./other/desc.json')
desc = json.loads(descFile.read())

# Global variables
width, height = 200, 200
genCooldown = 900 # in seconds (30m = 1800s)
prefix = 's!'
activity = discord.Activity(type=discord.ActivityType.listening, name="s!help")
bot = commands.Bot(command_prefix=prefix, activity=activity, case_insensitive=True)

# Initialize database
firebase_admin.initialize_app(dbCred)
db = firestore.client()

# Load colors
colors = []
with open('./res/colors.txt', 'r') as f:
	for line in f.readlines():
		colors.append(line.replace('\n', ''))
		f.close()

# Part counters
# Used to reduce hard-coding random ranges when new parts are added to increase workflow
def countFiles(dir):
	# Counts the amount of files in a directory
	return len([f for f in os.listdir(dir) if os.path.isfile(dir + f)])
partDirs       = './res/parts/slimes/'
_specialBgs    = countFiles(partDirs + 'backgrounds/special/')
_regBodies     = countFiles(partDirs + 'bodies/regular/')
_specialBodies = countFiles(partDirs + 'bodies/special/')
_eyes          = countFiles(partDirs + 'face/eyes/')
_mouths        = countFiles(partDirs + 'face/mouths/')
_hats          = countFiles(partDirs + 'hats/')
print(' > Finished initial setup.')


#####################
# Utility Functions #
#####################

# Checks if a given slime passes the given filter
def passesFilter(filter, slime):
	# Check if every character passes the filter
	for i, c in enumerate(slime):
		if filter[i] != '?' and filter[i] != c:
			return False
	return True

# Turns a list into a string with a given character in between
def formatList(list, c):
	res = ''
	for i in list:
		res += (i + c)
	return res[:-1]

# Makes a new document for a user if they aren't registered
def checkUser(id, author=''):
	# Check if already registered
	ref = db.collection('users').document(id)

	if not ref.get().exists:
		# Only register a user if they generate a slime
		if not author: return False
		# Make document
		data = {'tag': str(author), 'slimes': []}
		ref.set(data)
		print('| Registered: {0} ({1})'.format(author, id))
		return False
	else:
		return True

# Encodes a given slime ID into a more readable compact form
def encodeSlimeID(id):
	enc = ''
	for n in id.split('-'):
		if n == 'X':
			enc += '!'
		else:
			enc += encodeNum(int(n))
	return enc

# Encodes a single number
def encodeNum(n):
    if n < 10:
        return str(n)
    elif n < 36:
        return chr(n + 55)
    else:
        return chr(n + 61)

# Decodes an encoded slime id to the form they're generated as [Non-public facing]
def decodeSlimeID(enc):
	id = ''
	for c in enc:
		if c == '!':
			id += 'X-'
		else:
			if ord(c) > 96:
				id += (str(ord(c) - 61) + '-')
			elif ord(c) > 64:
				id += (str(ord(c) - 55) + '-')
			else:
				id += (c + '-')
	id = id[:-1] # remove trailing 'x'
	return id

# Generates two different paint colors from the global list (RETURNS THEIR INDEX!)
def getPaintColors():
	colorCount = len(colors)
	c1 = random.randrange(0, colorCount)
	c2 = random.randrange(0, colorCount)

	# Flip paint color if same as bg
	if c1 == c2:
		c1 = colorCount - c1 - 1
	return c1, c2


########################
# Generation Functions #
########################

# Given a list of files, creates a layered image of them in order
# Used to smooth the process of making new image collections
def rollLayers(fName, layers, bgColor):
	# Generate the image
	final = Image.new(mode='RGB', size=(width, height), color=colors[bgColor])

	# Roll Layers
	for file in layers:
		layer = Image.open(file[0])

		# Check if the layer needs a transparency mask
		if file[1]:
			final.paste(layer, (0, 0), layer)
		else:
			final.paste(layer)
		layer.close()

	# Save the image/close
	final.save(fName)
	final.close()

# Places layers of randomly chosen elements to make a slime image
def genSlime():
	fName = './output/'

	# Loops until a unique ID is created
	while True:
		bgColor, altColor = getPaintColors()
		layers = [] # Tuples of form: (file path, transparent?)

		# Start ID
		# Used to remove the possibility of duplicates
		# Form: bgtype-primarycolor (or special type)-altcolor (stripe color for bg)-eyes-mouth-hat
		# For example, a red and blue striped slime would start as 1_<redid>-<blueid>-...
		# -X- means nothing for that catagory was used, like if a bg is a solid color it has no tertiary, or if it has no hat
		id = ''

		# Get all the layers

		# Background [50% solid color, 45% stripes, 5% special]
		bgRoll = random.randint(1, 100)
		if bgRoll > 95:
			# Apply special background
			roll = str(random.randrange(0, _specialBgs))
			id += ('2-' + roll + '-X-')
			layers.append(('{0}backgrounds/special/{1}.png'.format(partDirs, roll), False))
		elif bgRoll > 50:
			# Apply stripe layer
			id += ('1-{0}-{1}-'.format(bgColor, altColor))
			layers.append(('{0}backgrounds/stripes/{1}.png'.format(partDirs, altColor), True))
		else:
			# Solid Color
			id += ('0-' + str(bgColor) + '-X-')

		# Add slime body [90% chance of regular body, 10% special]
		if random.randrange(0, 10):
			roll = str(random.randrange(0, _regBodies))
			id += ('0-' + str(roll) + '-')
			layers.append(('{0}bodies/regular/{1}.png'.format(partDirs, roll), True))
		else:
			roll = str(random.randrange(0, _specialBodies))
			id += ('1-' + str(roll) + '-')
			layers.append(('{0}bodies/special/{1}.png'.format(partDirs, roll), True))

		# Eyes
		roll = str(random.randrange(0, _eyes))
		id += (roll + '-')
		layers.append(('{0}face/eyes/{1}.png'.format(partDirs, roll), True))

		# Mouth [80% chance]
		if random.randint(0, 4) != 0:
			roll = str(random.randrange(0, _mouths))
			id += (roll + '-')
			layers.append(('{0}face/mouths/{1}.png'.format(partDirs, roll), True))
		else: id += 'X-'

		# Add hat [50% chance of having a hat]
		if random.randint(0, 1):
			roll = str(random.randrange(0, _hats))
			id += roll
			layers.append(('{0}hats/{1}.png'.format(partDirs, roll), True))
		else: id += 'X'

		# Encode ID
		id = encodeSlimeID(id)

		# Check that ID doesn't exist. If so, leave the loop
		if not exists(fName + id + '.png'):
			break
		else: print('| DUPE SLIME:', id)

	# Roll the layers and return the rolled file
	fName = fName + id + '.png'
	rollLayers(fName, layers, bgColor)
	return fName


################
# Bot Commands #
################

@bot.command(brief=desc['gen']['short'], description=desc['gen']['long'])
@commands.cooldown(1, genCooldown, commands.BucketType.user)
async def gen(ctx):
	userID = str(ctx.author.id)
	checkUser(userID, ctx.author)

	# Generate slime and get id
	path = genSlime()
	id    = path[path.rfind('/') + 1:path.rfind('.')]

	# Add slime to the database
	ref = db.collection('users').document(userID)
	ref.update({'slimes': firestore.ArrayUnion([id])})

	# Make embed and send it
	file = discord.File(path)
	embed = discord.Embed(title='slime#{0} was generated!'.format(id), color=discord.Color.green())
	await ctx.reply(embed=embed, file=file)

@bot.command(brief=desc['view']['short'], description=desc['view']['long'])
async def view(ctx, arg=None):
	# Check if given id is valid (incredibly insecure)
	if not arg or len(arg) != 8:
		await ctx.reply('I need a valid ID you fucking idiot.', delete_after=5)
		return

	path = './output/{0}.png'.format(arg)
	
	# Check if the slime exists
	if not exists(path):
		await ctx.reply('**slime#{0}** doesn\'t exist!'.format(arg))
		return
	
	# Make embed and send it
	file = discord.File(path)
	embed = discord.Embed(title='Here\'s slime#{0}!'.format(arg), color=discord.Color.green())
	await ctx.reply(embed=embed, file=file)

@bot.command(brief=desc['inv']['short'], description=desc['inv']['long'])
@commands.cooldown(1, 120, commands.BucketType.user)
async def inv(ctx, filter=''):
	perPage = 10
	username = str(ctx.author)[:str(ctx.author).rfind('#')]
	userID = str(ctx.author.id)
	checkUser(userID, ctx.author)
	buttons = ['⏮️', '⬅️', '➡️', '⏭️']
	slimes = db.collection('users').document(userID).get().to_dict()['slimes']

	# Check if user even has slimes
	if not slimes:
		await ctx.reply('You have no slimes!', delete_after=5)
		return

	# Filter slimes
	filtered = []
	if len(filter) == 8:
		for slime in slimes:
			if passesFilter(filter, slime):
				filtered.append(slime)
	else:
		filtered = slimes

	# Check if there are any slimes that match the filter
	if not filtered:
		await ctx.reply('No slimes you own match that filter!', delete_after=5)
		return

	# Only post one page if less than listing amount
	if len(filtered) < perPage:
		embed = embed=discord.Embed(title='{0}\'s Inventory'.format(username), description=formatList(filtered, '\n'), color=discord.Color.green())
		embed.set_footer(text='{0} slime(s)...'.format(len(filtered)))
		await ctx.reply(embed=embed)
		return

	# Put into pages of embeds
	pages = []
	numPages = math.ceil(len(filtered) / perPage)
	for i in range(numPages):
		# Slice array for page
		page = []
		max = ((i * perPage) + perPage) if (i != numPages - 1) else len(filtered)
		if i != numPages - 1:
			page = filtered[i * perPage:(i * perPage) + perPage]
		else:
			page = filtered[i * perPage:]
		# Setup pages embed
		embed=discord.Embed(title='{0}\'s Inventory'.format(username), description=formatList(page, '\n'), color=discord.Color.green())
		embed.set_footer(text='Slimes {0}-{1} of {2}...'.format((i * perPage) + 1, max, len(filtered)))
		pages.append(embed)

	# Setup embed for reactions
	cur = 0
	msg = await ctx.reply(embed=pages[cur])
	for button in buttons:
		await msg.add_reaction(button)

	while True:
		try:
			reaction, _ = await bot.wait_for("reaction_add", check=lambda reaction, user: user == ctx.author and reaction.emoji in buttons, timeout=10.0)
		except asyncio.TimeoutError:
			return
		else:
			# Pick next page based on reaction
			prev = cur
			if reaction.emoji == buttons[0]:
				cur = 0
			if reaction.emoji == buttons[1]:
				if cur > 0:
					cur -= 1
			if reaction.emoji == buttons[2]:
				if cur < len(pages) - 1:
					cur += 1
			if reaction.emoji == buttons[3]:
				cur = len(pages) - 1
			for button in buttons:
				await msg.remove_reaction(button, ctx.author)
			if cur != prev:
				await msg.edit(embed=pages[cur])

@bot.command(brief=desc['trade']['short'], description=desc['trade']['long'])
@commands.cooldown(1, 60, commands.BucketType.user)
async def trade(ctx, other, slime1, slime2):
	# Check if both users are registerd
	userID = str(ctx.author.id)
	otherID = other[3:-1]
	if userID == otherID:
		await ctx.reply('You can\t trade with yourself, dumbass.', delete_after=5)
		return
	elif not checkUser(userID, ctx.author) or not checkUser(otherID):
		await ctx.reply('You both need to be registered to trade!', delete_after=5)
		return

	# Basic check on given id's
	if len(slime1) != 8 or len(slime2) != 8:
		await ctx.reply('Given ID\'s need to be valid!', delete_after=5)
		return

	# Check if both users have slimes, including the ones referenced in args
	ref = db.collection('users').document(userID)
	otherRef = db.collection('users').document(otherID)
	slimes = ref.get().to_dict()['slimes']
	otherSlimes = otherRef.get().to_dict()['slimes']
	if slime1 not in slimes:
		await ctx.reply(f'You don\'t own {slime1}!', delete_after=5)
	elif slime2 not in otherSlimes:
		await ctx.reply(f'They doesn\t own {slime2}!', delete_after=5)

	# Make combined image
	s1img = Image.open(f'./output/{slime1}.png')
	s2img = Image.open(f'./output/{slime2}.png')
	exchangeImg = Image.open('./res/arrows.png')
	combined = Image.new(mode='RGBA', size=(550, 200), color=(0, 0, 0, 0))
	combined.paste(s1img, (0, 0))
	combined.paste(exchangeImg, (200, 0))
	combined.paste(s2img, (350, 0))
	fName = f'./output/trade_{slime1}_{slime2}.png'
	# Place text
	font = ImageFont.truetype("consola.ttf", 20)
	draw = ImageDraw.Draw(combined)
	draw.text((100, 0), f"#{slime1}", (0, 0, 0), font=font)
	draw.text((450, 0), f"#{slime2}", (0, 0, 0), font=font)
	# Save image
	combined.save(fName)
	combined.close()
	file = discord.File(fName)

	# Post trade request
	buttons = ['✔️', '❌']
	msg = await ctx.send(f'{other}: <@{userID}> wants to trade their **{slime1}** for your **{slime2}**. Do you accept?', file=file)
	os.remove(fName)
	for button in buttons:
		await msg.add_reaction(button)

	# Process message reaction
	try:
		reaction, user = await bot.wait_for("reaction_add", check=lambda reaction, user: user.id == int(otherID) and reaction.emoji in buttons, timeout=30.0)
	except asyncio.TimeoutError:
		return
	else:
		if reaction.emoji == buttons[0]:
			await ctx.send('The trade has been accepted!')

			# Add other persons slimes
			ref.update({'slimes': firestore.ArrayUnion([slime2])})
			otherRef.update({'slimes': firestore.ArrayUnion([slime1])})
			# Remove old slimes
			ref.update({'slimes': firestore.ArrayRemove([slime1])})
			otherRef.update({'slimes': firestore.ArrayRemove([slime2])})
			# Update trade message
			await msg.edit(content=f'The trade has been accepted!\n**{slime1}** :arrow_right: **{user}**\n**{slime2}** :arrow_right: **{ctx.author}**')
		elif reaction.emoji == buttons[1]:
			await ctx.send('The trade has been declined!')

@bot.command(brief=desc['reset_self']['short'], description=desc['reset_self']['long'])
@commands.cooldown(1, 86400, commands.BucketType.user)
async def reset_self(ctx):
	userID = str(ctx.author.id)
	if not checkUser(userID):
		await ctx.reply('You have nothing to reset!', delete_after=5)
		return

	# Make confirmation method
	buttons = ['✔️', '❌']
	msg = await ctx.reply('Are you completely sure you want to reset your account? There are no reversals.')
	for button in buttons:
		await msg.add_reaction(button)

	# Process response
	try:
		reaction, _ = await bot.wait_for("reaction_add", check=lambda reaction, user: user == ctx.author and reaction.emoji in buttons, timeout=10.0)
	except asyncio.TimeoutError:
		return
	else:
		if reaction.emoji == buttons[0]:
			dir = './output/'
			ref = db.collection('users').document(userID)

			# Reset slimes stored on server
			slimes = ref.get().to_dict()['slimes']
			if slimes:
				allSlimes = os.listdir(dir)
				for slime in slimes:
					for f in allSlimes:
						if os.path.isfile(dir + f) and f[:f.rfind('.')] == slime:
							os.remove(dir + f)

			# Remove user document in database and respond
			ref.delete()
			await msg.edit(content='Your account has been reset.')
		elif reaction.emoji == buttons[1]:
			await msg.edit(content='Your account is safe!')


#############
# Bot Setup #
#############

@bot.event
async def on_command_error(ctx, error):
	if isinstance(error, commands.CommandOnCooldown):
		# Check if more than 2 minutes remaining
		if error.retry_after < 121:
			await ctx.reply('You can use this command again in *{0} seconds*.'.format(int(error.retry_after)), delete_after=5)
		else:
			await ctx.reply('You can use this command again in *{0} minutes*.'.format(int(error.retry_after / 60)), delete_after=5)
	elif isinstance(error, commands.CommandNotFound):
		await ctx.reply('That command doesn\'t exist!')

@bot.event
async def on_ready():
	random.seed()
	print('> Slimes! has been turned on:')

def main(gen, amount=100):
	if gen:
		# For generating mass amounts
		for i in range(amount):
			genSlime()
	else:
		bot.run(keys['discordToken'])

if __name__ == '__main__':
	# Check if command-line says to generate specific amount of images
	if len(sys.argv) > 1:
		if sys.argv[1] == 'gen':
			if len(sys.argv) > 2:
				main(True, int(sys.argv[2]))
			else:
				main(True)
		else:
			main(False)
	else:
		main(False)