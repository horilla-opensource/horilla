# How to Get Each Secret Value for AWS Secrets Manager

Your secret name is: **`dev/horilla`** (in region `eu-north-1`)

## Step-by-Step Guide to Get Each Value

### 1. LIGHTSAIL_SSH_PRIVATE_KEY

**Option A: If you already have the key file locally:**
```bash
# On Windows (PowerShell)
Get-Content ~/.ssh/lightsail-key.pem | Out-String

# Or just open the .pem file in a text editor and copy all contents
```

**Option B: Download from AWS Lightsail Console:**
1. Go to AWS Lightsail Console
2. Click on your instance
3. Go to **"Account"** → **"SSH keys"** tab
4. Download the default key or the key associated with your instance
5. Open the downloaded `.pem` file and copy the entire contents

**Important:** Copy the ENTIRE key including:
```
-----BEGIN RSA PRIVATE KEY-----
[all the encoded content]
-----END RSA PRIVATE KEY-----
```

### 2. DATABASE_USER, DATABASE_PASSWORD, DATABASE_NAME

**Get from AWS RDS Console:**
1. Go to AWS RDS Console → **Databases**
2. Click on your database: `ls-55259936bea462f21e2453f3a91f5f072171ca31`
3. Check the **"Configuration"** tab:
   - **Master username** = `DATABASE_USER`
   - **Database name** = `DATABASE_NAME` (check "Connectivity & security" → "Database name")
4. For **DATABASE_PASSWORD**:
   - If you remember it, use that
   - If you forgot it, you'll need to reset it:
     - Go to RDS → Your database → **"Modify"**
     - Scroll to **"Master password"** section
     - Enter new password and save
     - **Note:** This will cause a brief downtime

**Alternative:** Check if you have these values in:
- Your local `.env` file
- Any deployment scripts
- AWS Systems Manager Parameter Store

### 3. SECRET_KEY

**Option A: Generate a new one (recommended for production):**
```bash
# On your local machine (in the horilla project directory)
python manage.py shell
>>> from django.core.management.utils import get_random_secret_key
>>> print(get_random_secret_key())
```

**Option B: Use existing one from local development:**
- Check your local `.env` file in the horilla project
- Look for `SECRET_KEY=...`
- If not found, check `horilla/settings.py` for the default (but don't use the default in production!)

### 4. DEBUG
Set to: `"False"` (as a string, not boolean)

### 5. ALLOWED_HOSTS

**Format:** Comma-separated list of domains/IPs (no spaces)

**Examples:**
- If you have a domain: `"yourdomain.com,www.yourdomain.com,3.9.110.17"`
- If only using IP: `"3.9.110.17"`
- For development: `"*"` (not recommended for production)

**To get your domain:**
- Check your DNS settings
- Check your Lightsail static IP domain (if configured)
- Check your nginx configuration on the Lightsail instance

### 6. CSRF_TRUSTED_ORIGINS

**Format:** Comma-separated list with full URLs (http:// or https://)

**Examples:**
- If you have HTTPS: `"https://yourdomain.com,https://www.yourdomain.com,http://3.9.110.17"`
- If only HTTP: `"http://3.9.110.17"`
- Must match the URLs users will access the site from

## Creating the Secret in AWS Secrets Manager

1. Go to AWS Secrets Manager Console
2. Click **"Store a new secret"**
3. Select **"Other type of secret"**
4. Select **"Plaintext"** tab
5. Paste this JSON structure (replace with your actual values):

```json
{
  "LIGHTSAIL_SSH_PRIVATE_KEY": "-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEA...\n-----END RSA PRIVATE KEY-----",
  "DATABASE_USER": "postgres",
  "DATABASE_PASSWORD": "your_actual_password",
  "DATABASE_NAME": "horilla",
  "SECRET_KEY": "django-insecure-...",
  "DEBUG": "False",
  "ALLOWED_HOSTS": "yourdomain.com,3.9.110.17",
  "CSRF_TRUSTED_ORIGINS": "https://yourdomain.com,http://3.9.110.17"
}
```

6. Click **"Next"**
7. **Secret name:** `dev/horilla` (or update the workflow to match your name)
8. **Description:** "Horilla deployment secrets"
9. Click **"Next"** → **"Next"** → **"Store"**

## Important Notes

⚠️ **Region Mismatch:** Your secret is in `eu-north-1` but your RDS is in `eu-west-2`. You have two options:

**Option 1:** Move the secret to `eu-west-2` (recommended)
- Create a new secret in `eu-west-2` with the same values
- Update `AWS_SECRET_NAME` in GitHub to use the new secret

**Option 2:** Update the workflow to access secrets from `eu-north-1`
- The workflow can access secrets from a different region, but you may need to specify the region explicitly

## Quick Test: Verify Secret Access

After creating the secret, test if you can access it:

```bash
aws secretsmanager get-secret-value \
  --secret-id dev/horilla \
  --region eu-north-1 \
  --query 'SecretString' \
  --output text | jq .
```

This should display your JSON secret (make sure you have AWS CLI configured with appropriate permissions).

