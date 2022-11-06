# This script is used to add a character to the ID property, for example:
# You want to add a new part type to the slime slimes (like a thing to the side of them),
# a new character will have to appended to the ID

# For the images stored in firestore, they will have to be deleted and reuploaded manually
# Good idea to do all your ID changes at once, so you don't have to do this multiple times


import os
from firebase_admin import credentials, firestore, initialize_app


dev = True
collection = 'users-dev' if dev else 'users'
dbCred = credentials.Certificate('./other/firebase.json')
initialize_app(dbCred)
db = firestore.client()

currentIDLength = 8
positionOfNewChar = currentIDLength # 0-indexing

SKIP_FILES = False
SKIP_FIRESTORE = False

def addCharToID(id):
	# z is the default "nothing" character
	newID = id[:positionOfNewChar] + 'z' + id[positionOfNewChar:]
	return newID

# Rename all the files on the server with the new ID
if not SKIP_FILES:
	outputDir = './output' + ('/dev' if dev else '/prod')
	for file in os.listdir(outputDir):
		oldID = file.split('.')[0]
		newID = addCharToID(oldID)
		os.rename(os.path.join(outputDir, file), os.path.join(outputDir, newID + '.png'))
	print(' > Renamed all files')

# Rename all the IDs in firestore
if not SKIP_FIRESTORE:
	# Fetch all users (this grabs the ranch too)
	ref = db.collection(collection)
	userDocs = ref.get()

	for user in userDocs:
		# Get the user
		userRef = ref.document(str(user.id))
		user = userRef.get().to_dict()
		slimes = user['slimes']
		favs = user['favs']

		newSlimes = []
		newFavs = []

		# Update the slimes
		for slime in slimes:
			id = addCharToID(slime)
			newSlimes.append(id)
		for fav in favs:
			id = addCharToID(fav)
			newFavs.append(id)

		# Update the user
		userRef.update({
			'slimes': newSlimes,
			'favs': newFavs
		})
	print(' > Updated all slimes in firestore')