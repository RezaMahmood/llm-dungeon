"""Deployment entry point.

Azure Functions' Python v2 (decorator) model requires `function_app.py` at
the deployed package root (backend-deploy.yml deploys `package: "src"`). The
real app and all route registrations live in backend/function_app.py so
every internal module can import via the `backend.` package prefix — the
same convention pytest.ini's `pythonpath = src` already uses for tests. This
file just re-exports that app object.
"""

from backend.function_app import app  # noqa: F401
