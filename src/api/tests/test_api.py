import json


def test_api_api_key_not_sent(test_client, create_token):
    create_token
    response = test_client.get("/api/events")
    assert response.status_code == 401
    assert response.data == b"Missing tokens"


def test_api_wrong_tokens(test_client, create_token):
    create_token
    api_key = "g345f3g45g345g34"
    api_secret_key = "g5354g345g345g"
    response = test_client.get("/api/events", headers={'X-Api-Key': api_key, 'X-Api-Secret-Key': api_secret_key})
    assert response.status_code == 403
    assert response.data == b"Unauthorized"


def test_api_all_events_no_data(test_client, create_token):
    tokens = create_token
    response = test_client.get("/api/events", headers=tokens, query_string={"min": "-", "max": "+"})
    assert response.status_code == 200
    json.loads(response.data)['events'] == []


def test_api_all_events_incomplete_request(test_client, user_auth, prepare_db, create_token, create_document):
    create_document
    tokens = create_token
    response = test_client.get("/api/events", headers=tokens)
    assert response.status_code == 422
    assert json.loads(response.data)['response'] == "Incomplete request"
    response = test_client.get("/api/events", headers=tokens)
    assert response.status_code == 422
    assert json.loads(response.data)['response'] == "Incomplete request"


def test_api_all_events_all_data(test_client, user_auth, prepare_db, create_token, create_document):
    create_document
    tokens = create_token
    response = test_client.get("/api/events", headers=tokens, query_string={"min": "-", "max": "+"})
    assert response.status_code == 200
    assert json.loads(response.data)['events'][0][1]['full_path'] == "/save?"
    assert json.loads(response.data)['events'][0][1]['user'] == "00000000000000000000"
