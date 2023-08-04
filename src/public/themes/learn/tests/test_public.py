

def test_public_drafts_forbidden(test_client, create_document):
    doc_id = create_document
    response = test_client.get("/kb/{}".format(doc_id))
    assert response.status_code == 403


def test_public_published_default_forbidden(test_client, user_auth, create_document):
    doc_id = create_document
    user_auth.set_group("admin")
    response = test_client.post("/publish", data={'id': doc_id,
                                                  'name': 'my name is...',
                                                  'content': 'my content is...'})
    assert response.status_code == 200
    response = test_client.get("/kb/{}".format(doc_id))
    assert response.status_code == 403


def test_public_published_internal_forbidden(test_client, user_auth, create_document):
    doc_id = create_document
    user_auth.set_group("admin")
    test_client.post("/setprivacy", data={'id': doc_id,
                                          'privacy': 'internal'})

    test_client.post("/publish", data={'id': doc_id,
                                       'name': 'my name is...',
                                       'content': 'my content is...'})
    response = test_client.get("/kb/{}".format(doc_id))
    assert response.status_code == 403


def test_public_published_public_allowed(test_client, user_auth, create_document):
    doc_id = create_document
    user_auth.set_group("admin")
    test_client.post("/setprivacy", data={'id': doc_id,
                                          'privacy': 'public'})

    test_client.post("/publish", data={'id': doc_id,
                                       'name': 'my name is...',
                                       'content': 'my content is...'})

    response = test_client.get("/kb/{}".format(doc_id))
    assert response.status_code == 200


def test_public_published_review_allowed(test_client, user_auth, create_document):
    doc_id = create_document
    user_auth.set_group("admin")
    test_client.post("/setprivacy", data={'id': doc_id,
                                          'privacy': 'public'})

    test_client.post("/publish", data={'id': doc_id,
                                       'name': 'my name is...',
                                       'content': 'my content is...'})

    test_client.post("/update", data={'id': doc_id,
                                      'name': 'my name is...',
                                      'content': 'my content is...'})
    response = test_client.get("/kb/{}".format(doc_id))
    assert response.status_code == 200
