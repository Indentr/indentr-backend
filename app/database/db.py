import certifi
from mongoengine import connect


def connect_to_mongoengine(MONGO_URI: str):
    try:
        # Attempt to connect to MongoDB
        print(f"Attempting to connect to MongoDB with URI: {MONGO_URI}")
        connect(host=MONGO_URI, tlsCAFile=certifi.where())
        print("Successfully connected to MongoDB using mongoengine")
    except Exception as e:
        # Print any error that occurs
        print(f"Failed to connect to MongoDB. Error: {e}")
