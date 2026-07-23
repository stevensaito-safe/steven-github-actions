import json
import os
import subprocess
import requests
import shutil


def build_bw_command(args):
    bw_path = os.environ.get("BW_PATH") or 'bw'

    if bw_path.endswith(".js"):
        node = shutil.which("node")
        if not node:
            raise FileNotFoundError("node is required to run the Bitwarden CLI JavaScript entrypoint")
        return [node, bw_path] + args

    return [bw_path] + args



def run_bw(args, env, input_text=None, check=True):
    """Run a bw CLI command and return stdout, stripped."""
    result = subprocess.run(
        build_bw_command(args),
        env=env,
        input=input_text,
        capture_output=True,
        text=True,
    )
    if check and result.returncode != 0:
        raise RuntimeError(f"bw {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()
    # result = subprocess.run(
    #     [BW_PATH] + args,
    #     env=env,
    #     input=input_text,
    #     capture_output=True,
    #     text=True,
    # )
    # if check and result.returncode != 0:
    #     raise RuntimeError(f"bw {' '.join(args)} failed: {result.stderr.strip()}")
    # return result.stdout.strip()


def get_session(env):
    """Log in and unlock the Bitwarden vault, returning a session key.

    Reuses a cached session on Lambda warm starts.
    """
    session_file = "/tmp/bw/session"
    if os.path.exists(session_file):
        with open(session_file) as f:
            return f.read().strip()

    run_bw(["login", "--apikey"], env, check=False)  # no-op if already logged in

    session = run_bw(
        ["unlock", "--passwordenv", "BW_PASSWORD", "--raw"],
        env,
    )
    os.makedirs("/tmp/bw", exist_ok=True)
    with open(session_file, "w") as f:
        f.write(session)

    return session


def create_org_collection(env, organization_id, collection_name):
    """Create a new org collection and return the parsed collection object."""
    payload = {
        "name": collection_name,
        "organizationId": organization_id,
    }
    encoded_payload = run_bw(["encode"], env, input_text=json.dumps(payload))
    raw_collection = run_bw(
        ["create", "org-collection", "--organizationid", organization_id, encoded_payload],
        env,
    )
    return json.loads(raw_collection)


def get_org_api_token(client_id, client_secret):
    """Return a Bitwarden Public API token for organization member management."""
    response = requests.post(
        "https://identity.bitwarden.com/connect/token",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": "api.organization",
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def find_org_member(env, organization_id, user_email):
    """Return an org member matching user_email, or None if absent."""
    raw_members = run_bw(["list", "org-members", "--organizationid", organization_id], env)
    members = json.loads(raw_members)
    return next(
        (m for m in members if (m.get("email") or "").lower() == user_email.lower()),
        None,
    )


def invite_org_member(env, organization_id, user_email, client_id, client_secret):
    """Invite user_email into the Bitwarden organization and return the member object."""
    existing_member = find_org_member(env, organization_id, user_email)
    if existing_member:
        return existing_member

    access_token = get_org_api_token(client_id, client_secret)
    response = requests.post(
        "https://api.bitwarden.com/public/members",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
        },
        json={
            "email": user_email,
            "type": 2,
            "accessAll": False,
            "resetPasswordEnrolled": False,
            "collections": [],
        },
        timeout=30,
    )
    response.raise_for_status()

    invited_member = response.json()
    return invited_member if isinstance(invited_member, dict) else find_org_member(env, organization_id, user_email)


def grant_user_collection_access(env, organization_id, collection, user_email, member=None):
    """Add user_email to the collection's member list and persist via bw edit.

    Returns the updated collection object.
    """
    member = member or find_org_member(env, organization_id, user_email)

    if not member:
        raise RuntimeError(f"No org member found for user '{user_email}'")

    existing_users = collection.get("users") or []
    if not any(u.get("id") == member.get("id") for u in existing_users):
        existing_users.append({
            "id": member.get("id"),
            "readOnly": False,
            "hidePasswords": False,
            "manage": False,
        })

    edit_payload = {
        "id": collection.get("id"),
        "organizationId": organization_id,
        "name": collection.get("name"),
        "users": existing_users,
    }
    encoded_edit_payload = run_bw(["encode"], env, input_text=json.dumps(edit_payload))
    raw_updated = run_bw(
        [
            "edit",
            "--organizationid",
            organization_id,
            "org-collection",
            collection.get("id"),
            encoded_edit_payload,
        ],
        env,
    )
    return json.loads(raw_updated)
