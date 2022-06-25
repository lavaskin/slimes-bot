# Script to auto generate the stripe images for the slime backgrounds.
# Reads in from ./res/colors.txt and deletes the old stripes folder
# Makes manually creating them slightly less tedious
import json
import os
import shutil
from PIL import Image


def hex2rgb(h):
	return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

stripesDir = './res/stripes.png'

# Load colors
colors = []
with open('./res/colors.txt', 'r') as f:
	for line in f.readlines():
		colors.append(line.replace('\n', ''))
		f.close()

# Delete and recreate directory
if os.path.exists(stripesDir):
	shutil.rmtree(stripesDir, ignore_errors=True)
	os.mkdir(stripesDir)

# Load stripe pattern
stripes = Image.open('./res/parts/slimes/backgrounds/stripes.png')
pixels = stripes.load()

# Make seperate images
for n, color in enumerate(colors, 0):
	newStripes = Image.new(mode='RGBA', size=(200, 200), color=(0, 0, 0, 0))
	newPixels = newStripes.load()
	for i in range(stripes.size[0]):
		for j in range(stripes.size[1]):
			r, g, b, a = pixels[i, j]
			if r ==  255 and g == 255 and b == 255:
				newPixels[i, j] = hex2rgb(color[1:])
	newStripes.save('{}/{}.png'.format(stripesDir, n))
	newStripes.close()

# Cleanup
stripes.close()