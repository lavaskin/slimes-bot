# Mass produces slimes given a command-line argument
# I'm just copy/pasting the generation code from the slimes class, may be out of date


import random
import sys
from PIL import Image
import os
from os.path import exists
import shutil


# Globals
dupes = 0
output = './output/mass/'
def countFiles(dir):
	# Counts the amount of files in a directory
	return len([f for f in os.listdir(dir) if os.path.isfile(dir + f)])
partsDir      = './res/parts/slimes/'
specialBgs    = countFiles(partsDir + 'backgrounds/special/')
regBodies     = countFiles(partsDir + 'bodies/regular/')
specialBodies = countFiles(partsDir + 'bodies/special/')
eyes          = countFiles(partsDir + 'face/eyes/')
mouths        = countFiles(partsDir + 'face/mouths/')
hats          = countFiles(partsDir + 'hats/')
random.seed()
colors = []
with open('./res/colors.txt', 'r') as f:
	for line in f.readlines():
		colors.append(line.replace('\n', ''))
		f.close()


# Functions
def encodeNum(n):
	if n < 10:
		return str(n)
	elif n < 36:
		return chr(n + 55)
	else:
		return chr(n + 61)

def getPaintColors():
	colorCount = len(colors)
	c1 = random.randrange(0, colorCount)
	c2 = random.randrange(0, colorCount)

	# Flip paint color if same as bg
	if c1 == c2:
		c1 = colorCount - c1 - 1
	return c1, c2

def rollLayers(fName, layers, bgColor):
	# Generate the image
	final = Image.new(mode='RGB', size=(200, 200), color=colors[bgColor])

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
		
def genSlime():
	# Loops until a unique ID is created
	while True:
		bgColor, altColor = getPaintColors()
		layers = [] # Tuples of form: (file path, transparent?)
		id = ''

		# Background [50% solid color, 45% stripes, 5% special]
		bgRoll = random.randint(1, 100)
		if bgRoll > 95:
			# Apply special background
			roll = random.randrange(0, specialBgs)
			id += ('2' + encodeNum(roll) + '!')
			layers.append(('{0}backgrounds/special/{1}.png'.format(partsDir, roll), False))
		elif bgRoll > 50:
			# Apply stripe layer
			id += ('1' + encodeNum(bgColor) + encodeNum(altColor))
			layers.append(('{0}backgrounds/stripes/{1}.png'.format(partsDir, altColor), True))
		else:
			# Solid Color
			id += ('0' + encodeNum(bgColor) + '!')

		# Add slime body [90% chance of regular body, 10% special]
		if random.randrange(0, 10):
			roll = random.randrange(0, regBodies)
			id += ('0' + encodeNum(roll))
			layers.append(('{0}bodies/regular/{1}.png'.format(partsDir, roll), True))
		else:
			roll = random.randrange(0, specialBodies)
			id += ('1' + encodeNum(roll))
			layers.append(('{0}bodies/special/{1}.png'.format(partsDir, roll), True))

		# Eyes
		roll = random.randrange(0, eyes)
		id += encodeNum(roll)
		layers.append(('{0}face/eyes/{1}.png'.format(partsDir, roll), True))

		# Mouth [80% chance]
		if random.randint(0, 4) != 0:
			roll = random.randrange(0, mouths)
			id += encodeNum(roll)
			layers.append(('{0}face/mouths/{1}.png'.format(partsDir, roll), True))
		else: id += '!'

		# Add hat [75% chance of having a hat]
		if random.randint(0, 3) != 0:
			roll = random.randrange(0, hats)
			id += encodeNum(roll)
			layers.append(('{0}hats/{1}.png'.format(partsDir, roll), True))
		else: id += '!'

		# Check that ID doesn't exist. If so, leave the loop
		if not exists(output + id + '.png'):
			break
		else:
			global dupes
			dupes += 1
			print('| DUPE SLIME:', id)

	# Roll the layers and return the rolled file
	fName = output + id + '.png'
	rollLayers(fName, layers, bgColor)
	return fName


# Setup
if __name__ == '__main__':
	random.seed()
	# Get command-line args
	amt = 100
	clear = False

	if len(sys.argv) > 2:
		if sys.argv[2] in ['c', 'clear']:
			clear = True
	if len(sys.argv) > 1:
		amt = int(sys.argv[1])

	# Make directory if it doesn't exist
	if not exists(output):
		os.mkdir(output)
	elif exists(output) and clear:
		shutil.rmtree(output)
		os.mkdir(output)

	for i in range(amt):
		genSlime()
	print(f'| Total dupes: {dupes} ({round((dupes / amt) * 100, 2)}%)')