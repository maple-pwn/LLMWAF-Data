from app.main import create_app


def test_review_queue_route_requires_admin(db_session):
    app = create_app()
    review_route = next(route for route in app.routes if getattr(route, "path", None) == "/review-queue")
    dependency_calls = {dependency.call.__name__ for dependency in review_route.dependant.dependencies}
    assert "require_admin_access" in dependency_calls
