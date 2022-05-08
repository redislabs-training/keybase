
"""
REDIS_CFG = {
    "host" : "localhost",
    "port" : 4321,
    "password" : ""
} 
"""

REDIS_CFG = {
    "host" : "redis-12189.c55.eu-central-1-1.ec2.cloud.redislabs.com",
    "port" : 12189,
    "password" : "FlwotDxjYryWUDJzyFOWyNW2n3ou0h7n"
} 


# General Config
#SECRET_KEY = environ.get('SECRET_KEY')
#FLASK_APP = environ.get('FLASK_APP')
#FLASK_ENV = environ.get('FLASK_ENV')

# Flask-Session
#SESSION_TYPE = environ.get('SESSION_TYPE')

TESTING = True
DEBUG = True
#FLASK_ENV = 'development'
SECRET_KEY = 'GDtfDCFYjD'

REDIS_URL = "redis://:@localhost:4321/0"

