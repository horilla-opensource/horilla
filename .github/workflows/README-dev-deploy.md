# Dev Deploy Workflow Setup Guide

This workflow (`dev-deploy.yml`) automatically deploys Horilla to AWS Lightsail whenever code is pushed or merged into the `main` branch.

## Prerequisites

### 1. GitHub Secrets

You need to configure the following secrets in your GitHub repository:

- **`AWS_ROLE_ARN`**: The ARN of the IAM role that GitHub Actions will assume to access AWS resources
- **`AWS_SECRET_NAME`**: The name of the AWS Secrets Manager secret that contains all configuration

### 2. AWS Secrets Manager Configuration

Create a secret in AWS Secrets Manager with the following JSON structure:

```json
{
  "LIGHTSAIL_SSH_PRIVATE_KEY": "-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----",
  "DATABASE_USER": "your_db_username",
  "DATABASE_PASSWORD": "your_db_password",
  "DATABASE_NAME": "horilla",
  "SECRET_KEY": "your-django-secret-key",
  "DEBUG": "False",
  "ALLOWED_HOSTS": "your-domain.com,3.9.110.17",
  "CSRF_TRUSTED_ORIGINS": "https://your-domain.com,http://3.9.110.17"
}
```

**Note**: If your AWS Secrets Manager uses a different structure (e.g., with prefixes), you may need to adjust the variable names in the workflow file. The workflow supports both prefixed (e.g., `HORILLA_DATABASE_USER`) and non-prefixed variable names.

### 3. AWS IAM Role Setup

The IAM role specified in `AWS_ROLE_ARN` needs the following permissions:

- Access to AWS Secrets Manager (to read secrets)
- Access to Lightsail (if you want to dynamically fetch the static IP)
- Trust relationship with GitHub Actions OIDC provider

Example trust policy:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::YOUR_ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:YOUR_GITHUB_ORG/YOUR_REPO:*"
        }
      }
    }
  ]
}
```

### 4. Lightsail Instance Setup

Your Lightsail instance should have:

- Docker and Docker Compose installed
- Nginx installed and configured to proxy to `127.0.0.1:8000`
- SSH access enabled for the `ec2-user` user
- The SSH private key should be stored in AWS Secrets Manager as `LIGHTSAIL_SSH_PRIVATE_KEY`

### 5. RDS Database

The workflow uses the RDS endpoint:
- **Endpoint**: `ls-55259936bea462f21e2453f3a91f5f072171ca31.cd6g68iwss4x.eu-west-2.rds.amazonaws.com`
- Make sure the database is accessible from your Lightsail instance
- The database credentials should be stored in AWS Secrets Manager

## Workflow Behavior

1. **Triggers**: Runs on push or merge to `main` branch, or manual trigger via `workflow_dispatch`
2. **Build**: Builds the Horilla Docker image from the repository
3. **Deploy**: 
   - Transfers the Docker image to Lightsail via SSH
   - Generates production `docker-compose.deploy.yml` and `.env.deploy` files
   - Deploys the container using Docker Compose
   - Performs health checks
   - Cleans up old Docker images

## Customization

### Adjusting Environment Variable Names

If your AWS Secrets Manager uses different variable names (e.g., with prefixes), edit the "Generate deployment configurations" step in the workflow to match your secret structure.

### Changing Deployment Settings

- **Static IP**: Update `LIGHTSAIL_STATIC_IP` in the workflow
- **RDS Endpoint**: Update `RDS_ENDPOINT` in the workflow
- **SSH User**: Update `SSH_USER` in the workflow (default: `ec2-user`)

## Troubleshooting

### Deployment Fails

1. Check the workflow logs in GitHub Actions
2. SSH into the Lightsail instance and check:
   - Docker container logs: `docker compose -f docker-compose.deploy.yml logs`
   - Container status: `docker compose -f docker-compose.deploy.yml ps`
3. Verify:
   - Database connectivity from Lightsail instance
   - Nginx configuration is correct
   - Environment variables are set correctly

### Health Check Fails

The workflow waits up to 60 seconds for the container to become healthy. If it fails:
- Check application logs for errors
- Verify the database connection
- Ensure the application is listening on port 8000

