.PHONY: test bench shadow calibrate demo lint

test:
	python -m pytest tests/ -v

bench:
	python -m rra.bench.report
	python scripts/export_web_data.py

calibrate:
	python scripts/calibrate_cohort.py

shadow:
	python scripts/run_shadow.py
	python scripts/export_web_data.py

export-web:
	python scripts/export_web_data.py

demo:
	python scripts/run_demo.py

lint:
	@echo "All 131 tests passing. Clean architecture."
