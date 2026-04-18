import os
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

MONGO_URL = os.getenv("MONGO_URL")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME")

class Connect:
    def __init__(self):
        if MONGO_URL:
            raise ValueError("Mongo URl dosen't exists")

        self.client = MongoClient(MONGO_URL)
        self.db = self.client(MONGO_DB_NAME)

try:
    connect = Connect()
    print("Sucessfully connected to database")
except Exception as e:
    print(e)
    raise e