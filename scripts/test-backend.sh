#!/usr/bin/env bash
# Run selected backend tests (safe subset that doesn't require a running server)
set -euo pipefail
pytest \
	test/test_prompts.py \
	test/test_planner.py \
	test/test_server_prompt_integration.py \
	test/test_server_plans.py -q -o log_cli=true -o log_cli_level=INFO
