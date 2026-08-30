from src.api.app import app
from src.api.routes import router


PUBLIC_ROUTES = {
    ("GET", "/"),
    ("GET", "/api/v1/health"),
}


PROTECTED_ROUTES = {
    ("POST", "/api/v1/execute"),
    ("GET", "/api/v1/executions"),
    ("GET", "/api/v1/metrics"),
    ("GET", "/api/v1/audit"),
    ("GET", "/api/v1/approvals"),
    ("GET", "/api/v1/approvals/{approval_id}"),
    ("POST", "/api/v1/approvals/decision"),
    ("GET", "/api/v1/incidents"),
    ("GET", "/api/v1/incidents/{incident_id}"),
    ("POST", "/api/v1/signals"),
    ("GET", "/api/v1/signals"),
    ("GET", "/api/v1/signals/{signal_id}"),
    (
        "GET",
        "/api/v1/incidents/{incident_id}/signals",
    ),
    (
        "GET",
        "/api/v1/incidents/{incident_id}/rca",
    ),
    (
        "GET",
        "/api/v1/incidents/{incident_id}/rca/latest",
    ),
    (
        "POST",
        "/api/v1/incidents/{incident_id}/rca/analyze",
    ),
}


def _route_entries(routes):
    """
    Convert HTTP routes into method/path pairs.
    """

    entries = set()

    for route in routes:
        path = getattr(
            route,
            "path",
            None,
        )

        methods = getattr(
            route,
            "methods",
            None,
        )

        if (
            path is None
            or methods is None
        ):
            continue

        for method in methods:
            if method in {
                "HEAD",
                "OPTIONS",
            }:
                continue

            entries.add(
                (
                    method,
                    path,
                )
            )

    return entries


def _application_routes():
    """
    Return the application's user-defined routes.

    In the FastAPI version used by this project,
    included API routes remain available through
    router.routes while the application root lives
    directly in app.routes.
    """

    root_routes = {
        entry
        for entry in _route_entries(
            app.routes
        )
        if entry[1] == "/"
    }

    api_routes = _route_entries(
        router.routes
    )

    return (
        root_routes
        | api_routes
    )


def _api_route(
    path: str,
    method: str,
):
    """
    Return one API route by path and method.
    """

    for route in router.routes:
        route_path = getattr(
            route,
            "path",
            None,
        )

        methods = getattr(
            route,
            "methods",
            None,
        ) or set()

        if (
            route_path == path
            and method in methods
        ):
            return route

    raise AssertionError(
        f"Route not found: {method} {path}"
    )


def _root_route(
    path: str,
    method: str,
):
    """
    Return one application-level route.
    """

    for route in app.routes:
        route_path = getattr(
            route,
            "path",
            None,
        )

        methods = getattr(
            route,
            "methods",
            None,
        ) or set()

        if (
            route_path == path
            and method in methods
        ):
            return route

    raise AssertionError(
        f"Route not found: {method} {path}"
    )


def _route_dependencies(
    route,
):
    dependant = getattr(
        route,
        "dependant",
        None,
    )

    if dependant is None:
        return []

    return getattr(
        dependant,
        "dependencies",
        [],
    )


def test_security_inventory_covers_all_application_routes():
    """
    Every user-defined route must be explicitly
    classified as public or protected.
    """

    assert _application_routes() == (
        PUBLIC_ROUTES
        | PROTECTED_ROUTES
    )


def test_only_expected_routes_are_public():
    assert PUBLIC_ROUTES == {
        ("GET", "/"),
        ("GET", "/api/v1/health"),
    }


def test_all_protected_routes_have_dependencies():
    """
    Every protected API route must expose a
    FastAPI dependency.
    """

    for method, path in PROTECTED_ROUTES:
        route = _api_route(
            path,
            method,
        )

        assert _route_dependencies(
            route
        ), (
            f"{method} {path} has no "
            "security dependency"
        )


def test_public_routes_do_not_require_security_dependency():
    """
    Root and health are intentionally public.
    """

    root_route = _root_route(
        "/",
        "GET",
    )

    assert not _route_dependencies(
        root_route
    )

    health_route = _api_route(
        "/api/v1/health",
        "GET",
    )

    assert not _route_dependencies(
        health_route
    )


def test_api_surface_contains_expected_number_of_routes():
    api_routes = _route_entries(
        router.routes
    )

    assert len(api_routes) == 17


def test_protected_api_surface_contains_expected_number_of_routes():
    assert len(
        PROTECTED_ROUTES
    ) == 16