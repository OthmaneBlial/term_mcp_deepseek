from tools.json_rpc import JSONRPCError, JSONRPCServer


def make_dispatcher():
    dispatcher = JSONRPCServer()
    dispatcher.register_method("math/add", lambda a, b: a + b)

    def fail():
        raise JSONRPCError(-32001, "Expected failure", {"retryable": False})

    dispatcher.register_method("test/fail", fail)
    return dispatcher


def test_dispatches_named_params():
    response = make_dispatcher().dispatch(
        {
            "jsonrpc": "2.0",
            "method": "math/add",
            "params": {"a": 2, "b": 5},
            "id": 7,
        }
    )

    assert response == {"jsonrpc": "2.0", "result": 7, "id": 7}


def test_dispatches_positional_params():
    response = make_dispatcher().dispatch(
        {"jsonrpc": "2.0", "method": "math/add", "params": [3, 4], "id": 8}
    )

    assert response["result"] == 7


def test_reports_invalid_request():
    response = make_dispatcher().dispatch({"jsonrpc": "1.0", "method": "math/add", "id": 1})

    assert response["error"]["code"] == -32600


def test_reports_invalid_params_without_internal_trace():
    response = make_dispatcher().dispatch(
        {"jsonrpc": "2.0", "method": "math/add", "params": {"a": 1}, "id": 2}
    )

    assert response["error"]["code"] == -32602
    assert "Traceback" not in str(response)


def test_preserves_structured_jsonrpc_error():
    response = make_dispatcher().dispatch({"jsonrpc": "2.0", "method": "test/fail", "id": 3})

    assert response["error"] == {
        "code": -32001,
        "message": "Expected failure",
        "data": {"retryable": False},
    }


def test_notification_returns_none():
    response = make_dispatcher().dispatch(
        {"jsonrpc": "2.0", "method": "math/add", "params": [1, 2]}
    )

    assert response is None
