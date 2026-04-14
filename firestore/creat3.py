import firebase_admin
from firebase_admin import credentials, firestore

cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)

db = firestore.client()

doc = {
  "name": "林苡琦2",
  "mail": "s1130310@o365st.pu.edu.tw",
  "lab": 402
}

doc_ref = db.collection("靜宜資管2026a")
doc_ref.add(doc)
