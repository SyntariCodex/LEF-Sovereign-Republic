---
description: Attempt to fix a detected error or test failure automatically.
---

1. Run tests to confirm the failure:
// turbo

```bash
./run_docker.sh --test
```

1. If tests FAIL, analyze the output and fix the code.
   - If `tests/` failed, likely a logic bug.
   - If `run_docker.sh` failed, likely a script bug.

2. If tests PASS, check for `[FIX]` proposals in `The_Bridge/Proposals`.
// turbo

```bash
ls "The_Bridge/Proposals" | grep "\[FIX\]"
```

1. If a proposal exists:
   - Read the proposal file.
   - Implement the fix described in the proposal.
   - Delete the proposal file after fixing.
   - Run tests again to verify.

2. If no errors are found, report "System Healthy".
