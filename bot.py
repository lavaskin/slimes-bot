import json
import sys
import os
from os.path import exists
import random
import discord
from discord.ext import commands
from PIL import Image
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import datetime


##########################################
# Globals Setup (I know globals are bad) #
##########################################

# Load keys
keyFile = open('./other/auth.json', 'r')
keys = json.loads(keyFile.read())
dbCred = credentials.Certificate('./other/firebase.json')

# Global variables
prefix = 'b!'
activity = discord.Activity(type=discord.ActivityType.listening, name="b!help")
bot = commands.Bot(command_prefix=prefix, activity=activity)
width, height = 200, 200
genCooldown = 1800 # in seconds (30m)

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
_specialBgs = countFiles('./res/parts/slimes/backgrounds/special/')
_bodies     = countFiles('./res/parts/slimes/bodies/')
_eyes       = countFiles('./res/parts/slimes/face/eyes/')
_mouths     = countFiles('./res/parts/slimes/face/mouths/')
_hats       = countFiles('./res/parts/slimes/hats/')
_dots       = countFiles('./nfts/dots/')    # Index: 0
_planets    = countFiles('./nfts/planets/') # Index: 1
print(' > Counted files.')

# Initialize database
firebase_admin.initialize_app(dbCred)
db = firestore.client()
print(' > Setup firestore.')


#####################
# Utility Functions #
#####################

# Makes a new document for a user if they aren't registered
def checkUser(author, userID):
	# Check if already registered
	ref = db.collection('users').document(userID)

	if not ref.get().exists:
		# Make document
		data = {'slimes': [],'timestamp': ''}
		ref.set(data)
		print('| Registered: {0} ({1})'.format(author, userID))

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

# Encodes a given slime ID into a more readable compact form
def encodeSlimeID(id):
	enc = ''
	for n in id.split('-'):
		if n == 'X':
			enc += '!'
		else:
			enc += encodeNum(int(n))
	return enc

# Decodes an encoded slime id to the form they're generated as
# Non-public facing
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

# Encodes a single number
def encodeNum(n):
    if n < 10:
        return str(n)
    elif n < 36:
        return chr(n + 55)
    else:
        return chr(n + 61)

# Checks if a pixel's in-bound or not
def checkBounds(x, y, maxX, maxY):
	if x < 0 or x > maxX:
		return False
	if y < 0 or y > maxY:
		return False
	return True

# Draws a circle of a given size at a random location
def drawPlanet(nft, pixels, size, color):
	randX = random.randint(1, nft.size[0] - 2)
	randY = random.randint(1, nft.size[1] - 2)

	halfSize = int(size / 2)

	# Find upper bound
	topLeft = [randX - halfSize, randY - halfSize]
	if topLeft[0] < 0:
		topLeft[0] = 0
	if topLeft[1] < 0:
		topLeft[1] = 0

	# Find lower bound
	botRight = [randX + halfSize, randY + halfSize]
	if botRight[0] > nft.size[0] - 1:
		botRight[0] = nft.size[0]
	if botRight[1] > nft.size[1] - 1:
		botRight[1] = nft.size[1]

	# Draw the planet by filling in-between the bounds
	for i in range(topLeft[0], botRight[0]):
		for j in range(topLeft[1], botRight[1]):
			pixels[i, j] = color

# Generates two different paint colors from the global list (RETURNS THEIR INDEX!)
def getPaintColors():
	colorCount = len(colors)
	c1 = random.randrange(0, colorCount)
	c2 = random.randrange(0, colorCount)

	# Flip paint color if same as bg
	if c1 == c2:
		c1 = colorCount - c1 - 1
	return c1, c2

# Gets the number for the next NFT
def generateNFTNumber(collection):
	if collection == 'dots':
		global _dots
		_dots += 1
		return _dots
	if collection == 'planets':
		global _planets
		_planets += 1
		return _planets

# Generates an nft based on random parameters
def generateNFT(type):
	# Check if argument matches an nft type
	if type == 'slime':
		return genSlime()
	if type == 'planets':
		return genPlanets()
	if type == 'dots':
		return genDots()


########################
# Generation Functions #
########################

# Places layers of randomly chosen elements to make a slime image
def genSlime():
	fName = './nfts/slimes/slimes_'
	partDir = './res/parts/slimes/'

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
			layers.append(('{0}backgrounds/special/{1}.png'.format(partDir, roll), False))
		elif bgRoll > 50:
			# Apply stripe layer
			id += ('1-{0}-{1}-'.format(bgColor, altColor))
			layers.append(('{0}backgrounds/stripes/{1}.png'.format(partDir, altColor), True))
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
		layers.append(('{0}bodies/{1}.png'.format(partDir, roll), True))

		# Eyes
		roll = str(random.randrange(0, _eyes))
		id += (roll + '-')
		layers.append(('{0}face/eyes/{1}.png'.format(partDir, roll), True))

		# Mouth [75% chance]
		if random.randint(0, 3) != 0:
			roll = str(random.randrange(0, _mouths))
			id += (roll + '-')
			layers.append(('{0}face/mouths/{1}.png'.format(partDir, roll), True))
		else: id += 'X-'

		# Add hat [50% chance of having a hat]
		if random.randint(0, 1):
			roll = str(random.randrange(0, _hats))
			id += roll
			layers.append(('{0}hats/{1}.png'.format(partDir, roll), True))
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


# Makes random amounts of planets in various sizes
def genPlanets():
	fName = './nfts/planets/planets_{0}.png'.format(generateNFTNumber('planets'))

	# Generate random parameters
	numPlanets  = random.randint(5, 25)
	randomSizes = random.randint(0, 2) # 1/3 for random sizes
	fixedSize   = random.randrange(5, 39, 2)
	bgColor, paintColor = getPaintColors()

	# Generate the image
	nft = Image.new(mode='RGB', size=(width, height), color=colors[bgColor])
	pixels = nft.load()

	# Place planets
	for i in range(numPlanets):
		if randomSizes == 0:
			drawPlanet(nft, pixels, random.randrange(5, 39, 2), colors[paintColor])
		else:
			drawPlanet(nft, pixels, fixedSize, colors[paintColor])

	nft.save(fName)
	nft.close()

	return fName

# Makes an image with 
def genDots():
	fName = './nfts/dots/dots_{0}.png'.format(generateNFTNumber('dots'))

	# Generate random parameters
	paintChance = random.randint(1, 100)
	bgColor, paintColor = getPaintColors()

	# Generate the image
	nft = Image.new(mode='RGB', size=(width, height), color=colors[bgColor])
	pixels = nft.load()

	# Mix the pixels
	for i in range(1, nft.size[0] - 1):
		for j in range(1, nft.size[1] - 1):
			if random.randint(0, paintChance) == 0:
				pixels[i, j] = colors[paintColor]

	nft.save(fName)
	nft.close()

	return fName


################
# Bot Commands #
################

# Generates an nft and posts it as a reply
@bot.command(brief='Generates an NFT', description='Creates a unique "NFT" and replies to the user with it. 30m cooldown.')
async def gen(ctx, type='slime'):
	userID = str(ctx.author.id)

	checkUser(ctx.author, userID)

	# Check if user has used command recently (with slime)
	if type == 'slime':
		# Get last generated slime and local time
		timestamp = db.collection('users').document(userID).get().to_dict()['timestamp']
		time = datetime.datetime.now().time()
		
		# Figure out if it's been 30 minutes
		# ex: 02:51:25.786564  |  02:51:18.662908
		# TODO

		if timestamp == '...':

			return

	# Get name/id of generated file
	fName   = generateNFT(type)
	nftType = fName[7:fName.rfind('/')]
	id      = fName[fName.rfind('_') + 1:fName.rfind('.')]

	# Add nft to the database
	if type == 'slime':
		ref = db.collection('users').document(userID)
		ref.update({'slimes': firestore.ArrayUnion([id])})
		ref.update({'timestamp': str(datetime.datetime.now().time())})

	# Make embed and send it
	file = discord.File(fName)
	embed = discord.Embed(title='{0}#{1} was generated!'.format(nftType, id))
	embed.set_image(url='attachment://' + fName)
	await ctx.reply(embed=embed, file=file)

# Replies with an embed showing all of a users *slimes*
@bot.command(brief='[WIP] Shows the users inventory')
async def inv(ctx):
	await ctx.reply('This hasn\'t been implemented yet!')

# Views a *slime* given an ID
@bot.command(brief='Shows a given slime', description='Shows the slime corresponding to the given ID.')
async def view(ctx, arg=None):
	# Check if given id is valid (incredibly insecure)
	if not arg or len(arg) != 7:
		await ctx.reply('I need a valid ID you fucking idiot.')
		return

	path = './nfts/slimes/slimes_{0}.png'.format(arg)
	
	# Check if the slime exists
	if not exists(path):
		await ctx.reply('**slimes#{0}** doesn\'t exist!'.format(arg))
		return
	
	# Make embed and send it
	file = discord.File(path)
	embed = discord.Embed(title='Here\'s slimes#' + arg)
	embed.set_image(url='attachment://' + path)
	await ctx.reply(embed=embed, file=file)


#############
# Bot Setup #
#############

@bot.event
async def on_ready():
	random.seed()
	print('> Botty has been turned on:')

def main(genNFTs, amount=100):
	if genNFTs:
		# For generating mass amounts
		for i in range(amount):
			# generateNFT(None)
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