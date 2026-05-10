PYTHON ?= python3
SCHEME_DIR := $(HOME)/.local/share/color-schemes
KONSOLE_DIR := $(HOME)/.local/share/konsole

.PHONY: install install-gui link-schemes link-konsole unlink-schemes uninstall test gen-themes clean flatpak flatpak-install flatpak-run

install:
	@# pipx install --force silently no-ops on .py changes when the version is
	@# unchanged, so explicitly uninstall first.
	-pipx uninstall kolour 2>/dev/null
	pipx install . || $(PYTHON) -m pip install --user --upgrade .
	$(MAKE) link-schemes

install-gui:
	-pipx uninstall kolour 2>/dev/null
	pipx install '.[gui]' || $(PYTHON) -m pip install --user --upgrade '.[gui]'
	$(MAKE) link-schemes

link-schemes:
	@mkdir -p $(SCHEME_DIR)
	@for f in src/kolour/themes/*/*.colors; do \
		ln -sf "$$(realpath $$f)" "$(SCHEME_DIR)/$$(basename $$f)"; \
	done
	@echo "Linked $$(ls src/kolour/themes/*/*.colors | wc -l) colour schemes into $(SCHEME_DIR)"

link-konsole:
	@mkdir -p $(KONSOLE_DIR)
	@for f in src/kolour/konsole/*.colorscheme; do \
		[ -e "$$f" ] || continue; \
		ln -sf "$$(realpath $$f)" "$(KONSOLE_DIR)/$$(basename $$f)"; \
	done
	@echo "Linked Konsole colour schemes into $(KONSOLE_DIR)"

unlink-schemes:
	@for f in src/kolour/themes/*/*.colors; do \
		rm -f "$(SCHEME_DIR)/$$(basename $$f)"; \
	done
	@echo "Removed kolour-managed schemes from $(SCHEME_DIR)"

uninstall: unlink-schemes
	pipx uninstall kolour 2>/dev/null || $(PYTHON) -m pip uninstall -y kolour

test:
	$(PYTHON) -m pytest -q

gen-themes:
	$(PYTHON) tools/generate-colors.py

clean:
	rm -rf build dist *.egg-info src/*.egg-info .pytest_cache .flatpak-builder build-flatpak repo
	find . -type d -name __pycache__ -exec rm -rf {} +

# --- Flatpak --------------------------------------------------------------

FLATPAK_APP_ID := io.github.foofly.kolour
FLATPAK_MANIFEST := flatpak/$(FLATPAK_APP_ID).yml

flatpak:
	flatpak-builder --force-clean --user --install-deps-from=flathub --repo=repo build-flatpak $(FLATPAK_MANIFEST)

flatpak-install:
	flatpak-builder --force-clean --user --install --install-deps-from=flathub build-flatpak $(FLATPAK_MANIFEST)

flatpak-run:
	flatpak run $(FLATPAK_APP_ID) gui
