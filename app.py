import json
import os
from chalice import Chalice

# Setup Logging
import logging
logging.getLogger().setLevel(logging.INFO)

from chalicelib import aws_functions
from chalicelib import bitwarden_functions

app = Chalice(app_name='techops-onboard-bitwarden')

# Bitwarden Password Manager API Credentials
BW_CLIENT_ID = aws_functions.get_access_token('/TechOps/Automation/Bitwarden/bw_client_id')
BW_CLIENT_SECRET = aws_functions.get_access_token('/TechOps/Automation/Bitwarden/bw_client_secret')
BW_USER_PASSWORD = aws_functions.get_access_token('/TechOps/Automation/Bitwarden/bw_user_password')
BW_ORG_CLIENT_ID = aws_functions.get_access_token('/TechOps/Automation/Bitwarden/client_id')
BW_ORG_CLIENT_SECRET = aws_functions.get_access_token('/TechOps/Automation/Bitwarden/client_secret')

# Organization ID
ORGANIZATION_ID = "755241c4-0e40-4924-97b3-af640164e823"

@app.lambda_function()
def index(event, context):
    """ This will onboard a user into Docker and add them to the Google group

    Returns:
        bool: returns True if onboarding was successful, False otherwise
    """
    logging.info("Let's onboard the user into Bitwarden and create a collection for them")
    employee_data = event
    
    # TEST DATA
    # employee_data = {'action': 'CREATE', 'data': {'name': 'Evelyn Saito', 'active_directory': 'ssaito', 'email': 'jilliam.sagun@safe.com', 'position_title': 'IT Support Engineer II', 'team_name': 'IT Support', 'hours_weekly': 40, 'status': 'Full-Time', 'employee_type': 'Permanent', 'co_op': False, 'payment_type': 'Salaried', 'supervisor_email': 'michael.steele@safe.com', 'org_level_1_code': 'IS0000', 'org_level_2_code': 'IS1000', 'org_level_3_code': 'IS1100', 'team_ukg_code': 'PR1100', 'password': 'Blepharosynechia-Cloddish-Aminobenzene-66'}}
    user_email = "jilliam.sagun11@safe.com"

    # user_email = employee_data['data']['email'].strip().lower()

    # Build env for Bitwarden CLI subprocess calls
    env = os.environ.copy()
    env["BITWARDENCLI_APPDATA_DIR"] = "/tmp/bw"
    env["HOME"] = "/tmp"
    env["BW_CLIENTID"] = BW_CLIENT_ID
    env["BW_CLIENTSECRET"] = BW_CLIENT_SECRET
    env["BW_PASSWORD"] = BW_USER_PASSWORD

    session = bitwarden_functions.get_session(env)
    env["BW_SESSION"] = session

    collection_name = user_email.replace("@safe.com", "")
    full_collection_name = f"A-Staff-Individual/{collection_name}"

    try:
        logging.info("Inviting user into Bitwarden organization")
        member = bitwarden_functions.invite_org_member(
            env,
            ORGANIZATION_ID,
            user_email,
            BW_ORG_CLIENT_ID,
            BW_ORG_CLIENT_SECRET,
        )

        logging.info("Lets create the collection and grant access to the user")
        collection = bitwarden_functions.create_org_collection(env, ORGANIZATION_ID, full_collection_name)
        collection = bitwarden_functions.grant_user_collection_access(
            env,
            ORGANIZATION_ID,
            collection,
            user_email,
            member=member,
        )

        logging.debug(json.dumps(collection, indent=2))
        logging.info("Successfully created collection and granted access to user")

        return {
            'status_code' : 200,
            'message' : 'NO ACTION',
            'application' : 'Bitwarden Collection'
            }
    except Exception as error:
        logging.error(str(error))
        return {
            'status_code' : 400,
            'message' : str(error),
            'application' : 'Bitwarden Collection'
            }



index({"user": "jilliam.sagun@safe.com"}, "taa")
