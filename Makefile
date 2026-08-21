.PHONY: venv download etl coldp worms col load api clean test

# Base release TextTree: 53 MB compressed, 380 MB uncompressed.
TEXTREE_URL  := https://api.checklistbank.org/dataset/315777/export.zip?format=TextTree
TEXTREE_ZIP  := data/raw/textree_base.zip
TEXTREE_FILE := data/raw/textree_base/dataset-315777.txtree
# ColDP enrichments: 1 GB compressed, several GB extracted.
COLDP_URL    := https://api.checklistbank.org/dataset/315777/export.zip?extended=true&format=ColDP
COLDP_DIR    := data/raw/coldp/extracted
# WoRMS ColDP (dataset 2011) — 26 MB compressed, 187 MB uncompressed.
# Used as enrichment over CoL: matched by (name, rank), worms_id added to
# existing CoL rows, WoRMS-only taxa inserted as new rows.
WORMS_URL    := https://api.checklistbank.org/dataset/2011/export.zip?format=ColDP
WORMS_ZIP    := data/raw/worms_coldp/worms.zip
WORMS_DIR    := data/raw/worms_coldp
WORMS_TSV    := $(WORMS_DIR)/NameUsage.tsv
DB           := data/db/taxa.db

venv:
	python3 -m venv .venv
	.venv/bin/pip install --quiet --upgrade pip
	.venv/bin/pip install --quiet -r requirements.txt

download:
	@mkdir -p data/raw
	@if [ ! -f $(TEXTREE_FILE) ]; then \
		echo "Downloading TextTree Base from CoL..."; \
		curl -sSL -o $(TEXTREE_ZIP) "$(TEXTREE_URL)"; \
		unzip -o -q $(TEXTREE_ZIP) -d data/raw/textree_base; \
	else \
		echo "TextTree already downloaded"; \
	fi

etl: download
	.venv/bin/python3 etl/parse_textree.py $(TEXTREE_FILE) $(DB)

coldp:
	@if [ ! -d $(COLDP_DIR) ]; then \
		echo "Downloading ColDP from CoL (1 GB)..."; \
		mkdir -p data/raw/coldp; \
		curl -sSL -o data/raw/coldp/coldp.zip "$(COLDP_URL)"; \
		unzip -o -q data/raw/coldp/coldp.zip -d $(COLDP_DIR); \
	else \
		echo "ColDP already extracted at $(COLDP_DIR)"; \
	fi
	.venv/bin/python3 etl/load_coldp.py $(COLDP_DIR) $(DB)

# Selector: load sources independently. WoRMS is ENRICHMENT over CoL —
# matched by (name, rank), worms_id added to existing CoL rows, WoRMS-only
# taxa inserted. Run CoL first, then WoRMS to enrich.
#
# Usage:
#   make col                # Catalogue of Life base + ColDP enrichment
#   make worms              # World Register of Marine Species (enrichment)
#   make load-all           # both, in order
#
# Each is idempotent. Re-running worms clears worms_id and re-enriches.
worms: $(WORMS_TSV)
	.venv/bin/python3 etl/load_worms.py $(WORMS_TSV)

col: etl coldp

load-all: col worms

# Backwards-compatible selector (kept for the make load SOURCE=... flow)
load:
	@if [ "$(SOURCE)" = "col" ]; then \
		$(MAKE) col; \
	elif [ "$(SOURCE)" = "worms" ]; then \
		$(MAKE) worms; \
	else \
		echo "Usage: make load SOURCE=col|worms  (or: make col / make worms)"; \
		exit 1; \
	fi

# Download + extract WoRMS ColDP (idempotent — skips if already there).
$(WORMS_TSV): $(WORMS_ZIP)
	unzip -o -q $(WORMS_ZIP) -d $(WORMS_DIR)

$(WORMS_ZIP):
	@mkdir -p $(WORMS_DIR)
	@if [ ! -f $(WORMS_TSV) ]; then \
		echo "Downloading WoRMS ColDP (26 MB compressed)..."; \
		curl -sSL -o $(WORMS_ZIP) "$(WORMS_URL)"; \
		unzip -o -q $(WORMS_ZIP) -d $(WORMS_DIR); \
	else \
		echo "WoRMS ColDP already extracted at $(WORMS_DIR)"; \
	fi

api:
	.venv/bin/python3 -m uvicorn api.server:app --host 127.0.0.1 --port 8765

test:
	@echo "=== Health ==="
	@curl -sS http://127.0.0.1:8765/api/health | python3 -m json.tool
	@echo "=== Domains ==="
	@curl -sS http://127.0.0.1:8765/api/domains | python3 -m json.tool

clean:
	rm -f data/etl.log data/api.log data/load.log
	rm -rf data/db data/raw
	rm -rf .venv __pycache__ */__pycache__
