import certifi
from mongoengine import connect


def connect_to_mongoengine(MONGO_URI: str):
    connect(host=MONGO_URI, tlsCAFile=certifi.where())
    print("Connected to MongoDB using mongoengine")
