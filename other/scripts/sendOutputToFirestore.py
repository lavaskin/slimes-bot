# Upload all the images in output/prod to firebase storage

import os
from firebase_admin import credentials, firestore, initialize_app, storage


dev = True
dbCred = credentials.Certificate('./other/firebase.json')
initialize_app(dbCred, {'storageBucket': os.getenv('STORAGE_BUCKET')})
db = firestore.client()

# Upload all the images in output/prod to firebase storage
bucket = storage.bucket()
folder = './output/dev' if dev else './output/prod'
bucketPath = 'dev/' if dev else 'prod/'

files = os.listdir(folder)
n = 0
for file in files:
	slimeID = file.split('.')[0]
	blob = bucket.blob(f'{bucketPath}{slimeID}.png')
	blob.upload_from_filename(f'{folder}/{file}')
	n += 1
	print(f' > [{round(n / len(files))}%] Uploaded {slimeID}.png')