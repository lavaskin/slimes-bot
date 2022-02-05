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
from firebase_admin import credentials, firestore, initialize_app, storage


# Load Descriptions File
descFile = open('./other/desc.json')
desc = json.loads(descFile.read())

# Get Dev Mode
env = os.getenv('SLIME_DEV', 'True')
dev = True if env == 'True' else False


class Slimes(commands.Cog):
	def __init__(self, bot):
		# Set random class properties
		self.bot = bot
		self.outputDir = './output/dev/' if dev else './output/prod/'
		self.width, self.height = 200, 200
		# self.fontPath = open('./other/font.txt', 'r').readline()
		self.fontPath = os.getenv('FONT_PATH', 'consola.ttf')

		# Init Database
		dbCred = credentials.Certificate('./other/firebase.json')
		self.collection = 'users-dev' if dev else 'users'
		initialize_app(dbCred, {'storageBucket': os.getenv('STORAGE_BUCKET')})
		self.db = firestore.client()
		self.bucket = storage.bucket()

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
		self.partsDir      = './res/parts/'
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
	def checkUser(self, id, author=None):
		# Check if already registered
		ref = self.db.collection(self.collection).document(id)

		if not ref.get().exists:
			if not author: return False
			# Make document
			data = {'tag': str(author), 'slimes': [], 'favs': []}
			ref.set(data)
			return False
		else:
			# They are already registered
			return True

	# Encodes a single number
	def encodeNum(self, n):
		if n < 10:
			return str(n)
		elif n < 36:
			return chr(n + 55)
		else:
			return chr(n + 61)

	# Turn a character from an encoded string into a number
	def decodeChar(self, n):
		if n == 'z':
			return 'z'
		else:
			if ord(n) > 96:
				return ord(n) - 61
			elif ord(n) > 64:
				return ord(n) - 55
			else:
				return int(n)

	# Generates two different paint colors from the global list (RETURNS THEIR INDEX!)
	def getPaintColors(self):
		colorCount = len(self.colors)
		c1 = random.randrange(0, colorCount)
		c2 = random.randrange(0, colorCount)

		# Flip paint color if same as bg
		if c1 == c2:
			c1 = colorCount - c1 - 1
		return c1, c2

	# Given a list of files, creates a layered image of them in order
	# Used to smooth the process of making new image collections
	def rollLayers(self, fName, layers, bgColor):
		# Generate the image
		final = Image.new(mode='RGB', size=(self.width, self.height), color=self.colors[bgColor])

		# Roll Layers
		for file in layers:
			try:
				layer = Image.open(file[0])
			except FileNotFoundError:
				return None

			# Check if the layer needs a transparency mask
			if file[1]:
				final.paste(layer, (0, 0), layer)
			else:
				final.paste(layer)
			layer.close()

		# Save the image/close
		final.save(fName)
		final.close()
		return fName


	########################
	# Generation Functions #
	########################

	# Given a slime ID, creates a slime
	def genSlimeLayers(self, id):
		splitID = [self.decodeChar(c) for c in id]
		layers = []

		# id[0] = background variant (0 = solid, 1 = stripes, 2 = specials)
		# id[1] = primary background (solid color/special bg)
		# id[2] = secondary background color (stripes)
		if splitID[0] == 1:
			layers.append((f'{self.partsDir}backgrounds/stripes/{splitID[2]}.png', True))
		elif splitID[0] == 2:
			layers.append((f'{self.partsDir}backgrounds/special/{splitID[1]}.png', False))

		# id[3] = body varient (0 = normal, 1 = special)
		# id[4] = body
		if splitID[3] == 0:
			layers.append((f'{self.partsDir}bodies/regular/{splitID[4]}.png', True))
		elif splitID[3] == 1:
			layers.append((f'{self.partsDir}bodies/special/{splitID[4]}.png', True))
		
		# id[5] = eyes
		layers.append((f'{self.partsDir}face/eyes/{splitID[5]}.png', True))

		# id[6] = mouth
		if splitID[6] != 'z':
			layers.append((f'{self.partsDir}face/mouths/{splitID[6]}.png', True))

		# id[7] = hat
		if splitID[7] != 'z':
			layers.append((f'{self.partsDir}hats/{splitID[7]}.png', True))

		return layers

	# Based on random parameters, generates a slime ID
	# Returns the ID and background color for rollLayers to use
	def genSlimeID(self):
		# Loops until a unique ID is created
		while True:
			bgColor, altColor = self.getPaintColors()
			id = ''

			# Background [50% solid color, 45% stripes, 5% special]
			bgRoll = random.randint(1, 100)
			if bgRoll > 95:
				# Apply special background
				roll = random.randrange(0, self.specialBgs)
				id += ('2' + self.encodeNum(roll) + 'z')
			elif bgRoll > 50:
				# Apply stripe layer
				id += ('1' + self.encodeNum(bgColor) + self.encodeNum(altColor))
			else:
				# Solid Color
				id += ('0' + self.encodeNum(bgColor) + 'z')

			# Add slime body [90% chance of regular body, 10% special]
			if random.randrange(0, 10):
				roll = random.randrange(0, self.regBodies)
				id += ('0' + self.encodeNum(roll))
			else:
				roll = random.randrange(0, self.specialBodies)
				id += ('1' + self.encodeNum(roll))

			# Eyes
			roll = random.randrange(0, self.eyes)
			id += self.encodeNum(roll)

			# Mouth [80% chance]
			if random.randint(0, 4) != 0:
				roll = random.randrange(0, self.mouths)
				id += self.encodeNum(roll)
			else: id += 'z'

			# Add hat [75% chance of having a hat]
			if random.randint(0, 3) != 0:
				roll = random.randrange(0, self.hats)
				id += self.encodeNum(roll)
			else: id += 'z'

			# Check that ID doesn't exist. If so, leave the loop
			if not exists(self.outputDir + id + '.png'):
				return id, bgColor
			else: print('| DUPE SLIME:', id)

	# Generates a slime
	def genSlime(self, id=None):
		# Check if an ID is given
		if not id:
			id, bg = self.genSlimeID()
		else:
			# Check if it already exists
			if exists(self.outputDir + id + '.png'):
				return None
			else:
				bg = self.decodeChar(id[1])

		layers = self.genSlimeLayers(id)
		return self.rollLayers(self.outputDir + id + '.png', layers, bg), id


	################
	# Bot Commands #
	################

	@commands.command(brief=desc['gen']['short'], description=desc['gen']['long'])
	@commands.cooldown(1, 900, commands.BucketType.user)
	async def gen(self, ctx):
		userID = str(ctx.author.id)
		self.checkUser(userID, ctx.author)

		# Generate slime and get id
		path, id = self.genSlime()

		# Add slime to the database
		ref = self.db.collection(self.collection).document(userID)
		ref.update({'slimes': firestore.ArrayUnion([id])})

		# Make embed and send it
		file = discord.File(path)
		embed = discord.Embed(title=f'slime#{id} was generated!', color=discord.Color.green())
		await ctx.reply(embed=embed, file=file)

		# Upload slime to firebase storage (Takes a second, better to do after response is given)
		bucket = storage.bucket()
		bucketPath = 'dev/' if dev else 'prod/'
		blob = bucket.blob(f'{bucketPath}{id}.png')
		blob.upload_from_filename(path)

	@commands.command(brief=desc['view']['short'], description=desc['view']['long'])
	async def view(self, ctx, arg=None):
		# Check if given id is valid (incredibly insecure)
		if not arg or len(arg) != 8:
			await ctx.reply('I need a valid ID you fucking idiot.', delete_after=5)
			return

		path = f'{self.outputDir}{arg}.png'
		
		# Check if the slime exists
		if not exists(path):
			await ctx.reply(f'**slime#{arg}** doesn\'t exist!')
			return
		
		# Make embed and send it
		file = discord.File(path)
		embed = discord.Embed(title=f'Here\'s slime#{arg}', color=discord.Color.green())
		await ctx.reply(embed=embed, file=file)

	@commands.command(brief=desc['inv']['short'], description=desc['inv']['long'])
	@commands.cooldown(1, 60, commands.BucketType.user)
	async def inv(self, ctx, filter=None):
		perPage = 10
		username = str(ctx.author)[:str(ctx.author).rfind('#')]
		userID = str(ctx.author.id)
		self.checkUser(userID)
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
		if len(filtered) <= perPage:
			embed = embed=discord.Embed(title=f'{username}\'s Inventory', description=self.formatList(filtered, '\n'), color=discord.Color.green())
			embed.set_footer(text=f'{len(filtered)} slime(s)...')
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
			embed=discord.Embed(title=f'{username}\'s Inventory', description=self.formatList(page, '\n'), color=discord.Color.green())
			embed.set_footer(text=f'Slimes {(i * perPage) + 1}-{max} of {len(filtered)}...')
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
		other.replace(' ', '')
		# Check if both users are registerd
		userID = str(ctx.author.id)
		otherID = other[3:-1]

		if userID == otherID:
			await ctx.reply('You can\t trade with yourself.', delete_after=5)
			return
		if not self.checkUser(userID) or not self.checkUser(otherID):
			await ctx.reply('You both need to be registered to trade!', delete_after=5)
			return

		# Basic check on given id's
		if len(slime1) != 8 or len(slime2) != 8:
			await ctx.reply('Given ID\'s need to be valid!', delete_after=5)
			return

		# Check if both users have slimes, including the ones referenced in args
		ref         = self.db.collection(self.collection).document(userID)
		otherRef    = self.db.collection(self.collection).document(otherID)
		slimes      = ref.get().to_dict()['slimes']
		otherSlimes = otherRef.get().to_dict()['slimes']
		if slime1 not in slimes:
			await ctx.reply(f'You don\'t own **{slime1}**!', delete_after=5)
			return
		if slime2 not in otherSlimes:
			await ctx.reply(f'They don\'t own **{slime2}**!', delete_after=5)
			return

		# Check if slimes are favorited:
		favs      = ref.get().to_dict()['favs']
		otherFavs = otherRef.get().to_dict()['favs']
		if slime1 in favs or slime2 in otherFavs:
			await ctx.reply('You can\'t trade favorited slimes!', delete_after=5)
			return

		# Make combined image
		s1img = Image.open(f'{self.outputDir}{slime1}.png')
		s2img = Image.open(f'{self.outputDir}{slime2}.png')
		exchangeImg = Image.open('./res/arrows.png')
		combined = Image.new(mode='RGBA', size=((self.width * 2) + 150, self.width), color=(0, 0, 0, 0))
		combined.paste(s1img, (0, 0))
		combined.paste(exchangeImg, (200, 0))
		combined.paste(s2img, (350, 0))
		fName = f'{self.outputDir}trade_{slime1}_{slime2}.png'
		# Place text
		font = ImageFont.truetype(self.fontPath, 20, encoding='unic')
		fontLen, _ = font.getsize('#' + slime1)
		draw = ImageDraw.Draw(combined)
		draw.text((self.width - fontLen, 0), f"#{slime1}", (0, 0, 0), font=font)
		draw.text((((self.width * 2) + 150) - fontLen, 0), f"#{slime2}", (0, 0, 0), font=font)
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
				
				# Reset slimes stored in firebase storage
				# TODO

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
			await ctx.reply(f'**slime#{id}** has been removed from your favorites!')
		elif len(favs) == 9:
			await ctx.reply('You can only have a max of 9 favorites!')
		else:
			ref.update({'favs': firestore.ArrayUnion([id])})
			await ctx.reply(f'**slime#{id}** has been added to your favorites!')

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
		font = ImageFont.truetype(self.fontPath, 20)
		fontLen,  _ = font.getsize('#' + favs[0])
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
					draw.text(((x + self.width) - fontLen, y), f"#{favs[n]}", (0, 0, 0), font=font)
					n += 1
				else:
					break
		
		# Finish up
		combined.save(fName)
		combined.close()
		file = discord.File(fName)
		await ctx.reply('Here are your favorites!', file=file)
		os.remove(fName)
	
	@commands.command(brief=desc['give']['short'], description=desc['give']['long'])
	@commands.is_owner()
	async def give(self, ctx, other, id):
		userID = str(ctx.author.id)
		otherID = other[3:-1]

		# Do basic checks
		if not self.checkUser(otherID):
			await ctx.reply(f'**{otherID}** needs to be registered.')
			return
		if len(id) != 8:
			await ctx.reply('ID\'s are 8 characters.')
			return
		
		# Generate slime and get id
		path, id = self.genSlime(id)

		if not path:
			await ctx.reply(f'**{id}** isn\'t a valid ID.')
			return

		# Add slime to the database
		ref = self.db.collection(self.collection).document(otherID)
		ref.update({'slimes': firestore.ArrayUnion([id])})

		# Send slime to user
		file = discord.File(path)
		await ctx.reply(f'slime#{id} was given to **{otherID}**!', file=file)

		# Upload slime to firebase storage (Takes a second, better to do after response is given)
		bucket = storage.bucket()
		bucketPath = 'dev/' if dev else 'prod/'
		blob = bucket.blob(f'{bucketPath}{id}.png')
		blob.upload_from_filename(path)


def setup(bot):
	bot.add_cog(Slimes(bot))