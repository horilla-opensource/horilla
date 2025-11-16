# Terraform AWS LightSail Deployment for Horilla

This Terraform configuration deploys the Horilla application on AWS LightSail with a static IP address.

## Prerequisites

1. AWS CLI configured with appropriate credentials
2. Terraform installed (>= 1.0)
3. Docker image pushed to ECR or Docker Hub
4. Domain name ready for DNS configuration

## Setup Steps

### 1. Build and Push Docker Image

First, build your Docker image and push it to AWS ECR using the provided PowerShell script:

```powershell
# Get your AWS account ID
aws sts get-caller-identity --query Account --output text

# Build and push the image
.\build-and-push-to-ecr.ps1 -AccountId "YOUR_ACCOUNT_ID"
```

Or manually:

```bash
# Authenticate Docker to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <your-account-id>.dkr.ecr.us-east-1.amazonaws.com

# Create ECR repository (if not exists)
aws ecr create-repository --repository-name horilla --region us-east-1

# Build the image
docker build -t horilla:latest .

# Tag the image
docker tag horilla:latest <your-account-id>.dkr.ecr.us-east-1.amazonaws.com/horilla:latest

# Push the image
docker push <your-account-id>.dkr.ecr.us-east-1.amazonaws.com/horilla:latest
```

### 2. Configure Terraform Variables

Copy the example variables file and fill in your values:

```powershell
cd terraform
Copy-Item terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` and set:
- `container_image`: Your ECR image URL (from step 1)
- `db_password`: Secure database password
- `django_secret_key`: Generate using:
  ```powershell
  python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
  ```

### 3. Initialize and Deploy

```powershell
cd terraform
terraform init
terraform plan
terraform apply
```

### 4. Configure DNS

After deployment, Terraform will output the static IP address. Configure your DNS:

1. Go to your domain registrar (where sahdiagnostics.com is registered)
2. Add an A record:
   - Name: `hr`
   - Type: `A`
   - Value: `<static-ip-from-terraform-output>`
   - TTL: 300

### 5. Update Container Deployment

When you need to update the application:

1. Build and push a new Docker image using the PowerShell script
2. Update the `container_image` variable in `terraform.tfvars` with the new tag
3. Apply the changes:
   ```powershell
   terraform apply
   ```

## Variables

### Required Variables

- `container_image`: Container image URL (from ECR)
- `db_password`: Database master password
- `django_secret_key`: Django secret key for production

### Optional Variables (with defaults)

- `aws_region`: AWS region (default: "us-east-1")
- `availability_zone`: Availability zone (default: "us-east-1a")
- `container_power`: Container power (default: "nano")
- `container_scale`: Container scale (default: 1)
- `db_username`: Database username (default: "horilla")
- `db_bundle_id`: Database bundle (default: "micro_1_0")
- `allowed_hosts`: Allowed hosts (default: "hr.sahdiagnostics.com")
- `domain_name`: Domain name (default: "hr.sahdiagnostics.com")

## Outputs

After deployment, Terraform will output:

- `static_ip_address`: The static IP to configure in DNS
- `container_service_url`: The container service URL
- `database_endpoint`: Database endpoint (sensitive)
- `database_port`: Database port
- `container_service_name`: Container service name

## Future: Dev and Staging Environments

To add dev and staging environments on EC2, create separate Terraform modules or configurations:

- `terraform/environments/dev/` - EC2 instance for dev
- `terraform/environments/staging/` - EC2 instance for staging

## Cost Optimization

- Start with `nano` power and `micro_1_0` database bundle
- Scale up as needed based on traffic
- Monitor costs in AWS Cost Explorer

## Security Notes

- Never commit `terraform.tfvars` with sensitive values
- Use AWS Secrets Manager for production secrets
- Enable database backups
- Configure security groups appropriately
- Keep `DEBUG=False` in production

## Troubleshooting

### Container service not accessible
- Check that the static IP is attached
- Verify DNS is configured correctly
- Check container service logs in AWS Console

### Database connection issues
- Verify database endpoint and credentials
- Check security groups allow connections
- Ensure database is not publicly accessible (as configured)

### Image pull errors
- Verify ECR authentication
- Check image URI is correct
- Ensure IAM permissions for ECR access

