"""Lightweight context manager for grouping multi-note writes."""
from contextlib import contextmanager


@contextmanager
def collection_transaction(col, op_name):
    """Best-effort wrapper for grouping multiple writes.

    Tries Anki's modern ``Collection.transact`` first, then falls back to the
    legacy ``checkpoint`` API, then to a no-op so this also works inside unit
    tests that pass plain mocks.
    """
    cm = None
    transact = getattr(col, "transact", None)
    if callable(transact):
        try:
            cm = transact(op_name)
        except Exception:
            cm = None
    if cm is None:
        checkpoint = getattr(col, "checkpoint", None)
        if callable(checkpoint):
            try:
                cm = checkpoint(op_name)
            except Exception:
                cm = None
    if cm is not None and hasattr(cm, "__enter__"):
        with cm:
            yield
        return
    # Fallback: no transactional support available - just run the body.
    yield
