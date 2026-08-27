def test_stream_starts_with_session_hello(client):
    response = client.get("/stream?session_id=session-test", buffered=False)

    first_chunk = next(response.response).decode("utf-8")
    response.close()

    assert response.status_code == 200
    assert "event: hello" in first_chunk
    assert '"session": "session-test"' in first_chunk
