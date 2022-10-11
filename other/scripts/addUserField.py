# Made for when you need to add a new field to the users collection to existng users
from firebase_admin import credentials, firestore, initialize_app


# Field to add
fieldName = 'exp'
field = { fieldName: 0 }

dev = False
collection = 'users-dev' if dev else 'users'
dbCred = credentials.Certificate('./other/firebase.json')
initialize_app(dbCred)
db = firestore.client()


# Fetch all users
ref = db.collection(collection)
userDocs = ref.get()

for user in userDocs:
	userRef = ref.document(str(user.id))

	try:
		userRef.get().to_dict()[fieldName]
		print(f'> Skipped: {user.id}')
	except KeyError:
		userRef.update(field)
		print(f'> Added Field: {user.id}')