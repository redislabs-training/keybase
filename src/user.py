from flask_login import UserMixin
from flask_login import (current_user)
from functools import wraps
from flask import url_for, redirect
from enum import IntEnum
import time
from common.config import get_db

# Simulate user database
USERS_DB = {}


class User(UserMixin):
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
        return get_db().exists("keybase:okta:{}".format(user_id))

    @staticmethod
    def create(user_id, given_name, name, email):
        get_db().hmset("keybase:okta:{}".format(user_id), {
            'name': name,
            'given_name': given_name,
            'email': email,
            'group': 'viewer',
            'signup': time.time(),
            'login': time.time()})

        USERS_DB[user_id] = User(user_id, given_name, name, email, Role.VIEWER)
        return USERS_DB[user_id]

    @staticmethod
    def update(user_id, given_name, name, email):
        get_db().hmset("keybase:okta:{}".format(user_id), {
            'name': name,
            'given_name': given_name,
            'email': email,
            'signup': time.time(),
            'login': time.time()})

        access_level = Role.group2role(get_db().hmget("keybase:okta:{}".format(user_id), ['group'])[0])
        USERS_DB[user_id] = User(user_id, given_name, name, email, access_level)
        return USERS_DB[user_id]

    def set_role(self, access_level):
        self.access_level = access_level

    def get_role(self):
        return self.access_level

    def is_editor(self):
        return self.access_level >= Role.EDITOR

    def is_admin(self):
        return self.access_level >= Role.ADMIN

    def is_allowed(self, access_level):
        return self.access_level >= access_level


class Role(IntEnum):
    ADMIN = 3
    EDITOR = 2
    VIEWER = 1

    @staticmethod
    def group2role(group):
        if group == 'admin':
            return Role.ADMIN
        elif group == 'editor':
            return Role.EDITOR
        elif group == 'viewer':
            return Role.VIEWER


def requires_access_level(access_level):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_allowed(access_level):
                return redirect(url_for('document_bp.browse'))
            return f(*args, **kwargs)

        return decorated_function

    return decorator
