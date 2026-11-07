PYTHONPATH=.:src${PYTHONPATH:+:$PYTHONPATH} pytest tests -n auto
PYTHONPATH=.:src${PYTHONPATH:+:$PYTHONPATH} pytest tests/integration_tests -n auto
PYTHONPATH=.:src${PYTHONPATH:+:$PYTHONPATH} pytest tests/backend_integration_tests -n auto
