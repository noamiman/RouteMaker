PYTHON := .venv/bin/python
STREAMLIT := .venv/bin/streamlit

.PHONY: test validate-data smoke-app rebuild update

test:
	$(PYTHON) -m unittest discover tests

validate-data:
	$(PYTHON) scripts/validate_pipeline.py --data-dir app/finalData

smoke-app:
	$(STREAMLIT) run app/main.py --server.headless true --server.port 8510

rebuild:
	$(PYTHON) run_pipeline.py

update:
	$(PYTHON) update_pipeline.py --new-data NEW_DATA/
