# ==========================================================
# Copyright (c) 2026 ArtistBots
# Channel : https://t.me/artistbots
# ==========================================================
from pathlib import Path


def _list_modules():
    """List every module in this package (relative dotted names), excluding __init__.py."""
    mod_dir = Path(__file__).parent
    modules = []
    for file in mod_dir.rglob("*.py"):
        if file.is_file() and file.name != "__init__.py":
            relative_path = file.relative_to(mod_dir)
            module_path = str(relative_path.with_suffix("")).replace("\\", ".").replace("/", ".")
            modules.append(module_path)
    return modules


all_modules = frozenset(sorted(_list_modules()))
