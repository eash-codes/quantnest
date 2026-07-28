#!/usr/bin/env python3
"""Enforce the DDD dependency rule.

The domain layer must not depend on infrastructure, the web layer, or any
third-party framework. This parses the AST rather than grepping, so that an
import *inside a function body* — a deliberate lazy shim — is allowed while a
module-level import is rejected.

Run standalone or from CI:  python scripts/check_architecture.py
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

DOMAIN = Path("quantnest/domain")

#: Anything the domain must never import at module scope.
FORBIDDEN_PREFIXES = (
    "quantnest.infra",
    "quantnest.api",
    "quantnest.application",
    "fastapi",
    "starlette",
    "sqlalchemy",
    "pydantic",
    "yfinance",
    "jwt",
    "passlib",
    "bcrypt",
    "redis",
)


def module_level_imports(tree: ast.Module):
    """Yield (lineno, module) for imports at module scope only."""
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield node.lineno, alias.name
        elif isinstance(node, ast.ImportFrom):
            if node.level:  # relative import, stays inside the domain
                continue
            if node.module:
                yield node.lineno, node.module


def main() -> int:
    if not DOMAIN.is_dir():
        print(f"error: {DOMAIN} not found; run from the repository root")
        return 2

    violations: list[str] = []

    for path in sorted(DOMAIN.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue

        tree = ast.parse(path.read_text(), filename=str(path))

        for lineno, module in module_level_imports(tree):
            if any(module == p or module.startswith(f"{p}.") for p in FORBIDDEN_PREFIXES):
                violations.append(f"{path}:{lineno}: module-level import of '{module}'")

    if violations:
        print("Domain layer violates the dependency rule:\n")
        for violation in violations:
            print(f"  {violation}")
        print(
            "\nThe domain must depend only on the standard library. Move the "
            "dependency behind a Protocol in quantnest/domain/ports.py, or "
            "import it lazily inside the function that needs it."
        )
        return 1

    checked = len([p for p in DOMAIN.rglob("*.py") if "__pycache__" not in p.parts])
    print(f"Domain layer is clean: {checked} files, no forbidden module-level imports.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
