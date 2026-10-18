# DeepInsight – perintah pengembangan. Jalankan dari folder v2/.
PY_BOOT ?= python3
CFG_VENV := $(shell sed -n 's/^VENV_DIR=//p' env.cfg | head -n 1)
ifeq ($(origin DEEPINSIGHT_VENV),environment)
VENV := $(DEEPINSIGHT_VENV)
else ifneq ($(CFG_VENV),)
VENV := $(CFG_VENV)
else
VENV := deepenv
endif
PYTHON  := $(VENV)/bin/python
ENGINE  := services/engine

.PHONY: help setup dev dev-engine dev-web lint typecheck test build gen docs-errors clean

help:
	@echo "setup       pasang dependensi Python (env.cfg, bawaan deepenv) dan Node (pnpm)"
	@echo "dev         jalankan engine (127.0.0.1:8000) + tampilan web (127.0.0.1:5173)"
	@echo "lint        ruff, mypy, eslint, prettier"
	@echo "typecheck   tsc di semua paket"
	@echo "test        pytest + vitest"
	@echo "build       build produksi tampilan web (disajikan engine lewat start.py)"
	@echo "gen         ekspor OpenAPI dan bangkitkan tipe TypeScript"
	@echo "docs-errors perbarui docs/ERROR_CODES.md dari registri kode error"

$(PYTHON):
	$(PY_BOOT) -m venv $(VENV) 2>/dev/null || $(PY_BOOT) -m virtualenv $(VENV)

setup: $(PYTHON)
	$(PYTHON) -m pip install -q -e "$(ENGINE)[dev]"
	pnpm install

dev-engine: $(PYTHON)
	$(PYTHON) -m deepinsight_engine

dev-web:
	pnpm --filter @deepinsight/desktop dev

dev: $(PYTHON)
	@trap 'kill 0' INT TERM EXIT; \
	$(PYTHON) -m deepinsight_engine & \
	pnpm --filter @deepinsight/desktop dev & \
	wait

lint: $(PYTHON)
	cd $(ENGINE) && ../../$(VENV)/bin/ruff check . && ../../$(VENV)/bin/ruff format --check . && ../../$(VENV)/bin/mypy
	pnpm lint

typecheck:
	pnpm typecheck

test: $(PYTHON)
	cd $(ENGINE) && ../../$(VENV)/bin/pytest
	pnpm test

build:
	pnpm build

gen: $(PYTHON)
	$(PYTHON) $(ENGINE)/scripts/export_openapi.py packages/shared/openapi.json
	pnpm --filter @deepinsight/shared gen

docs-errors: $(PYTHON)
	$(PYTHON) $(ENGINE)/scripts/export_error_codes.py docs/ERROR_CODES.md

clean:
	rm -rf node_modules apps/*/node_modules packages/*/node_modules apps/desktop/dist
	@case "$(VENV)" in /*|*:*) echo "clean tidak menghapus environment di luar folder: $(VENV)";; *) rm -rf "$(VENV)";; esac
