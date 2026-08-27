from benchmarks.run_benchmark import run_benchmark


def test_benchmark_is_local_bounded_and_complete(tmp_path):
    report = run_benchmark(iterations=2, workspace=tmp_path)

    assert report["iterations"] == 2
    assert report["model"]["enabled"] is False
    assert report["model"]["cost_usd"] is None
    assert report["metrics"]["plan_latency_ms"]["p95"] >= 0
    assert report["metrics"]["time_to_first_event_ms"]["p95"] >= 0
    assert report["metrics"]["output_bytes"]["max"] > 0
    assert report["metrics"]["cancellation_rate"] == 1.0
