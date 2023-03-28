import redis
import logging

from flask import redirect, url_for

logging.basicConfig(filename="/tmp/rediskb.log")

REDIS_CFG = {   "host" : "",
                "port" : 6379,
                "password" : "",
                "ssl" : False,
                "ssl_keyfile" : '', 
                "ssl_certfile" : '', 
                "ssl_cert_reqs" : '', 
                "ssl_ca_certs" : ''} 

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
    try:
        return redis.StrictRedis(host=REDIS_CFG["host"],
                                port=REDIS_CFG["port"],
                                password=REDIS_CFG["password"],
                                db=0,
                                ssl=REDIS_CFG["ssl"],
                                ssl_keyfile=REDIS_CFG["ssl_keyfile"],
                                ssl_certfile=REDIS_CFG["ssl_certfile"],
                                ssl_ca_certs=REDIS_CFG["ssl_ca_certs"],
                                ssl_cert_reqs=REDIS_CFG["ssl_cert_reqs"],
                                decode_responses=True)
    except redis.exceptions.ConnectionError:
        return redirect(url_for("main_bp.error-page"))