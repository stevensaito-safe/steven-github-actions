# Bitwarden onboard
- Invite the staff to Bitwarden
- Create a-staff-individual collection for new staff

# SETUP
had to install bw with npm install -g @bitwarden/cli

# Setup

To set up this workflow, you will need a 

- Docker image in AWS ECR
- Lambda created from Docker image

- [Steven Written Skeleton Documentation](https://safesoftware.atlassian.net/wiki/spaces/IS/pages/edit-v2/3337191606?draftShareId=d4f6a33a-2c14-4adf-bc78-a07250b10de4)

## Lambda Code

# Deployment

## Base Commands

1. Build Docker image

    ```docker build -t PRIVATE_REPO_NAME .```

    - Test it locally if you want (optional but recommended)

        ```docker run -p 9000:8080 PRIVATE_REPO_NAME```

1. Then in another terminal, use this command to test your image creation

    ```curl -XPOST "http://localhost:9000/2015-03-31/functions/function/invocations" -d '{}'```

1. Create an ECR repository (one-time setup)

    ```aws ecr create-repository --repository-name PRIVATE_REPO_NAME --region us-west-2```

1. This returns a repositoryUri like:

    ```588146318465.dkr.ecr.us-west-2.amazonaws.com/PRIVATE_REPO_NAME```

1. Save that value — you'll use it below. Authenticate Docker to ECR

    ```
    aws ecr get-login-password --region us-west-2 | \
    docker login --username AWS --password-stdin 588146318465.dkr.ecr.us-west-2.amazonaws.com
    ```

1. Tag and push the image

    ```
    docker tag PRIVATE_REPO_NAME:latest 588146318465.dkr.ecr.us-west-2.amazonaws.com/PRIVATE_REPO_NAME:latest
    docker push 588146318465.dkr.ecr.us-west-2.amazonaws.com/PRIVATE_REPO_NAME:latest
    ```

### Updating Existing Lambda

```
aws lambda update-function-code \
  --function-name TECHOPS-FUNCTION_NAME \
  --image-uri 588146318465.dkr.ecr.us-west-2.amazonaws.com/PRIVATE_REPO_NAME:latest
```

### Creating New Lambda

```
aws lambda create-function \
  --function-name TECHOPS-FUNCTION_NAME \
  --package-type Image \
  --code ImageUri=588146318465.dkr.ecr.us-west-2.amazonaws.com/PRIVATE_REPO_NAME:latest \
  --role arn:aws:iam::588146318465:role/TechOps-lambda-role \
  --timeout 360 \
  --memory-size 512
```

- If necessary, attach the lambda to a VPC

# Troubleshooting



# Reference

- [Seamlessly Execute Remote Commands on EC2 Instances with AWS Lambda: A Guide to Leveraging AWS Systems Manager](https://medium.com/@kamal.maiti/how-can-aws-lambda-remotely-execute-any-command-on-an-ec2-machine-c07d628c1a1f)
- [](https://stackoverflow.com/questions/25116521/how-do-i-get-a-part-of-the-output-of-a-command-in-linux-bash)