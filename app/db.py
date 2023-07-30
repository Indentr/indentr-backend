import pymongo

def connect_to_mongodb(MONGO_URI: str):
    client = pymongo.MongoClient(MONGO_URI)
    db = client.get_default_database()
    print("Connected to MongoDB")
    return db
