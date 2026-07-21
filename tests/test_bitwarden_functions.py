import json

from chalicelib import bitwarden_functions


class DummyResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def test_invite_org_member_returns_existing_member(monkeypatch):
    existing_member = {"id": "member-1", "email": "user@safe.com"}

    monkeypatch.setattr(bitwarden_functions, "find_org_member", lambda env, org_id, email: existing_member)
    monkeypatch.setattr(
        bitwarden_functions,
        "get_org_api_token",
        lambda client_id, client_secret: (_ for _ in ()).throw(AssertionError("token should not be requested")),
    )

    result = bitwarden_functions.invite_org_member({}, "org-1", "user@safe.com", "client", "secret")

    assert result == existing_member


def test_invite_org_member_posts_public_api_invite(monkeypatch):
    recorded = {}

    monkeypatch.setattr(bitwarden_functions, "find_org_member", lambda env, org_id, email: None)
    monkeypatch.setattr(bitwarden_functions, "get_org_api_token", lambda client_id, client_secret: "api-token")

    def fake_post(url, headers=None, json=None, timeout=None):
        recorded["url"] = url
        recorded["headers"] = headers
        recorded["json"] = json
        recorded["timeout"] = timeout
        return DummyResponse({"id": "member-2", "email": "user@safe.com"})

    monkeypatch.setattr(bitwarden_functions.requests, "post", fake_post)

    result = bitwarden_functions.invite_org_member({}, "org-1", "user@safe.com", "client", "secret")

    assert result == {"id": "member-2", "email": "user@safe.com"}
    assert recorded == {
        "url": "https://api.bitwarden.com/public/members",
        "headers": {
            "Content-Type": "application/json",
            "Authorization": "Bearer api-token",
        },
        "json": {
            "email": "user@safe.com",
            "type": 2,
            "accessAll": False,
            "resetPasswordEnrolled": False,
            "collections": [],
        },
        "timeout": 30,
    }


def test_grant_user_collection_access_uses_supplied_member(monkeypatch):
    run_bw_calls = []

    def fake_run_bw(args, env, input_text=None, check=True):
        run_bw_calls.append((args, input_text, check))
        if args == ["encode"]:
            return "encoded-payload"
        if args[:4] == ["edit", "--organizationid", "org-1", "org-collection"]:
            return json.dumps({"id": "collection-1", "name": "A-Staff-Individual/user", "users": [{"id": "member-1"}]})
        raise AssertionError(f"Unexpected bw call: {args}")

    monkeypatch.setattr(bitwarden_functions, "run_bw", fake_run_bw)
    monkeypatch.setattr(
        bitwarden_functions,
        "find_org_member",
        lambda env, org_id, email: (_ for _ in ()).throw(AssertionError("provided member should be used")),
    )

    collection = {"id": "collection-1", "name": "A-Staff-Individual/user", "users": []}
    member = {"id": "member-1", "email": "user@safe.com"}

    updated = bitwarden_functions.grant_user_collection_access(
        {},
        "org-1",
        collection,
        "user@safe.com",
        member=member,
    )

    assert updated == {"id": "collection-1", "name": "A-Staff-Individual/user", "users": [{"id": "member-1"}]}
    assert run_bw_calls[0][0] == ["encode"]
    edit_payload = json.loads(run_bw_calls[0][1])
    assert edit_payload == {
        "id": "collection-1",
        "organizationId": "org-1",
        "name": "A-Staff-Individual/user",
        "users": [
            {
                "id": "member-1",
                "readOnly": False,
                "hidePasswords": False,
                "manage": False,
            }
        ],
    }
    assert run_bw_calls[1][0] == [
        "edit",
        "--organizationid",
        "org-1",
        "org-collection",
        "collection-1",
        "encoded-payload",
    ]