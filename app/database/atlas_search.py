from pymongo import MongoClient


def mongo_patient_autocomplete(MONGO_URI: str, search_param: str, practice_id):
    client = MongoClient(MONGO_URI)
    database_name = MONGO_URI.split("/")[-1].split("?")[0]

    try:
        result = client[database_name]["patients"].aggregate(
            [
                {
                    "$search": {
                        "index": "default",
                        "compound": {
                            "should": [
                                {"autocomplete": {"query": search_param, "path": "forename"}},
                                {"autocomplete": {"query": search_param, "path": "surname"}},
                                {"autocomplete": {"query": search_param, "path": "email"}},
                                {"phrase": {"query": practice_id, "path": practice_id}},
                            ],
                            "minimumShouldMatch": 1,
                        },
                    }
                },
                {"$limit": 4},
                {
                    "$project": {
                        "_id": 1,
                        "forename": 1,
                        "surname": 1,
                        "dob": 1,
                        "gender": 1,
                        "address": 1,
                        "email": 1,
                    }
                },
            ]
        )

        result_list = []

        for i in result:
            i["_id"] = str(i["_id"])
            result_list.append(i)

        return result_list

    finally:
        client.close()
