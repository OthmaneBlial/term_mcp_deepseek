def test_stream_starts_with_session_hello(client, auth_headers):
    session_response = client.post("/sessions", headers=auth_headers)
    session_id = session_response.get_json()["session_id"]

    response = client.get(
        f"/stream?session_id={session_id}",
        headers=auth_headers,
        buffered=False,
    )
    first_chunk = next(response.response).decode("utf-8")
    response.close()

    assert response.status_code == 200
    assert "event: hello" in first_chunk
    assert f'"session": "{session_id}"' in first_chunk
