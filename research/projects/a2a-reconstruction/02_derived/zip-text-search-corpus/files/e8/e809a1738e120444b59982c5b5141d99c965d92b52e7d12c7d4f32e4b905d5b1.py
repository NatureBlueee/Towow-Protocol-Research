from __future__ import annotations

from collections import deque
from typing import Iterable


def affected_dependency_closure(
    changed_nodes: Iterable[str],
    dependency_edges: dict[str, list[str]],
) -> list[str]:
    """Return only the downstream relation nodes affected by a defeater.

    dependency_edges maps a node to nodes whose validity depends on it.
    Historical nodes are not deleted; callers create a new RelationVersion for
    the returned closure.
    """
    queue = deque(changed_nodes)
    seen = set(changed_nodes)
    while queue:
        node = queue.popleft()
        for dependent in dependency_edges.get(node, []):
            if dependent not in seen:
                seen.add(dependent)
                queue.append(dependent)
    return sorted(seen)
