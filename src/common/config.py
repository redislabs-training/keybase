import os
from dotenv import load_dotenv

load_dotenv()

CFG_THEME = os.getenv('CFG_THEME', 'redis')
CFG_VSS_WITH_LUA = os.getenv('CFG_VSS_WITH_LUA').lower() in ('true', '1', 't')

# Redis
REDIS_CFG = {"host": os.getenv('DB_SERVICE', '127.0.0.1'),
             "port": int(os.getenv('DB_PORT')),
             "password": os.getenv('DB_PWD',''),
             "ssl": os.getenv('DB_SSL', False),
             "ssl_keyfile": os.getenv('DB_SSL_KEYFILE', ''),
             "ssl_certfile": os.getenv('DB_SSL_CERTFILE', ''),
             "ssl_cert_reqs": os.getenv('DB_CERT_REQS', ''),
             "ssl_ca_certs": os.getenv('DB_CA_CERTS', '')}


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
    "auth_uri": "https://{}/oauth2/v1/authorize".format(OKTA_BASE),
    "token_uri": "https://{}/oauth2/v1/token".format(OKTA_BASE),
    "issuer": "https://{}".format(OKTA_BASE),
    "userinfo_uri": "https://{}/oauth2/v1/userinfo".format(OKTA_BASE),
    "redirect_uri": OKTA_CALLBACK_URL,
    "groups_uri": "https://{}/api/v1/users/".format(OKTA_BASE)
}
