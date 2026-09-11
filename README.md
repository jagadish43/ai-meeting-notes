# AI Meeting Notes

## Run the backend

Use Python 3.12+ and install the dependencies declared in `pyproject.toml`
(for example, `uv sync --no-install-project`). Run commands from the repository root.

Create a `.env` file in the repository root with `JWT_SECRET_KEY` and
`JWT_REFRESH_SECRET_KEY`. Generate each value independently with
`openssl rand -hex 32`. Both keys are required, must differ, and must each be at
least 32 bytes. The application refuses to start with missing or invalid keys.
Keep this file private; it is ignored by Git.

`DATABASE_URL` is optional. It defaults to `sqlite:///./meeting_notes.db` for local
use. To use PostgreSQL, set it to your own
`postgresql+psycopg2://USER:PASSWORD@HOST:5432/DATABASE` connection URL.
Registration and login always use this same database.

Start the server with `.venv/bin/python -m uvicorn backend.main:app --reload`.
Open `http://127.0.0.1:8000/docs` to try the API.

## Authentication flow

1. `POST /signup` accepts JSON fields `email`, `name`, and `password` (8–128
   characters). `POST /users/` is an alias using the same registration logic.
2. `POST /login` accepts form fields `username` (your email) and `password`.
   It returns `access_token`, `refresh_token`, and `token_type`.
3. `GET /users/me` requires `Authorization: Bearer <access_token>`.
   In Swagger's Authorize dialog, enter your email in the username field.
4. `POST /refresh` accepts JSON with `refresh_token` and returns a new pair.
   The submitted refresh token is consumed; save the replacement token.
5. `POST /logout` accepts JSON with the current `refresh_token` and revokes it.
   The client should also discard both tokens.

Passwords are hashed with Argon2. Access tokens expire after 30 minutes; refresh
tokens expire after 7 days. Tokens have separate signing keys and explicit
purposes, so refresh tokens cannot be used on protected routes. User IDs are
used as token subjects, and authentication checks that the user still exists.
Token helpers follow the [FastAPI JWT guide](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/).

## Verification and limitations

Run `.venv/bin/python -m unittest discover -s tests -v`. Tests use a temporary
SQLite database and randomly generated test keys, without touching app data.

Table creation at startup supports a fresh database; it does not migrate an
existing schema. An older `Users.password` column needs an explicit migration
to `hashed_password` and safe handling of any old credentials before reuse.

Logout revokes only the submitted refresh token; already-issued access tokens
remain valid until expiry. Refresh rotation rejects reuse of consumed tokens,
but does not revoke the entire token family on reuse. Login rate limiting,
password reset, email verification, and frontend token storage are not included.
Use HTTPS for deployment. PostgreSQL has not been exercised by the local tests.
