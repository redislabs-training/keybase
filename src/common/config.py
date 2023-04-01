import os


# Redis
REDIS_CFG = {"host": os.getenv('DB_SERVICE'),
             "port": int(os.getenv('DB_PORT')),
             "password": os.getenv('DB_PWD'),
             "ssl": False,
             "ssl_keyfile": '',
             "ssl_certfile": '',
             "ssl_cert_reqs": '',
             "ssl_ca_certs": ''}


# Okta
OKTA_BASE = os.getenv('OKTA_BASE')
OKTA_CALLBACK_URL = os.getenv('OKTA_CALLBACK_URL')
OKTA_CLIENT_ID = os.getenv('OKTA_CLIENT_ID')
OKTA_CLIENT_SECRET = os.getenv('OKTA_CLIENT_SECRET')
OKTA_API_TOKEN = os.getenv('OKTA_API_TOKEN')

okta = {
    "client_id": OKTA_CLIENT_ID,
    "client_secret": OKTA_CLIENT_SECRET,
    "api_token": OKTA_API_TOKEN,
    "auth_uri": "https://{}/oauth2/default/v1/authorize".format(OKTA_BASE),
    "token_uri": "https://{}/oauth2/default/v1/token".format(OKTA_BASE),
    "issuer": "https://{}/oauth2/default",
    "userinfo_uri": "https://{}/oauth2/default/v1/userinfo".format(OKTA_BASE),
    "redirect_uri": OKTA_CALLBACK_URL,
    "groups_uri": "https://" + OKTA_BASE + "/api/v1/users/{}/groups"
}
