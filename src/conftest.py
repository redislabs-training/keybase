from flask import template_rendered
from src.application import create_app
from redis_om import (Migrator)
from src.common.config import get_db, REDIS_CFG
import pytest, json, flask_login
from src.user import User


@pytest.fixture
def create_flask_app():
    flask_app = create_app()
    with flask_app.app_context():
        with flask_app.test_request_context():
            # flask_login.login_required(False)
            yield flask_app


@pytest.fixture
def test_client(create_flask_app):
    # Create a test client using the Flask application configured for testing
    with create_flask_app.test_client() as test_client:
        yield test_client


@pytest.fixture
def captured_templates(create_flask_app):
    recorded = []

    def record(sender, template, context, **extra):
        recorded.append((template, context))

    template_rendered.connect(record, create_flask_app)
    try:
        yield recorded
    finally:
        template_rendered.disconnect(record, create_flask_app)


@pytest.fixture
def create_token():
    get_db().flushall()
    api_key = "43f34fwwf4wf4wfw"
    api_secret_key = "4827fgyho83w4uyf2o834yfbwo"
    tokens = {'X-Api-Key': api_key, 'X-Api-Secret-Key': api_secret_key}
    get_db().hset("keybase:api:token", mapping={api_key: api_secret_key})
    return tokens


@pytest.fixture
def prepare_db():
    get_db().execute_command(
        'FT.CREATE document_idx ON JSON PREFIX 1 keybase:kb SCHEMA $.name TEXT $.content TEXT $.creation NUMERIC SORTABLE $.update NUMERIC SORTABLE $.state TAG $.owner TEXT $.processable TAG $.tags TAG $.category TAG $.feedback[*].state AS feedback_state TAG')
    get_db().execute_command(
        'FT.CREATE vss_idx ON HASH PREFIX 1 keybase:vss SCHEMA content_embedding VECTOR HNSW 6 TYPE FLOAT32 DIM 768 DISTANCE_METRIC COSINE')
    get_db().execute_command('FT.CREATE user_idx ON HASH PREFIX 1 keybase:okta SCHEMA name TEXT group TEXT')
    Migrator().run()


@pytest.fixture
def user_auth():
    REDIS_CFG['port'] = 6379
    get_db().flushall()
    user = User.create("00000000000000000000", "test_name", "test_username", "test_mail")
    flask_login.login_user(user)
    yield user
    get_db().delete("keybase:okta:00000000000000000000")


@pytest.fixture
def create_document(test_client, user_auth, prepare_db):
    user_auth.set_group("editor")
    response = test_client.post("/save", data={'name': 'my name is...', 'content': 'my content is...'})
    return json.loads(response.data)['id']
