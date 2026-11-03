.PHONY: test bench clean

test:
	python -m pytest -q tests/

bench:
	python bench/harness.py

clean:
	rm -rf results/*.csv results/*.md
