from pymongo.collection import Collection
from werkzeug.security import generate_password_hash, check_password_hash

def check_user(email: str, password: str, db: Collection):
    users = db['users']
    login_user = users.find_one({'email': email})
    print(login_user)

    # if login_user and login_user['password'] == password:
    if login_user and check_password_hash(login_user['password'], password):
        return True

    return False
