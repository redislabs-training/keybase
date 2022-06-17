import redis
from flask import g

REDIS_CFG = {   "host" : "",
                "port" : 6380,
                "password" : "",
                "ssl" : False,
                "ssl_keyfile" : '', 
                "ssl_certfile" : '', 
                "ssl_cert_reqs" : '', 
                "ssl_ca_certs" : ''} 
SIGNUP_CFG = 'debug'

okta = {
    "client_id": "",
    "client_secret": "",
    "api_token" : "",
    "auth_uri": "https://dev-XXX.okta.com/oauth2/default/v1/authorize",
    "token_uri": "https://dev-XXX.okta.com/oauth2/default/v1/token",
    "issuer": "https://dev-XXX.okta.com/oauth2/default",
    "userinfo_uri": "https://dev-XXX.okta.com/oauth2/default/v1/userinfo",
    "redirect_uri": "http://XXX/authorization-code/callback",
    "groups_uri" : "https://dev-XXX.okta.com/api/v1/users/{}/groups"
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