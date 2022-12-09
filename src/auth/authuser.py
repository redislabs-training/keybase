from flask_login import UserMixin
import time
from src.common.config import get_db
from src.common.utils import Role

# Simulate user database
USERS_DB = {}


class AuthUser(UserMixin):
    def __init__(self, id_, given_name, name, email, access_level):
        self.id = id_
        self.given_name = given_name
        self.name = name
        self.email = email
        self.access_level = access_level

    def claims(self):
        """Use this method to render all assigned claims on profile page."""
        return {'name': self.name,
                'email': self.email}.items()

    @staticmethod
    def get(user_id):
        return USERS_DB.get(user_id)

    @staticmethod
    def exists(user_id):
        return get_db().exists("keybase:auth:{}".format(user_id))

    @staticmethod
    def create(user_id, given_name, name, email):
        get_db().hset("keybase:auth:{}".format(user_id), mapping={
            'name': name,
            'given_name': given_name,
            'email': email,
            'group': 'viewer',
            'signup': time.time(),
            'login': time.time()})

        USERS_DB[user_id] = AuthUser(user_id, given_name, name, email, Role.VIEWER)
        return USERS_DB[user_id]

    @staticmethod
    def update(user_id, given_name, name, email):
        get_db().hset("keybase:auth:{}".format(user_id), mapping={
            'name': name,
            'given_name': given_name,
            'email': email,
            'signup': time.time(),
            'login': time.time()})

        access_level = Role.group2role(get_db().hmget("keybase:auth:{}".format(user_id), ['group'])[0])
        USERS_DB[user_id] = AuthUser(user_id, given_name, name, email, access_level)
        return USERS_DB[user_id]

    def set_role(self, access_level):
        self.access_level = access_level

    def set_group(self, group):
        self.access_level = Role.group2role(group)
        get_db().hset("keybase:auth:{}".format(self.id), mapping={"group": group})

    def get_role(self):
        return self.access_level

    def is_viewer(self):
        return self.access_level == Role.VIEWER

    def is_editor(self):
        return self.access_level >= Role.EDITOR

    def is_admin(self):
        return self.access_level >= Role.ADMIN

    def is_allowed(self, access_level):
        return self.access_level >= access_level

