
def test_drafts_read_mine(test_client, create_document, captured_templates):
    # TODO to improve: return a json and test that
    response = test_client.get("/drafts")
    assert response.status_code == 200
    assert len(captured_templates) == 1
    template, context = captured_templates[0]
    assert template.name == "draft.html"
    assert "drafts" in context
