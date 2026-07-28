.PHONY: help check env new-study research-index research-view-check research-audit-check research-governance-check research-status research-batch-plan

PYTHON ?= python3

help:
	@echo "make check                    Check workspace integrity only"
	@echo "make env                      Print a redacted environment snapshot"
	@echo "make new-study STUDY=<name>   Create an optional blank research project"
	@echo "make research-index           Rebuild A2A catalogs and derived views"
	@echo "make research-view-check      Check A2A catalog and provenance integrity"
	@echo "make research-audit-check     Check A2A capability audit and cross-links"
	@echo "make research-governance-check Validate bounded research contracts and tests"
	@echo "make research-status          Show the current research truth surface"
	@echo "make research-batch-plan MODE=mock [PROBLEM=v0] [LINE=LINE-...] Plan a version-matched batch"

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

research-governance-check:
	PYTHONPYCACHEPREFIX=/tmp/towow-research-pycache $(PYTHON) tools/researchctl.py validate --strict
	PYTHONPYCACHEPREFIX=/tmp/towow-research-pycache $(PYTHON) -m unittest -v tests.test_researchctl

research-status:
	PYTHONPYCACHEPREFIX=/tmp/towow-research-pycache $(PYTHON) tools/researchctl.py status

research-batch-plan:
	PYTHONPYCACHEPREFIX=/tmp/towow-research-pycache $(PYTHON) tools/researchctl.py batch plan --mode "$(or $(MODE),mock)" $(if $(PROBLEM),--problem "$(PROBLEM)",) $(if $(LINE),--line "$(LINE)",)
