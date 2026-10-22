import sys
import os

# Ensure project root is in sys.path for serverless resolution
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app

# ---------------------------------------------------------------------------
# Vercel Path Fix Middleware
# ---------------------------------------------------------------------------
# When Vercel rewrites all routes to /api/index.py, the ASGI scope["path"]
# is set to the destination path (/api/index), NOT the original request URL.
# Vercel injects the original URL in the "x-vercel-forwarded-path" or
# "x-matched-path" header, or we can recover it from "x-forwarded-uri".
# This middleware restores the original path so FastAPI routing works correctly.
# ---------------------------------------------------------------------------
from starlette.types import ASGIApp, Receive, Scope, Send


class VercelPathFixMiddleware:
    """Restores the original request path when running behind Vercel's rewrite proxy."""

    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            headers = dict(scope.get("headers", []))
            # Vercel sets x-forwarded-uri to the original request path+query
            original_uri = (
                headers.get(b"x-forwarded-uri", b"").decode("utf-8")
                or headers.get(b"x-vercel-forwarded-path", b"").decode("utf-8")
            )
            if original_uri and original_uri.startswith("/"):
                # Split path from query string
                if "?" in original_uri:
                    original_path, original_qs = original_uri.split("?", 1)
                else:
                    original_path, original_qs = original_uri, ""

                scope["path"] = original_path
                scope["raw_path"] = original_path.encode("utf-8")
                if original_qs:
                    scope["query_string"] = original_qs.encode("utf-8")

        await self._app(scope, receive, send)


# Wrap FastAPI app with the path-fixing middleware
app = VercelPathFixMiddleware(app)
