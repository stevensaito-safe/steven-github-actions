import json
import os
import subprocess
import requests
import shutil
import logging
import time
logging.getLogger().setLevel(logging.INFO)
logger = logging.getLogger(__name__)

# testing
import socket
import time

# def build_bw_command(args):
#     bw_path = os.environ.get("BW_PATH") or 'bw'

#     if bw_path.endswith(".js"):
#         node = shutil.which("node")
#         if not node:
#             raise FileNotFoundError("node is required to run the Bitwarden CLI JavaScript entrypoint")
#         return [node, bw_path] + args

#     return [bw_path] + args

# BW_PATH = "/opt/bin/bw"

def test_connectivity():
    try:
        start = time.time()
        logger.info("[test] Resolving vault.bitwarden.com...")
        ip = socket.gethostbyname("vault.bitwarden.com")
        logger.info(f"[test] Resolved to {ip} in {time.time()-start:.2f}s")

        start = time.time()
        s = socket.create_connection((ip, 443), timeout=5)
        s.close()
        logger.info(f"[test] TCP connect succeeded in {time.time()-start:.2f}s")
    except Exception as e:
        logger.error(f"[test] Connectivity test failed: {e}")


def run_bw(args, env, input_text=None, check=True):
    """Run a bw CLI command and return stdout, stripped."""
    test_connectivity()
    
    command_str = " ".join(args)
    logger.info(f"[run_bw] Starting: bw {command_str}")
    start_time = time.time()
    
    bw_appdata_dir = "/tmp/bw-config"
    os.makedirs(bw_appdata_dir, exist_ok=True)
    env = {**env, "BITWARDENCLI_APPDATA_DIR": bw_appdata_dir}

    try:
        logger.info("[run_bw] Testing bw binary directly")
        test_start = time.time()
        result = subprocess.run(
            ["bw", "--version"],
            env=env,
            capture_output=True,
            text=True,
            timeout=10,
            stdin=subprocess.DEVNULL,   # <-- add this
        )
        test_elapsed = time.time() - test_start
        logger.info(f"[run_bw] bw --version took {test_elapsed:.2f}s")
        logger.info(f"[run_bw] bw --version stdout: {result.stdout.strip()}")
        if result.stderr.strip():
            logger.info(f"[run_bw] bw --version stderr: {result.stderr.strip()}")
    except subprocess.TimeoutExpired:
        logger.error("[run_bw] bw --version itself timed out after 10s — binary may be broken or hanging on startup")
    except FileNotFoundError as e:
        logger.error(f"[run_bw] bw binary not found: {e}")

    logger.info(f"[run_bw] Executing: bw {command_str}")
    cmd_start = time.time()
    result = subprocess.run(
        ["bw"] + args,
        env=env,
        input=input_text,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL if input_text is None else None,  # <-- only if no input_text is being piped
)
    cmd_elapsed = time.time() - cmd_start
    
    logger.info(f"[run_bw] Command completed in {cmd_elapsed:.2f}s, return code: {result.returncode}")
    if result.stdout:
        logger.debug(f"[run_bw] stdout length: {len(result.stdout)} chars")
    if result.stderr:
        logger.warning(f"[run_bw] stderr: {result.stderr.strip()}")
    
    if check and result.returncode != 0:
        logger.error(f"[run_bw] Command failed: bw {command_str}")
        raise RuntimeError(f"bw {command_str} failed: {result.stderr.strip()}")
    
    total_elapsed = time.time() - start_time
    logger.info(f"[run_bw] Total time for 'bw {command_str}': {total_elapsed:.2f}s")
    return result.stdout.strip()


def get_session(env):
    """Log in and unlock the Bitwarden vault, returning a session key.

    Reuses a cached session on Lambda warm starts.
    """
    session_file = "/tmp/bw/session"
    logger.info("[get_session] Starting get_session")
    
    if os.path.exists(session_file):
        logger.info("[get_session] Found cached session file")
        with open(session_file) as f:
            session = f.read().strip()
            logger.info("[get_session] Using cached session (warm start)")
            return session

    logger.info("[get_session] No cached session, performing login and unlock")
    
    login_start = time.time()
    run_bw(["login", "--apikey"], env, check=False)  # no-op if already logged in
    login_elapsed = time.time() - login_start
    logger.info(f"[get_session] Login step took {login_elapsed:.2f}s")

    unlock_start = time.time()
    session = run_bw(
        ["unlock", "--passwordenv", "BW_PASSWORD", "--raw"],
        env,
    )
    unlock_elapsed = time.time() - unlock_start
    logger.info(f"[get_session] Unlock step took {unlock_elapsed:.2f}s")
    
    os.makedirs("/tmp/bw", exist_ok=True)
    with open(session_file, "w") as f:
        f.write(session)
    logger.info("[get_session] Session cached to file")

    return session


def create_org_collection(env, organization_id, collection_name):
    """Create a new org collection and return the parsed collection object."""
    logger.info(f"[create_org_collection] Creating collection '{collection_name}' in org {organization_id}")
    func_start = time.time()
    
    payload = {
        "name": collection_name,
        "organizationId": organization_id,
    }
    logger.debug(f"[create_org_collection] Payload: {payload}")
    
    encode_start = time.time()
    encoded_payload = run_bw(["encode"], env, input_text=json.dumps(payload))
    encode_elapsed = time.time() - encode_start
    logger.info(f"[create_org_collection] Encode step took {encode_elapsed:.2f}s")
    
    create_start = time.time()
    raw_collection = run_bw(
        ["create", "org-collection", "--organizationid", organization_id, encoded_payload],
        env,
    )
    create_elapsed = time.time() - create_start
    logger.info(f"[create_org_collection] Create step took {create_elapsed:.2f}s")
    
    result = json.loads(raw_collection)
    total_elapsed = time.time() - func_start
    logger.info(f"[create_org_collection] Total time: {total_elapsed:.2f}s, created collection ID: {result.get('id')}")
    return result


def get_org_api_token(client_id, client_secret):
    """Return a Bitwarden Public API token for organization member management."""
    logger.info("[get_org_api_token] Requesting API token")
    req_start = time.time()
    
    try:
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
        req_elapsed = time.time() - req_start
        logger.info(f"[get_org_api_token] Request completed in {req_elapsed:.2f}s, status: {response.status_code}")
        response.raise_for_status()
        token = response.json()["access_token"]
        logger.info("[get_org_api_token] Successfully obtained API token")
        return token
    except requests.exceptions.Timeout:
        logger.error("[get_org_api_token] Request timed out after 30s")
        raise
    except requests.exceptions.RequestException as e:
        logger.error(f"[get_org_api_token] Request failed: {e}")
        raise


def find_org_member(env, organization_id, user_email):
    """Return an org member matching user_email, or None if absent."""
    logger.info(f"[find_org_member] Searching for member with email: {user_email}")
    start = time.time()
    
    raw_members = run_bw(["list", "org-members", "--organizationid", organization_id], env)
    members = json.loads(raw_members)
    logger.info(f"[find_org_member] Found {len(members)} total members in organization")
    
    member = next(
        (m for m in members if (m.get("email") or "").lower() == user_email.lower()),
        None,
    )
    elapsed = time.time() - start
    if member:
        logger.info(f"[find_org_member] Found member, took {elapsed:.2f}s")
    else:
        logger.warning(f"[find_org_member] Member not found, took {elapsed:.2f}s")
    return member


def invite_org_member(env, organization_id, user_email, client_id, client_secret):
    """Invite user_email into the Bitwarden organization and return the member object."""
    logger.info(f"[invite_org_member] Starting invite process for {user_email}")
    func_start = time.time()
    
    existing_member = find_org_member(env, organization_id, user_email)
    if existing_member:
        logger.info(f"[invite_org_member] Member {user_email} already exists, returning existing")
        return existing_member

    logger.info(f"[invite_org_member] Member not found, fetching API token")
    access_token = get_org_api_token(client_id, client_secret)
    
    logger.info(f"[invite_org_member] Sending invite via API for {user_email}")
    invite_start = time.time()
    try:
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
        invite_elapsed = time.time() - invite_start
        status_code = getattr(response, "status_code", "unknown")
        logger.info(f"[invite_org_member] API request completed in {invite_elapsed:.2f}s, status: {status_code}")
        response.raise_for_status()

        invited_member = response.json()
        total_elapsed = time.time() - func_start
        logger.info(f"[invite_org_member] Successfully invited {user_email}, total time: {total_elapsed:.2f}s")
        return invited_member if isinstance(invited_member, dict) else find_org_member(env, organization_id, user_email)
    except requests.exceptions.Timeout:
        logger.error(f"[invite_org_member] Invite request timed out after 30s")
        raise
    except requests.exceptions.RequestException as e:
        logger.error(f"[invite_org_member] Invite request failed: {e}")
        raise


def grant_user_collection_access(env, organization_id, collection, user_email, member=None):
    """Add user_email to the collection's member list and persist via bw edit.

    Returns the updated collection object.
    """
    logger.info(f"[grant_user_collection_access] Granting {user_email} access to collection {collection.get('id')}")
    func_start = time.time()
    
    member = member or find_org_member(env, organization_id, user_email)

    if not member:
        logger.error(f"[grant_user_collection_access] No org member found for user '{user_email}'")
        raise RuntimeError(f"No org member found for user '{user_email}'")
    
    logger.info(f"[grant_user_collection_access] Found member ID: {member.get('id')}")

    existing_users = collection.get("users") or []
    if not any(u.get("id") == member.get("id") for u in existing_users):
        logger.info(f"[grant_user_collection_access] Adding member to collection user list")
        existing_users.append({
            "id": member.get("id"),
            "readOnly": False,
            "hidePasswords": False,
            "manage": False,
        })
    else:
        logger.info(f"[grant_user_collection_access] Member already in collection user list")

    edit_payload = {
        "id": collection.get("id"),
        "organizationId": organization_id,
        "name": collection.get("name"),
        "users": existing_users,
    }
    
    encode_start = time.time()
    encoded_edit_payload = run_bw(["encode"], env, input_text=json.dumps(edit_payload))
    encode_elapsed = time.time() - encode_start
    logger.info(f"[grant_user_collection_access] Encode step took {encode_elapsed:.2f}s")
    
    edit_start = time.time()
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
    edit_elapsed = time.time() - edit_start
    logger.info(f"[grant_user_collection_access] Edit step took {edit_elapsed:.2f}s")
    
    result = json.loads(raw_updated)
    total_elapsed = time.time() - func_start
    logger.info(f"[grant_user_collection_access] Total time: {total_elapsed:.2f}s")
    return result
