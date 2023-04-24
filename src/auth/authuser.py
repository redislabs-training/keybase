from flask_login import UserMixin
import time
from src.common.utils import Role, get_db

# Simulate user database
USERS_DB = {}


class AuthUser(UserMixin):
    def __init__(self, id_, name, access_level):
        self.id = id_
        self.name = name
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
    def get(username):
        user = get_db().hgetall("keybase:auth:{}".format(username))
        access_level = Role.group2role(user['group'])
        USERS_DB[username] = AuthUser(username, user['name'], access_level)
        return USERS_DB[username]

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

