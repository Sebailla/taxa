# shellcheck disable=SC1089,SC1132,SC2034
# SC1089 fires because shellcheck parses each recipe line as a separate
# script (it doesn't know about Make's .ONESHELL: directive below).
# SC1132 fires because $(VAR) in a Makefile is variable expansion, not
# shell command substitution. SC2034 fires because shellcheck mis-parses
# `format=` inside URL query strings (e.g. COLDP_URL) as a variable
# assignment. All three are false positives when shellcheck runs against
# a Makefile that uses .ONESHELL: + $(VAR) expansion + URL variables.

.PHONY: venv download etl coldp worms col load api clean test smoke css

# Pass each recipe to a single shell invocation so multi-line shell
# constructs (if/then/else/fi, for/done) parse cleanly without `\<newline>`
# continuations. Requires GNU Make 3.82+ — CI (ubuntu-latest) ships 4.x,
# local macOS still ships 3.81 where this directive is silently ignored.
.ONESHELL:

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

# Frontend CSS build — installs the Node toolchain on first run, then
# compiles web/index.css into web/dist/tailwind.css via the Tailwind CLI.
# Run before `make api` (the dev server serves web/dist/tailwind.css).
# Idempotent: npm install is a no-op when node_modules/ is already in sync.
css:
	npm install --no-audit --no-fund
	npm run build:css

download:
	@mkdir -p data/raw
	@if [ ! -f "$(TEXTREE_FILE)" ]; then echo "Downloading TextTree Base from CoL..."; curl -sSL -o "$(TEXTREE_ZIP)" "$(TEXTREE_URL)"; unzip -o -q "$(TEXTREE_ZIP)" -d data/raw/textree_base; else echo "TextTree already downloaded"; fi

etl: download
	.venv/bin/python3 etl/parse_textree.py $(TEXTREE_FILE) $(DB)

coldp:
	@if [ ! -d "$(COLDP_DIR)" ]; then echo "Downloading ColDP from CoL (1 GB)..."; mkdir -p data/raw/coldp; curl -sSL -o data/raw/coldp/coldp.zip "$(COLDP_URL)"; unzip -o -q data/raw/coldp/coldp.zip -d "$(COLDP_DIR)"; else echo "ColDP already extracted at $(COLDP_DIR)"; fi
	.venv/bin/python3 -m etl.load_coldp $(COLDP_DIR) $(DB)

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
	.venv/bin/python3 -m etl.load_worms $(WORMS_TSV)

# Freshwater fish (cladification from the user's Google Sheet) — ISOLATED tree
# with its own synthetic root, separate from CoL and WoRMS. Manual workflow:
# the user exports the Sheet to CSV and drops it at data/raw/freshwater.csv.
#
# The spreadsheet has no explicit parent IDs nor a rank column — rank is
# inferred from which taxonomic columns are populated and the parent chain
# is reconstructed by scripts/transform_freshwater.py. The loader reads the
# flat (freshwater_id, freshwater_parent_id, rank, name, authorship) format
# produced by that step.
#
# Usage:
#   make freshwater                       # load the CSV into taxa.db
#   make load-all                         # col + worms + freshwater
#
# Each is idempotent. Re-running freshwater clears freshwater_id and re-loads.
FRESHWATER_CSV := data/raw/freshwater.csv
freshwater:
	@if [ ! -f $(FRESHWATER_CSV) ]; then echo "Missing $(FRESHWATER_CSV). Export your Freshwater Fishes Google Sheet to CSV and place it at this path."; exit 1; fi
	.venv/bin/python3 scripts/transform_freshwater.py $(FRESHWATER_CSV)
	.venv/bin/python3 -m etl.load_freshwater /tmp/freshwater.flat.csv

# Freshwater fish (cladification from the user's Google Sheet) — ISOLATED tree
# with its own synthetic root, separate from CoL and WoRMS. Manual workflow:
# the user exports the Sheet to CSV and drops it at data/raw/freshwater.csv.
#
# The spreadsheet has no explicit parent IDs nor a rank column — rank is
# inferred from which taxonomic columns are populated and the parent chain
# is reconstructed by scripts/transform_freshwater.py. The loader reads the
# flat (freshwater_id, freshwater_parent_id, rank, name, authorship) format
# produced by that step.
#
# Usage:
#   make freshwater                       # load the CSV into taxa.db
#   make load-all                         # col + worms + freshwater
#
# Each is idempotent. Re-running freshwater clears freshwater_id and re-loads.
FRESHWATER_CSV := data/raw/freshwater.csv
freshwater:
	@if [ ! -f $(FRESHWATER_CSV) ]; then echo "Missing $(FRESHWATER_CSV). Export your Freshwater Fishes Google Sheet to CSV and place it at this path."; exit 1; fi
	.venv/bin/python3 scripts/transform_freshwater.py $(FRESHWATER_CSV)
	.venv/bin/python3 etl/load_freshwater.py /tmp/freshwater.flat.csv

col: etl coldp

load-all: col worms freshwater

# Backwards-compatible selector (kept for the make load SOURCE=... flow)
load:
	@if [ "$(SOURCE)" = "col" ]; then $(MAKE) col; elif [ "$(SOURCE)" = "worms" ]; then $(MAKE) worms; elif [ "$(SOURCE)" = "freshwater" ]; then $(MAKE) freshwater; else echo "Usage: make load SOURCE=col|worms|freshwater  (or: make col / make worms / make freshwater)"; exit 1; fi

# Download + extract WoRMS ColDP (idempotent — skips if already there).
$(WORMS_TSV): $(WORMS_ZIP)
	unzip -o -q $(WORMS_ZIP) -d $(WORMS_DIR)

$(WORMS_ZIP):
	@mkdir -p $(WORMS_DIR)
	@if [ ! -f $(WORMS_TSV) ]; then echo "Downloading WoRMS ColDP (26 MB compressed)..."; curl -sSL -o $(WORMS_ZIP) "$(WORMS_URL)"; unzip -o -q $(WORMS_ZIP) -d $(WORMS_DIR); else echo "WoRMS ColDP already extracted at $(WORMS_DIR)"; fi

api: css
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
	@echo "=== Files tree (registered route — status 200 with DB, 404 without) ==="
	@curl -sS http://127.0.0.1:8765/api/taxon/2707543/files | python3 -c "import json,sys; d=json.load(sys.stdin); assert 'exists' in d; print('files:', d['exists'])"

clean:
	rm -f data/etl.log data/api.log data/load.log
	rm -rf data/db data/raw
	rm -rf .venv __pycache__ */__pycache__
