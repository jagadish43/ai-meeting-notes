"""Run with: .venv/bin/python -m unittest discover -s tests -v"""
import os
import secrets
import tempfile
import unittest
from datetime import timedelta

# Use an isolated temporary database and ephemeral keys, never application credentials.
_test_dir = tempfile.TemporaryDirectory()
os.environ["DATABASE_URL"] = "sqlite:///" + _test_dir.name + "/auth.db"
os.environ["JWT_SECRET_KEY"] = secrets.token_hex(32)
os.environ["JWT_REFRESH_SECRET_KEY"] = secrets.token_hex(32)

import jwt
from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.auth.utils import create_token, token_key, verify_password
from backend.database import Base, SessionLocal, engine
from backend.main import app
from backend.model import User


class AuthTests(unittest.TestCase):
    def setUp(self):
        Base.metadata.drop_all(engine)
        self.client = TestClient(app)
        self.client.__enter__()
        self.data = {"email": "Person@example.com", "name": "Person", "password": "strong-password-123"}

    def tearDown(self):
        self.client.__exit__(None, None, None)

    def signup(self, path="/signup"):
        result = self.client.post(path, json=self.data)
        self.assertEqual(result.status_code, 201, result.text)
        return result.json()

    def login(self):
        result = self.client.post("/login", data={"username": self.data["email"], "password": self.data["password"]})
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(result.headers["cache-control"], "no-store")
        return result.json()

    def me(self, token):
        return self.client.get("/users/me", headers={"Authorization": "Bearer " + token})

    def test_signup_login_and_protected_route(self):
        user = self.signup()
        self.assertEqual(set(user), {"id", "email", "name"})
        with SessionLocal() as db:
            stored = db.scalar(select(User))
            self.assertNotEqual(stored.hashed_password, self.data["password"])
            self.assertTrue(verify_password(self.data["password"], stored.hashed_password))
        tokens = self.login()
        self.assertEqual(tokens["token_type"], "bearer")
        self.assertEqual(self.me(tokens["access_token"]).json(), user)
        self.assertEqual(self.client.get("/users/me").status_code, 401)

    def test_duplicate_and_legacy_signup_route(self):
        self.signup("/users/")
        self.data["email"] = "person@example.com"
        self.assertEqual(self.client.post("/signup", json=self.data).status_code, 409)
        self.data["email"] = "second@example.com"
        self.signup()

    def test_validation(self):
        for field, value in [("email", "invalid"), ("password", "short"), ("name", " ")]:
            with self.subTest(field=field):
                self.assertEqual(self.client.post("/signup", json={**self.data, field: value}).status_code, 422)

    def test_bad_login(self):
        self.signup()
        for email in [self.data["email"], "missing@example.com"]:
            result = self.client.post("/login", data={"username": email, "password": "wrong"})
            self.assertEqual(result.status_code, 401)
            self.assertEqual(result.json()["detail"], "Incorrect email or password")

    def test_invalid_tokens(self):
        user = self.signup()
        tokens = self.login()
        expired, _ = create_token(user["id"], "access", timedelta(seconds=-1))
        missing_user, _ = create_token(999, "access", timedelta(minutes=1))
        claims = jwt.decode(tokens["access_token"], token_key("access"), algorithms=["HS256"])
        forged = jwt.encode({**claims, "sub": "999"}, "wrong-key" * 8, algorithm="HS256")
        wrong_type = jwt.encode({**claims, "type": "refresh"}, token_key("access"), algorithm="HS256")
        incomplete = jwt.encode({"sub": str(user["id"])}, token_key("access"), algorithm="HS256")
        for token in ["garbage", expired, missing_user, forged, wrong_type, incomplete, tokens["refresh_token"]]:
            with self.subTest(token=token[:12]):
                self.assertEqual(self.me(token).status_code, 401)

    def test_refresh_rotation_and_logout(self):
        self.signup()
        tokens = self.login()
        body = {"refresh_token": tokens["refresh_token"]}
        result = self.client.post("/refresh", json=body)
        self.assertEqual(result.status_code, 200, result.text)
        updated = result.json()
        self.assertNotEqual(updated["refresh_token"], tokens["refresh_token"])
        self.assertEqual(self.client.post("/refresh", json=body).status_code, 401)
        self.assertEqual(self.me(updated["access_token"]).status_code, 200)
        current = {"refresh_token": updated["refresh_token"]}
        self.assertEqual(self.client.post("/logout", json=current).status_code, 204)
        self.assertEqual(self.client.post("/refresh", json=current).status_code, 401)
        self.assertEqual(self.me(updated["access_token"]).status_code, 200)

    def test_refresh_rejects_expired_and_access_tokens(self):
        user = self.signup()
        tokens = self.login()
        expired, _ = create_token(user["id"], "refresh", timedelta(seconds=-1))
        for token in [expired, tokens["access_token"], "invalid"]:
            self.assertEqual(self.client.post("/refresh", json={"refresh_token": token}).status_code, 401)

    def test_deleted_user_is_rejected(self):
        self.signup()
        tokens = self.login()
        with SessionLocal() as db:
            db.delete(db.scalar(select(User)))
            db.commit()
        self.assertEqual(self.me(tokens["access_token"]).status_code, 401)
        self.assertEqual(self.client.post("/refresh", json={"refresh_token": tokens["refresh_token"]}).status_code, 401)


if __name__ == "__main__":
    unittest.main()
