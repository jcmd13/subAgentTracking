"""
Compatibility shim for legacy imports like `import src.core`.
"""

from __future__ import annotations

import sys
from pathlib import Path


_package_root = Path(__file__).resolve().parents[1]
if str(_package_root) not in __path__:
    __path__.append(str(_package_root))


for name in ("core", "orchestration", "observability", "subagent_cli"):
    module = sys.modules.get(name)
    if module:
        sys.modules[f"{__name__}.{name}"] = module
        setattr(sys.modules[__name__], name, module)
