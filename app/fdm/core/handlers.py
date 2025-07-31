import threading
from contextlib import contextmanager

__all__ = [
    "cascading_delete",
    "is_cascading_delete",
]

local_state = threading.local()


@contextmanager
def cascading_delete():
    local_state.cascading_delete = True
    try:
        yield
    finally:
        local_state.cascading_delete = False


def is_cascading_delete():
    return getattr(local_state, "cascading_delete", False)
