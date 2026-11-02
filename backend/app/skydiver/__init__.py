"""Skydiver beta feature modules, served under ``/api/skydiver/v1``.

Modules here must not import ``app.core.config`` / ``app.core.db`` at import
time; concrete adapters are wired at the application composition root
(``app.main``). See docs/product/architecture.md (A1, A10).
"""
