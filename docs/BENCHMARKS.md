# Reproducible local benchmark

The benchmark measures the product boundary, not model quality. It uses a temporary workspace, makes no network request, sends no prompt, and runs through the same plan, event, execution, cancellation, and receipt code as the server.

```bash
.venv/bin/python -m benchmarks.run_benchmark --iterations 10 --json
```

Reported facts:

- plan latency;
- time to the first session event;
- bounded `pwd` execution latency;
- receipt output size;
- cancellation success rate for an approved `sleep` process;
- optional model cost as `null`, because the default benchmark disables the model.

Each latency includes min, median, p95, and max in milliseconds. Compare results only when version, iteration count, architecture, OS load, and filesystem class are comparable. This is not a shell throughput benchmark and it makes no performance promise for DeepSeek or remote MCP clients.
