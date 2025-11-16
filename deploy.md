# Terraform AWS LightSail Deployment for Horilla

This Terraform configuration deploys the Horilla application on AWS LightSail with a static IP address.

## Prerequisites

1. AWS CLI configured with appropriate credentials
2. Terraform installed (>= 1.0)
3. Docker image pushed to ECR or Docker Hub
4. Domain name ready for DNS configuration

## Setup Steps

### 1. Build and Push Docker Image

First, build your Docker image and push it to AWS ECR:

# Authenticate Docker to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <your-account-id>.dkr.ecr.us-east-1.amazonaws.com

# Create ECR repository (if not exists)
aws ecr create-repository --repository-name horilla --region us-east-1

# Build the image
docker build -t horilla:latest .

# Tag the image
docker tag horilla:latest <your-account-id>.dkr.ecr.us-east-1.amazonaws.com/horilla:latest

# Push the image
docker push <your-account-id>.dkr.ecr.us-east-1.amazonaws.com/horilla:latest### 2. Configure Terraform Variables

Copy the example variables file and fill in your values:

cp terraform.tfvars.example terraform.tfvarsEdit `terraform.tfvars` and set:
- `container_image`: Your ECR image URL
- `db_password`: Secure database password
- `django_secret_key`: Generate using `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`

### 3. Initialize and Deploy

cd terraform
terraform init
terraform plan
terraform apply### 4. Configure DNS

After deployment, Terraform will output the static IP address. Configure your DNS:

1. Go to your domain registrar (where sahdiagnostics.com is registered)
2. Add an A record:
   - Name: `hr`
   - Type: `A`
   - Value: `<static-ip-from-terraform-output>`
   - TTL: 300

### 5. Update Container Deployment

When you need to update the application:

1. Build and push a new Docker image
2. Update the `container_image` variable or create a new deployment:

# Update the deployment version in main.tf or use AWS CLI
aws lightsail create-container-service-deployment \
  --service-name horilla-prod \
  --cli-input-json file://deployment.json## Future: Dev and Staging Environments

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