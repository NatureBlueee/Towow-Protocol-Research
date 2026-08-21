from __future__ import annotations

import json

from formation import run_experiment


if __name__ == "__main__":
    print(json.dumps(run_experiment(), ensure_ascii=False, indent=2))
