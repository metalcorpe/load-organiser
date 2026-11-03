"""Beta authorization conventions (#146).

- `policy`: plain rules (actor, roles, audiences). No FastAPI, SQL or settings.
- `sql`: the owner predicate every personal-record query must use.
- `http`: FastAPI dependencies that turn a bearer session into an `Actor`.

Every check is made by the backend on each request; the web app's route guards are
navigation conveniences, not authorization.
"""
