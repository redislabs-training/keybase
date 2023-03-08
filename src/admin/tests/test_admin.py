import json


def test_admin_editor_tags_forbidden(test_client, user_auth):
    # create the document
    user_auth.set_group("editor")
    response = test_client.post("/tag", data={'tag': 'oss', 'description': ''})
    assert response.status_code == 403


def test_admin_admin_tags_allowed(test_client, user_auth):
    # create the tag
    user_auth.set_group("admin")

    response = test_client.post("/tag", data={'tag': 'oss', 'description': ''})
    # if all fine, redirect. TODO: make this an api and test better
    assert response.status_code == 302

    # search the tag
    response = test_client.get("/tagsearch", query_string={'q': 'oss'})
    assert response.status_code == 200
    assert json.loads(response.data)['matching_results'] == ["oss"]

def test_admin_editor_category_forbidden(test_client, user_auth):
    # create the document
    user_auth.set_group("editor")
    response = test_client.post("/addcategory", data={'category': 'Redis Stack'})
    assert response.status_code == 403

    user_auth.set_group("viewer")
    response = test_client.post("/addcategory", data={'category': 'Redis Stack'})
    assert response.status_code == 403

def test_admin_admin_category_allowed(test_client, user_auth, captured_templates):
    # create the document
    user_auth.set_group("admin")
    response = test_client.post("/addcategory", data={'category': 'Redis Stack'})
    assert response.status_code == 302