import json


def test_document_editor_cannot_create_tags(test_client, user_auth):
    # create the document
    user_auth.set_group("editor")
    response = test_client.post("/tag", data={'tag': 'oss', 'description': ''})
    assert response.status_code == 403


def test_document_admin_can_create_tags(test_client, user_auth):
    # create the tag
    user_auth.set_group("admin")

    response = test_client.post("/tag", data={'tag': 'oss', 'description': ''})
    # if all fine, redirect. TODO: make this an api and test better
    assert response.status_code == 302

    # search the tag
    response = test_client.get("/tagsearch", query_string={'q': 'oss'})
    assert response.status_code == 200
    assert json.loads(response.data)['matching_results'] == ["oss"]
