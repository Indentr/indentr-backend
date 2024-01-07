from pymongo import MongoClient


def atlas_search(MONGO_URI: str, table_name: str, pipeline: list):
    client = MongoClient(MONGO_URI)
    database_name = MONGO_URI.split("/")[-1].split("?")[0]

    try:
        result = list(client[database_name][table_name].aggregate(pipeline))
        return result

    finally:
        client.close()
