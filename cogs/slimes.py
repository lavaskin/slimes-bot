from ast import alias
import asyncio
import json
import math
import random
import time
import discord
import os
from os.path import exists
from discord.ext import commands
from PIL import Image, ImageFont, ImageDraw
from firebase_admin import credentials, firestore, initialize_app, storage


# ID Constants
ID_BG_VARIENT   = 0
ID_BG_PRIMARY   = 1
ID_BG_SECONDARY = 2
ID_BODY_VARIENT = 3
ID_BODY         = 4
ID_EYES         = 5
ID_MOUTH        = 6
ID_HAT          = 7
# Shop Constants
SLIME_PRICE   = 10
SELLING_RATIO = 1 # Amount to remove from price when selling
RANCH_RATIO   = 3 # Increase in price of slimes bought from the ranch

# Load Descriptions File
descFile = open('./other/commands.json')
desc = json.loads(descFile.read())

# Get Dev Mode
_env = os.getenv('SLIME_DEV', 'True')
_dev = True if _env == 'True' else False
_cd  = 0 if _dev else 1 # Turn off cooldowns in dev


class Slimes(commands.Cog, name='Slimes'):
	def __init__(self, bot):
		# Set random class properties
		self.bot = bot
		self.outputDir = './output/dev/' if _dev else './output/prod/'
		self.width, self.height = 200, 200
		self.fontPath = os.getenv('FONT_PATH', 'consola.ttf')
		self.siteLink = os.getenv('SITE_LINK') if not _dev else 'http://localhost:4200/'
		self.desc = desc # Allow access in functions

		# Init Database
		dbCred = credentials.Certificate('./other/firebase.json')
		self.collection = 'users-dev' if _dev else 'users'
		initialize_app(dbCred, {'storageBucket': os.getenv('STORAGE_BUCKET')})
		self.db = firestore.client()
		self.bucket = storage.bucket()

		# Load colors
		self.colors = []
		with open('./res/colors.txt', 'r') as f:
			for line in f.readlines():
				self.colors.append(line.replace('\n', ''))
				f.close()

		# Load roll parameters
		paramsFile = open('./other/params.json')
		self.params = json.loads(paramsFile.read())
		paramsFile.close()

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

	# Returns the user and db reference for a given user if they exist
	# Else, creates a new user and returns them with a ref
	def getUser(self, ctx, id=None):
		docID = str(ctx.author.id) if id is None else str(id)
		ref = self.db.collection(self.collection).document(docID)
		rawUser = ref.get()
		
		if not rawUser.exists:
			# Create new user. If no author provided, use ID
			data = {'tag': str(ctx.author), 'slimes': [], 'favs': [], 'coins': 100, 'exp': 0, 'pfp': '', 'selling': [], 'lastclaim': 0}
			ref.set(data)

			# Re-fetch user and return
			print(f' > New Registered User: {docID}')
			return ref.get().to_dict(), ref

		# Return the found user and ref
		else:
			return rawUser.to_dict(), ref

	# Given a slime ID, determines how rare it is. Returns its rank and rarity number
	def getRarity(self, id):
		text = 'This slimes rarity is unknown...'
		score = 0

		# Check background (solid is 0, stripes is 1 and special is 4)
		if id[ID_BG_VARIENT] == '1': score += 1
		elif id[ID_BG_VARIENT] == '2': score += 6

		# Check if body is special
		if id[ID_BODY_VARIENT] == '1': score += 8

		# Check if the slime doesn't have eyes
		if id[ID_EYES] == 'z': score += 9

		# Check if it has a mouth
		if id[ID_MOUTH] != 'z': score += 1

		# Check if it has a hat
		if id[ID_HAT] != 'z': score += 1

		if score == 0:
			text = 'This is an **extremely ordinary** slime!'
		elif score < 3:
			text = 'This is a **common** slime.'
		elif score < 6:
			text = 'This is an **uncommon** slime.'
		elif score < 9:
			text = 'This is a **rare** slime!'
		elif score < 12:
			text = 'This is a **pretty rare** slime!'
		elif score < 20:
			text = 'This is a **very rare** slime!!'
		elif score >= 20:
			text = 'This is an :sparkles:**overwhelmingly rare** slime!!!'

		# Get value
		value = int(score * SELLING_RATIO)
		value = 1 if value == 0 else value # Pity points

		return text, score, value

	# Test if a given parameter randomly passes
	def passesParam(self, param):
		return random.randint(1, 100) < (self.params[param] * 100)

	# Favorites a given slime or removes it if already favorited
	def favSlime(self, id, ref, favs):
		# Check if already in favorites and if favorites are maxed out
		if id in favs:
			ref.update({'favs': firestore.ArrayRemove([id])})
			return f'**{id}** has been removed from your favorites!'
		elif len(favs) == 9:
			return 'You can only have a max of 9 favorites!'
		else:
			ref.update({'favs': firestore.ArrayUnion([id])})
			return f'**{id}** has been added to your favorites!'

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

	# Encodes a single number
	def encodeNum(self, n):
		if n < 10:
			return str(n)
		if n < 36:
			return chr(n + 55)
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

	# Makes a 3x3 grid of slimes and returns the path to the output image
	def makeCollage(self, ctx, slimes):
		userID = ctx.author.id
		numFavs = len(slimes)
		font = ImageFont.truetype(self.fontPath, 20)
		fontLen,  _ = font.getsize('#' + slimes[0])
		width = (3 * self.width) if numFavs > 2 else numFavs * self.width
		height = math.ceil(numFavs / 3) * self.height
		n = 0
		combined = Image.new(mode='RGBA', size=(width, height), color=(0, 0, 0, 0))
		draw = ImageDraw.Draw(combined)
		fName = f'{self.outputDir}{random.randint(100000, 999999)}_{userID}.png'

		for y in range(0, height, self.height):
			for x in range(0, width, self.width):
				if n < numFavs:
					img = Image.open(f'{self.outputDir}{slimes[n]}.png')
					combined.paste(img, (x, y))
					draw.text(((x + self.width) - fontLen, y), f"#{slimes[n]}", (0, 0, 0), font=font)
					n += 1
				else:
					break
		
		# Finish up
		combined.save(fName)
		combined.close()
		return fName

	def timeSince(self, date):
		return math.ceil(time.time() - date)

	# Retuns the minutes, seconds of a time in seconds
	def convertTime(self, secs):
		minutes = int(secs / 60)
		seconds = int(secs % 60)
		return minutes, seconds

	# Returns an object of (claimed coins, error message)
	def claimCoins(self, ref, user):
		coins = int(user['coins'])

		# Check coin count
		if coins >= 9999:
			return 0, 'You have reached the maximum amount of claimable coins!'

		# Check cooldown
		since = self.timeSince(user['lastclaim'])
		left = (desc['claim']['cd'] - since) * _cd
		if left > 0:
			minutes, seconds = self.convertTime(left)
			return 0, f'There\'s *{minutes}m, {seconds}s* left before you can claim coins again!'

		# Calc payout
		# Every 1000 coins collected, lower the payout amount by 10% (Minimum of 10% payout))
		# Only triggers over 500 coins
		payout = 40 + random.randint(-SLIME_PRICE, SLIME_PRICE)
		multiplier = max(round(1 - round((coins / 1000) * 0.1, 3), 3), 0.1) if coins > 500 else 1
		payout = math.ceil(payout * multiplier)

		ref.update({'coins': firestore.Increment(payout), 'lastclaim': time.time()})
		return payout, None

	# Returns the users level given their xp, and their % to the next level
	def calculateLevel(self, xp) -> tuple:
		level = round((0.25 * math.sqrt(xp)) + 1, 2)
		lo = math.floor(level)
		percent = int(round((level - lo) * 100, 2))
		return lo, percent

	def checkID(self, id: str, filter=False) -> bool:
		if not id: return False

		validChars = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
		if filter: validChars += '?'

		if len(id) != 8:
			return False
		for i in id:
			if i not in validChars:
				return False
		return True

	def getRanchPrice(self, value: int) -> int:
		return math.ceil(value * RANCH_RATIO)

	def getSlimesInRanch(self) -> list:
		ranchRef = self.db.collection(self.collection).document('ranch')
		return ranchRef.get().to_dict()['slimes']

	def sendToRanch(self, slimes: list):
		ranchRef = self.db.collection(self.collection).document('ranch')
		ranchRef.update({'slimes': firestore.ArrayUnion(slimes)})

	def checkIfInRanch(self, slime: str) -> bool:
		ranchRef = self.db.collection(self.collection).document('ranch')
		ranch = ranchRef.get().to_dict()['slimes']
		return slime in ranch

	def removeFromRanch(self, id: str):
		ranchRef = self.db.collection(self.collection).document('ranch')
		ranchRef.update({'slimes': firestore.ArrayRemove([id])})

	def filterSlimes(self, slimes: list, filter: str):
		if not slimes: return []

		# Filter slimes
		filtered = []
		if filter:
			for slime in slimes:
				if self.passesFilter(filter, slime):
					filtered.append(slime)
		else:
			filtered = slimes

		return filtered

	def buildPages(self, slimes: list, title: str, url='') -> list:
		if not slimes: return []

		# Put into pages of embeds
		pages = []
		perPage = 10
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
			embed=discord.Embed(title=title, description=self.formatList(page, '\n'), url=url, color=discord.Color.green())
			embed.set_footer(text=f'Slimes {(i * perPage) + 1}-{max} of {len(slimes)}...')
			pages.append(embed)

		return pages

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
		if splitID[ID_BG_VARIENT] == 1:
			layers.append((f'{self.partsDir}backgrounds/stripes/{splitID[ID_BG_SECONDARY]}.png', True))
		elif splitID[ID_BG_VARIENT] == 2:
			layers.append((f'{self.partsDir}backgrounds/special/{splitID[ID_BG_PRIMARY]}.png', False))

		# id[3] = body varient (0 = normal, 1 = special)
		# id[4] = body
		if splitID[ID_BODY_VARIENT] == 0:
			layers.append((f'{self.partsDir}bodies/regular/{splitID[ID_BODY]}.png', True))
		elif splitID[ID_BODY_VARIENT] == 1:
			layers.append((f'{self.partsDir}bodies/special/{splitID[ID_BODY]}.png', True))
		
		# id[5] = eyes
		if splitID[ID_EYES] != 'z':
			layers.append((f'{self.partsDir}face/eyes/{splitID[ID_EYES]}.png', True))
			
			# id[6] = mouth (Only possible if the slime has eyes)
			if splitID[ID_MOUTH] != 'z':
				layers.append((f'{self.partsDir}face/mouths/{splitID[ID_MOUTH]}.png', True))

		# id[7] = hat
		if splitID[ID_HAT] != 'z':
			layers.append((f'{self.partsDir}hats/{splitID[ID_HAT]}.png', True))

		return layers

	# Based on random parameters, generates a slime ID
	# Returns the ID and background color for rollLayers to use
	def genSlimeID(self):
		# Loops until a unique ID is created
		while True:
			bgColor, altColor = self.getPaintColors()
			id = ''

			# Choose background
			if self.passesParam('bg_special'):
				# Apply special background
				roll = random.randrange(0, self.specialBgs)
				id += ('2' + self.encodeNum(roll) + 'z')
			elif self.passesParam('bg_stripes'):
				# Apply stripe layer
				id += ('1' + self.encodeNum(bgColor) + self.encodeNum(altColor))
			else:
				# Solid Color
				id += ('0' + self.encodeNum(bgColor) + 'z')

			# Add slime body
			if self.passesParam('bg_special'):
				roll = random.randrange(0, self.specialBodies)
				id += ('1' + self.encodeNum(roll))
			else:
				roll = random.randrange(0, self.regBodies)
				id += ('0' + self.encodeNum(roll))

			# Eyes
			if self.passesParam('eyes'):
				roll = random.randrange(0, self.eyes)
				id += self.encodeNum(roll)

				# Mouth (Can only be applied if the slime has eyes)
				if self.passesParam('mouth'):
					roll = random.randrange(0, self.mouths)
					id += self.encodeNum(roll)
				else: id += 'z'
			else: id += 'zz' # For both eyes and mouth

			# Hat
			if self.passesParam('hat'):
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

	@commands.command(brief=desc['claim']['short'], description=desc['claim']['long'], aliases=desc['claim']['alias'])
	@commands.cooldown(1, 0, commands.BucketType.user)
	async def claim(self, ctx):
		user, ref = self.getUser(ctx)

		# Get Payout
		payout, err = self.claimCoins(ref, user)

		if err != None:
			await ctx.reply(err, delete_after=10)
		else:
			newBal = int(user['coins'] + payout)
			await ctx.reply(f'You collected **{payout}** coins! You now have **{newBal}**.')

	@commands.command(brief=desc['generate']['short'], description=desc['generate']['long'], aliases=desc['generate']['alias'])
	@commands.cooldown(1, desc['generate']['cd'] * _cd, commands.BucketType.user)
	async def generate(self, ctx, count=1):
		user, ref = self.getUser(ctx)

		# Check if count is between 1 and 99
		if int(count) < 1 or int(count) > 99:
			await ctx.reply('You can only generate between 1 and 99 slimes at a time.', delete_after=5)
			return

		# Check if user has enough coins
		coins = user['coins']
		desc = ''
		if coins < SLIME_PRICE * count:
			# Try to claim coins
			payout, err = self.claimCoins(ref, user)
			if err != None:
				# Get time left till next claim
				since = self.timeSince(user['lastclaim'])
				mins, secs = self.convertTime(self.desc['claim']['cd'] - since)

				await ctx.reply(f'You need **{SLIME_PRICE * count - coins}** more coins! You can get more in *{mins}m, {secs}s*.', delete_after=10)
				return
			else:
				desc = f'You claimed {payout} coins!\n'
				coins = user['coins'] + payout
		
		# Change count to the amount the user can afford
		if coins < SLIME_PRICE * count:
			count = int(coins / SLIME_PRICE)

		# Generate slimes
		slimes = []
		totalRarity = 0
		for _ in range(int(count)):
			generatedSlime = self.genSlime()
			slimes.append(generatedSlime)
			totalRarity += self.getRarity(generatedSlime[1])[1]

		# Add slimes to the database
		slimeIDs = []
		for slime in slimes:
			slimeIDs.append(slime[1])
		ref.update({'slimes': firestore.ArrayUnion(slimeIDs)})

		# Update balance
		ref.update({'coins': firestore.Increment(-SLIME_PRICE * count)})
		balance = f':coin: *{int(coins - SLIME_PRICE * count)} left...*'

		# A single slime response
		if count == 1:
			slime = slimes[0]

			# Get rarity text
			rarityText = self.getRarity(slime[1])[0] + '\n\n'

			# Make embed and send it
			file = discord.File(slime[0])
			embed = discord.Embed(title=f'Generated **{slime[1]}**', description=rarityText + desc + balance, color=discord.Color.green())
			await ctx.reply(embed=embed, file=file)
		
		# Multiple slimes response
		else:
			# Sort slimes by rarity and get top 9 (only if amount generated > 9)
			if (len(slimeIDs) > 9):
				slimeIDs.sort(key=lambda x: self.getRarity(x)[1], reverse=True)
				slimeIDs = slimeIDs[:9]

			# Make collage of generated slimes
			collage = self.makeCollage(ctx, slimeIDs)

			# Make embed and send it
			file = discord.File(collage)
			titleAddendum = '' if len(slimes) < 10 else ' (Top 9)'
			embed = discord.Embed(title=f'Generated {count} slimes{titleAddendum}', description=desc + balance, color=discord.Color.green())
			await ctx.reply(embed=embed, file=file)
			os.remove(collage)

		# Update EXP based on slime rarity
		oldLevel = self.calculateLevel(user['exp'])[0]
		newLevel = self.calculateLevel(user['exp'] + totalRarity)[0]
		ref.update({'exp': firestore.Increment(totalRarity)})

		# If the user leveled up, send a message and give them coins based on the new level
		if newLevel > oldLevel:
			# Calc the amount to give accounting for multiple level-ups with one pull
			levelBonus = 0
			for i in range(oldLevel, newLevel):
				levelBonus += min(int((i * 0.5) * 100), 500)
			ref.update({'coins': firestore.Increment(levelBonus)})
			await ctx.reply(f'You leveled up to **Level {newLevel}**! Here\'s **{levelBonus}** :coin: as a bonus!')

		# Upload slimes to firebase storage (Takes a second, better to do after response is given)
		bucket = storage.bucket()
		bucketPath = 'dev/' if _dev else 'prod/'
		for slime in slimes:
			blob = bucket.blob(f'{bucketPath}{slime[1]}.png')
			blob.upload_from_filename(slime[0])

	@commands.command(brief=desc['view']['short'], description=desc['view']['long'], aliases=desc['view']['alias'])
	@commands.cooldown(1, desc['view']['cd'] * _cd, commands.BucketType.user)
	async def view(self, ctx, id=None):
		# Check if given id is valid (incredibly insecure)
		if not self.checkID(id):
			await ctx.reply('I need a valid ID!', delete_after=5)
			return

		path = f'{self.outputDir}{id}.png'
		
		# Check if the slime exists
		if not exists(path):
			await ctx.reply(f'**{id}** doesn\'t exist!')
			return
		
		# Make embed and send it
		file = discord.File(path)
		await ctx.reply(file=file)

	@commands.command(brief=desc['inventory']['short'], description=desc['inventory']['long'], aliases=desc['inventory']['alias'])
	@commands.cooldown(1, desc['inventory']['cd'] * _cd, commands.BucketType.user)
	async def inventory(self, ctx, filter=None):
		user, _ = self.getUser(ctx)
		slimes = user['slimes']
		favs = user['favs']

		# Check if id is valid
		if filter and not self.checkID(filter, True):
			await ctx.reply('I need a valid ID!', delete_after=5)
			return

		# Filter slimes
		slimes = self.filterSlimes(slimes, filter)

		# Remove favs from slimes, add star to favs
		for i in range(len(favs)):
			slimes.remove(favs[i])
			favs[i] = f':star: {favs[i]}'
		allSlimes = favs + slimes
		
		# Create the URL to the site
		siteAdd = self.siteLink + f'inventory/{ctx.author.id}'
		siteAdd = siteAdd + '?filter=' + filter if filter else siteAdd

		# Build the username
		username = str(ctx.author)[:str(ctx.author).rfind('#')]

		# Put into pages of embeds
		pages = self.buildPages(allSlimes, f'{username}\'s Inventory', siteAdd)
		if not pages:
			await ctx.reply('No slimes available!', delete_after=5)
			return

		# Setup embed for reactions
		msg = await ctx.reply(embed=pages[0])
		buttons = ['⏮️', '⬅️', '➡️', '⏭️']
		for button in buttons:
			await msg.add_reaction(button)

		cur = 0
		while True:
			try:
				reaction, _ = await self.bot.wait_for('reaction_add', check=lambda reaction, user: user == ctx.author and reaction.emoji in buttons, timeout=10.0)
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

	@commands.command(brief=desc['trade']['short'], description=desc['trade']['long'], aliases=desc['trade']['alias'])
	@commands.cooldown(1, desc['trade']['cd'] * _cd, commands.BucketType.user)
	@commands.guild_only()
	async def trade(self, ctx, other_person, your_slime, their_slime):
		# Remove whitespace from id and format arguments to make sense in s!help usage
		other = other_person.replace(' ', '')
		
		# Check if both users are registerd
		idOne = str(ctx.author.id)
		idTwo = other[2:-1]

		# Check if the ID's are equal and valid
		if idOne == idTwo:
			await ctx.reply('You can\t trade with yourself.', delete_after=5)
			return
		if len(idTwo) != 18:
			await ctx.reply('Invalid user!', delete_after=5)
			return

		userOne, refOne = self.getUser(ctx)
		userTwo, refTwo = self.getUser(ctx, idTwo) # This is very unsafe !

		# Check if both users have slimes, including the ones referenced in args
		slimesOne = userOne['slimes']
		slimesTwo = userTwo['slimes']
		if your_slime not in slimesOne:
			await ctx.reply(f'You don\'t own **{your_slime}**!', delete_after=5)
			return
		if their_slime not in slimesTwo:
			await ctx.reply(f'They don\'t own **{their_slime}**!', delete_after=5)
			return

		# Check if slimes are favorited:
		favsOne = userOne['favs']
		favsTwo = userTwo['favs']
		if your_slime in favsOne or their_slime in favsTwo:
			await ctx.reply('You can\'t trade favorited slimes!', delete_after=5)
			return

		# Make combined image
		s1img = Image.open(f'{self.outputDir}{your_slime}.png')
		s2img = Image.open(f'{self.outputDir}{their_slime}.png')
		exchangeImg = Image.open('./res/arrows.png')
		combined = Image.new(mode='RGBA', size=((self.width * 2) + 150, self.width), color=(0, 0, 0, 0))
		combined.paste(s1img, (0, 0))
		combined.paste(exchangeImg, (200, 0))
		combined.paste(s2img, (350, 0))
		fName = f'{self.outputDir}trade_{your_slime}_{their_slime}.png'
		# Place text
		font = ImageFont.truetype(self.fontPath, 20, encoding='unic')
		fontLen, _ = font.getsize('#' + your_slime)
		draw = ImageDraw.Draw(combined)
		draw.text((self.width - fontLen, 0), f"#{your_slime}", (0, 0, 0), font=font)
		draw.text((((self.width * 2) + 150) - fontLen, 0), f"#{their_slime}", (0, 0, 0), font=font)
		# Save image
		combined.save(fName)
		combined.close()
		file = discord.File(fName)

		# Post trade request
		buttons = ['✔️', '❌']
		msg = await ctx.send(f'{other}: <@{idOne}> wants to trade their **{your_slime}** for your **{their_slime}**. Do you accept?', file=file)
		os.remove(fName)
		for button in buttons:
			await msg.add_reaction(button)

		# Process message reaction
		try:
			reaction, user = await self.bot.wait_for("reaction_add", check=lambda reaction, user: user.id == int(idTwo) and reaction.emoji in buttons, timeout=45.0)
		except asyncio.TimeoutError:
			return
		else:
			if reaction.emoji == buttons[0]:
				await ctx.send('The trade has been accepted!')

				# Add new slimes
				refOne.update({'slimes': firestore.ArrayUnion([their_slime])})
				refTwo.update({'slimes': firestore.ArrayUnion([your_slime])})

				# Remove traded slimes
				refOne.update({'slimes': firestore.ArrayRemove([your_slime])})
				refTwo.update({'slimes': firestore.ArrayRemove([their_slime])})

				# Update trade message
				await msg.edit(content=f'The trade has been accepted!\n**{your_slime}** :arrow_right: **{user}**\n**{their_slime}** :arrow_right: **{ctx.author}**')
			elif reaction.emoji == buttons[1]:
				await ctx.send('The trade has been declined!')

	@commands.command(brief=desc['favorite']['short'], description=desc['favorite']['long'], aliases=desc['favorite']['alias'])
	@commands.cooldown(1, desc['favorite']['cd'] * _cd, commands.BucketType.user)
	async def favorite(self, ctx, id=None):
		# Get user data
		user, ref = self.getUser(ctx)
		slimes = user['slimes']

		if not slimes:
			await ctx.reply('You have no slimes to favorite!', delete_after=5)
			return

		# Check if an id is provided or if they own it
		if not id:
			# Use most recently generated slime as id
			id = slimes[-1]

		# Check parameter validity
		if not self.checkID(id):
			await ctx.reply('Invalid slime ID!', delete_after=5)
			return
		if id not in slimes:
			await ctx.reply('You don\'t own this slime!', delete_after=5)
			return

		res = self.favSlime(id, ref, user['favs'])
		await ctx.reply(res)

	@commands.command(brief=desc['favorites']['short'], description=desc['favorites']['long'], aliases=desc['favorites']['alias'])
	@commands.cooldown(1, desc['favorites']['cd'] * _cd, commands.BucketType.user)
	async def favorites(self, ctx, clear=None):
		user, ref = self.getUser(ctx)
		
		# Check if they have slimes
		if not user['slimes']:
			await ctx.reply('You have no slimes!', delete_after=5)
			return

		# Check if they have any favs
		favs = user['favs']
		if not favs:
			await ctx.reply('You don\'t have any favs!')
			return

		# Remove all favs from current user
		if clear in ['c', 'clear']:
			ref.update({'favs': []})
			await ctx.reply('Your favorites were reset.')
			return

		collage = self.makeCollage(ctx, favs)
		file = discord.File(collage)
		await ctx.reply('Here are your favorites!', file=file)
		os.remove(collage)
	
	@commands.command(brief=desc['give']['short'], description=desc['give']['long'], aliases=desc['give']['alias'])
	@commands.cooldown(1, desc['give']['cd'] * _cd, commands.BucketType.user)
	@commands.is_owner()
	async def give(self, ctx, other, id):
		other.replace(' ', '')
		userID = other[2:-1]
		_, ref = self.getUser(ctx, userID)

		# Check for a valid ID
		if not self.checkID(id):
			await ctx.reply('Invalid ID!', delete_after=5)
			return
		
		# Generate slime and get id
		path, id = self.genSlime(id)

		if not path:
			await ctx.reply(f'**{id}** isn\'t a valid ID.')
			return

		# Add slime to the database
		ref.update({'slimes': firestore.ArrayUnion([id])})

		# Send slime to user
		file = discord.File(path)
		await ctx.reply(f'**{id}** was given to **{userID}**!', file=file)

		# Upload slime to firebase storage (Takes a second, better to do after response is given)
		bucket = storage.bucket()
		bucketPath = 'dev/' if _dev else 'prod/'
		blob = bucket.blob(f'{bucketPath}{id}.png')
		blob.upload_from_filename(path)

	@commands.command(brief=desc['rarity']['short'], description=desc['rarity']['long'], aliases=desc['rarity']['alias'])
	@commands.cooldown(1, desc['rarity']['cd'] * _cd, commands.BucketType.user)
	async def rarity(self, ctx, id=None):
		# Check if given id is valid
		if not self.checkID(id):
			await ctx.reply('I need a valid ID!', delete_after=5)
			return

		# Get data
		text, score, _ = self.getRarity(id)

		# Send embed response
		embed = discord.Embed(title=f'{id}\'s Rarity', description=text + f' (Score of {score})', color=discord.Color.green())
		await ctx.reply(embed=embed)

	@commands.command(brief=desc['rarities']['short'], description=desc['rarities']['long'], aliases=desc['rarities']['alias'])
	@commands.cooldown(1, desc['rarities']['cd'] * _cd, commands.BucketType.user)
	async def rarities(self, ctx):
		rarities = [
			'Extremely Ordinary',
			'Common',
			'Uncommon',
			'Rare',
			'Pretty Rare',
			'Very Rare',
			':sparkles: Overwhelmingly Rare',
		]

		embed = discord.Embed(title='Slime bRarities', description='\n'.join(rarities), color=discord.Color.green())
		await ctx.reply(embed=embed)

	@commands.command(brief=desc['top']['short'], description=desc['top']['long'], aliases=desc['top']['alias'])
	@commands.cooldown(1, desc['top']['cd'] * _cd, commands.BucketType.user)
	async def top(self, ctx, num=10):
		user, _ = self.getUser(ctx)
		slimes = user['slimes']
		if not slimes:
			await ctx.reply('You have no slimes!', delete_after=5)
			return

		if num > 20:
			await ctx.reply('You can only check your top 20!', delete_after=5)
			return

		# Get rarities
		rarities = [(self.getRarity(slime)[1], slime) for slime in slimes]
		rarities.sort(reverse=True)
		rarities = rarities[:num]

		# Send embed response
		embed = discord.Embed(title=f'{ctx.author.name}\'s Top {num} Slimes', color=discord.Color.green())
		for i, (score, slime) in enumerate(rarities):
			embed.add_field(name=f'#{i + 1}', value=f'{slime} (Score of {score})')
		await ctx.reply(embed=embed)

	@commands.command(brief=desc['sell']['short'], description=desc['sell']['long'], aliases=desc['sell']['alias'])
	@commands.cooldown(1, desc['sell']['cd'] * _cd, commands.BucketType.user)
	async def sell(self, ctx, id=None):
		# Get user info
		user, ref = self.getUser(ctx)
		slimes = user['slimes']
		coins = user['coins']
		favs = user['favs']

		# Check if they own slimes
		if not slimes:
			await ctx.reply('You have no slimes to sell!', delete_after=5)
			return

		# No id is provided
		if not id:
			# Select most recent slime if no id is given
			# Don't use favs
			idx = len(slimes) - 1
			while idx >= 0 and slimes[idx] in favs:
				idx -= 1
			id = slimes[idx]
		
		# They provide an id...
		else:
			# Check if id is valid
			if not self.checkID(id):
				await ctx.reply('I need a valid ID!', delete_after=5)
				return
			# Check if they own it
			if id not in slimes:
				await ctx.reply('You don\'t own that slime!', delete_after=5)
				return
			# Check if its favorited
			if id in favs:
				await ctx.reply('You can\'t sell favorited slimes!', delete_after=5)
				return

		# Get slimes value
		value = self.getRarity(id)[2]

		# Build response
		buttons = ['✔️', '❌']
		path = f'{self.outputDir}{id}.png'
		file = discord.File(path)
		msg = await ctx.reply(f'Are you sure you want to sell **{id}** for {value} coin(s)?', file=file)
		for button in buttons: await msg.add_reaction(button)

		# Process response
		try:
			response, _ = await self.bot.wait_for('reaction_add', check=lambda reaction, user: user == ctx.author and reaction.emoji in buttons, timeout=10.0)
		except asyncio.TimeoutError:
			return
		else:
			# Sell the slime
			if response.emoji == buttons[0]:
				ref.update({'slimes': firestore.ArrayRemove([id]) ,'coins': firestore.Increment(value)})
				s = 's' if value > 1 else ''
				await msg.edit(content=f'**{id}** was sold for {value} coin{s} (*New Balance: {int(coins + value)}*)!')

				# Send the slime to the ranch
				self.sendToRanch([id])

			# Don't sell
			elif response.emoji == buttons[1]:
				await msg.edit(content='You turned away the offer.')


	@commands.command(brief=desc['bulksell']['short'], description=desc['bulksell']['long'], aliases=desc['bulksell']['alias'])
	@commands.cooldown(1, desc['bulksell']['cd'] * _cd, commands.BucketType.user)
	async def bulksell(self, ctx, parameter=None, num=None):
		validParameters = ['last', 'rarity', 'all']

		# Check if the user used a valid parameter
		if not parameter or parameter not in validParameters:
			await ctx.reply('You need to specify a valid parameter!', delete_after=5)
			return

		# Check if the user gave a valid number if the parameter needs it
		if parameter == 'last' or parameter == 'rarity':
			if not num or not num.isdigit():
				await ctx.reply('You need to specify a valid number!', delete_after=5)
				return
				
			# Turn num into an int and check if its valid
			num = int(num)
			if num <= 0 or num > 9999:
				await ctx.reply('The max range is 1 -> 9999!', delete_after=5)
				return

		# Get user information
		user, ref = self.getUser(ctx)
		slimes = user['slimes']
		favs = user['favs']
		coins = int(user['coins'])

		# Remove favorites from the list of slimes, then check if they have any
		for fav in favs: slimes.remove(fav)
		if not slimes:
			await ctx.reply('You have no slimes to sell!', delete_after=5)
			return

		# Get the slimes to sell and their values
		toSell = []
		saleValue = 0
		if parameter == 'last':
			# Check if the user has enough slimes
			if len(slimes) < num:
				await ctx.reply(f'You don\'t have {num} slimes!', delete_after=5)
				return

			# Get the last num slimes
			toSell = slimes[-num:]
			for slime in toSell:
				saleValue += self.getRarity(slime)[2]

		elif parameter == 'rarity':
			# Get the slimes under/equal to the given rarity
			for slime in slimes:
				_, rarity, value = self.getRarity(slime)
				if rarity < num:
					toSell.append(slime)
					saleValue += value

		elif parameter == 'all':
			toSell = slimes
			for slime in toSell:
				saleValue += self.getRarity(slime)[2]

		else:
			await ctx.reply('Something went wrong...', delete_after=5)
			return

		if not toSell:
			await ctx.reply('No slimes matched your parameter!', delete_after=5)
			return

		# Build response
		buttons = ['✔️', '❌']
		msg = await ctx.reply(f'Are you sure you want to sell {len(toSell)} slime(s) for **{saleValue}** coin(s)?')
		for button in buttons: await msg.add_reaction(button)

		# Process response
		try:
			reaction, _ = await self.bot.wait_for("reaction_add", check=lambda reaction, user: user == ctx.author and reaction.emoji in buttons, timeout=10.0)
		except asyncio.TimeoutError:
			return
		else:
			if reaction.emoji == buttons[0]:
				# Sell slimes
				ref.update({'slimes': firestore.ArrayRemove(toSell), 'coins': firestore.Increment(saleValue)})

				await msg.edit(content=f'**{len(toSell)}** slime(s) were sold for {saleValue} coin(s) (*New Balance: {coins + saleValue}*)!')

				# Send the slimes to the ranch
				self.sendToRanch(toSell)
			elif reaction.emoji == buttons[1]:
				await msg.edit(content='Your slimes are safe!')

	@commands.command(brief=desc['balance']['short'], description=desc['balance']['long'], aliases=desc['balance']['alias'])
	@commands.cooldown(1, desc['balance']['cd'] * _cd, commands.BucketType.user)
	async def balance(self, ctx):
		user, _ = self.getUser(ctx)
		coins = int(user['coins'])
		
		await ctx.reply(f'You have **{coins}** :coin:, that\'s worth like {int(coins / SLIME_PRICE)} slime(s)!')


	@commands.command(brief=desc['profile']['short'], description=desc['profile']['long'], aliases=desc['profile']['alias'])
	@commands.cooldown(1, desc['profile']['cd'] * _cd, commands.BucketType.user)
	async def profile(self, ctx):
		user, ref = self.getUser(ctx)
		
		# Get user data
		slimes = user['slimes']
		coins = int(user['coins'])
		favs = user['favs']
		exp = user['exp']
		level = self.calculateLevel(exp)[0]

		# Loop through slimes to gather statistics
		totalValue = 0
		averageRarity = 0
		highestRarity = ('', 0)

		for slime in slimes:
			_, rarity, value = self.getRarity(slime)
			if rarity > highestRarity[1]: highestRarity = (slime, rarity)
			averageRarity += rarity
			totalValue += value

		averageRarity = averageRarity / len(slimes) if len(slimes) > 0 else 0
		averageRarity = round(averageRarity, 1)

		# Update tag in db
		ref.update({'tag': str(ctx.author)})

		# Build response
		embed = discord.Embed(title=f'{ctx.author.name}\'s Profile', color=discord.Color.green())
		embed.set_thumbnail(url=ctx.author.display_avatar)
		embed.add_field(name='Level', value=level)
		embed.add_field(name='Total Slimes', value=f'{len(slimes)}')
		embed.add_field(name='Coins', value=f'{coins}')
		embed.add_field(name='Number of Favorites', value=f'{len(favs)}')
		embed.add_field(name='Total Value', value=f'{math.ceil(totalValue)} :coin:')
		embed.add_field(name='Average Rarity', value=f'{averageRarity}')
		if highestRarity[0]: embed.add_field(name='Rarest Slime', value=f'{highestRarity[0]} ({highestRarity[1]})')
		await ctx.reply(embed=embed)

	@commands.command(brief=desc['level']['short'], description=desc['level']['long'], aliases=desc['level']['alias'])
	@commands.cooldown(1, desc['level']['cd'] * _cd, commands.BucketType.user)
	async def level(self, ctx):
		user, _ = self.getUser(ctx)
		slimes = user['slimes']
		if not slimes:
			await ctx.reply('Generate a slime to start getting EXP!', delete_after=5)
			return

		exp = user['exp']
		level, toNext = self.calculateLevel(exp)

		# Get the number of full bars
		fullBars = int(toNext / 10)
		emptyBars = 10 - fullBars
		progressBar = ':green_square:' * fullBars + ':white_large_square:' * emptyBars

		# Build response
		embed = discord.Embed(title=f'{ctx.author.name}\'s Level', color=discord.Color.green())
		embed.add_field(name='Level', value=f'{level}')
		embed.add_field(name='EXP', value=f'{toNext}%')
		embed.add_field(name='Progress', value=f'{progressBar}')
		await ctx.reply(embed=embed)

	@commands.command(brief=desc['adopt']['short'], description=desc['adopt']['long'], aliases=desc['adopt']['alias'])
	@commands.cooldown(1, desc['adopt']['cd'] * _cd, commands.BucketType.user)
	async def adopt(self, ctx, id=None):
		user, ref = self.getUser(ctx)

		# Check if the id's valid
		if not self.checkID(id):
			await ctx.reply('Invalid ID!', delete_after=5)
			return

		# Check if in ranch
		if not self.checkIfInRanch(id):
			await ctx.reply(f'**{id}** isn\'t in the ranch!', delete_after=5)
			return
		
		price = self.getRanchPrice(self.getRarity(id)[2])
		coins = int(user['coins'])
		if coins < price:
			await ctx.reply(f'You don\'t have enough coins to adopt that slime! ({price} :coin:)', delete_after=5)
			return
		
		# Make yes/no buttons for confirmation
		buttons = ['✔️', '❌']
		path = f'{self.outputDir}{id}.png'
		file = discord.File(path)
		msg = await ctx.reply(f'Are you sure you want to adopt **{id}** for {price} :coin:?', file=file)
		for button in buttons:
			await msg.add_reaction(button)
		
		# Wait for a response
		try:
			reaction, user = await self.bot.wait_for('reaction_add', timeout=30, check=lambda reaction, user: user == ctx.author and str(reaction.emoji) in buttons)
		except asyncio.TimeoutError:
			return
		else:
			# Reject adoption
			if str(reaction.emoji) == buttons[1]:
				await ctx.reply(f'Decided to not adopt *{id}*...', delete_after=5)

			# Adopt the slime
			elif str(reaction.emoji) == buttons[0]:
				# Update db
				ref.update({'coins': coins - price, 'slimes': firestore.ArrayUnion([id])})
				self.removeFromRanch(id)
				await ctx.reply(f'You adopted **{id}**!', delete_after=5)

	@commands.command(brief=desc['ranch']['short'], description=desc['ranch']['long'], aliases=desc['ranch']['alias'])
	@commands.cooldown(1, desc['ranch']['cd'] * _cd, commands.BucketType.user)
	async def ranch(self, ctx, filter=None):
		slimes = self.getSlimesInRanch()

		# Check if id is valid
		if filter and not self.checkID(filter, True):
			await ctx.reply('I need a valid ID!', delete_after=5)
			return

		# Filter slimes
		slimes = self.filterSlimes(slimes, filter)

		# Build ranch URL
		siteAdd = self.siteLink + f'ranch'
		siteAdd = siteAdd + '?filter=' + filter if filter else siteAdd

		pages = self.buildPages(slimes, 'The Ranch', siteAdd)
		if not pages:
			await ctx.reply('No slimes available!', delete_after=5)
			return

		# Setup embed for reactions
		msg = await ctx.reply(embed=pages[0])
		buttons = ['⏮️', '⬅️', '➡️', '⏭️']
		for button in buttons:
			await msg.add_reaction(button)

		cur = 0
		while True:
			try:
				reaction, _ = await self.bot.wait_for('reaction_add', check=lambda reaction, user: user == ctx.author and reaction.emoji in buttons, timeout=10.0)
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

	@commands.command(brief=desc['reset']['short'], description=desc['reset']['long'], aliases=desc['reset']['alias'])
	@commands.cooldown(1, desc['reset']['cd'] * _cd, commands.BucketType.user)
	async def reset(self, ctx):
		user, ref = self.getUser(ctx)
		slimes = user['slimes']
		if not slimes:
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
				# Send all the users slimes to the ranch
				self.sendToRanch(slimes)

				# Reset slimes stored on server
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


async def setup(bot):
	await bot.add_cog(Slimes(bot))