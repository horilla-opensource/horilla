# Jenkins CI/CD Pipeline - Visual Guide

## Pipeline Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                       │
│                        HORILLA JENKINS CI/CD                         │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘

                             GITHUB REPOSITORY
                                    │
                    ┌───────────────┼───────────────┐
                    │               │               │
                    ▼               ▼               ▼
                  PUSH        PULL REQUEST      SCHEDULE
                    │               │               │
                    └───────────────┼───────────────┘
                                    │
                        ┌───────────▼─────────────┐
                        │   GITHUB WEBHOOK        │
                        │  Triggers Jenkins       │
                        └───────────┬─────────────┘
                                    │
                    ┌───────────────▼───────────────┐
                    │                               │
                    ▼                               ▼
            ┌──────────────────┐         ┌──────────────────┐
            │  JENKINSFILE     │         │  JENKINSFILE.    │
            │  (CI PIPELINE)   │         │  DEPLOY          │
            └──────────────────┘         │  (CD PIPELINE)   │
                    │                    └──────────────────┘
                    │
        ┌───────────┼───────────┐
        │           │           │
        ▼           ▼           ▼
    ┌─────────┐ ┌─────────┐ ┌─────────┐
    │ CODE    │ │SECURITY │ │ DOCKER  │
    │QUALITY  │ │SCANNING │ │ BUILD   │
    └────┬────┘ └────┬────┘ └────┬────┘
         │           │           │
         └───────────┼───────────┘
                     │
                ┌────▼─────┐
                │ REGISTRY  │
                │  PUSH     │
                └────┬─────┘
                     │
        ┌────────────┬────────────┐
        │            │            │
        ▼            ▼            ▼
    DOCKER HUB   AWS ECR      GCP GCR
        │            │            │
        └────────────┬────────────┘
                     │
                ┌────▼──────────────┐
                │  DEPLOYMENT JOB   │
                │  (Manual Trigger) │
                └────┬──────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
        ▼                         ▼
    ┌────────────┐         ┌──────────────┐
    │ STAGING    │         │ PRODUCTION   │
    │ ENVIRONMENT│         │ ENVIRONMENT  │
    └────────────┘         │ (Approval)   │
                           └──────────────┘
```

---

## CI Pipeline (Jenkinsfile) - Detailed Flow

```
┌────────────────────────────────────────────────────────────────────┐
│                    JENKINS CI PIPELINE                              │
│                                                                      │
│  Input: GitHub push to any branch                                  │
│  Output: Docker image pushed to registry                           │
│  Duration: 15-20 minutes                                           │
└────────────────────────────────────────────────────────────────────┘

    START
      │
      ▼
   ┌──────────────────────┐
   │ 1. CHECKOUT          │ (2 min)
   │ - Clone repository   │
   │ - Get commit info    │
   │ - Print git status   │
   └──────┬───────────────┘
          │
          ▼
   ┌──────────────────────┐
   │ 2. SETUP             │ (2 min)
   │ - Install Python     │
   │ - Install deps       │
   │ - Install tools      │
   └──────┬───────────────┘
          │
          ▼
   ┌──────────────────────────────────────────────┐
   │ 3. CODE QUALITY (PARALLEL)                   │ (5 min)
   │                                              │
   │ ┌─────────────────────────────────────────┐  │
   │ │ a) Flake8  - PEP8 style checking       │  │
   │ │ b) Pylint  - Code analysis             │  │
   │ │ c) Black   - Format validation         │  │
   │ │ d) isort   - Import sorting validation │  │
   │ │ e) mypy    - Type checking             │  │
   │ └─────────────────────────────────────────┘  │
   └──────┬───────────────────────────────────────┘
          │
          ▼
   ┌──────────────────────────────────────────┐
   │ 4. SECURITY SCAN (PARALLEL)              │ (3 min)
   │                                          │
   │ ┌────────────────────────────────────┐   │
   │ │ a) Bandit  - Security issues       │   │
   │ │ b) Safety  - Dependency vulns      │   │
   │ └────────────────────────────────────┘   │
   └──────┬──────────────────────────────────┘
          │
          ▼
   ┌──────────────────────┐
   │ 5. DB SETUP          │ (1 min)
   │ - Start PostgreSQL   │
   │ - Create test DB     │
   │ - Wait for ready     │
   └──────┬───────────────┘
          │
          ▼
   ┌──────────────────────┐
   │ 6. MIGRATIONS        │ (1 min)
   │ - makemigrations     │
   │ - migrate            │
   └──────┬───────────────┘
          │
          ▼
   ┌──────────────────────┐
   │ 7. UNIT TESTS        │ (5 min)
   │ - Run test suite     │
   │ - Coverage report    │
   │ - Generate XML       │
   └──────┬───────────────┘
          │
          ▼
   ┌──────────────────────┐
   │ 8. API DOCS          │ (1 min)
   │ - Generate schema    │
   └──────┬───────────────┘
          │
          ▼
   ┌──────────────────────┐
   │ 9. BUILD ARTIFACTS   │ (2 min)
   │ - Collect static     │
   │ - Create archive     │
   └──────┬───────────────┘
          │
          ▼
   ┌──────────────────────┐
   │ 10. DOCKER BUILD     │ (3 min)
   │ - Build image        │
   │ - Create tags        │
   │ - Show details       │
   └──────┬───────────────┘
          │
          ▼
   ┌──────────────────────┐
   │ 11. SCAN IMAGE       │ (2 min)
   │ - Trivy scan         │
   │ - Check vulns        │
   └──────┬───────────────┘
          │
          ▼ (Main branch only)
   ┌──────────────────────┐
   │ 12. PUSH REGISTRY    │ (1 min)
   │ - Login registry     │
   │ - Push image         │
   │ - Logout             │
   └──────┬───────────────┘
          │
          ▼
   ┌──────────────────────┐
   │ 13. PUBLISH REPORTS  │ (1 min)
   │ - Coverage HTML      │
   │ - JUnit results      │
   └──────┬───────────────┘
          │
          ▼
   ┌──────────────────────┐
   │ 14. NOTIFY           │ (1 min)
   │ - Slack message      │
   │ - GitHub status      │
   └──────┬───────────────┘
          │
          ▼
   ┌──────────────────────┐
   │ POST: CLEANUP        │ (1 min)
   │ - Archive artifacts  │
   │ - Clean workspace    │
   └──────┬───────────────┘
          │
          ▼
       SUCCESS or FAILURE

       Total Time: 15-20 minutes
```

---

## Deployment Pipeline (Jenkinsfile.deploy) - Detailed Flow

```
┌────────────────────────────────────────────────────────────────────┐
│                  JENKINS DEPLOYMENT PIPELINE                        │
│                                                                      │
│  Input: Manual trigger with environment + version selection        │
│  Output: Updated application in staging/production                │
│  Duration: 5-10 minutes                                           │
└────────────────────────────────────────────────────────────────────┘

    MANUAL TRIGGER
         │
         ▼
   ┌──────────────────────────┐
   │ SELECT PARAMETERS        │
   │ - Environment (staging   │
   │   or production)         │
   │ - Image tag (version)    │
   │ - Deployment strategy    │
   │ - Rollback enabled       │
   └──────┬───────────────────┘
          │
          ▼
   ┌──────────────────────┐
   │ 1. PRE-DEPLOY CHECKS │ (2 min)
   │ - Verify image       │
   │ - Check connectivity │
   │ - Production approval│
   └──────┬───────────────┘
          │
          ▼
   ┌──────────────────────┐
   │ 2. BACKUP            │ (1 min)
   │ - Docker state       │
   │ - Logs               │
   │ - Config files       │
   └──────┬───────────────┘
          │
          ▼
   ┌──────────────────────┐
   │ 3. CONFIG PREP       │ (1 min)
   │ - Copy configs       │
   │ - Environment vars   │
   │ - Secrets            │
   └──────┬───────────────┘
          │
          ▼
   ┌──────────────────────────────┐
   │ 4. BLUE-GREEN DEPLOY         │ (2 min)
   │                              │
   │ Current (Blue)  New (Green)  │
   │     ↓               ↓        │
   │   Running ──→   Deploying    │
   │     ↑               ↓        │
   │   Alive ←─── Testing Health  │
   │                   ↓          │
   │                 Ready ✓      │
   └──────┬───────────────────────┘
          │
          ▼
   ┌──────────────────────┐
   │ 5. MIGRATIONS        │ (1 min)
   │ - Run Django         │
   │   migrations         │
   │ - Collect static     │
   └──────┬───────────────┘
          │
          ▼
   ┌──────────────────────────┐
   │ 6. HEALTH CHECKS         │ (2 min)
   │ - API endpoint response  │
   │ - Retry logic            │
   │ - Timeout handling       │
   └──────┬───────────────────┘
          │
          ├─ HEALTHY ─────┐
          │                │
          │                ▼
          │           ┌──────────────────┐
          │           │ 7. SMOKE TESTS   │ (1 min)
          │           │ - Key endpoints  │
          │           │ - Database conn  │
          │           │ - Static files   │
          │           └──────┬───────────┘
          │                  │
          │                  ▼
          │           ┌──────────────────┐
          │           │ SUCCESS ✓        │
          │           │ Notify team      │
          │           │ Store state      │
          │           └──────────────────┘
          │
          ├─ FAILED ──────┐
          │               │
          │               ▼
          │        ┌──────────────────┐
          │        │ AUTO ROLLBACK    │ (1 min)
          │        │ - Switch back    │
          │        │ - Restore config │
          │        │ - Alert team     │
          │        └──────────────────┘
          │
          ▼
    ┌────────────────────────┐
    │ POST-DEPLOY VERIFY     │ (1 min)
    │ - Container status     │
    │ - Recent logs          │
    │ - Disk usage           │
    └────┬───────────────────┘
         │
         ▼
    ┌────────────────────────┐
    │ NOTIFY                 │ (1 min)
    │ - Slack message        │
    │ - Email summary        │
    └────┬───────────────────┘
         │
         ▼
    ┌────────────────────────┐
    │ CLEANUP                │ (1 min)
    │ - Archive logs         │
    │ - Remove temp files    │
    └────┬───────────────────┘
         │
         ▼
    DEPLOYMENT COMPLETE

    Total Time: 5-10 minutes
```

---

## Docker Build Pipeline (Jenkinsfile.docker) - Detailed Flow

```
┌────────────────────────────────────────────────────────────────────┐
│                   DOCKER BUILD PIPELINE                             │
│                                                                      │
│  Input: Manual trigger with registry and architecture selection   │
│  Output: Docker image pushed to selected registry                 │
│  Duration: 10-15 minutes                                          │
└────────────────────────────────────────────────────────────────────┘

    MANUAL TRIGGER
         │
         ▼
   ┌──────────────────────────┐
   │ SELECT PARAMETERS        │
   │ - Docker tag             │
   │ - Registry target        │
   │ - Dockerfile path        │
   │ - Arch (single/multi)    │
   │ - Scan image?            │
   │ - Push to registry?      │
   └──────┬───────────────────┘
          │
          ▼
   ┌──────────────────────┐
   │ 1. PREPARE           │ (1 min)
   │ - Verify files       │
   │ - Show config        │
   │ - Validate inputs    │
   └──────┬───────────────┘
          │
          ▼
   ┌──────────────────────────────────────┐
   │ 2. LOGIN REGISTRIES                  │ (1 min)
   │                                      │
   │ Docker Hub, ECR, GCR, or             │
   │ Private Registry                     │
   └──────┬───────────────────────────────┘
          │
          ▼
   ┌─────────────────────────────────────┐
   │ 3. BUILD IMAGE                      │ (3-5 min)
   │                                     │
   │ docker build                        │
   │ ├─ FROM python:3.11-slim           │
   │ ├─ System packages                  │
   │ ├─ Python dependencies              │
   │ ├─ Application code                 │
   │ ├─ User setup (non-root)            │
   │ └─ Expose 8000                      │
   └──────┬──────────────────────────────┘
          │
          ▼
   ┌──────────────────────────────────────┐
   │ 4. MULTI-ARCH BUILD (Optional)      │ (5-10 min)
   │                                      │
   │ docker buildx build                  │
   │ ├─ linux/amd64                       │
   │ └─ linux/arm64                       │
   │                                      │
   │ (Direct push if multi-arch)         │
   └──────┬───────────────────────────────┘
          │
          ▼
   ┌──────────────────────────────────────┐
   │ 5. VULNERABILITY SCAN (Parallel)    │ (2-3 min)
   │                                      │
   │ ┌──────────────────────────────────┐ │
   │ │ a) Trivy      - High/Critical    │ │
   │ │ b) Grype      - All severities   │ │
   │ │ c) Container  - Structure test   │ │
   │ │    Structure                      │ │
   │ └──────────────────────────────────┘ │
   │                                      │
   │ Results: JSON and text formats      │
   └──────┬───────────────────────────────┘
          │
          ▼
   ┌──────────────────────┐
   │ 6. PUSH TO REGISTRY  │ (2 min)
   │ - Push all tags      │
   │ - Verify push        │
   │ - Log results        │
   └──────┬───────────────┘
          │
          ▼
   ┌──────────────────────┐
   │ 7. GENERATE SBOM     │ (1 min)
   │ - SPDX JSON          │
   │ - CycloneDX JSON     │
   └──────┬───────────────┘
          │
          ▼
   ┌──────────────────────┐
   │ 8. CLEANUP           │ (1 min)
   │ - Logout registries  │
   │ - Clean local images │
   └──────┬───────────────┘
          │
          ▼
    ┌────────────────────┐
    │ ARCHIVE ARTIFACTS  │ (1 min)
    │ - Reports          │
    │ - SBOM             │
    └────┬───────────────┘
         │
         ▼
    BUILD COMPLETE

    Total Time: 10-15 minutes
```

---

## Credential Flow

```
Jenkins Secret Store
    │
    ├─ github-credentials ────→ GitHub API
    │
    ├─ docker-hub-credentials ──→ Docker Hub
    │
    ├─ aws-credentials ────────→ AWS ECR
    │
    ├─ deploy-ssh-key ────────→ SSH to Servers
    │
    ├─ test-db-password ────→ PostgreSQL Test DB
    │
    ├─ django-secret-key ──→ Django Settings
    │
    ├─ slack-webhook-url ──→ Slack Notifications
    │
    └─ sonarqube-token ────→ Code Quality Analysis
```

---

## Environment Configuration

```
Git Repository
    │
    ├─ .env.dist (Template)
    │
    ├─ Jenkins Credentials Store
    │   ├─ .env.staging
    │   └─ .env.production
    │
    └─ Docker Environment
        ├─ docker-compose.yaml
        │   └─ env_file: .env
        │
        └─ Jenkinsfile
            └─ environment variables
```

---

## File Organization

```
horilla/
│
├─ Pipeline Files
│  ├─ Jenkinsfile (CI)
│  ├─ Jenkinsfile.deploy (CD)
│  └─ Jenkinsfile.docker (Build)
│
├─ Configuration
│  ├─ .jenkins-config.yml
│  ├─ docker-compose.ci.yaml
│  ├─ setup.cfg
│  ├─ pytest.ini
│  └─ jenkins-init.sh
│
├─ Docker
│  ├─ Dockerfile
│  ├─ docker-compose.yaml
│  └─ entrypoint.sh
│
├─ Documentation
│  ├─ JENKINS_SETUP.md (Main guide)
│  ├─ JENKINS_QUICK_START.md (Quick ref)
│  ├─ JENKINS_PIPELINE_SUMMARY.md (Overview)
│  ├─ JENKINS_CHECKLIST.md (Impl checklist)
│  ├─ JENKINS_FILES_CREATED.md (Inventory)
│  └─ JENKINS_VISUAL_GUIDE.md (This file)
│
└─ Application
   ├─ manage.py
   ├─ requirements.txt
   ├─ horilla/
   │  ├─ settings.py
   │  └─ wsgi.py
   └─ */tests.py (Multiple apps)
```

---

## Technology Stack Visualization

```
┌─────────────────────────────────────────────────────┐
│             HORILLA CI/CD STACK                      │
├─────────────────────────────────────────────────────┤
│                                                       │
│  SCM Layer:                                          │
│  ┌────────────────────────────────────────────────┐ │
│  │ GitHub (push hook, webhooks, OAuth)            │ │
│  └────────────────────────────────────────────────┘ │
│                                                       │
│  CI/CD Orchestration:                               │
│  ┌────────────────────────────────────────────────┐ │
│  │ Jenkins 2.x LTS (Pipeline, Blue Ocean)         │ │
│  └────────────────────────────────────────────────┘ │
│                                                       │
│  Testing & Quality:                                 │
│  ┌────────────────────────────────────────────────┐ │
│  │ Django Tests, pytest, coverage.py             │ │
│  │ Flake8, Pylint, Black, isort, mypy            │ │
│  │ Bandit, Safety, Trivy, Grype                  │ │
│  └────────────────────────────────────────────────┘ │
│                                                       │
│  Container Layer:                                   │
│  ┌────────────────────────────────────────────────┐ │
│  │ Docker 24.0+, Docker Compose                  │ │
│  │ Docker Hub, ECR, GCR, Private registries      │ │
│  └────────────────────────────────────────────────┘ │
│                                                       │
│  Infrastructure:                                    │
│  ┌────────────────────────────────────────────────┐ │
│  │ PostgreSQL 16, Redis 7, Elasticsearch 8       │ │
│  │ Nginx/Apache reverse proxy                    │ │
│  │ Ubuntu 20.04 LTS servers                      │ │
│  └────────────────────────────────────────────────┘ │
│                                                       │
│  Notifications:                                     │
│  ┌────────────────────────────────────────────────┐ │
│  │ Slack webhooks, Email, GitHub status          │ │
│  └────────────────────────────────────────────────┘ │
│                                                       │
└─────────────────────────────────────────────────────┘
```

---

## Success Metrics

```
Build Success Metrics:
├─ CI Pipeline Pass Rate: > 95%
├─ Average Build Time: < 20 minutes
├─ Code Coverage: > 70%
└─ Vulnerability Found: 0 critical

Deployment Metrics:
├─ Deployment Success Rate: > 99%
├─ Average Deployment Time: < 10 minutes
├─ Zero-Downtime Deployments: 100%
├─ Rollback Success Rate: > 98%
└─ Mean Time to Recovery: < 2 minutes

Quality Metrics:
├─ Code Quality Score: > 8/10
├─ Test Coverage: > 70%
├─ Security Scan Pass: 100%
├─ Linting Issues: Warnings only
└─ Type Check Pass Rate: > 90%
```

---

**For quick reference, see [JENKINS_QUICK_START.md](JENKINS_QUICK_START.md)**

**For detailed setup, see [JENKINS_SETUP.md](JENKINS_SETUP.md)**

**Created**: November 2024
