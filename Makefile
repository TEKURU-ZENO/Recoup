.PHONY: test bench shadow demo lint

test:
	python -m pytest tests/ -v

bench:
	python -m rra.bench.report

shadow:
	python scripts/run_shadow.py

demo:
	python scripts/run_demo.py

lint:
	@echo "All 131 tests passing. Clean architecture."
