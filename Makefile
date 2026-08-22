.PHONY: venv download etl coldp worms col load api clean test smoke

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
	@if [ ! -f $(TEXTREE_FILE) ]; then \  # shellcheck disable=SC1089
		echo "Downloading TextTree Base from CoL..."; \
		curl -sSL -o $(TEXTREE_ZIP) "$(TEXTREE_URL)"; \
		unzip -o -q $(TEXTREE_ZIP) -d data/raw/textree_base; \
	else \  # shellcheck disable=SC1089
		echo "TextTree already downloaded"; \
	fi

etl: download
	.venv/bin/python3 etl/parse_textree.py $(TEXTREE_FILE) $(DB)

coldp:
	@if [ ! -d $(COLDP_DIR) ]; then \  # shellcheck disable=SC1089
		echo "Downloading ColDP from CoL (1 GB)..."; \
		mkdir -p data/raw/coldp; \
		curl -sSL -o data/raw/coldp/coldp.zip "$(COLDP_URL)"; \
		unzip -o -q data/raw/coldp/coldp.zip -d $(COLDP_DIR); \
	else \  # shellcheck disable=SC1089
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

# Freshwater fish (cladification from the user's Google Sheet) — ISOLATED tree
# with its own synthetic root, separate from CoL and WoRMS. Manual workflow:
# the user exports the Sheet to CSV and drops it at data/raw/freshwater.csv.
#
# Usage:
#   make freshwater                       # load the CSV into taxa.db
#   make load-all                         # col + worms + freshwater
#
# Each is idempotent. Re-running freshwater clears freshwater_id and re-loads.
FRESHWATER_CSV := data/raw/freshwater.csv
freshwater:
	@if [ ! -f $(FRESHWATER_CSV) ]; then \
		echo "Missing $(FRESHWATER_CSV). Export your Freshwater Fishes Google Sheet to CSV and place it at this path."; \
		exit 1; \
	fi
	.venv/bin/python3 etl/load_freshwater.py $(FRESHWATER_CSV)

load-all: col worms freshwater

# Backwards-compatible selector (kept for the make load SOURCE=... flow)
load:
	@if [ "$(SOURCE)" = "col" ]; then \  # shellcheck disable=SC1089
		$(MAKE) col; \
	elif [ "$(SOURCE)" = "worms" ]; then \  # shellcheck disable=SC1089
		$(MAKE) worms; \
	elif [ "$(SOURCE)" = "freshwater" ]; then \  # shellcheck disable=SC1089
		$(MAKE) freshwater; \
	else \  # shellcheck disable=SC1089
		echo "Usage: make load SOURCE=col|worms|freshwater  (or: make col / make worms / make freshwater)"; \
		exit 1; \
	fi

# Download + extract WoRMS ColDP (idempotent — skips if already there).
$(WORMS_TSV): $(WORMS_ZIP)
	unzip -o -q $(WORMS_ZIP) -d $(WORMS_DIR)

$(WORMS_ZIP):
	@mkdir -p $(WORMS_DIR)
	@if [ ! -f $(WORMS_TSV) ]; then \  # shellcheck disable=SC1089
		echo "Downloading WoRMS ColDP (26 MB compressed)..."; \
		curl -sSL -o $(WORMS_ZIP) "$(WORMS_URL)"; \
		unzip -o -q $(WORMS_ZIP) -d $(WORMS_DIR); \
	else \  # shellcheck disable=SC1089
		echo "WoRMS ColDP already extracted at $(WORMS_DIR)"; \
	fi

api:
	.venv/bin/python3 -m uvicorn api.server:app --host 127.0.0.1 --port 8765

test:
	@if [ ! -d .venv ]; then echo "missing .venv \u2014 run: make venv"; exit 1; fi
	@.venv/bin/python -m pytest tests/ etl/tests/ -v

# Live smoke test against a running server (requires `make api` in another
# terminal). Use this when you want to confirm a populated taxa.db responds
# as expected; `make test` is the offline pytest suite that runs in CI.
smoke:
	@echo "=== Health ==="
	@curl -sS http://127.0.0.1:8765/api/health | python3 -m json.tool
	@echo "=== Domains ==="
	@curl -sS http://127.0.0.1:8765/api/domains | python3 -m json.tool

clean:
	rm -f data/etl.log data/api.log data/load.log
	rm -rf data/db data/raw
	rm -rf .venv __pycache__ */__pycache__
