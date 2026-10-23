"""Production ASGI entry point for the bundled PayArc web application.

The React build is served from the same origin as FastAPI. API, OpenAPI, and
documentation routes stay owned by the main application; every other browser
GET request receives a static asset or the React application's entry point.
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import unquote

from starlette.responses import FileResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from .main import app as api_app


DIST_DIR = Path(__file__).resolve().parent.parent / "frontend-dist"
INDEX_FILE = DIST_DIR / "index.html"
API_PATHS = ("/api", "/docs", "/redoc", "/openapi.json")


class PayArcProductionApp:
    """Serve the compiled SPA while delegating API and lifespan traffic."""

    def __init__(self, api: ASGIApp) -> None:
        self.api = api

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.api(scope, receive, send)
            return

        path = scope.get("path", "/")
        method = scope.get("method", "GET")
        is_api = path == "/api" or path.startswith("/api/")
        is_api_documentation = path in API_PATHS[1:]

        if method not in {"GET", "HEAD"} or is_api or is_api_documentation or not INDEX_FILE.is_file():
            await self.api(scope, receive, send)
            return

        requested_path = unquote(path).lstrip("/")
        candidate = (DIST_DIR / requested_path).resolve()
        try:
            candidate.relative_to(DIST_DIR.resolve())
        except ValueError:
            candidate = INDEX_FILE

        response = FileResponse(candidate if candidate.is_file() else INDEX_FILE)
        await response(scope, receive, send)


app = PayArcProductionApp(api_app)
