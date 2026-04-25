_MindMapDialog = None


def __getattr__(name):
    global _MindMapDialog
    if name == "MindMapDialog":
        if _MindMapDialog is None:
            from .main_dialog import MindMapDialog as _MindMapDialog
        return _MindMapDialog
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return ["MindMapDialog"]
