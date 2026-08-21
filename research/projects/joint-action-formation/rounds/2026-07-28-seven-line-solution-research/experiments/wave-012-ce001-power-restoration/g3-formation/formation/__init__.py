"""CE-001 G3 formation/reachability local component model."""


def run_experiment(*args, **kwargs):
    from .runner import run_experiment as implementation

    return implementation(*args, **kwargs)


__all__ = ["run_experiment"]
