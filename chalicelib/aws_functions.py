# standard libraries
import boto3
import logging

def get_access_token(path):
    """ Returns a token from the AWS parameter store

    Args:
        path (string) : This is a string of the path for the variable that we would like to get from the AWS parameter store

    Returns:
        string: A token, raises if there is an error

    """
    
    try:
        ssm = boto3.client('ssm', region_name='us-west-2')
        access_token = ssm.get_parameter(Name=path, WithDecryption=True)
        token = access_token['Parameter']['Value']
        return token

    except Exception as e:
        logging.error(str(e))
        raise


# def add_item_to_collection(user, password, collection_id, instance_name):
#     """ Add the login item to a collection by using System Manager

#     Args:
#         user (string) : This is the username that'll be used in the bitwarden entry
#         password (string) : This is the password that'll be used in the bitwarden entry
#         collection_id (string) : This is the Staff individual collection id
#         instance_name (string) : This is the instances that'll be used in the name of the bitwarden entry

#     """

#     # Bitwarden Public API Credentials
#     # The EC2 instance that the command will run on
#     INSTANCE_ID = get_access_token('/TechOps/Automation/Bitwarden/bw_instance_id')
#     print(INSTANCE_ID)

#     # Create an SSM client
#     ssm = boto3.client('ssm')

#     # The variables to interact with the BW CLI
#     BW_CLIENT_ID = get_access_token('/TechOps/Automation/Bitwarden/bw_client_id')
#     BW_CLIENT_SECRET = get_access_token('/TechOps/Automation/Bitwarden/bw_client_secret')
#     BW_USER_PASSWORD = get_access_token('/TechOps/Automation/Bitwarden/bw_user_password')
#     # The commands that will be sent to the instance 
#     COMMAND = ' export BW_CLIENTID=' + BW_CLIENT_ID + ' && \
#             export BW_CLIENTSECRET=' + BW_CLIENT_SECRET + ' && \
#             export BW_PASSWORD=' + BW_USER_PASSWORD + ' && \
#             export INSTANCE_NAME=' + instance_name + ' && \
#             export INSTANCE_USERNAME=' + user + '&& \
#             export INSTANCE_PASSWORD=' + password + '&& \
#             export COLLECTION_ID=' + collection_id + ' && \
#             /home/vhosts/bw_scripts/steven_script.sh'

#     # The command that is sent to the instance
#     response = ssm.send_command(
#     InstanceIds=[INSTANCE_ID],
#     DocumentName="AWS-RunShellScript",
#     Parameters={'commands': [COMMAND]}
#     )

#     logging.info(response)

#     ''' EXAMPLE OUTPUT
#     {'Command': {'CommandId': '2c33ac65-9c8d-4f02-b658-9470ca0edfc6', 'DocumentName': 'AWS-RunShellScript', 'DocumentVersion': '$DEFAULT', 'Comment': '', 'ExpiresAfter': datetime.datetime(2024, 4, 29, 16, 53, 30, 646000, tzinfo=tzlocal()), 'Parameters': {'commands': ['mkdir second_folder']}, 'InstanceIds': ['i-0f6f15e4ca355d223'], 'Targets': [], 'RequestedDateTime': datetime.datetime(2024, 4, 29, 14, 53, 30, 646000, tzinfo=tzlocal()), 'Status': 'Pending', 'StatusDetails': 'Pending', 'OutputS3Region': 'us-west-2', 'OutputS3BucketName': '', 'OutputS3KeyPrefix': '', 'MaxConcurrency': '50', 'MaxErrors': '0', 'TargetCount': 1, 'CompletedCount': 0, 'ErrorCount': 0, 'DeliveryTimedOutCount': 0, 'ServiceRole': '', 'NotificationConfig': {'NotificationArn': '', 'NotificationEvents': [], 'NotificationType': ''}, 'CloudWatchOutputConfig': {'CloudWatchLogGroupName': '', 'CloudWatchOutputEnabled': False}, 'TimeoutSeconds': 3600, 'AlarmConfiguration': {'IgnorePollAlarmFailure': False, 'Alarms': []}, 'TriggeredAlarms': []}, 'ResponseMetadata': {'RequestId': '6f4e32ca-4ad5-433b-9999-f029affdc826', 'HTTPStatusCode': 200, 'HTTPHeaders': {'server': 'Server', 'date': 'Mon, 29 Apr 2024 21:53:30 GMT', 'content-type': 'application/x-amz-json-1.1', 'content-length': '906', 'connection': 'keep-alive', 'x-amzn-requestid': '6f4e32ca-4ad5-433b-9999-f029affdc826'}, 'RetryAttempts': 0}}
#     '''