# Quick Start: Setting Up Your Secrets

Based on your AWS Secrets Manager setup, here's what you need to do:

## Your Current Setup

- **Secret Name:** `dev/horilla`
- **Secret Region:** `eu-north-1`
- **Secret ARN:** `arn:aws:secretsmanager:eu-north-1:280648354859:secret:dev/horilla-MFwciu`

## Step 1: Add Values to Your Secret

Go to AWS Secrets Manager → `dev/horilla` → **"Retrieve secret value"** → **"Edit"**

Replace the JSON with your actual values (see `SETUP_SECRETS.md` for detailed instructions on getting each value):

```json
{
  "LIGHTSAIL_SSH_PRIVATE_KEY": "-----BEGIN RSA PRIVATE KEY-----\n[your key here]\n-----END RSA PRIVATE KEY-----",
  "DATABASE_USER": "postgres",
  "DATABASE_PASSWORD": "your_actual_password",
  "DATABASE_NAME": "horilla",
  "SECRET_KEY": "django-insecure-...",
  "DEBUG": "False",
  "ALLOWED_HOSTS": "yourdomain.com,3.9.110.17",
  "CSRF_TRUSTED_ORIGINS": "https://yourdomain.com,http://3.9.110.17"
}
```

## Step 2: Configure GitHub Secrets

In your GitHub repository, go to **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

Add these two secrets:

1. **`AWS_ROLE_ARN`**
   - Value: The ARN of your IAM role (e.g., `arn:aws:iam::280648354859:role/github-actions-role`)
   - This role needs permissions to read from Secrets Manager in `eu-north-1`

2. **`AWS_SECRET_NAME`**
   - Value: `dev/horilla` (your secret name)

## Step 3: Verify IAM Role Permissions

Your IAM role needs this policy to read the secret:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret"
      ],
      "Resource": "arn:aws:secretsmanager:eu-north-1:280648354859:secret:dev/horilla-*"
    }
  ]
}
```

## Step 4: Test the Workflow

1. Push a commit to `main` branch, OR
2. Go to **Actions** tab → **Deploy to AWS Lightsail** → **Run workflow**

## Common Issues

### "Secret not found"
- Check that `AWS_SECRET_NAME` in GitHub matches exactly: `dev/horilla`
- Verify the secret exists in `eu-north-1` region
- Check IAM role has permissions for `eu-north-1` region

### "Access denied"
- Verify IAM role trust relationship allows GitHub Actions
- Check IAM role has `secretsmanager:GetSecretValue` permission
- Ensure the role can access secrets in `eu-north-1`

### "SSH connection failed"
- Verify `LIGHTSAIL_SSH_PRIVATE_KEY` in secret is complete (includes BEGIN/END lines)
- Check the key matches the one used for your Lightsail instance
- Ensure Lightsail instance allows SSH from GitHub Actions IPs

## Need Help Getting Values?

See `SETUP_SECRETS.md` for detailed instructions on how to get each secret value.

