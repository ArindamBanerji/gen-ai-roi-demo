## Running SOC Playwright Tests

SOC tests MUST run with --workers=1 because:
- 4 specs call the S2P backend (port 8002) which is single-threaded
- Under workers=2, cross-copilot API calls timeout
- This is by design, not a bug

Correct command:
  npx playwright test "tests/e2e" --reporter=list --timeout=60000 --workers=1
