# Made for when you want to change how ID generation is done
# For example, I swapped '!' in the ID for lowercase 'z', so I need to change all existing ID's accordingly
import os
from firebase_admin import credentials, firestore, initialize_app


# Setup
old, new = '!', 'z'
path, collection = './output/dev/', 'users-dev'
files = os.listdir(path)
dbCred = credentials.Certificate('./other/firebase.json')
initialize_app(dbCred)
db = firestore.client()

# Replace files in local storage
for file in files:
	if os.path.isfile(path + file):
		newFile = file.replace(old, new)
		os.rename(path + file, path + newFile)

# Replace ID's in firestore
ref = db.collection(collection)
userDocs = ref.get()

for user in userDocs:
	userRef = ref.document(str(user.id))
	userDict = userRef.get().to_dict()
	slimes = userDict['slimes']
	favs   = userDict['favs']

	# Update slimes
	for slime in slimes:
		newID = slime.replace(old, new)
		userRef.update({'slimes': firestore.ArrayRemove([slime])})
		userRef.update({'slimes': firestore.ArrayUnion([newID])})

	# Update Favs
	for fav in favs:
		newID = fav.replace(old, new)
		userRef.update({'favs': firestore.ArrayRemove([fav])})
		userRef.update({'favs': firestore.ArrayUnion([newID])})

# Replace ID's in firebase storage
# TODO