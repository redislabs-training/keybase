import redis
import os
from flask import g

REDIS_CFG = {   "host" : os.getenv('DB_SERVICE'),
                "port" : int(os.getenv('DB_PORT')),
                "password" : os.getenv('DB_PWD'),
                "ssl" : False,
                "ssl_keyfile" : '', 
                "ssl_certfile" : '', 
                "ssl_cert_reqs" : '', 
                "ssl_ca_certs" : ''} 
SIGNUP_CFG = 'debug'

OKTA_BASE=os.getenv('OKTA_BASE')
OKTA_CALLBACK_URL=os.getenv('OKTA_CALLBACK_URL')

okta = {
    "client_id": os.getenv('OKTA_CLIENT_ID'),
    "client_secret": os.getenv('OKTA_CLIENT_SECRET'),
    "api_token" : os.getenv('OKTA_API_TOKEN'),
    "auth_uri": "https://{}/oauth2/default/v1/authorize".format(OKTA_BASE),
    "token_uri": "https://{}/oauth2/default/v1/token".format(OKTA_BASE),
    "issuer": "https://{}/oauth2/default",
    "userinfo_uri": "https://{}/oauth2/default/v1/userinfo".format(OKTA_BASE),
    "redirect_uri": OKTA_CALLBACK_URL,
    "groups_uri" : "https://" + OKTA_BASE + "/api/v1/users/{}/groups"
}

def get_db():
    # Database Connection if there is none yet for the current application context
    host = REDIS_CFG["host"]
    port = REDIS_CFG["port"]
    pwd = REDIS_CFG["password"]
    ssl = REDIS_CFG["ssl"]
    ssl_keyfile = REDIS_CFG["ssl_keyfile"]
    ssl_certfile = REDIS_CFG["ssl_certfile"]
    ssl_cert_reqs = REDIS_CFG["ssl_cert_reqs"]
    ssl_ca_certs = REDIS_CFG["ssl_ca_certs"]

    if not hasattr(g, 'redis'):
        g.redis = redis.StrictRedis(host=host,
                                    port=port,
                                    password=pwd,
                                    db=0,
                                    ssl=ssl,
                                    ssl_keyfile=ssl_keyfile,
                                    ssl_certfile=ssl_certfile,
                                    ssl_ca_certs=ssl_ca_certs,
                                    ssl_cert_reqs=ssl_cert_reqs,
                                    decode_responses=True)

    return g.redis