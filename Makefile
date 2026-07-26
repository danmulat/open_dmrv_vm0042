.PHONY: install test lint synthetic app

install:
	python -m pip install -e ".[dev]"

test:
	pytest

lint:
	ruff check src tests examples

synthetic:
	open-dmrv synthetic --output outputs

app:
	streamlit run src/open_dmrv/app.py
