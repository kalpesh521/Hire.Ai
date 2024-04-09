from pymongo import MongoClient
from .constants import DATABASE_URL


client = MongoClient(DATABASE_URL)
db = client["AIInterviewer"]
collection = db["interviews"]