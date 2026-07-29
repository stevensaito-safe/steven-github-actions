import importlib
import sys
import types


class FakeChalice:
    def __init__(self, app_name):
        self.app_name = app_name

    def lambda_function(self):
        return lambda func: func


def load_app_module(monkeypatch):
    import chalicelib.aws_functions as aws_functions

    secrets = {
        "/TechOps/Automation/Bitwarden/bw_client_id": "cli-client-id",
        "/TechOps/Automation/Bitwarden/bw_client_secret": "cli-client-secret",
        "/TechOps/Automation/Bitwarden/bw_user_password": "vault-password",
        "/TechOps/Automation/Bitwarden/client_id": "org-client-id",
        "/TechOps/Automation/Bitwarden/client_secret": "org-client-secret",
    }

    monkeypatch.setattr(aws_functions, "get_access_token", lambda path: secrets[path])
    monkeypatch.setitem(sys.modules, "chalice", types.SimpleNamespace(Chalice=FakeChalice))
    sys.modules.pop("app", None)
    return importlib.import_module("app")


def test_index_invites_then_creates_and_grants(monkeypatch):
    app_module = load_app_module(monkeypatch)
    calls = []
    invited_member = {"id": "member-123", "email": "jilliam.sagun11@safe.com"}

    def fake_get_session(env):
        calls.append(("get_session", dict(env)))
        return "session-token"

    def fake_invite_org_member(env, organization_id, user_email, client_id, client_secret):
        calls.append(("invite", organization_id, user_email, client_id, client_secret, env.get("BW_SESSION")))
        return invited_member

    def fake_create_org_collection(env, organization_id, collection_name):
        calls.append(("create", organization_id, collection_name, env.get("BW_SESSION")))
        return {"id": "collection-123", "name": collection_name, "users": []}

    def fake_grant_user_collection_access(env, organization_id, collection, user_email, member=None):
        calls.append(("grant", organization_id, collection["id"], user_email, member, env.get("BW_SESSION")))
        return {**collection, "users": [member]}

    monkeypatch.setattr(app_module.bitwarden_functions, "get_session", fake_get_session)
    monkeypatch.setattr(app_module.bitwarden_functions, "invite_org_member", fake_invite_org_member)
    monkeypatch.setattr(app_module.bitwarden_functions, "create_org_collection", fake_create_org_collection)
    monkeypatch.setattr(app_module.bitwarden_functions, "grant_user_collection_access", fake_grant_user_collection_access)

    response = app_module.index({"data": {"email": "person@safe.com"}}, None)

    assert response == {
        "status_code": 200,
        "message": "SUCCESS",
        "application": "Bitwarden Collection",
    }
    assert calls[0][0] == "get_session"
    assert calls[1] == (
        "invite",
        app_module.ORGANIZATION_ID,
        "person@safe.com",
        "org-client-id",
        "org-client-secret",
        "session-token",
    )
    assert calls[2] == (
        "create",
        app_module.ORGANIZATION_ID,
        "A-Staff-Individual/person",
        "session-token",
    )
    assert calls[3] == (
        "grant",
        app_module.ORGANIZATION_ID,
        "collection-123",
        "person@safe.com",
        invited_member,
        "session-token",
    )


def test_index_returns_400_when_invite_fails(monkeypatch):
    app_module = load_app_module(monkeypatch)

    monkeypatch.setattr(app_module.bitwarden_functions, "get_session", lambda env: "session-token")
    monkeypatch.setattr(
        app_module.bitwarden_functions,
        "invite_org_member",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("invite failed")),
    )

    response = app_module.index({"data": {"email": "person@safe.com"}}, None)

    assert response == {
        "status_code": 400,
        "message": "invite failed",
        "application": "Bitwarden Collection",
    }