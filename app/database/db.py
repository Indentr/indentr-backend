from pymongo import MongoClient


def connect_to_mongodb(MONGO_URI: str):
    client = MongoClient(MONGO_URI)

    # Extract the database name from the URI
    database_name = MONGO_URI.split("/")[-1].split("?")[0]

    # Return the specified database
    db = client[database_name]
    print(f"Connected to MongoDB - Database: {database_name}")
    return db
