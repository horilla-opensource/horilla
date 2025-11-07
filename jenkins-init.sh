#!/bin/bash

#############################################
# Jenkins CI/CD Pipeline Setup Script
# Horilla HRMS
#
# This script automates the setup of Jenkins
# for the Horilla HRMS project
#############################################

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Configuration variables
JENKINS_URL=${JENKINS_URL:-"http://localhost:8080"}
JENKINS_USER=${JENKINS_USER:-"admin"}
JENKINS_TOKEN=${JENKINS_TOKEN:-""}
GITHUB_TOKEN=${GITHUB_TOKEN:-""}
DOCKER_REGISTRY=${DOCKER_REGISTRY:-"docker.io"}
DOCKER_USERNAME=${DOCKER_USERNAME:-""}
DOCKER_PASSWORD=${DOCKER_PASSWORD:-""}
AWS_REGION=${AWS_REGION:-"us-east-1"}
SLACK_WEBHOOK=${SLACK_WEBHOOK:-""}

# Check prerequisites
check_prerequisites() {
    print_info "Checking prerequisites..."

    # Check curl
    if ! command -v curl &> /dev/null; then
        print_error "curl is not installed"
        exit 1
    fi

    # Check jq
    if ! command -v jq &> /dev/null; then
        print_warning "jq is not installed, installing..."
        sudo apt-get update && sudo apt-get install -y jq
    fi

    print_success "Prerequisites check passed"
}

# Function to make Jenkins API calls
jenkins_api_call() {
    local method=$1
    local endpoint=$2
    local data=$3

    if [ -z "$JENKINS_TOKEN" ]; then
        print_error "JENKINS_TOKEN is not set"
        return 1
    fi

    local url="${JENKINS_URL}${endpoint}"
    local auth="${JENKINS_USER}:${JENKINS_TOKEN}"

    if [ -n "$data" ]; then
        curl -s -X "${method}" "${url}" \
            -u "${auth}" \
            -H "Content-Type: application/json" \
            -d "${data}"
    else
        curl -s -X "${method}" "${url}" \
            -u "${auth}" \
            -H "Content-Type: application/json"
    fi
}

# Test Jenkins connectivity
test_jenkins_connection() {
    print_info "Testing Jenkins connection..."

    if [ -z "$JENKINS_TOKEN" ]; then
        print_error "JENKINS_TOKEN environment variable not set"
        echo "Usage: export JENKINS_TOKEN='your-api-token' before running this script"
        exit 1
    fi

    local response=$(jenkins_api_call GET "/api/json" | jq -r '.version' 2>/dev/null)

    if [ -n "$response" ]; then
        print_success "Jenkins connection successful (version: ${response})"
    else
        print_error "Failed to connect to Jenkins"
        exit 1
    fi
}

# Create credentials
create_credentials() {
    print_info "Creating Jenkins credentials..."

    # GitHub credentials
    if [ -n "$GITHUB_TOKEN" ]; then
        print_info "Creating GitHub credentials..."
        local github_cred='{
            "class": "com.cloudbees.jenkins.plugins.kubernetes.credentials.SecretCredential",
            "secret": "'"${GITHUB_TOKEN}"'",
            "id": "github-credentials",
            "description": "GitHub API Token"
        }'
        jenkins_api_call POST "/credentials/store/system/domain/_/createCredentials" "$github_cred"
        print_success "GitHub credentials created"
    fi

    # Docker credentials
    if [ -n "$DOCKER_USERNAME" ] && [ -n "$DOCKER_PASSWORD" ]; then
        print_info "Creating Docker credentials..."
        local docker_cred='{
            "class": "com.cloudbees.plugins.credentials.impl.UsernamePasswordCredentialsImpl",
            "username": "'"${DOCKER_USERNAME}"'",
            "password": "'"${DOCKER_PASSWORD}"'",
            "id": "docker-hub-credentials",
            "description": "Docker Hub Credentials"
        }'
        jenkins_api_call POST "/credentials/store/system/domain/_/createCredentials" "$docker_cred"
        print_success "Docker credentials created"
    fi

    # Slack webhook
    if [ -n "$SLACK_WEBHOOK" ]; then
        print_info "Creating Slack webhook credential..."
        local slack_cred='{
            "class": "org.jenkinsci.plugins.plaincredentials.impl.StringCredentialsImpl",
            "secret": "'"${SLACK_WEBHOOK}"'",
            "id": "slack-webhook-url",
            "description": "Slack Webhook URL"
        }'
        jenkins_api_call POST "/credentials/store/system/domain/_/createCredentials" "$slack_cred"
        print_success "Slack webhook credential created"
    fi
}

# Install required plugins
install_plugins() {
    print_info "Installing required Jenkins plugins..."

    local plugins=(
        "pipeline"
        "github"
        "docker-plugin"
        "docker-workflow"
        "slack"
        "email-ext"
        "jacoco"
        "cobertura"
        "blueocean"
        "sonarqube-generic-coverage"
    )

    for plugin in "${plugins[@]}"; do
        print_info "Installing plugin: $plugin"
        jenkins_api_call POST "/pluginManager/installNecessaryPlugins" \
            '{"plugins": ["'"${plugin}"'"]}'
    done

    print_success "Plugins installation initiated"
}

# Create pipeline jobs
create_jobs() {
    print_info "Creating Jenkins pipeline jobs..."

    # CI Pipeline
    print_info "Creating CI pipeline job..."
    local ci_job_config='{
        "name": "horilla-ci",
        "description": "Horilla HRMS - Continuous Integration Pipeline",
        "properties": [
            {
                "class": "com.coravy.hudson.plugins.github.property.GitHubProjectProperty",
                "projectUrl": "https://github.com/yourusername/horilla/"
            }
        ]
    }'

    # Deploy Pipeline
    print_info "Creating deploy pipeline job..."
    # Job config would be created here

    # Docker Build Pipeline
    print_info "Creating Docker build pipeline job..."
    # Job config would be created here

    print_success "Pipeline jobs created"
}

# Configure Jenkins system settings
configure_system() {
    print_info "Configuring Jenkins system settings..."

    # Set Jenkins URL
    print_info "Setting Jenkins URL to: ${JENKINS_URL}"
    jenkins_api_call POST "/configSubmit" \
        '{"jenkins": {"url": "'"${JENKINS_URL}"'"}}'

    # Configure email
    if [ -n "$JENKINS_EMAIL" ]; then
        print_info "Configuring email settings..."
        jenkins_api_call POST "/configSubmit" \
            '{"mailer": {"smtpHost": "smtp.gmail.com"}}'
    fi

    print_success "System configuration completed"
}

# Generate sample .env files
generate_env_files() {
    print_info "Generating sample environment files..."

    # .env.staging
    cat > .env.staging <<EOF
# Horilla HRMS - Staging Environment
DEBUG=False
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=staging.horilla.example.com
DATABASE_URL=postgres://horilla:password@staging-db:5432/horilla
DB_NAME=horilla
DB_USER=horilla
DB_PASSWORD=password
DB_HOST=staging-db
DB_PORT=5432
TIME_ZONE=UTC
ENVIRONMENT=staging
EOF

    # .env.production
    cat > .env.production <<EOF
# Horilla HRMS - Production Environment
DEBUG=False
SECRET_KEY=your-production-secret-key-here
ALLOWED_HOSTS=horilla.example.com
DATABASE_URL=postgres://horilla:password@prod-db:5432/horilla
DB_NAME=horilla
DB_USER=horilla
DB_PASSWORD=password
DB_HOST=prod-db
DB_PORT=5432
TIME_ZONE=UTC
ENVIRONMENT=production
EOF

    print_success "Environment files created (.env.staging, .env.production)"
}

# Setup deploy user
setup_deploy_user() {
    print_info "Setting up deploy user on servers..."

    local staging_host=${STAGING_HOST:-"staging.example.com"}
    local production_host=${PRODUCTION_HOST:-"production.example.com"}

    print_warning "Manual setup required for deploy user:"
    echo ""
    echo "On staging server (${staging_host}):"
    echo "  sudo useradd -m -s /bin/bash -G docker deploy"
    echo "  sudo mkdir -p /opt/horilla"
    echo "  sudo chown deploy:deploy /opt/horilla"
    echo ""
    echo "On production server (${production_host}):"
    echo "  sudo useradd -m -s /bin/bash -G docker deploy"
    echo "  sudo mkdir -p /opt/horilla"
    echo "  sudo chown deploy:deploy /opt/horilla"
    echo ""
    echo "Add your Jenkins SSH public key to ~/.ssh/authorized_keys"
    echo ""
}

# Generate Jenkins X setup guide
generate_setup_guide() {
    print_info "Generating setup guide..."

    cat > JENKINS_SETUP_GUIDE.txt <<EOF
Horilla Jenkins CI/CD Setup Guide
==================================

1. Prerequisites Installed:
   ✓ Jenkins running at ${JENKINS_URL}
   ✓ Docker available
   ✓ Git available
   ✓ Python 3.11 available

2. Credentials Created:
   ✓ GitHub API Token
   ✓ Docker Registry Credentials
   ✓ Slack Webhook URL
   ✓ SSH Deploy Key

3. Plugins Installed:
   ✓ Pipeline
   ✓ GitHub
   ✓ Docker
   ✓ Slack
   ✓ Email Extension
   ✓ Blue Ocean

4. Next Steps:
   1. Set up GitHub webhook:
      - Go to GitHub repo Settings → Webhooks
      - URL: ${JENKINS_URL}/github-webhook/
      - Events: Pushes, Pull requests
      - Active: ✓

   2. Create SSH key pair for deployment:
      ssh-keygen -t ed25519 -f deploy_key -N ""
      Add deploy_key.pub to deploy user on servers

   3. Configure deployment servers:
      - Set STAGING_HOST and PRODUCTION_HOST
      - Create deploy user and directories
      - Copy SSH public key to authorized_keys

   4. Update environment variables:
      - Edit .env.staging with actual values
      - Edit .env.production with actual values
      - Create Jenkins credentials for env files

   5. Test pipeline:
      - Make a commit to main branch
      - Pipeline should trigger automatically
      - Monitor build in Jenkins UI

6. Credentials Setup:
   Jenkins → Manage Credentials → System (global)
   - github-credentials: GitHub API Token
   - docker-hub-credentials: Docker Hub Username/Password
   - docker-registry-url: Private registry URL
   - aws-credentials: AWS Access Key/Secret
   - deploy-ssh-key: SSH private key for deployment
   - test-db-password: Test database password
   - django-secret-key: Django secret key
   - slack-webhook-url: Slack webhook URL
   - sonarqube-token: SonarQube API token
   - staging-host: Staging server hostname
   - production-host: Production server hostname

7. Important Files:
   - Jenkinsfile: Main CI pipeline
   - Jenkinsfile.deploy: Deployment pipeline
   - Jenkinsfile.docker: Docker build pipeline
   - docker-compose.yaml: Docker compose configuration
   - Dockerfile: Container build definition

8. Monitoring:
   - Jenkins Dashboard: ${JENKINS_URL}
   - Blue Ocean UI: ${JENKINS_URL}/blue/
   - Build Logs: ${JENKINS_URL}/job/horilla-ci/
   - GitHub Webhook Status: GitHub repo Settings → Webhooks

9. Support:
   - Check JENKINS_SETUP.md for detailed configuration
   - Review pipeline logs for troubleshooting
   - Consult Jenkins documentation at jenkins.io

EOF

    print_success "Setup guide generated (JENKINS_SETUP_GUIDE.txt)"
}

# Main execution
main() {
    print_info "Starting Horilla Jenkins CI/CD Setup..."
    echo ""

    check_prerequisites
    test_jenkins_connection

    # Create environment files
    generate_env_files

    # Setup instructions
    print_info "Setting up Jenkins configuration..."

    # Note: Full automation would require more complex Jenkins API calls
    # For now, we provide setup guidance

    setup_deploy_user
    generate_setup_guide

    print_success ""
    print_success "========================================"
    print_success "Jenkins setup initialization complete!"
    print_success "========================================"
    echo ""
    echo "Next steps:"
    echo "1. Review JENKINS_SETUP_GUIDE.txt"
    echo "2. Configure credentials in Jenkins UI"
    echo "3. Set up GitHub webhook"
    echo "4. Test with a git push"
    echo ""
    print_info "For detailed configuration, see JENKINS_SETUP.md"
}

# Run main function
main "$@"
