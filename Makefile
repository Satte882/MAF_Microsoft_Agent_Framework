.PHONY: install run test clean

install:
	python -m pip install -r requirements-lock.txt
	python -m pip install -e . --no-deps

run:
	maf-lab

test:
	pytest --cov=maf_lab --cov-report=term-missing

clean:
	rm -rf .pytest_cache .coverage htmlcov data
