import json


def test_feedback_comment_wrong_document_pk(test_client, user_auth, create_document):
    doc_id = create_document
    response = test_client.post("/comment", data={'pk': "54g345345",
                                                  'desc': 'my name is...',
                                                  'msg': 'my content is...'})
    assert response.status_code == 404
    assert json.loads(response.data)['message'] == "The document does not exist"


def test_feedback_comment_short_description(test_client, user_auth, create_document):
    doc_id = create_document
    response = test_client.post("/comment", data={'pk': doc_id,
                                                  'desc': 'my ',
                                                  'msg': 'my '})
    assert response.status_code == 422
    assert json.loads(response.data)['message'] == "The description is too short"


def test_feedback_comment_short_message(test_client, user_auth, create_document):
    doc_id = create_document
    response = test_client.post("/comment", data={'pk': doc_id,
                                                  'desc': 'This is a correct description',
                                                  'msg': 'my '})
    assert response.status_code == 422
    assert json.loads(response.data)['message'] == "The message is too short"


def test_feedback_comment_success(test_client, user_auth, create_document):
    doc_id = create_document
    response = test_client.post("/comment", data={'pk': doc_id,
                                                  'desc': 'This is a correct description',
                                                  'msg': 'This is a correct message'})
    assert response.status_code == 200
    assert json.loads(response.data)['message'] == "The feedback has been posted"


def test_feedback_viewer_not_allowed(test_client, user_auth, prepare_db):
    user_auth.set_group("viewer")
    response = test_client.get("/feedback")
    assert response.status_code == 403
    assert response.data == b"Unauthorized"


def test_feedback_editor_allowed(test_client, user_auth, create_document, captured_templates):
    doc_id = create_document
    response = test_client.post("/comment", data={'pk': doc_id,
                                                  'desc': 'This is a correct description',
                                                  'msg': 'This is a correct message'})
    response = test_client.get("/feedback")
    assert response.status_code == 200

    assert len(captured_templates) == 1
    template, context = captured_templates[0]
    assert template.name == "feedback/view.html"
    assert "results" in context
    assert context['results'][0]['description'] == 'This is a correct description'
    assert context['results'][0]['docid'] == doc_id


def test_feedback_non_existing_parameters(test_client, user_auth, create_document, captured_templates):
    doc_id = create_document
    response = test_client.post("/comment", data={'pk': doc_id,
                                                  'desc': 'This is a correct description',
                                                  'xxx': 'This is a correct message'})

    assert response.status_code == 400


def test_feedback_detail_not_allowed(test_client, user_auth):
    user_auth.set_group("viewer")
    response = test_client.get("/detail", query_string={"pk": "54g345345"})
    assert response.status_code == 403
    assert response.data == b"Unauthorized"


def test_feedback_detail_wrong_feedback_pk(test_client, user_auth):
    user_auth.set_group("editor")
    response = test_client.get("/detail", query_string={"pk": "54g345345"})
    assert response.status_code == 404
    assert json.loads(response.data)['message'] == "The feedback does not exist"


def test_feedback_editor_allowed(test_client, user_auth, create_document, captured_templates):
    doc_id = create_document
    response = test_client.post("/comment", data={'pk': doc_id,
                                                  'desc': 'This is a correct description',
                                                  'msg': 'This is a correct message'})
    response = test_client.get("/feedback")
    assert response.status_code == 200

    assert len(captured_templates) == 1
    template, context = captured_templates[0]
    assert template.name == "feedback/view.html"
    assert "results" in context
    assert context['results'][0]['description'] == 'This is a correct description'
    assert context['results'][0]['docid'] == doc_id
    feedback_key = context['results'][0]['key']

    response = test_client.get("/detail", query_string={"pk": feedback_key})
    assert response.status_code == 200
    assert json.loads(response.data)['description'] == "This is a correct description"
    assert json.loads(response.data)['document'] == doc_id
    assert json.loads(response.data)['message'] == 'This is a correct message'
    assert json.loads(response.data)['state'] == 'open'


def test_feedback_response_not_allowed(test_client, user_auth):
    user_auth.set_group("viewer")
    response = test_client.post("/response", data={"pk": "54g345345"})
    assert response.status_code == 403
    assert response.data == b"Unauthorized"


def test_feedback_response_not_allowed(test_client, user_auth):
    user_auth.set_group("editor")
    response = test_client.post("/response", data={"pk": "544t545g3",
                                                   "state": "implemented",
                                                   "response": "A response text"})
    assert response.status_code == 404
    assert json.loads(response.data)['message'] == "The feedback does not exist"


def test_feedback_response_wrong_state(test_client, user_auth, create_document, captured_templates):
    doc_id = create_document
    response = test_client.post("/comment", data={'pk': doc_id,
                                                  'desc': 'This is a correct description',
                                                  'msg': 'This is a correct message'})
    response = test_client.get("/feedback")
    assert response.status_code == 200

    assert len(captured_templates) == 1
    template, context = captured_templates[0]
    assert template.name == "feedback/view.html"
    assert "results" in context
    assert context['results'][0]['description'] == 'This is a correct description'
    assert context['results'][0]['docid'] == doc_id
    feedback_key = context['results'][0]['key']

    response = test_client.post("/response", data={"pk": feedback_key,
                                                   "state": "xxxxxx",
                                                   "response": "A response text"})
    assert response.status_code == 422
    assert json.loads(response.data)['message'] == "Wrong feedback state"


def test_feedback_response_success(test_client, user_auth, create_document, captured_templates):
    doc_id = create_document
    response = test_client.post("/comment", data={'pk': doc_id,
                                                  'desc': 'This is a correct description',
                                                  'msg': 'This is a correct message'})
    response = test_client.get("/feedback")
    assert response.status_code == 200

    assert len(captured_templates) == 1
    template, context = captured_templates[0]
    assert template.name == "feedback/view.html"
    assert "results" in context
    assert context['results'][0]['description'] == 'This is a correct description'
    assert context['results'][0]['docid'] == doc_id
    feedback_key = context['results'][0]['key']

    response = test_client.post("/response", data={"pk": feedback_key,
                                                   "state": "implemented",
                                                   "response": "A response text"})
    assert response.status_code == 200
    assert json.loads(response.data)['message'] == "The feedback has been responded"

    response = test_client.get("/detail", query_string={"pk": feedback_key})
    assert response.status_code == 200
    assert json.loads(response.data)['description'] == "This is a correct description"
    assert json.loads(response.data)['document'] == doc_id
    assert json.loads(response.data)['message'] == 'This is a correct message'
    assert json.loads(response.data)['state'] == 'implemented'
    assert json.loads(response.data)['response'] == 'A response text'

