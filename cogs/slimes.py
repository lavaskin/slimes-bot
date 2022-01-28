import asyncio
import json
import math
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


# Load Descriptions File
descFile = open('./other/desc.json')
desc = json.loads(descFile.read())


class Slimes(commands.Cog):
	def __init__(self, bot, dev=True):
		# Set random class properties
		self.bot = bot
		self.outputDir = './output/dev/' if dev else './output/prod/'
		self.width, self.height = 200, 200

		# Init Database
		dbCred = credentials.Certificate('./other/firebase.json')
		self.collection = 'users-dev' if dev else 'users'
		firebase_admin.initialize_app(dbCred)
		self.db = firestore.client()

		# Load colors
		self.colors = []
		with open('./res/colors.txt', 'r') as f:
			for line in f.readlines():
				self.colors.append(line.replace('\n', ''))
				f.close()

		# Count Parts
		def countFiles(dir):
			# Counts the amount of files in a directory
			return len([f for f in os.listdir(dir) if os.path.isfile(dir + f)])
		self.partsDir      = './res/parts/slimes/'
		self.specialBgs    = countFiles(self.partsDir + 'backgrounds/special/')
		self.regBodies     = countFiles(self.partsDir + 'bodies/regular/')
		self.specialBodies = countFiles(self.partsDir + 'bodies/special/')
		self.eyes          = countFiles(self.partsDir + 'face/eyes/')
		self.mouths        = countFiles(self.partsDir + 'face/mouths/')
		self.hats          = countFiles(self.partsDir + 'hats/')
		random.seed()
		print(' > Finished initial setup.')

	#####################
	# Utility Functions #
	#####################

	# Checks if a given slime passes the given filter
	def passesFilter(self, filter, slime):
		# Check if every character passes the filter
		for i, c in enumerate(slime):
			if filter[i] != '?' and filter[i] != c:
				return False
		return True

	# Turns a list into a string with a given character in between
	def formatList(self, list, c):
		res = ''
		for i in list:
			res += (i + c)
		return res[:-1]

	# Makes a new document for a user if they aren't registered
	def checkUser(self, id, author=''):
		# Check if already registered
		ref = self.db.collection(self.collection).document(id)

		if not ref.get().exists:
			# Only register a user if they generate a slime
			if not author: return False
			# Make document
			data = {'tag': str(author), 'slimes': [], 'favs': []}
			ref.set(data)
			print(' | Registered: {0} ({1})'.format(author, id))
			return False
		else:
			return True

	# Encodes a given slime ID into a more readable compact form
	def encodeSlimeID(self, id):
		enc = ''
		for n in id.split('-'):
			if n == 'X':
				enc += '!'
			else:
				enc += self.encodeNum(int(n))
		return enc

	# Encodes a single number
	def encodeNum(self, n):
		if n < 10:
			return str(n)
		elif n < 36:
			return chr(n + 55)
		else:
			return chr(n + 61)

	# Decodes an encoded slime id to the form they're generated as [Non-public facing]
	def decodeSlimeID(self, enc):
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
	def getPaintColors(self):
		colorCount = len(self.colors)
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
	def rollLayers(self, fName, layers, bgColor):
		# Generate the image
		final = Image.new(mode='RGB', size=(self.width, self.height), color=self.colors[bgColor])

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
	def genSlime(self):
		# Loops until a unique ID is created
		while True:
			bgColor, altColor = self.getPaintColors()
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
				roll = str(random.randrange(0, self.specialBgs))
				id += ('2-' + roll + '-X-')
				layers.append(('{0}backgrounds/special/{1}.png'.format(self.partsDir, roll), False))
			elif bgRoll > 50:
				# Apply stripe layer
				id += ('1-{0}-{1}-'.format(bgColor, altColor))
				layers.append(('{0}backgrounds/stripes/{1}.png'.format(self.partsDir, altColor), True))
			else:
				# Solid Color
				id += ('0-' + str(bgColor) + '-X-')

			# Add slime body [90% chance of regular body, 10% special]
			if random.randrange(0, 10):
				roll = str(random.randrange(0, self.regBodies))
				id += ('0-' + str(roll) + '-')
				layers.append(('{0}bodies/regular/{1}.png'.format(self.partsDir, roll), True))
			else:
				roll = str(random.randrange(0, self.specialBodies))
				id += ('1-' + str(roll) + '-')
				layers.append(('{0}bodies/special/{1}.png'.format(self.partsDir, roll), True))

			# Eyes
			roll = str(random.randrange(0, self.eyes))
			id += (roll + '-')
			layers.append(('{0}face/eyes/{1}.png'.format(self.partsDir, roll), True))

			# Mouth [80% chance]
			if random.randint(0, 4) != 0:
				roll = str(random.randrange(0, self.mouths))
				id += (roll + '-')
				layers.append(('{0}face/mouths/{1}.png'.format(self.partsDir, roll), True))
			else: id += 'X-'

			# Add hat [75% chance of having a hat]
			if random.randint(0, 3) != 0:
				roll = str(random.randrange(0, self.hats))
				id += roll
				layers.append(('{0}hats/{1}.png'.format(self.partsDir, roll), True))
			else: id += 'X'

			# Encode ID
			id = self.encodeSlimeID(id)

			# Check that ID doesn't exist. If so, leave the loop
			if not exists(self.outputDir + id + '.png'):
				break
			else: print('| DUPE SLIME:', id)

		# Roll the layers and return the rolled file
		fName = self.outputDir + id + '.png'
		self.rollLayers(fName, layers, bgColor)
		return fName

	################
	# Bot Commands #
	################

	@commands.command(brief=desc['gen']['short'], description=desc['gen']['long'])
	@commands.cooldown(1, 900, commands.BucketType.user)
	async def gen(self, ctx):
		userID = str(ctx.author.id)
		self.checkUser(userID, ctx.author)

		# Generate slime and get id
		path = self.genSlime()
		id   = path[path.rfind('/') + 1:path.rfind('.')]

		# Add slime to the database
		ref = self.db.collection(self.collection).document(userID)
		ref.update({'slimes': firestore.ArrayUnion([id])})

		# Make embed and send it
		file = discord.File(path)
		embed = discord.Embed(title='slime#{0} was generated!'.format(id), color=discord.Color.green())
		await ctx.reply(embed=embed, file=file)

	@commands.command(brief=desc['view']['short'], description=desc['view']['long'])
	async def view(self, ctx, arg=None):
		# Check if given id is valid (incredibly insecure)
		if not arg or len(arg) != 8:
			await ctx.reply('I need a valid ID you fucking idiot.', delete_after=5)
			return

		path = f'{self.outputDir}{arg}.png'
		
		# Check if the slime exists
		if not exists(path):
			await ctx.reply('**slime#{0}** doesn\'t exist!'.format(arg))
			return
		
		# Make embed and send it
		file = discord.File(path)
		embed = discord.Embed(title=f'Here\'s slime#{arg}', color=discord.Color.green())
		await ctx.reply(embed=embed, file=file)

	@commands.command(brief=desc['inv']['short'], description=desc['inv']['long'])
	@commands.cooldown(1, 60, commands.BucketType.user)
	async def inv(self, ctx, filter=''):
		perPage = 10
		username = str(ctx.author)[:str(ctx.author).rfind('#')]
		userID = str(ctx.author.id)
		self.checkUser(userID, ctx.author)
		buttons = ['⏮️', '⬅️', '➡️', '⏭️']
		slimes = self.db.collection(self.collection).document(userID).get().to_dict()['slimes']

		# Check if user even has slimes
		if not slimes:
			await ctx.reply('You have no slimes!', delete_after=5)
			return

		# Filter slimes
		filtered = []
		if filter:
			if len(filter) == 8:
				for slime in slimes:
					if self.passesFilter(filter, slime):
						filtered.append(slime)
			else:
				await ctx.reply('Incorrect filter!', delete_after=5)
				return
		else:
			filtered = slimes

		# Check if there are any slimes that match the filter
		if not filtered:
			await ctx.reply('No slimes you own match that filter!', delete_after=5)
			return

		# Only post one page if less than listing amount
		if len(filtered) < perPage:
			embed = embed=discord.Embed(title='{0}\'s Inventory'.format(username), description=self.formatList(filtered, '\n'), color=discord.Color.green())
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
			embed=discord.Embed(title='{0}\'s Inventory'.format(username), description=self.formatList(page, '\n'), color=discord.Color.green())
			embed.set_footer(text='Slimes {0}-{1} of {2}...'.format((i * perPage) + 1, max, len(filtered)))
			pages.append(embed)

		# Setup embed for reactions
		cur = 0
		msg = await ctx.reply(embed=pages[cur])
		for button in buttons:
			await msg.add_reaction(button)

		while True:
			try:
				reaction, _ = await self.bot.wait_for("reaction_add", check=lambda reaction, user: user == ctx.author and reaction.emoji in buttons, timeout=10.0)
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

	@commands.command(brief=desc['trade']['short'], description=desc['trade']['long'])
	@commands.cooldown(1, 60, commands.BucketType.user)
	@commands.guild_only()
	async def trade(self, ctx, other, slime1, slime2):
		# Check if both users are registerd
		userID = str(ctx.author.id)
		otherID = other[3:-1]
		if userID == otherID:
			await ctx.reply('You can\t trade with yourself, dumbass.', delete_after=5)
			return
		elif not self.checkUser(userID, ctx.author) or not self.checkUser(otherID):
			await ctx.reply('You both need to be registered to trade!', delete_after=5)
			return

		# Basic check on given id's
		if len(slime1) != 8 or len(slime2) != 8:
			await ctx.reply('Given ID\'s need to be valid!', delete_after=5)
			return

		# Check if both users have slimes, including the ones referenced in args
		ref      = self.db.collection(self.collection).document(userID)
		otherRef = self.db.collection(self.collection).document(otherID)
		slimes = ref.get().to_dict()['slimes']
		otherSlimes = otherRef.get().to_dict()['slimes']
		if slime1 not in slimes:
			await ctx.reply(f'You don\'t own {slime1}!', delete_after=5)
		elif slime2 not in otherSlimes:
			await ctx.reply(f'They doesn\t own {slime2}!', delete_after=5)

		# Make combined image
		s1img = Image.open(f'{self.outputDir}{slime1}.png')
		s2img = Image.open(f'{self.outputDir}{slime2}.png')
		exchangeImg = Image.open('./res/arrows.png')
		combined = Image.new(mode='RGBA', size=((self.width * 2) + 50, self.width), color=(0, 0, 0, 0))
		combined.paste(s1img, (0, 0))
		combined.paste(exchangeImg, (200, 0))
		combined.paste(s2img, (350, 0))
		fName = f'{self.outputDir}trade_{slime1}_{slime2}.png'
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
			reaction, user = await self.bot.wait_for("reaction_add", check=lambda reaction, user: user.id == int(otherID) and reaction.emoji in buttons, timeout=45.0)
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

	@commands.command(brief=desc['reset_self']['short'], description=desc['reset_self']['long'])
	@commands.cooldown(1, 86400, commands.BucketType.user)
	async def reset_self(self, ctx):
		userID = str(ctx.author.id)
		if not self.checkUser(userID):
			await ctx.reply('You have nothing to reset!', delete_after=5)
			return

		# Make confirmation method
		buttons = ['✔️', '❌']
		msg = await ctx.reply('Are you completely sure you want to reset your account? There are no reversals.')
		for button in buttons:
			await msg.add_reaction(button)

		# Process response
		try:
			reaction, _ = await self.bot.wait_for("reaction_add", check=lambda reaction, user: user == ctx.author and reaction.emoji in buttons, timeout=10.0)
		except asyncio.TimeoutError:
			return
		else:
			if reaction.emoji == buttons[0]:
				ref = self.db.collection(self.collection).document(userID)

				# Reset slimes stored on server
				slimes = ref.get().to_dict()['slimes']
				if slimes:
					allSlimes = os.listdir(self.outputDir)
					for slime in slimes:
						for f in allSlimes:
							if os.path.isfile(self.outputDir + f) and f[:f.rfind('.')] == slime:
								os.remove(self.outputDir + f)

				# Remove user document in database and respond
				ref.delete()
				await msg.edit(content='Your account has been reset.')
			elif reaction.emoji == buttons[1]:
				await msg.edit(content='Your account is safe!')

	@commands.command(brief=desc['fav']['short'], description=desc['fav']['long'])
	@commands.cooldown(1, 5, commands.BucketType.user)
	async def fav(self, ctx, id):
		# Check user is registered
		userID = str(ctx.author.id)
		if not self.checkUser(userID):
			await ctx.reply('You have no slimes!', delete_after=5)
			return

		# Check they have any slimes and if they own the one mentioned
		ref = self.db.collection(self.collection).document(userID)
		slimes = ref.get().to_dict()['slimes']
		if id not in slimes:
			await ctx.reply('You don\'t own this slime!', delete_after=5)
			return

		# Check if already in favorites and if favorites are maxed out
		favs = ref.get().to_dict()['favs']
		if id in favs:
			ref.update({'favs': firestore.ArrayRemove([id])})
			await ctx.reply(f'**{id}** has been removed from your favorites!')
		elif len(favs) == 9:
			await ctx.reply('You can only have a max of 9 favorites!')
		else:
			ref.update({'favs': firestore.ArrayUnion([id])})
			await ctx.reply(f'**{id}** has been added to your favorites!')

	@commands.command(brief=desc['favs']['short'], description=desc['favs']['long'])
	@commands.cooldown(1, 60, commands.BucketType.user)
	async def favs(self, ctx, clear=''):
		# Check user is registered
		userID = str(ctx.author.id)
		if not self.checkUser(userID):
			await ctx.reply('You have no slimes!', delete_after=5)
			return

		# Check if they have any favs
		ref = self.db.collection(self.collection).document(userID)
		favs = ref.get().to_dict()['favs']
		if not favs:
			await ctx.reply('You don\'t have any favs!')
			return

		# Remove all favs from current user
		if clear in ['c', 'clear']:
			ref.update({'favs': []})
			await ctx.reply('Your favorites were reset.')
			return


		# Make collage (this is awful)
		numFavs = len(favs)
		idOffset = 100
		font = ImageFont.truetype("consola.ttf", 20)
		width = (3 * self.width) if numFavs > 2 else numFavs * self.width
		height = math.ceil(numFavs / 3) * self.height
		n = 0
		combined = Image.new(mode='RGBA', size=(width, height), color=(0, 0, 0, 0))
		draw = ImageDraw.Draw(combined)
		fName = f'{self.outputDir}favs_{userID}.png'

		for y in range(0, height, self.height):
			for x in range(0, width, self.width):
				if n < numFavs:
					img = Image.open(f'{self.outputDir}{favs[n]}.png')
					combined.paste(img, (x, y))
					draw.text((x + idOffset, y), f"#{favs[n]}", (0, 0, 0), font=font)
					n += 1
				else:
					break
		
		# Finish up
		combined.save(fName)
		combined.close()
		file = discord.File(fName)
		await ctx.reply('Here are your favorites!', file=file)
		os.remove(fName)


def setup(bot):
	bot.add_cog(Slimes(bot, dev=False))