import asyncio
import json
import math
import sys
import os
from os.path import exists
import random
import discord
from discord.ext import commands
from discord_slash import SlashCommand, SlashContext
from discord_slash.model import ButtonStyle
from discord_slash.utils.manage_components import ComponentContext, create_actionrow, create_button
from PIL import Image
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore


##########################################
# Globals Setup (I know globals are bad) #
##########################################

# Load keys
keyFile = open('./other/auth.json', 'r')
keys = json.loads(keyFile.read())
dbCred = credentials.Certificate('./other/firebase.json')

# Global variables
width, height = 200, 200
genCooldown = 1800 # in seconds (30m = 1800s)
prefix = 's!'
activity = discord.Activity(type=discord.ActivityType.listening, name="s!help")
bot = commands.Bot(command_prefix=prefix, activity=activity, case_insensitive=True)

# Initialize database
firebase_admin.initialize_app(dbCred)
db = firestore.client()
print(' > Setup firestore.')

# Load colors
colors = []
with open('./res/colors.txt', 'r') as f:
	for line in f.readlines():
		colors.append(line.replace('\n', ''))
		f.close()
print(' > Loaded colors.')

# Part counters
# Used to reduce hard-coding random ranges when new parts are added to increase workflow
def countFiles(dir):
	# Counts the amount of files in a directory
	return len([f for f in os.listdir(dir) if os.path.isfile(dir + f)])
partDirs = './res/parts/slimes/'
_specialBgs = countFiles(partDirs + 'backgrounds/special/')
_bodies     = countFiles(partDirs + 'bodies/')
_eyes       = countFiles(partDirs + 'face/eyes/')
_mouths     = countFiles(partDirs + 'face/mouths/')
_hats       = countFiles(partDirs + 'hats/')
print(' > Counted files.')


#####################
# Utility Functions #
#####################

# Turns a list into a string with a given character in between
def formatList(list, c):
	res = ''
	for i in list:
		res += (i + c)
	return res[:-1]

# Makes a new document for a user if they aren't registered
def checkUser(author, id):
	# Check if already registered
	ref = db.collection('users').document(id)

	if not ref.get().exists:
		# Make document
		data = {'slimes': []}
		ref.set(data)
		print('| Registered: {0} ({1})'.format(author, id))

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
# Used to smooth te process of making new NFT collections
def rollLayers(fName, layers, bgColor):
	# Generate the image
	nft = Image.new(mode='RGB', size=(width, height), color=colors[bgColor])

	# Roll Layers
	for file in layers:
		layer = Image.open(file[0])

		# Check if the layer needs a transparency mask
		if file[1]:
			nft.paste(layer, (0, 0), layer)
		else:
			nft.paste(layer)
		layer.close()

	# Save the image/close
	nft.save(fName)
	nft.close()

# Places layers of randomly chosen elements to make a slime image
def genSlime():
	fName = './nfts/slimes/'

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
		numNormals = 8
		if random.randrange(0, 10):
			roll = str(random.randrange(0, numNormals))
		else:
			roll = str(random.randrange(numNormals, _bodies))
		id += (roll + '-')
		layers.append(('{0}bodies/{1}.png'.format(partDirs, roll), True))

		# Eyes
		roll = str(random.randrange(0, _eyes))
		id += (roll + '-')
		layers.append(('{0}face/eyes/{1}.png'.format(partDirs, roll), True))

		# Mouth [75% chance]
		if random.randint(0, 3) != 0:
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

# Generates an nft and posts it as a reply
@bot.command(brief='Generates an NFT', description='Creates a unique "NFT" and replies to the user with it. 30m cooldown.')
@commands.cooldown(1, genCooldown, commands.BucketType.user)
async def gen(ctx):
	userID = str(ctx.author.id)
	checkUser(ctx.author, userID)

	# Generate slime and get id
	path = genSlime()
	id    = path[path.rfind('/') + 1:path.rfind('.')]

	# Add nft to the database
	ref = db.collection('users').document(userID)
	ref.update({'slimes': firestore.ArrayUnion([id])})

	# Make embed and send it
	file = discord.File(path)
	embed = discord.Embed(title='slime#{0} was generated!'.format(id), color=discord.Color.green())
	embed.set_image(url='attachment://' + path)
	await ctx.reply(embed=embed, file=file)

# Views a slime given an ID
@bot.command(brief='Shows a given slime', description='Shows the slime corresponding to the given ID.')
async def view(ctx, arg=None):
	# Check if given id is valid (incredibly insecure)
	if not arg or len(arg) != 7:
		await ctx.reply('I need a valid ID you fucking idiot.')
		return

	path = './nfts/slimes/{0}.png'.format(arg)
	
	# Check if the slime exists
	if not exists(path):
		await ctx.reply('**slime#{0}** doesn\'t exist!'.format(arg))
		return
	
	# Make embed and send it
	file = discord.File(path)
	embed = discord.Embed(title='Here\'s slime#' + arg)
	embed.set_image(url='attachment://' + path)
	await ctx.reply(embed=embed, file=file)

# Replies with an embed showing all of a users slimes
@bot.command(brief='Shows the users inventory')
@commands.cooldown(1, 120, commands.BucketType.user)
async def inv(ctx):
	perPage = 10
	userID = str(ctx.author.id)
	checkUser(ctx.author, userID)
	buttons = ['⏮️', '⬅️', '➡️', '⏭️']
	slimes = db.collection('users').document(userID).get().to_dict()['slimes']

	# Check if user even has slimes
	if not slimes:
		await ctx.reply('You have no slimes!')
		return

	# Only post one page if less than listing amount
	if len(slimes) < perPage:
		embed = embed=discord.Embed(title='{0}\'s Inventory'.format(ctx.author), description=formatList(slimes, '\n'), color=discord.Color.green())
		embed.set_footer(text='{0} slime(s)...'.format(len(slimes)))
		await ctx.reply(embed=embed)

	# Put into checked pages of embeds
	pages = []
	numPages = math.ceil(len(slimes) / perPage)
	for i in range(numPages):
		# Slice array for page
		page = []
		max = ((i * perPage) + perPage) if (i != numPages - 1) else len(slimes)
		if i != numPages - 1:
			page = slimes[i * perPage:(i * perPage) + perPage]
		else:
			page = slimes[i * perPage:]
		# Setup pages embed
		embed=discord.Embed(title='{0}\'s Inventory'.format(ctx.author), description=formatList(page, '\n'), color=discord.Color.green())
		embed.set_footer(text='Slimes {0}-{1} of {2} slime(s)...'.format((i * perPage) + 1, max, len(slimes)))
		pages.append(embed)

	# Setup embed for reactions
	cur = 0
	msg = await ctx.reply(embed=pages[cur])
	for button in buttons:
		await msg.add_reaction(button)

	while True:
		try:
			reaction, _ = await bot.wait_for("reaction_add", check=lambda reaction, user: user == ctx.author and reaction.emoji in buttons, timeout=60.0)
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

# Given a slime the user owns and someone elses, requests a trade
@bot.command(brief='[WIP] Trade with other users', description='Usage: {0}trade <your slime> <their slime>. '.format(prefix))
async def trade(ctx, slime1, slime2):
	await ctx.reply('This hasn\'t been implemented yet!')


#############
# Bot Setup #
#############

@bot.event
async def on_command_error(ctx, error):
	if isinstance(error, commands.CommandOnCooldown):
		# Check if more than 2 minutes remaining
		if error.retry_after < 121:
			await ctx.reply('You can use this command again in *{0} seconds*.'.format(int(error.retry_after)))
		else:
			await ctx.reply('You can use this command again in *{0} minutes*.'.format(int(error.retry_after / 60)))
	elif isinstance(error, commands.CommandNotFound):
		await ctx.reply('That command doesn\'t exist!')

@bot.event
async def on_ready():
	random.seed()
	print('> Botty has been turned on:')

def main(gen, amount=100):
	if gen:
		# For generating mass amounts
		for i in range(amount):
			genSlime()
	else:
		bot.run(keys['discordToken'])

if __name__ == '__main__':
	# Check if command-line says to generate specific nft amount
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