import math
from firebase_admin import credentials, firestore, initialize_app


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


dev = False
collection = 'users-dev' if dev else 'users'
dbCred = credentials.Certificate('./other/firebase.json')
initialize_app(dbCred)
db = firestore.client()

# Functions up to date as of 10/10/22
def calculateLevel(xp):
		level = round((0.25 * math.sqrt(xp)) + 1, 2)
		lo = math.floor(level)
		percent = int(round((level - lo) * 100, 2))
		return lo, percent
		
def getRarity(id):
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

		return score

# Fetch all users
ref = db.collection(collection)
userDocs = ref.get()

for user in userDocs:
	userRef = ref.document(str(user.id))

	# Get user data
	userData = userRef.get().to_dict()
	if userData['exp'] > 0:
		print(f'> Skipped: {user.id}')
		continue
	slimes = userData['slimes']

	# Loop through slimes
	exp = 0
	for slime in slimes:
		# Get rarity
		exp += getRarity(slime)

	# Calculate level up bonuses (half of level * 100)
	level, _ = calculateLevel(exp)
	levelBonus = 0
	if level > 1:
		for i in range(2, level + 1):
			levelBonus += min(int((level * 0.5) * 100), 500)

	# Update user data
	userRef.update({ 'exp': exp, 'coins': firestore.Increment(levelBonus) })
	print(f'> Updated: {user.id} to {exp} ({levelBonus} bonus)')