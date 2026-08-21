from __future__ import annotations

import json

from .runner import build_summary


def main() -> None:
    print(json.dumps(build_summary(), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
