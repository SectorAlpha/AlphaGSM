"""Core command-dispatch and process-management helpers for AlphaGSM."""

import sys

# Internal workers must boot without loading user/server configuration.
if sys.argv[1:2] != ["--_complete-self-update"]:
    from .main import *
