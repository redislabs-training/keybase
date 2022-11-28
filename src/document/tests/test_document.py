from src.application import create_app
from src.user import User
import json, pytest, flask_login
from src.common.config import get_db, REDIS_CFG
from flask import template_rendered
from contextlib import contextmanager

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
def prepare_db():
    get_db().execute_command('FT.CREATE document_idx ON HASH PREFIX 1 keybase:kb SCHEMA name TEXT content TEXT creation NUMERIC SORTABLE update NUMERIC SORTABLE state TAG owner TEXT processable TAG tags TAG content_embedding VECTOR HNSW 6 TYPE FLOAT32 DIM 768 DISTANCE_METRIC COSINE')
    get_db().execute_command('FT.CREATE user_idx ON HASH PREFIX 1 keybase:okta SCHEMA name TEXT group TEXT')


@pytest.fixture
def user_auth():
    REDIS_CFG['port'] = 6379
    get_db().flushall()
    user = User.create("00000000000000000000", "test_name", "test_username", "test_mail")
    flask_login.login_user(user)
    yield user
    get_db().delete("keybase:okta:00000000000000000000")


def user2_auth():
    REDIS_CFG['port'] = 6379
    user = User.create("11111111111111111111", "test_name", "test_username", "test_mail")
    flask_login.logout_user()
    flask_login.login_user(user)
    return user


@pytest.fixture
def create_flask_app():
    flask_app = create_app()
    with flask_app.app_context():
        with flask_app.test_request_context():
            #flask_login.login_required(False)
            yield flask_app


@pytest.fixture
def test_client(create_flask_app):
    # Create a test client using the Flask application configured for testing
    with create_flask_app.test_client() as test_client:
        yield test_client


def test_document_browse_not_authenticated(test_client):
    response = test_client.get("/browse")
    assert response.status_code == 401


def test_document_browse_authenticated_no_index(test_client, user_auth):
    response = test_client.get("/browse")
    assert response.status_code == 302


def test_document_browse_authenticated_index_created(test_client, user_auth, prepare_db):
    response = test_client.get("/browse")
    assert response.status_code == 200


def test_document_save_route_as_viewer(test_client, user_auth):
    # Default user group is viewer, can't create documents
    response = test_client.post("/save", data={'name': 'my name is...', 'content': 'my content is...'})
    assert response.status_code == 403


def test_document_save_route_as_editor(test_client, user_auth):
    # Editors can create documents but can't delete them
    user_auth.set_group("editor")

    response = test_client.post("/save", data={'name': 'my name is...', 'content': 'my content is...'})
    assert response.status_code == 200
    assert json.loads(response.data)['message'] == "Document created"

    response = test_client.get("/delete/{}".format(json.loads(response.data)['id']))
    assert response.status_code == 403


def test_document_save_route_as_admin(test_client, user_auth):
    # Admins can create and delete documents
    user_auth.set_group("admin")

    # Create and delete document
    response = test_client.post("/save", data={'name': 'my name is...', 'content': 'my content is...'})
    test_client.get("/delete/{}".format(json.loads(response.data)['id']))
    assert response.status_code == 200
    assert json.loads(response.data)['message'] == "Document created"


def test_document_save_route_draft_viewers_forbidden(test_client, user_auth):
    # Viewer can't see a draft
    user_auth.set_group("admin")
    response = test_client.post("/save", data={'name': 'my name is...', 'content': 'my content is...'})
    user_auth.set_group("viewer")
    response = test_client.get("/doc/{}".format(json.loads(response.data)['id']))
    assert response.status_code == 403


def test_document_save_route_draft_as_editor(test_client, user_auth):
    # Viewer can't see a draft
    user_auth.set_group("editor")
    response = test_client.post("/save", data={'name': 'my name is...', 'content': 'my content is...'})
    assert response.status_code == 200


def test_document_save_route_draft_see_own_drafts(test_client, user_auth):
    # If you create a draft, you can see it
    user_auth.set_group("editor")
    response = test_client.post("/save", data={'name': 'my name is...', 'content': 'my content is...'})
    doc_id = json.loads(response.data)['id']
    response = test_client.get("/doc/{}".format(doc_id))
    assert response.status_code == 200


def test_document_save_route_draft_others_drafts_forbidden(test_client, user_auth):
    # The editor creates a draft
    user_auth.set_group("editor")
    response = test_client.post("/save", data={'name': 'my name is...', 'content': 'my content is...'})
    doc_id = json.loads(response.data)['id']

    # Authenticating as another user, can't see own drafts
    user2_auth()
    response = test_client.get("/doc/{}".format(doc_id))
    assert response.status_code == 403


def test_document_save_route_published_as_viewer(test_client, user_auth):
    # create the document
    user_auth.set_group("admin")
    response = test_client.post("/save", data={'name': 'my name is...', 'content': 'my content is...'})
    doc_id = json.loads(response.data)['id']

    # Publish the document by id, need to pass the name and the content of the document too
    # It is a save and publish feature, in reality
    response = test_client.post("/publish", data={'id': doc_id,
                                                  'name': 'my name is...',
                                                  'content': 'my content is...'})
    assert response.status_code == 200
    assert json.loads(response.data)['message'] == "Document published"

    # Switch to viewer and verify it is visible
    user_auth.set_group("viewer")
    response = test_client.get("/doc/{}".format(doc_id))
    assert response.status_code == 200


def test_document_create_tag_not_exists(test_client, user_auth):
    # create the document
    user_auth.set_group("editor")
    response = test_client.post("/save", data={'name': 'my name is...', 'content': 'my content is...'})
    doc_id = json.loads(response.data)['id']

    response = test_client.post("/addtag", data={'id': doc_id, 'tag': 'oss'})
    assert response.status_code == 200
    assert json.loads(response.data)['message'] == "The tag does not exist"


def test_document_create_add_only_preexisting_tag(test_client, user_auth):
    # create the document
    user_auth.set_group("editor")
    response = test_client.post("/save", data={'name': 'my name is...', 'content': 'my content is...'})
    doc_id = json.loads(response.data)['id']

    response = test_client.post("/addtag", data={'id': doc_id, 'tag': 'oss'})
    assert response.status_code == 200
    assert json.loads(response.data)['message'] == "The tag does not exist"


def test_document_create_editor_cannot_add_tags(test_client, user_auth):
    # create the document
    user_auth.set_group("editor")
    response = test_client.post("/tag", data={'tag': 'oss', 'description':''})
    assert response.status_code == 403


def test_document_create_admin_can_add_tags(test_client, user_auth):
    # create the tag
    user_auth.set_group("admin")

    response = test_client.post("/tag", data={'tag': 'oss', 'description':''})
    # if all fine, redirect. TODO: make this an api and test better
    assert response.status_code == 302

    # search the tag
    response = test_client.get("/tagsearch", query_string={'q': 'oss'})
    assert response.status_code == 200
    assert json.loads(response.data)['matching_results'] == ["oss"]


def test_document_and_tag_creation_tag_document(test_client, user_auth):
    # create the document
    user_auth.set_group("admin")
    response = test_client.post("/save", data={'name': 'my name is...', 'content': 'my content is...'})
    doc_id = json.loads(response.data)['id']

    # create the tag
    test_client.post("/tag", data={'tag': 'oss', 'description':''})

    # tag the document
    response = test_client.post("/addtag", data={'id': doc_id, 'tag': 'oss'})
    assert response.status_code == 200
    assert json.loads(response.data)['message'] == "The tag has been added"

    # retag the document
    response = test_client.post("/addtag", data={'id': doc_id, 'tag': 'oss'})
    assert response.status_code == 200
    assert json.loads(response.data)['message'] == "Document already tagged"


def test_document_autocomplete_authenticated_index_created(test_client, user_auth, prepare_db):
    # create the document
    user_auth.set_group("admin")
    response = test_client.post("/save", data={'name': 'my name is...', 'content': 'my content is...'})
    doc_id = json.loads(response.data)['id']
    test_client.post("/publish", data=dict(id=doc_id, name='my name is...', content='my content is...'))

    response = test_client.get("/autocomplete", query_string={"q": "content"});
    assert response.status_code == 200
    assert json.loads(response.data)['matching_results'][0] ==  {'id': doc_id, 'label': 'my name is...', 'pretty': 'my-name-is', 'value': 'my name is...'}


def test_document_browse_authenticated_index_created(test_client, user_auth, prepare_db, captured_templates):
    # create the document
    user_auth.set_group("admin")
    response = test_client.post("/save", data={'name': 'my name is...', 'content': 'my content is...'})
    doc_id = json.loads(response.data)['id']
    test_client.post("/publish", data=dict(id=doc_id, name='my name is...', content='my content is...'))

    response = test_client.get("/browse", query_string={"q": "content"});
    assert response.status_code == 200
    assert len(captured_templates) == 1
    template, context = captured_templates[0]
    assert template.name == "browse.html"
    assert "keydocument" in context
    #keys,names,pretty,creations = zip(*context['keydocument'])


#flask_app.config['LOGIN_DISABLED'] = True
#flask_app.config['DEBUG'] = True
#flask_app.config['TESTING'] = True