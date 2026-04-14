#!/usr/bin/env python3
import os
import sys

print("Bounty solver script is running!")
print(f"TARGET_REPOS = {os.environ.get('TARGET_REPOS')}")
print(f"DRY_RUN = {os.environ.get('DRY_RUN')}")
print("If you see this, the workflow is working.")
sys.exit(0)
