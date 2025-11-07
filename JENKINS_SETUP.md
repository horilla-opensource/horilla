# Jenkins CI/CD Pipeline Setup for Horilla HRMS

## Overview

This guide provides comprehensive instructions for setting up a complete Jenkins CI/CD pipeline for the Horilla HRMS application. The pipeline includes:

- **Jenkinsfile** - Main CI pipeline (testing, code quality, security scanning)
- **Jenkinsfile.deploy** - Deployment pipeline (staging/production)
- **Jenkinsfile.docker** - Docker image build pipeline

### Pipeline Architecture

```
GitHub Push
    ↓
Jenkinsfile (CI)
├─ Code Quality (Flake8, Pylint, Black, isort, mypy)
├─ Security Scan (Bandit, Safety, Trivy)
├─ Unit Tests (Django tests with coverage)
├─ Docker Build
└─ Push to Registry
    ↓
Jenkinsfile.deploy (CD)
├─ Pre-deployment checks
├─ Database backups
├─ Blue-green deployment
├─ Database migrations
├─ Health checks
└─ Smoke tests
```

---

## Prerequisites

### Jenkins Installation

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y openjdk-17-jdk
wget -q -O - https://pkg.jenkins.io/debian-stable/jenkins.io.key | sudo apt-key add -
sudo sh -c 'echo deb https://pkg.jenkins.io/debian-stable binary/ > /etc/apt/sources.list.d/jenkins.list'
sudo apt-get update
sudo apt-get install -y jenkins

# Start Jenkins
sudo systemctl start jenkins
sudo systemctl enable jenkins
```

### Required Plugins

Install these plugins in Jenkins (Manage Jenkins → Plugin Manager):

**Pipeline & Job Management:**
- Pipeline
- Pipeline: Groovy
- Pipeline: Stage View
- Blue Ocean
- GitHub
- GitHub Branch Source
- Git parameter

**Code Quality & Testing:**
- Warnings Next Generation
- Cobertura Plugin
- JUnit Plugin
- HTML Publisher Plugin

**Docker Integration:**
- Docker
- Docker Pipeline
- Artifactory
- CloudBees Docker Build and Publish

**Security & Scanning:**
- SonarQube Scanner

**Notifications:**
- Slack Notification
- Email Extension
- GitHub Notifications

**Credentials:**
- Credentials Binding
- Plain Credentials

**Infrastructure:**
- SSH Build Agents
- SSH Slaves Plugin

Install plugins:
```bash
# Via Jenkins CLI
java -jar jenkins-cli.jar -s http://localhost:8080 install-plugin \
    pipeline github docker artifactory slack email-ext sonarqube
```

### System Requirements

- **Jenkins Master**: 4GB RAM, 20GB storage
- **Docker**: Latest stable version
- **Git**: For code checkout
- **Python 3.11**: For testing (can be in container)
- **PostgreSQL 16**: For testing database
- **Docker Registry Access**: Docker Hub, private registry, or cloud registries

---

## Jenkins Configuration

### 1. System Configuration

Navigate to **Manage Jenkins → System Configuration**:

#### Jenkins URL
```
http://jenkins.example.com:8080/
```

#### GitHub Configuration
- GitHub API URL: `https://api.github.com`
- GitHub Credentials: (create OAuth token)

#### Email Configuration
```
SMTP Server: smtp.gmail.com
SMTP Port: 465
SMTP Username: your-email@gmail.com
SMTP Password: (app password)
```

#### Slack Configuration
- Team Subdomain: your-workspace
- Integration Token: (Slack API token)
- Channel: #horilla-deployments

---

### 2. Credentials Setup

Create these credentials in **Manage Jenkins → Manage Credentials**:

#### GitHub Credentials
```
Type: Username with password
Username: github-user
Password: (GitHub personal access token)
ID: github-credentials
```

#### Docker Registry Credentials
```
Type: Username with password
Username: docker-username
Password: (Docker API token)
ID: docker-hub-credentials

Type: Username with password
Username: registry-user
Password: (Registry password)
ID: private-registry-credentials
```

#### AWS Credentials (for ECR)
```
Type: AWS Credentials
Access Key: (AWS access key)
Secret Key: (AWS secret key)
ID: aws-credentials
```

#### SSH Deploy Key
```
Type: SSH Username with private key
Username: deploy
Private Key: (deploy SSH private key)
Passphrase: (if key is encrypted)
ID: deploy-ssh-key
```

#### Database Credentials
```
Type: Secret text
Secret: (strong random password)
ID: test-db-password

Type: Secret text
Secret: (Django secret key from https://djecrety.ir)
ID: django-secret-key
```

#### Deployment Hosts
```
Type: Secret text
Secret: staging.example.com
ID: staging-host

Type: Secret text
Secret: prod.example.com
ID: production-host
```

#### SonarQube Token
```
Type: Secret text
Secret: (SonarQube authentication token)
ID: sonarqube-token

Type: Secret text
Secret: http://sonarqube:9000
ID: sonarqube-host
```

#### Slack Webhook
```
Type: Secret text
Secret: https://hooks.slack.com/services/YOUR/WEBHOOK/URL
ID: slack-webhook-url

Type: Secret text
Secret: #horilla-ci-notifications
ID: slack-channel
```

---

### 3. Jenkins Agents/Nodes

Configure build agents for distributed builds:

#### Ubuntu Agent Setup
```bash
# On agent machine
sudo apt-get install -y openjdk-17-jdk git docker.io python3.11

# Create jenkins user
sudo useradd -m -s /bin/bash -G docker jenkins

# Setup agent connection in Jenkins UI
# Manage Jenkins → Manage Nodes → New Node
# Configure as SSH agent
```

**Agent Labels**: `docker`, `python`, `deploy`, `linux`

---

## Pipeline Configuration

### 1. Create Main CI Pipeline

In Jenkins dashboard, **New Item**:

```
Name: horilla-ci
Type: Pipeline
Description: Horilla HRMS - Continuous Integration Pipeline
```

**Configuration:**

**General Tab:**
- GitHub Project: https://github.com/yourusername/horilla
- Build Triggers:
  - ✓ GitHub hook trigger for GITScm polling
  - ✓ Poll SCM: `H/15 * * * *`

**Advanced Project Options:**
- Concurrent builds: Disabled
- Quiet Period: 5 seconds

**Pipeline:**
- Definition: Pipeline script from SCM
- SCM: Git
  - Repository URL: https://github.com/yourusername/horilla.git
  - Credentials: github-credentials
  - Branch Specifier: `*/main` `*/1.0`
  - Additional Behaviours:
    - ✓ Shallow clone (depth: 5)
    - ✓ Sparse Checkout paths: `Jenkinsfile`
- Script Path: `Jenkinsfile`

---

### 2. Create Deployment Pipeline

**New Item:**

```
Name: horilla-deploy
Type: Parametrized Pipeline
Description: Horilla HRMS - Deployment Pipeline
```

**Configuration:**
- Definition: Pipeline script from SCM
- SCM: Git (same as above)
- Script Path: `Jenkinsfile.deploy`

**Build Parameters:**
```groovy
choice(
    name: 'ENVIRONMENT',
    choices: ['staging', 'production'],
    description: 'Target environment'
)
choice(
    name: 'IMAGE_TAG',
    choices: ['latest', 'stable'],
    description: 'Docker image tag'
)
```

---

### 3. Create Docker Build Pipeline

**New Item:**

```
Name: horilla-docker-build
Type: Parametrized Pipeline
Description: Horilla HRMS - Docker Build Pipeline
```

**Configuration:**
- Script Path: `Jenkinsfile.docker`

---

## GitHub Webhook Setup

### Configure GitHub → Jenkins Integration

1. **Generate Jenkins webhook token:**
   - Jenkins → Manage → Configure System
   - GitHub → Add Credentials → Jenkins API Token
   - Username: your-github-user
   - Token: (generate)

2. **GitHub Repository Settings:**
   - Settings → Webhooks → Add webhook
   - Payload URL: `http://jenkins.example.com:8080/github-webhook/`
   - Content type: `application/json`
   - Events:
     - ✓ Pushes
     - ✓ Pull requests
   - Active: ✓

3. **Test webhook:**
   ```bash
   git push origin main
   # Jenkins should trigger build automatically
   ```

---

## Environmental Configuration

### Create Environment-Specific Files

#### .env.staging
```env
# Staging Environment
DEBUG=False
ALLOWED_HOSTS=staging.horilla.example.com
DATABASE_URL=postgres://user:pass@staging-db:5432/horilla
SECRET_KEY=<generate-new-key>
ENVIRONMENT=staging
```

#### .env.production
```env
# Production Environment
DEBUG=False
ALLOWED_HOSTS=horilla.example.com
DATABASE_URL=postgres://user:pass@prod-db:5432/horilla
SECRET_KEY=<generate-new-key>
ENVIRONMENT=production
```

Store these as **Jenkins Credentials**:
- Type: Secret file
- File: .env.staging
- ID: env-staging

---

## Docker Setup

### Docker Registry Configuration

#### Docker Hub
```bash
# Credentials in Jenkins
# Username: docker-username
# Password: Docker Hub API token
```

#### Private Registry (Harbor, Artifactory, etc.)
```
Registry URL: registry.example.com:5000
Username: registry-user
Password: registry-password
```

#### AWS ECR
```bash
# Install AWS CLI on Jenkins agent
aws ecr get-authorization-token --region us-east-1 | \
    docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com
```

#### Google Container Registry
```bash
# Use GCP service account credentials
cat ${GCP_KEY_FILE} | docker login -u _json_key --password-stdin gcr.io
```

---

## Testing Configuration

### Unit Tests

The pipeline runs Django tests with coverage:

```bash
coverage run --source='.' manage.py test
coverage report
coverage xml  # For Jenkins integration
```

### Code Quality Tools

**Flake8** - Code style
```
flake8 . --max-line-length=120 --exclude=migrations,static,media
```

**Pylint** - Code analysis
```
pylint --max-line-length=120 .
```

**Black** - Code formatting
```
black --check --line-length=120 .
```

**isort** - Import sorting
```
isort --check-only --profile black .
```

**mypy** - Type checking
```
mypy . --ignore-missing-imports
```

### Security Scanning

**Bandit** - Security issues
```
bandit -r . -ll -f json -o bandit-report.json
```

**Safety** - Dependency vulnerabilities
```
safety check --json > safety-report.json
```

**Trivy** - Container image scanning
```
trivy image --severity HIGH,CRITICAL ${IMAGE_NAME}
```

---

## Deployment Configuration

### Server Requirements

#### Staging Server
- OS: Ubuntu 20.04+
- Docker & Docker Compose installed
- SSH access configured
- PostgreSQL 16 or managed service
- 2GB RAM, 10GB storage minimum

#### Production Server
- OS: Ubuntu 20.04 LTS
- Docker & Docker Compose installed
- SSH key authentication only
- PostgreSQL 16 with replication/backup
- 4GB+ RAM, 50GB+ storage
- Load balancer (optional)
- CDN for static assets (optional)

### Pre-deployment Checklist

```bash
# On deployment server
sudo apt-get update
sudo apt-get install -y docker.io docker-compose git

# Create deploy user
sudo useradd -m -s /bin/bash -G docker deploy

# Setup SSH key
sudo su - deploy
mkdir -p ~/.ssh
# Add Jenkins public key to ~/.ssh/authorized_keys
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys

# Create deployment directory
mkdir -p /opt/horilla
cd /opt/horilla
git clone https://github.com/yourusername/horilla.git .
```

### Blue-Green Deployment

The deployment pipeline supports blue-green deployments:

```
Current (Blue)
    ↓
New (Green) deployment
    ↓
Health checks
    ↓
Switch traffic to Green
    ↓
Keep Blue as rollback
```

File: `docker-compose.yaml.blue` and `docker-compose.yaml.green`

---

## Monitoring & Logging

### Jenkins Log Levels

Adjust log levels in **Manage Jenkins → System Log**:

```
org.jenkinsci.plugins.workflow: All
hudson.plugins.git: Fine
```

### Build Artifact Retention

- CI Pipeline: Keep 30 builds, 10 artifacts
- Deploy Pipeline: Keep 20 builds, all artifacts
- Docker Build: Keep 30 builds, 5 artifacts

### Jenkins Health Check

```bash
# Monitor Jenkins health
curl http://jenkins.example.com:8080/api/json | jq .

# Check build queue
curl http://jenkins.example.com:8080/queue/api/json | jq .

# Monitor agents
curl http://jenkins.example.com:8080/computer/api/json | jq .
```

---

## Backup & Recovery

### Backup Jenkins Configuration

```bash
#!/bin/bash
BACKUP_DIR=/backups/jenkins
DATE=$(date +%Y%m%d_%H%M%S)

# Backup Jenkins home
tar -czf ${BACKUP_DIR}/jenkins-config-${DATE}.tar.gz \
    --exclude=jobs/*/workspace \
    --exclude=jobs/*/builds/*/log \
    /var/lib/jenkins

# Backup to S3
aws s3 cp ${BACKUP_DIR}/jenkins-config-${DATE}.tar.gz \
    s3://your-backup-bucket/jenkins/
```

### Restore Jenkins

```bash
# Stop Jenkins
sudo systemctl stop jenkins

# Restore backup
cd /var/lib/jenkins
sudo tar -xzf jenkins-config-YYYYMMDD_HHMMSS.tar.gz

# Fix permissions
sudo chown -R jenkins:jenkins /var/lib/jenkins

# Start Jenkins
sudo systemctl start jenkins
```

---

## Troubleshooting

### Common Issues

#### 1. Pipeline fails to load from SCM
**Solution:**
- Check GitHub credentials in Jenkins
- Verify repository URL and branch
- Ensure Jenkinsfile exists in repository

#### 2. Docker login fails
**Solution:**
```bash
# Test credentials
docker login -u ${DOCKER_USERNAME} -p ${DOCKER_PASSWORD} ${REGISTRY}

# Verify registry connectivity
curl -I https://${REGISTRY}
```

#### 3. Tests fail due to database connection
**Solution:**
```bash
# Ensure PostgreSQL is running
docker-compose up -d db

# Check database connectivity
psql -h localhost -U horilla_test -d horilla_test -c "SELECT 1"
```

#### 4. Deployment fails with permission errors
**Solution:**
```bash
# Check deploy user permissions
ssh deploy@example.com "docker ps"

# Fix Docker group permissions
sudo usermod -aG docker deploy
```

#### 5. Health checks fail after deployment
**Solution:**
```bash
# Check application logs
docker-compose logs horilla-web

# Verify health endpoint
curl http://localhost:8000/api/health/

# Check migrations
docker-compose exec horilla-web python3 manage.py showmigrations
```

### Debug Mode

Enable detailed logging:

```groovy
// In Jenkinsfile
env.JENKINS_DEBUG = 'true'
sh 'set -x'  // Enable shell debug
```

### Validate Pipeline Syntax

```bash
# SSH into Jenkins host
curl -d @Jenkinsfile http://jenkins.example.com:8080/pipeline-model-converter/validate
```

---

## Best Practices

### 1. Security

- ✓ Use Jenkins credentials, not hardcoded secrets
- ✓ Rotate API tokens and passwords regularly
- ✓ Use SSH keys for deployment, not passwords
- ✓ Enable CSRF protection in Jenkins
- ✓ Run Jenkins behind a reverse proxy with HTTPS
- ✓ Limit job visibility and execution permissions

### 2. Performance

- ✓ Use distributed agents for parallel builds
- ✓ Cache Docker layers and dependencies
- ✓ Clean up workspace after builds
- ✓ Use shallow clones for Git
- ✓ Run tests in parallel when possible

### 3. Reliability

- ✓ Implement health checks in deployment
- ✓ Use blue-green deployments for zero-downtime
- ✓ Maintain automated rollback capabilities
- ✓ Backup critical data before deployments
- ✓ Monitor pipeline execution and success rates

### 4. Maintenance

- ✓ Review and update pipeline regularly
- ✓ Keep Jenkins and plugins updated
- ✓ Archive build artifacts for auditability
- ✓ Document environment-specific configurations
- ✓ Implement automated testing at every stage

---

## Advanced Configuration

### Multi-branch Pipeline

Support multiple branches with automatic Jenkinsfile detection:

```
New Item → Multibranch Pipeline
SCM:
  - Branches to build: *
  - Script path: Jenkinsfile
```

### Webhook Events Filtering

Filter builds based on branch or path:

```groovy
properties([
    pipelineTriggers([
        githubPush(),
        githubPullRequest(
            branches: [BaseBranchFilter(whitelist: 'main')],
            triggerPhrase: 'run.*test'
        )
    ])
])
```

### SonarQube Integration

Add code quality analysis:

```groovy
stage('SonarQube Analysis') {
    environment {
        SONAR_TOKEN = credentials('sonarqube-token')
    }
    steps {
        sh '''
            sonar-scanner \
                -Dsonar.projectKey=horilla \
                -Dsonar.sources=. \
                -Dsonar.host.url=${SONAR_HOST_URL} \
                -Dsonar.login=${SONAR_TOKEN}
        '''
    }
}
```

---

## References

- [Jenkins Documentation](https://www.jenkins.io/doc/)
- [Jenkins Pipeline](https://www.jenkins.io/doc/book/pipeline/)
- [Docker Plugin](https://plugins.jenkins.io/docker-plugin/)
- [GitHub Plugin](https://plugins.jenkins.io/github/)
- [Slack Integration](https://plugins.jenkins.io/slack/)

---

**Last Updated**: November 2024
**Version**: 1.0
