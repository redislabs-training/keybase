import json


def test_document_draft_document_not_existing(test_client, user_auth, create_document):
    create_document
    response = test_client.get("/version", query_string={"q": "content"})
    assert response.status_code == 404
    assert json.loads(response.data)['message'] == "The document does not exist"


def test_document_draft_document_draft_has_no_version(test_client, user_auth, create_document):
    doc_id = create_document
    response = test_client.get("/version", query_string={"pk": doc_id})
    assert response.status_code == 404
    assert json.loads(response.data)['message'] == "The version does not exist"


def test_document_draft_document_draft_has_version_wrong_id(test_client, user_auth, create_document):
    doc_id = create_document
    user_auth.set_group("admin")
    test_client.post("/publish", data={'id': doc_id,
                                       'name': 'my name is...',
                                       'content': 'my content is...'})
    response = test_client.get("/version", query_string={"pk": doc_id, "vpk": "u34iu4ib4i4"})
    assert response.status_code == 404
    assert json.loads(response.data)['message'] == "The version does not exist"


def test_document_draft_document_draft_has_version(test_client, user_auth, create_document, captured_templates):
    doc_id = create_document
    user_auth.set_group("admin")
    test_client.get("/version", query_string={"pk": doc_id})
    test_client.post("/publish", data={'id': doc_id,
                                       'name': 'my name is...',
                                       'content': 'my content is...'})

    test_client.get("/edit/{}".format(doc_id))

    assert len(captured_templates) == 1
    template, context = captured_templates[0]
    assert template.name == "edit.html"
    assert "document" in context
    vpk = context['document'].versions[0].pk

    response = test_client.get("/version", query_string={"pk": doc_id, "vpk": vpk})
    assert response.status_code == 200
    version = json.loads(response.data.decode('utf8'))
    assert json.loads(version)['pk'] == vpk