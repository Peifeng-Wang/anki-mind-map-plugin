"""Configuration merging helpers extracted from the addon entry point.

Kept in :mod:`core` so it is importable without depending on Anki's runtime
modules (``aqt``/``anki``). This makes the function trivial to unit test.
"""
from typing import Any, Tuple


def deep_merge_defaults(user_value: Any, default_value: Any) -> Tuple[Any, bool]:
    """Recursively fill missing defaults into a user-supplied config.

    Returns a tuple ``(merged_value, changed)`` where ``changed`` indicates
    whether ``merged_value`` differs from the original ``user_value``.

    Behaviour:
    - If ``default_value`` is a dict and ``user_value`` is **not** a dict,
      the default replaces the user value entirely (changed=True).
    - If both are dicts, every key from ``default_value`` missing in
      ``user_value`` is filled in. Common keys are merged recursively.
    - For non-dict defaults, the user value is preserved (changed=False);
      missing-key handling is performed at the parent dict level.
    """
    if isinstance(default_value, dict):
        if not isinstance(user_value, dict):
            return default_value, True
        changed = False
        for key, def_val in default_value.items():
            if key not in user_value:
                user_value[key] = def_val
                changed = True
            else:
                merged, was_changed = deep_merge_defaults(user_value[key], def_val)
                user_value[key] = merged
                changed = changed or was_changed
        return user_value, changed

    # For non-dict defaults, only fill in when missing at the dict level.
    return user_value, False
