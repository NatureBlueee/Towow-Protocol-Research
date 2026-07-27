.PHONY: help check env new-study research-index research-view-check research-audit-check

PYTHON ?= python3

help:
	@echo "make check                    Check workspace integrity only"
	@echo "make env                      Print a redacted environment snapshot"
	@echo "make new-study STUDY=<name>   Create an optional blank research project"
	@echo "make research-index           Rebuild A2A catalogs and derived views"
	@echo "make research-view-check      Check A2A catalog and provenance integrity"
	@echo "make research-audit-check     Check A2A capability audit and cross-links"

check:
	$(PYTHON) tools/workspace_check.py

env:
	$(PYTHON) tools/environment_snapshot.py

new-study:
	@test -n "$(STUDY)" || (echo "STUDY is required, for example: make new-study STUDY=capability-formation" && exit 2)
	$(PYTHON) tools/new_study.py --name "$(STUDY)"

research-index:
	PYTHONPYCACHEPREFIX=/tmp/towow-research-pycache $(PYTHON) tools/rebuild_a2a_research_view.py

research-view-check:
	PYTHONPYCACHEPREFIX=/tmp/towow-research-pycache $(PYTHON) tools/check_a2a_research_view.py

research-audit-check:
	PYTHONPYCACHEPREFIX=/tmp/towow-research-pycache $(PYTHON) tools/check_a2a_design_audit.py
