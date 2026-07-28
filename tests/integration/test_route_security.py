"""Route-level security audit.

Rather than trusting that each new endpoint remembers to authorise, this walks
the whole route table and asserts the invariant directly.

It exists because `POST /orders` shipped unprotected: it takes ``wallet_id`` in
the body, so it never passed through the path-based ``WalletIdDep`` that
secures every other wallet route. A per-endpoint test would not have caught
that — only an audit over *all* routes does.
"""

from __future__ import annotations

import ast
import importlib
import inspect
import textwrap

import pytest

from quantnest.api.main import create_app

#: Endpoints that are intentionally reachable without a token.
#: Market data is not wallet-scoped, so it leaks nothing about any user.
PUBLIC_ENDPOINTS = {
    ("GET", "/"),
    ("GET", "/health"),
    ("GET", "/portfolio/health"),
    ("POST", "/auth/register"),
    ("POST", "/auth/login"),
    ("POST", "/auth/refresh"),
    ("GET", "/market/quote/{symbol}"),
    ("GET", "/market/quotes"),
    ("GET", "/market/chart/{symbol}"),
    ("GET", "/market/search"),
}

#: Authenticated endpoints that legitimately touch wallets, but only ever the
#: caller's own, derived from ``CurrentUserDep`` rather than from user input.
SELF_SCOPED_ENDPOINTS = {
    ("GET", "/auth/me"),
    ("GET", "/auth/wallets"),
    ("POST", "/auth/wallets"),
    ("POST", "/auth/logout"),
    ("POST", "/auth/logout-all"),
}

ROUTER_MODULES = ("auth", "portfolio", "orders", "history", "market")


def _strip_docstrings(source: str) -> str:
    """Return the handler body with docstrings removed.

    Matching on raw source is unreliable: a docstring that merely *mentions*
    ``authorize_wallet`` would look like a real call. Parsing the AST and
    dropping string-literal statements keeps the check honest.
    """
    try:
        tree = ast.parse(textwrap.dedent(source))
    except SyntaxError:  # pragma: no cover - defensive
        return source

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
            continue
        body = getattr(node, "body", [])
        if (
            body
            and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)
        ):
            node.body = body[1:] or [ast.Pass()]

    return ast.unparse(tree)


def _endpoint_sources() -> dict[tuple[str, str], str]:
    """Map (method, path) -> handler source.

    Read from the router modules directly: this FastAPI version wraps included
    routers in ``_IncludedRouter`` objects, so walking ``app.routes`` misses
    everything mounted through ``include_router``.
    """
    sources: dict[tuple[str, str], str] = {}

    for name in ROUTER_MODULES:
        router = importlib.import_module(f"quantnest.api.{name}").router
        for route in router.routes:
            for method in sorted(set(getattr(route, "methods", set())) - {"HEAD", "OPTIONS"}):
                try:
                    raw = inspect.getsource(route.endpoint)
                except (OSError, TypeError):  # pragma: no cover
                    raw = ""
                # Include the signature (for the *Dep annotations) but strip
                # docstrings so prose cannot masquerade as a real call.
                sources[(method, route.path)] = _strip_docstrings(raw)

    return sources


def _documented_operations() -> list[tuple[str, str]]:
    spec = create_app().openapi()
    return [
        (verb.upper(), path)
        for path, operations in spec["paths"].items()
        for verb in operations
        if verb.upper() in {"GET", "POST", "PUT", "PATCH", "DELETE"}
    ]


def test_every_wallet_route_is_ownership_checked():
    """No route may act on a caller-supplied wallet id without checking it."""
    sources = _endpoint_sources()
    unprotected: list[str] = []

    for method, path in _documented_operations():
        if (method, path) in PUBLIC_ENDPOINTS or (method, path) in SELF_SCOPED_ENDPOINTS:
            continue

        source = sources.get((method, path), "")
        touches_wallet = "{wallet_id}" in path or "wallet_id" in source
        if not touches_wallet:
            continue

        # Either the path-based dependency, or an explicit call for routes
        # that receive the wallet id in the body.
        checked = "WalletIdDep" in source or "authorize_wallet" in source
        if not checked:
            unprotected.append(f"{method} {path}")

    assert not unprotected, (
        "These routes accept a wallet id without verifying ownership:\n  "
        + "\n  ".join(unprotected)
        + "\n\nUse WalletIdDep for a path parameter, or call "
          "auth.authorize_wallet(current_user, wallet_id) for a body field."
    )


def test_every_non_public_route_requires_a_token():
    """Anything not on the public list must demand authentication."""
    sources = _endpoint_sources()
    unauthenticated: list[str] = []

    for method, path in _documented_operations():
        if (method, path) in PUBLIC_ENDPOINTS:
            continue

        source = sources.get((method, path), "")
        authenticated = any(
            marker in source
            for marker in ("CurrentUserDep", "BearerTokenDep", "WalletIdDep", "authorize_wallet")
        )
        if not authenticated:
            unauthenticated.append(f"{method} {path}")

    assert not unauthenticated, (
        "These routes are reachable without a token:\n  "
        + "\n  ".join(unauthenticated)
        + "\n\nAdd CurrentUserDep, or add them to PUBLIC_ENDPOINTS if that is deliberate."
    )


def test_the_public_allowlist_matches_reality():
    """Guard the allowlist itself: a stale entry would silently excuse a route."""
    documented = set(_documented_operations())
    stale = [f"{m} {p}" for (m, p) in PUBLIC_ENDPOINTS | SELF_SCOPED_ENDPOINTS if (m, p) not in documented]

    assert not stale, (
        "These allowlist entries no longer match a real route:\n  " + "\n  ".join(stale)
    )


@pytest.mark.parametrize(
    "method,path",
    sorted(PUBLIC_ENDPOINTS - {("GET", "/market/chart/{symbol}")}),
)
def test_public_endpoints_stay_public(method, path):
    """A public route must not accidentally acquire an auth dependency."""
    sources = _endpoint_sources()
    source = sources.get((method, path), "")

    assert "CurrentUserDep" not in source, f"{method} {path} unexpectedly requires a user"
