from src.user import User
import json, pytest, flask_login
from src.common.config import REDIS_CFG


def user2_auth():
    REDIS_CFG['port'] = 6379
    user = User.create("11111111111111111111", "test_name", "test_username", "test_mail")
    flask_login.logout_user()
    flask_login.login_user(user)
    return user


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

    # Authenticating as another user, can't see others' drafts
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


def test_document_add_tag_tag_not_existing(test_client, user_auth, create_document):
    doc_id = create_document
    response = test_client.post("/addtag", data={'id': doc_id, 'tag': 'oss'})
    assert response.status_code == 200
    assert json.loads(response.data)['message'] == "The tag does not exist"


def test_document_add_tag_document_not_existing(test_client, user_auth):
    user_auth.set_group("editor")
    response = test_client.post("/addtag", data={'id': "1xmkzwa8w5", 'tag': 'oss'})
    assert response.status_code == 404
    assert json.loads(response.data)['message'] == "The document does not exist"


def test_document_add_tag_user_not_authorized(test_client, user_auth):
    response = test_client.post("/addtag", data={'id': "1xmkzwa8w5", 'tag': 'oss'})
    assert response.status_code == 403
    assert response.data == b"Unauthorized"


def test_document_del_tag_user_not_authorized(test_client, user_auth):
    response = test_client.post("/deltag", data={'id': "1xmkzwa8w5", 'tag': 'oss'})
    assert response.status_code == 403
    assert response.data == b"Unauthorized"


def test_document_del_tag_document_not_existing(test_client, create_document):
    response = test_client.post("/deltag", data={'id': "1xmkzwa8w5", 'tag': 'oss'})
    assert response.status_code == 404
    assert json.loads(response.data)['message'] == "The document does not exist"


def test_document_del_tag_document_success(test_client, create_document):
    doc_id = create_document
    test_client.post("/addtag", data={'id': doc_id, 'tag': 'oss'})
    response = test_client.post("/deltag", data={'id': doc_id, 'tag': 'oss'})
    assert response.status_code == 200
    assert json.loads(response.data)['message'] == "The tag has been removed"
    assert json.loads(response.data)['tags'] == []


def test_document_editor_cannot_create_tags(test_client, user_auth):
    # create the document
    user_auth.set_group("editor")
    response = test_client.post("/tag", data={'tag': 'oss', 'description':''})
    assert response.status_code == 403


def test_document_admin_can_create_tags(test_client, user_auth):
    # create the tag
    user_auth.set_group("admin")

    response = test_client.post("/tag", data={'tag': 'oss', 'description':''})
    # if all fine, redirect. TODO: make this an api and test better
    assert response.status_code == 302

    # search the tag
    response = test_client.get("/tagsearch", query_string={'q': 'oss'})
    assert response.status_code == 200
    assert json.loads(response.data)['matching_results'] == ["oss"]


def test_document_add_tag_retag_document(test_client, user_auth, create_document):
    doc_id = create_document
    user_auth.set_group("admin")

    # create the tag
    test_client.post("/tag", data={'tag': 'oss', 'description':''})
    test_client.post("/tag", data={'tag': 'troubleshooting', 'description': ''})

    # tag the document
    response = test_client.post("/addtag", data={'id': doc_id, 'tag': 'oss'})
    assert response.status_code == 200
    assert json.loads(response.data)['message'] == "The tag has been added"
    assert json.loads(response.data)['tags'] == ['oss']

    # tag the document
    response = test_client.post("/addtag", data={'id': doc_id, 'tag': 'troubleshooting'})
    assert response.status_code == 200
    assert json.loads(response.data)['message'] == "The tag has been added"
    assert json.loads(response.data)['tags'] == ['oss', 'troubleshooting']

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


def test_document_save_authenticated_index_created(test_client, user_auth, prepare_db, captured_templates):
    # create the document
    user_auth.set_group("admin")
    response = test_client.post("/save", data={'name': 'my name is...', 'content': 'my content is...'})
    doc_id = json.loads(response.data)['id']
    test_client.post("/publish", data=dict(id=doc_id, name='my name is...', content='my content is...'))

    response = test_client.get("/browse", query_string={"q": "content"})
    assert response.status_code == 200
    assert len(captured_templates) == 1
    template, context = captured_templates[0]
    assert template.name == "browse.html"
    assert "keydocument" in context
    #keys,names,pretty,creations = zip(*context['keydocument'])


def test_document_not_existing(test_client, user_auth, prepare_db):
    response = test_client.get("/doc/{}".format("1xmkzwa8w5"))
    assert response.status_code == 404


def test_document_save_delete_not_authorized(test_client, create_document):
    response = test_client.get("/doc/{}".format(create_document))
    assert response.status_code == 200
    response = test_client.get("/delete/{}".format(create_document))
    assert response.status_code == 403


def test_document_save_delete_authorized(test_client, user_auth, create_document):
    doc_id = create_document
    user_auth.set_group("admin")
    response = test_client.get("/doc/{}".format(doc_id))
    assert response.status_code == 200
    response = test_client.get("/delete/{}".format(doc_id))
    assert response.status_code == 302
    response = test_client.get("/doc/{}".format(doc_id))
    assert response.status_code == 404


def test_document_update_name_content_success(test_client, user_auth, create_document):
    doc_id = create_document
    response = test_client.post("/update", data={'id': doc_id, 'name': 'new name is...', 'content': 'new content is...'})


def test_document_update_name_content_user_not_authorized(test_client, user_auth, create_document):
    user_auth.set_group("viewer")
    doc_id = create_document
    response = test_client.post("/update", data={'id': doc_id, 'name': 'new name is...', 'content': 'new content is...'})
    assert response.status_code == 403
    assert response.data == b"Unauthorized"




#flask_app.config['LOGIN_DISABLED'] = True
#flask_app.config['DEBUG'] = True
#flask_app.config['TESTING'] = True