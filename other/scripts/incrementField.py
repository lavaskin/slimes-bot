# Used to increment a value to a given field
from firebase_admin import credentials, firestore, initialize_app


dev = False


def validate(user, field):
	# Test if the user has the field
	try:
		user[field]
	except KeyError:
		return 'Doesn\'t have the field'

	# Test if the lastclaim is greater than 1656904279.2220566
	if user[field] > 1656904279.2220566:
		return 'Hasn\'t claimed recent enough'

	return None

if __name__ == '__main__':
	# Field to increment
	field = 'coins'
	increment = 500

	collection = 'users-dev' if dev else 'users'
	dbCred = credentials.Certificate('./other/firebase.json')
	initialize_app(dbCred)
	db = firestore.client()

	# Fetch all users
	ref = db.collection(collection)
	userDocs = ref.get()

	for user in userDocs:
		# Get the user
		userRef = ref.document(str(user.id))
		user = userRef.get().to_dict()
		userTag = user['tag']

		# Validate the user
		err = validate(user, field)
		if err:
			print(f'> Skipped [{userTag}]: {err}')
			continue

		# Increment the field
		userRef.update({field: firestore.Increment(increment)})
		print(f'> Incremented [{userTag}]: {user[field]} -> {user[field] + increment}')