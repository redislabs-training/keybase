import redis
from config import get_db
import shortuuid
from flask import Flask, current_app

app = Flask(__name__)
with app.app_context():
    rs = get_db().keys("keybase:kb*")

    for key in rs:
        shortuuid.set_alphabet("123456789abcdefghijkmnopqrstuvwxyz")
        id = shortuuid.uuid()[:10]
        print(id)
        print(key)