# bw-create-individual-collection
Create a-staff-individual collection for new staff

GITHUB action - run the command that creates the lambda?
GITHBU action - code review


Requires an instance to run on. This would cost money
Claude thinks we can load it into a lambda

GITHUB ACTIONS


name: Deploy Chalice App

on:
  pull_request:
    types: [closed]
    branches:
      - main

jobs:
  deploy:
    # Only run if the PR was actually merged (not just closed)
    if: github.event.pull_request.merged == true
    runs-on: ubuntu-latest

    permissions:
      id-token: write   # needed if using OIDC to assume an AWS role
      contents: read

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install chalice
          pip install -r requirements.txt

      # Option A: Use long-lived AWS credentials stored as secrets
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1

      # Option B (preferred): Use OIDC to assume a role instead of static keys
      # - name: Configure AWS credentials via OIDC
      #   uses: aws-actions/configure-aws-credentials@v4
      #   with:
      #     role-to-assume: arn:aws:iam::123456789012:role/github-actions-deploy-role
      #     aws-region: us-east-1

      - name: Deploy with Chalice
        run: chalice deploy --stage prod


# Password into collection PRODUCTION

This code is meant for chalice deployment

# SETUP
had to install bw with npm install -g @bitwarden/cli

# Workflow

- This code will of course receive the information from the call, which requires 3 items (email, the password and the instance name)
- It will get all the collections from Bitwarden and then loop to find the users (based on external name of the collection)
- Once found it will attempt to add the password to the user's collection
- I will build up the command that will be sent to the AWS System Manager. Which is a bunch of shell commands
- Once the command is built from the user's information and the information required to interact with the BW CLI
- It will run an ssm.send_command command
- Which is to run a shell script to interat with the BW CLI installed on the bw-cli instance Steven Created. 

We have a shell script on the instance that is being invoked by our command that we send

# Setup

To set up this workflow, you will need a 

- IAM account with appropriate permissions
- Lambda
- Linux EC2 instance

## AWS IAM Account permissions

Make sure that the account/role that is executing the lambda has sufficient permissions

```
    {
      "Effect": "Allow",
      "Action": "ssm:SendCommand",
      "Resource": "arn:aws:ssm:us-west-2::document/AWS-RunShellScript"
    }

       {
      "Effect": "Allow",
      "Action": "ssm:SendCommand",
      "Resource": "arn:aws:ec2:us-west-2:588146318465:instance/i-0f6f15e4ca355d223"
    }
```

## EC2 Instance

The EC2 instance must at the minimum be a Small instance

1. Install bw
1. Install jq


## Lambda Code

# Deployment

chalice package packaged/ && aws cloudformation package --template-file ./packaged/sam.json --s3-bucket config-safe --s3-prefix cloudformation/OPS/sam-deployments/techops-onboard-bitwarden --output-template-file sam-packaged.yaml && aws cloudformation deploy --template-file ./sam-packaged.yaml --stack-name techops-onboard-bitwarden

# Troubleshooting

1. Need to figure out permissions required to perform this task. Steven may have added the wrong permission. For testing he added AllowAdminSSM

Error ------
```
when calling the SendCommand operation: User: arn:aws:iam::588146318465:user/techops_automation is not authorized to perform: ssm:SendCommand on resource: arn:aws:ec2:us-west-2:588146318465:instance/i-0f6f15e4ca355d223 because no identity-based policy allows the ssm:SendCommand action
```

1. I was getting an error
botocore.errorfactory.InvocationDoesNotExist: An error occurred (InvocationDoesNotExist) when calling the GetCommandInvocation operation: 
but the command was executing. I think it was the loop in the sample script was erroring out instead of handling when the commands were not True

# Reference

-[Seamlessly Execute Remote Commands on EC2 Instances with AWS Lambda: A Guide to Leveraging AWS Systems Manager](https://medium.com/@kamal.maiti/how-can-aws-lambda-remotely-execute-any-command-on-an-ec2-machine-c07d628c1a1f)
- [](https://stackoverflow.com/questions/25116521/how-do-i-get-a-part-of-the-output-of-a-command-in-linux-bash)