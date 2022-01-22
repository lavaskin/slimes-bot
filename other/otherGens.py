# Contains older NFT generation methods that are now deprecated.
# This file is just to hold functions, they won't work by themselves
# The last remnants of the old version of this code back when it was a parody of NFT's

import random
from PIL import Image


#################
# Globals Setup #
#################

width, height = 200, 200

# Load colors
colors = []
with open('./res/colors.txt', 'r') as f:
	for line in f.readlines():
		colors.append(line.replace('\n', ''))
		f.close()


#####################
# Utility Functions #
#####################

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