import redis

# bash: redis-server --port 6380
# Connect to Redis server (default localhost:6380)
try:
    r = redis.Redis(host='localhost', port=6380, db=0)

    # Test the connection
    r.ping()
    print("Connected to Redis!")

    # Set and Get a value
    r.set("username", "mitsu")
    print("Stored username:", r.get("username").decode())

    # Working with lists
    r.lpush("my_list", "apple", "banana", "cherry")
    print("List contents:", r.lrange("my_list", 0, -1))

    # Hash (dictionary-like structure)
    r.hset("profile:1001", mapping={"name": "Mitsu", "age": "28"})
    print("Profile name:", r.hget("profile:1001", "name").decode())

except redis.exceptions.ConnectionError as e:
    print("Could not connect to Redis:", e)