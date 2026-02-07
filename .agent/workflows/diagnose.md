---
description: Run system diagnostics and tests to check fleet health.
---

1. Run the test suite to verify core logic:
// turbo

```bash
./run_docker.sh --test
```

1. Check the Auditor's recent findings (Proposals):
// turbo

```bash
ls -lt "The_Bridge/Proposals" | head -n 5
```

1. Summarize the diagnostic results. If tests failed or new proposals exist, recommend using `/fix`.
