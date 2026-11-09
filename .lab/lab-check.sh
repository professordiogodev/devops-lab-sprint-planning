#!/usr/bin/env bash
# The plan can be fully verified automatically.
if python3 verify.py; then echo "- ✅ sprint-plan.md passes every planning check"; exit 0; else echo "- ❌ sprint-plan.md fails planning checks (see above)"; exit 1; fi
