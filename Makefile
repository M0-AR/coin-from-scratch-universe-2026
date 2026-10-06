test:
	PYTHONPATH=src python3 -m pytest tests -q -p no:cacheprovider

demo:
	PYTHONPATH=src python3 coin135.py

experiments:
	PYTHONPATH=src python3 experiments/01_fingerprint.py
	PYTHONPATH=src python3 experiments/02_chain_tamper.py
	PYTHONPATH=src python3 experiments/03_mining_cost.py
	PYTHONPATH=src python3 experiments/04_double_spend.py
	PYTHONPATH=src python3 experiments/05_signatures.py
	PYTHONPATH=src python3 experiments/06_forks.py
	python3 experiments/07_genesis_verify.py
	python3 experiments/08_live_market.py
	PYTHONPATH=src python3 benchmarks/benchmark_pow.py

nodes:
	docker compose up --build

node-local:
	PYTHONPATH=src python3 -m coin.node --port 3001
