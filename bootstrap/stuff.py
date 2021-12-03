from helpers import *

r = redis()

users = get_user_list_from_redis(r)
user_data = pull_user_data_from_redis(users, r)

data = {}

for piece in user_data:
    data[piece.get_username()] = piece.to_dict()

with open("redis_data.json", "w") as outfile:
    json.dump(data, outfile, indent=2)
