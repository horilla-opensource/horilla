# Jenkins CI/CD Pipeline - Quick Start Guide

## 5-Minute Setup

### 1. Prerequisites
```bash
# Install Jenkins (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install -y openjdk-17-jdk jenkins
sudo systemctl start jenkins

# Install Docker
sudo apt-get install -y docker.io docker-compose

# Verify Jenkins is running
curl http://localhost:8080
```

### 2. Get Initial Admin Password
```bash
sudo cat /var/lib/jenkins/secrets/initialAdminPassword
# Copy this password and login at http://localhost:8080
```

### 3. Install Recommended Plugins
- Jenkins Dashboard → Manage Jenkins → Plugin Manager
- Click "Install suggested plugins"
- Wait for installation to complete

### 4. Create GitHub Personal Access Token
```
GitHub Settings → Developer settings → Personal access tokens → Generate new token
Scopes: repo, admin:repo_hook, admin:org_hook
```

### 5. Add Credentials to Jenkins
Jenkins → Manage Credentials → System → Global credentials → Add credentials

**Type: Secret text**
- ID: `github-token`
- Secret: (paste GitHub token)

**Type: Username with password**
- ID: `docker-hub-credentials`
- Username: (Docker Hub username)
- Password: (Docker Hub API token)

### 6. Create CI Pipeline Job
```
New Item → horilla-ci → Pipeline
Pipeline → Pipeline script from SCM
  SCM: Git
  Repository URL: https://github.com/yourusername/horilla.git
  Branch: */main
  Script path: Jenkinsfile
```

### 7. Set GitHub Webhook
```
GitHub Repository Settings → Webhooks → Add webhook
Payload URL: http://your-jenkins-url:8080/github-webhook/
Content type: application/json
Events: Pushes, Pull requests
Active: ✓
```

### 8. Trigger First Build
```bash
cd horilla
git commit --allow-empty -m "Trigger Jenkins build"
git push origin main
# Watch Jenkins UI for build progress
```

---

## Common Commands

### View Jenkins Logs
```bash
# Local installation
sudo journalctl -u jenkins -f

# Docker installation
docker logs -f jenkins
```

### Access Jenkins CLI
```bash
# Download Jenkins CLI
wget http://localhost:8080/jnlpJars/jenkins-cli.jar

# Run commands
java -jar jenkins-cli.jar -s http://localhost:8080 list-jobs
java -jar jenkins-cli.jar -s http://localhost:8080 build horilla-ci
```

### Reset Jenkins
```bash
# Backup configuration
sudo tar -czf jenkins-backup.tar.gz /var/lib/jenkins

# Clear jobs
sudo rm -rf /var/lib/jenkins/jobs/*

# Restart
sudo systemctl restart jenkins
```

---

## Pipeline Status Checks

### Check Pipeline Status
```bash
# View all builds
curl http://localhost:8080/api/json | jq '.jobs'

# View specific job
curl http://localhost:8080/job/horilla-ci/api/json | jq '.builds[0]'

# View latest build logs
curl http://localhost:8080/job/horilla-ci/lastBuild/consoleText
```

### Monitor Build Queue
```bash
curl http://localhost:8080/queue/api/json | jq '.items'
```

### Check Agent Status
```bash
curl http://localhost:8080/computer/api/json | jq '.computer[].displayName'
```

---

## Troubleshooting

### Build Not Triggering
**Problem**: Pushed code but Jenkins didn't start build

**Solution**:
```bash
# Check webhook delivery
GitHub Repo → Settings → Webhooks → Recent Deliveries

# Verify Jenkins logs
sudo journalctl -u jenkins | tail -50

# Test connection
curl -I http://jenkins.example.com:8080/github-webhook/
```

### Docker Build Fails
**Problem**: Docker image build fails in pipeline

**Solution**:
```bash
# Check Docker daemon
docker ps

# Check disk space
df -h

# Clean docker
docker system prune -f

# Rebuild manually
docker build -t horilla:latest -f Dockerfile .
```

### Database Connection Error
**Problem**: Tests fail with database connection error

**Solution**:
```bash
# Start test database
docker-compose -f docker-compose.ci.yaml up -d test-db

# Check connectivity
psql -h localhost -U horilla_test -d horilla_test -c "SELECT 1"

# Check credentials in Jenkinsfile
grep "DB_" Jenkinsfile
```

### Permission Denied on Deploy
**Problem**: Cannot write to deployment directory

**Solution**:
```bash
# On deployment server
sudo chown -R deploy:deploy /opt/horilla
sudo chmod -R 755 /opt/horilla

# Verify SSH access
ssh -i deploy_key deploy@staging.example.com "ls -la /opt/horilla"
```

---

## Key Files

| File | Purpose |
|------|---------|
| `Jenkinsfile` | Main CI pipeline (tests, quality, security) |
| `Jenkinsfile.deploy` | Deployment pipeline (staging/prod) |
| `Jenkinsfile.docker` | Docker build pipeline |
| `JENKINS_SETUP.md` | Detailed configuration guide |
| `docker-compose.ci.yaml` | Test database setup |
| `setup.cfg` | Code quality tool configuration |
| `pytest.ini` | Testing configuration |

---

## Quick References

### Jenkins UI Shortcuts
- Jenkins Home: `http://localhost:8080`
- Blue Ocean: `http://localhost:8080/blue/`
- Credentials: `http://localhost:8080/credentials/store/system/domain/_/`
- Plugin Manager: `http://localhost:8080/pluginManager/`
- System Config: `http://localhost:8080/configure`

### Common Groovy Functions
```groovy
// Get environment variables
env.BUILD_NUMBER
env.GIT_COMMIT
env.BRANCH_NAME

// Print output
echo "Message"

// Conditional execution
if (env.BRANCH_NAME == 'main') { ... }

// Error handling
try { ... } catch (Exception e) { ... }

// Parallel execution
parallel {
    stage('A') { ... }
    stage('B') { ... }
}
```

### Git Operations
```bash
# Stage files
git add .

# Commit changes
git commit -m "[PREFIX] Description"

# Push to GitHub
git push origin branch-name

# Create tag
git tag -a v1.0.0 -m "Release 1.0.0"
git push origin v1.0.0
```

---

## Useful Jenkins Plugins

**Already Installed:**
- Pipeline
- GitHub
- Docker
- Slack
- Email Extension

**Recommended Additional:**
- Performance Plugin
- Log Parser Plugin
- Timestamper Plugin
- Build Name and Description Setter
- AnsiColor Plugin

Install: Manage Jenkins → Plugin Manager → Search and install

---

## Environment Variables

### Jenkins Built-in Variables
```bash
${BUILD_NUMBER}      # Build number
${BUILD_ID}          # Build ID
${JOB_NAME}          # Job name
${WORKSPACE}         # Build workspace path
${GIT_COMMIT}        # Git commit SHA
${GIT_BRANCH}        # Git branch name
${BUILD_URL}         # URL to build
${BUILD_LOG_REGEXP}  # Log content
```

### Custom Variables (in Jenkinsfile)
```groovy
environment {
    REPO_NAME = 'horilla'
    PYTHON_VERSION = '3.11'
    DOCKER_REGISTRY = 'docker.io'
}
```

---

## Performance Tuning

### Parallel Test Execution
```groovy
parallel {
    stage('Unit Tests') { ... }
    stage('Integration Tests') { ... }
    stage('API Tests') { ... }
}
```

### Caching Dependencies
```bash
# Cache pip packages
pip install --cache-dir /var/lib/jenkins/.cache -r requirements.txt

# Cache Docker layers
docker build --cache-from horilla:latest ...
```

### Artifact Management
Keep only recent builds:
- CI Pipeline: 30 builds (10 artifacts)
- Deploy Pipeline: 20 builds (all artifacts)
- Docker Pipeline: 30 builds (5 artifacts)

---

## Next Steps

1. **Read Full Setup Guide**: See [JENKINS_SETUP.md](JENKINS_SETUP.md)
2. **Configure Notifications**: Set up Slack and email alerts
3. **Setup Deployment**: Configure staging and production environments
4. **Monitor Builds**: Check build trends and performance
5. **Optimize Pipeline**: Reduce build times and improve reliability

---

## Support & Resources

- [Jenkins Documentation](https://www.jenkins.io/doc/)
- [Jenkins Pipeline Syntax](https://www.jenkins.io/doc/book/pipeline/syntax/)
- [Docker Plugin Docs](https://plugins.jenkins.io/docker-plugin/)
- [GitHub Plugin Docs](https://plugins.jenkins.io/github/)
- [Slack Plugin Docs](https://plugins.jenkins.io/slack/)

---

**Last Updated**: November 2024
**Version**: 1.0
