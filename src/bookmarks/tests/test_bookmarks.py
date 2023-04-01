import json


def test_bookmark_document_user_not_logged(test_client):
    response = test_client.post("/bookmark", data={'docid': "1xmkzwa8w5"})
    assert response.status_code == 401


def test_bookmark_document_not_existing(test_client, user_auth):
    # Try to bookmark a random key
    response = test_client.post("/bookmark", data={'docid': "1xmkzwa8w5"})
    assert response.status_code == 404
    assert json.loads(response.data)['message'] == "Document does not exist"


def test_bookmark_create_and_remove(test_client, create_document):
    response = test_client.post("/bookmark", data={'docid': create_document})
    assert response.status_code == 200
    assert json.loads(response.data)['message'] == "Bookmark created"
    response = test_client.post("/bookmark", data={'docid': create_document})
    assert response.status_code == 200
    assert json.loads(response.data)['message'] == "Bookmark removed"


def test_bookmark_read_mine(test_client, create_document, captured_templates):
    # TODO to improve: return a json and test that
    response = test_client.get("/bookmarks")
    assert response.status_code == 200
    assert len(captured_templates) == 1
    template, context = captured_templates[0]
    assert template.name == "bookmark.html"
    assert "bookmarks" in context
