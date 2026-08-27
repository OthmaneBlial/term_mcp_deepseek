def test_mission_control_and_local_assets_are_public(client):
    page = client.get("/")
    stylesheet = client.get("/static/app.css")
    script = client.get("/static/app.js")
    favicon = client.get("/static/favicon.svg")

    assert page.status_code == 200
    assert stylesheet.status_code == 200
    assert script.status_code == 200
    assert favicon.status_code == 200
    html = page.get_data(as_text=True)
    assert 'href="/static/app.css"' in html
    assert 'src="/static/app.js"' in html
    assert "https://" not in html
    assert "Approval-first mission control" in html
    assert "Signed receipt" in html
    assert "Pause" in html
    assert "Cancel" in html
    assert "@media (max-width: 520px)" in stylesheet.get_data(as_text=True)
    javascript = script.get_data(as_text=True)
    assert "sessionStorage" in javascript
    assert "localStorage" not in javascript
    assert "terminal_plan" in javascript
    assert "terminal_pause" in javascript


def test_public_demo_scenarios_do_not_require_a_model_key(client):
    response = client.get("/demo/scenarios")

    assert response.status_code == 200
    scenarios = response.get_json()["scenarios"]
    assert [scenario["command"] for scenario in scenarios] == ["pwd", "sleep 15", "ls -la"]
    assert all(scenario["label"] and scenario["outcome"] for scenario in scenarios)


def test_authenticated_info_exposes_real_ui_boundaries(client, auth_headers):
    response = client.get("/mcp/info", headers=auth_headers)

    assert response.status_code == 200
    info = response.get_json()
    assert info["network_allowed"] is False
    assert info["limits"] == {
        "command_timeout_seconds": 20.0,
        "max_output_bytes": 1_048_576,
        "session_timeout_seconds": 3600,
    }
    assert info["model"]["available"] is False
