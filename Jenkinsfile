// Horilla HRMS - CI/CD Pipeline
// Main Jenkinsfile for continuous integration and testing
// Supports: Python 3.11, Django 4.2, PostgreSQL 16, Docker

pipeline {
    agent {
        docker {
            image 'python:3.11-slim-bookworm'
            args '-v /var/run/docker.sock:/var/run/docker.sock'
        }
    }

    // Build parameters for manual triggers
    parameters {
        choice(
            name: 'ENVIRONMENT',
            choices: ['dev', 'staging', 'production'],
            description: 'Target environment for deployment'
        )
        booleanParam(
            name: 'SKIP_TESTS',
            defaultValue: false,
            description: 'Skip running tests (not recommended)'
        )
        booleanParam(
            name: 'RUN_SECURITY_SCAN',
            defaultValue: true,
            description: 'Run security vulnerability scans'
        )
    }

    // Define build triggers
    triggers {
        githubPush()  // Trigger on GitHub push
        pollSCM('H/15 * * * *')  // Poll every 15 minutes if no webhook
    }

    // Define environment variables
    environment {
        // Project settings
        REPO_NAME = 'horilla'
        PYTHON_VERSION = '3.11'
        DJANGO_SETTINGS_MODULE = 'horilla.settings'

        // Docker settings
        DOCKER_REGISTRY = credentials('docker-registry-url')
        DOCKER_USERNAME = credentials('docker-username')
        DOCKER_PASSWORD = credentials('docker-password')
        IMAGE_NAME = "${DOCKER_REGISTRY}/${REPO_NAME}"
        IMAGE_TAG = "${BUILD_NUMBER}"

        // Database settings (test database)
        DB_ENGINE = 'django.db.backends.postgresql'
        DB_NAME = 'horilla_test'
        DB_USER = 'horilla_test'
        DB_PASSWORD = credentials('test-db-password')
        DB_HOST = 'localhost'
        DB_PORT = '5432'

        // Django settings
        SECRET_KEY = credentials('django-secret-key')
        DEBUG = 'False'
        ALLOWED_HOSTS = 'localhost,127.0.0.1'

        // AWS/GCP for artifacts
        AWS_REGION = 'us-east-1'
        ARTIFACTS_BUCKET = 'horilla-build-artifacts'

        // SonarQube settings
        SONAR_HOST_URL = credentials('sonarqube-host')
        SONAR_LOGIN = credentials('sonarqube-token')
    }

    options {
        // Keep last 30 builds
        buildDiscarder(logRotator(numToKeepStr: '30', artifactNumToKeepStr: '10'))

        // Timeout after 1 hour
        timeout(time: 1, unit: 'HOURS')

        // Disable concurrent builds
        disableConcurrentBuilds()

        // Add timestamps to console output
        timestamps()

        // Configure build name
        buildName '${BRANCH_NAME}-${BUILD_NUMBER}'
    }

    stages {
        stage('Checkout') {
            steps {
                echo "=== Checking out source code ==="
                checkout scm
                script {
                    // Get commit info
                    env.GIT_COMMIT_SHORT = sh(
                        script: 'git rev-parse --short HEAD',
                        returnStdout: true
                    ).trim()
                    env.GIT_BRANCH = sh(
                        script: 'git rev-parse --abbrev-ref HEAD',
                        returnStdout: true
                    ).trim()
                    env.GIT_COMMIT_MSG = sh(
                        script: 'git log -1 --pretty=%B',
                        returnStdout: true
                    ).trim()
                }
                echo "Commit: ${GIT_COMMIT_SHORT}"
                echo "Branch: ${GIT_BRANCH}"
                echo "Message: ${GIT_COMMIT_MSG}"
            }
        }

        stage('Setup') {
            steps {
                echo "=== Setting up environment ==="
                sh '''
                    # Update pip
                    python3 -m pip install --upgrade pip setuptools wheel

                    # Install system dependencies
                    apt-get update
                    apt-get install -y --no-install-recommends \
                        postgresql-client \
                        git \
                        build-essential \
                        libpq-dev \
                        git-lfs

                    # Install Python dependencies
                    pip install -r requirements.txt

                    # Install testing and code quality tools
                    pip install pytest pytest-django pytest-cov coverage
                    pip install flake8 pylint black isort bandit
                    pip install django-stubs mypy
                '''
            }
        }

        stage('Code Quality') {
            parallel {
                stage('Linting - Flake8') {
                    steps {
                        echo "=== Running Flake8 linting ==="
                        catchError(buildResult: 'UNSTABLE', stageResult: 'UNSTABLE') {
                            sh '''
                                flake8 . \
                                    --count \
                                    --select=E9,F63,F7,F82 \
                                    --show-source \
                                    --statistics \
                                    --max-line-length=120 \
                                    --exclude=migrations,static,media,.venv,node_modules \
                                    | tee flake8-report.txt
                            '''
                        }
                    }
                }

                stage('Linting - Pylint') {
                    steps {
                        echo "=== Running Pylint checks ==="
                        catchError(buildResult: 'UNSTABLE', stageResult: 'UNSTABLE') {
                            sh '''
                                find . -name "*.py" \
                                    -not -path "./migrations/*" \
                                    -not -path "./static/*" \
                                    -not -path "./media/*" \
                                    -not -path "./.venv/*" \
                                    -not -path "./node_modules/*" \
                                    | xargs pylint --max-line-length=120 \
                                    > pylint-report.txt 2>&1 || true
                            '''
                        }
                    }
                }

                stage('Code Formatting - Black') {
                    steps {
                        echo "=== Checking Black code formatting ==="
                        catchError(buildResult: 'UNSTABLE', stageResult: 'UNSTABLE') {
                            sh '''
                                black --check --line-length=120 . \
                                    --exclude="migrations|static|media|.venv|node_modules" \
                                    | tee black-report.txt
                            '''
                        }
                    }
                }

                stage('Import Sorting - isort') {
                    steps {
                        echo "=== Checking import sorting with isort ==="
                        catchError(buildResult: 'UNSTABLE', stageResult: 'UNSTABLE') {
                            sh '''
                                isort --check-only --profile black . \
                                    --skip migrations \
                                    --skip static \
                                    --skip media \
                                    --skip .venv \
                                    --skip node_modules \
                                    | tee isort-report.txt
                            '''
                        }
                    }
                }

                stage('Type Checking - mypy') {
                    steps {
                        echo "=== Running mypy type checking ==="
                        catchError(buildResult: 'UNSTABLE', stageResult: 'UNSTABLE') {
                            sh '''
                                mypy . \
                                    --ignore-missing-imports \
                                    --exclude="migrations|static|media|.venv|node_modules" \
                                    > mypy-report.txt 2>&1 || true
                            '''
                        }
                    }
                }
            }
        }

        stage('Security Scan') {
            when {
                expression { params.RUN_SECURITY_SCAN == true }
            }
            parallel {
                stage('Bandit - Security Issues') {
                    steps {
                        echo "=== Running Bandit security scan ==="
                        catchError(buildResult: 'UNSTABLE', stageResult: 'UNSTABLE') {
                            sh '''
                                bandit -r . \
                                    -ll \
                                    -f json \
                                    -o bandit-report.json \
                                    --exclude "*/migrations/*,*/static/*,*/media/*,.venv,node_modules" || true

                                # Also generate text report
                                bandit -r . \
                                    -ll \
                                    -f txt \
                                    --exclude "*/migrations/*,*/static/*,*/media/*,.venv,node_modules" \
                                    | tee bandit-report.txt
                            '''
                        }
                    }
                }

                stage('Dependency Check') {
                    steps {
                        echo "=== Checking for vulnerable dependencies ==="
                        catchError(buildResult: 'UNSTABLE', stageResult: 'UNSTABLE') {
                            sh '''
                                pip install safety
                                safety check --json > safety-report.json || true
                                safety check | tee safety-report.txt || true
                            '''
                        }
                    }
                }
            }
        }

        stage('Database Setup') {
            steps {
                echo "=== Setting up test database ==="
                sh '''
                    # Start PostgreSQL service
                    service postgresql start || true

                    # Wait for PostgreSQL to be ready
                    for i in {1..30}; do
                        pg_isready -h localhost -U postgres && break
                        echo "Waiting for PostgreSQL... ($i/30)"
                        sleep 1
                    done

                    # Create test database and user
                    PGPASSWORD=postgres psql -h localhost -U postgres -c \
                        "CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASSWORD}';" || true

                    PGPASSWORD=postgres psql -h localhost -U postgres -c \
                        "CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};" || true

                    PGPASSWORD=postgres psql -h localhost -U postgres -d ${DB_NAME} -c \
                        "GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};"
                '''
            }
        }

        stage('Migrations') {
            steps {
                echo "=== Running Django migrations ==="
                sh '''
                    python3 manage.py makemigrations --check --dry-run --verbosity 3
                    python3 manage.py migrate --verbosity 2
                '''
            }
        }

        stage('Unit Tests') {
            when {
                expression { params.SKIP_TESTS == false }
            }
            steps {
                echo "=== Running unit tests ==="
                sh '''
                    # Run Django tests with coverage
                    coverage run --source='.' manage.py test \
                        --verbosity=2 \
                        --keepdb \
                        --parallel

                    # Generate coverage report
                    coverage report --include="./*" \
                        --omit="*/migrations/*,*/tests/*,*/static/*,*/media/*,manage.py,setup.py"

                    # Generate XML coverage report for Jenkins
                    coverage xml -o coverage.xml

                    # Generate HTML coverage report
                    coverage html -d coverage_html_report/
                '''
            }
        }

        stage('API Documentation') {
            steps {
                echo "=== Generating API documentation ==="
                catchError(buildResult: 'SUCCESS', stageResult: 'UNSTABLE') {
                    sh '''
                        # Generate API documentation (if using drf-yasg)
                        python3 manage.py spectacular --file schema.yml || true
                        python3 manage.py generateschema > api-schema.json || true
                    '''
                }
            }
        }

        stage('Build Artifacts') {
            steps {
                echo "=== Creating build artifacts ==="
                sh '''
                    # Collect static files
                    python3 manage.py collectstatic --noinput --verbosity=1

                    # Create artifact archive
                    tar -czf horilla-build-${BUILD_NUMBER}.tar.gz \
                        --exclude=.git \
                        --exclude=.venv \
                        --exclude=node_modules \
                        --exclude=.pytest_cache \
                        --exclude=.coverage \
                        --exclude=htmlcov \
                        --exclude=coverage_html_report \
                        --exclude=build \
                        --exclude=dist \
                        .
                '''
            }
        }

        stage('Docker Build') {
            steps {
                echo "=== Building Docker image ==="
                sh '''
                    docker build \
                        -t ${IMAGE_NAME}:${IMAGE_TAG} \
                        -t ${IMAGE_NAME}:latest \
                        -t ${IMAGE_NAME}:${GIT_BRANCH} \
                        --label "build_number=${BUILD_NUMBER}" \
                        --label "git_commit=${GIT_COMMIT_SHORT}" \
                        --label "build_date=$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
                        -f Dockerfile \
                        .

                    # Show image info
                    docker image inspect ${IMAGE_NAME}:${IMAGE_TAG}
                '''
            }
        }

        stage('Docker Security Scan') {
            steps {
                echo "=== Scanning Docker image for vulnerabilities ==="
                catchError(buildResult: 'UNSTABLE', stageResult: 'UNSTABLE') {
                    sh '''
                        # Install and run Trivy
                        curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin || true

                        trivy image \
                            --severity HIGH,CRITICAL \
                            --exit-code 0 \
                            --format json \
                            --output trivy-report.json \
                            ${IMAGE_NAME}:${IMAGE_TAG} || true

                        trivy image \
                            --severity HIGH,CRITICAL \
                            ${IMAGE_NAME}:${IMAGE_TAG} || true
                    '''
                }
            }
        }

        stage('Push to Registry') {
            when {
                branch 'main'  // Only push on main branch
            }
            steps {
                echo "=== Pushing image to Docker registry ==="
                sh '''
                    echo "${DOCKER_PASSWORD}" | docker login -u "${DOCKER_USERNAME}" --password-stdin ${DOCKER_REGISTRY}

                    docker push ${IMAGE_NAME}:${IMAGE_TAG}
                    docker push ${IMAGE_NAME}:latest
                    docker push ${IMAGE_NAME}:${GIT_BRANCH}

                    docker logout ${DOCKER_REGISTRY}
                '''
            }
        }

        stage('Publish Reports') {
            steps {
                echo "=== Publishing test and quality reports ==="
                publishHTML([
                    allowMissing: true,
                    alwaysLinkToLastBuild: true,
                    keepAll: true,
                    reportDir: 'coverage_html_report',
                    reportFiles: 'index.html',
                    reportName: 'Coverage Report'
                ])

                // Publish code quality reports
                step([$class: 'WarningsPlugin',
                    parsingRulesPath: '',
                    consoleParsers: [
                        [parserName: 'Flake8 Parser'],
                        [parserName: 'PEP8 Parser']
                    ]
                ])
            }
        }

        stage('Notify') {
            when {
                branch 'main'
            }
            steps {
                echo "=== Sending notifications ==="
                sh '''
                    # Prepare summary
                    cat > build-summary.txt <<EOF
Build Summary
=============
Build Number: ${BUILD_NUMBER}
Branch: ${GIT_BRANCH}
Commit: ${GIT_COMMIT_SHORT}
Author: ${GIT_AUTHOR_NAME}
Message: ${GIT_COMMIT_MSG}
Status: ${BUILD_STATUS}
Timestamp: $(date)
EOF

                    # Notify via different channels (configure credentials in Jenkins)
                    # Slack notification
                    if [ -n "${SLACK_WEBHOOK}" ]; then
                        curl -X POST ${SLACK_WEBHOOK} \
                            -H 'Content-Type: application/json' \
                            -d "{
                                \"text\": \"Horilla Build #${BUILD_NUMBER} ${BUILD_STATUS}\",
                                \"blocks\": [{
                                    \"type\": \"section\",
                                    \"text\": {\"type\": \"mrkdwn\", \"text\": \"*Build Status:* ${BUILD_STATUS}\n*Branch:* ${GIT_BRANCH}\n*Commit:* ${GIT_COMMIT_SHORT}\"}
                                }]
                            }" || true
                    fi
                '''
            }
        }
    }

    post {
        always {
            echo "=== Cleanup and archiving ==="

            // Archive test results
            junit testResults: '**/test-results.xml', allowEmptyResults: true

            // Archive coverage report
            publishCoverage(
                adapters: [
                    coberturaAdapter('coverage.xml')
                ],
                sourceFileResolver: sourceFiles('STORE_ALL_SOURCE')
            )

            // Archive code quality reports
            archiveArtifacts artifacts: '''
                **/flake8-report.txt,
                **/pylint-report.txt,
                **/black-report.txt,
                **/isort-report.txt,
                **/mypy-report.txt,
                **/bandit-report.json,
                **/bandit-report.txt,
                **/safety-report.json,
                **/safety-report.txt,
                **/trivy-report.json,
                **/api-schema.json,
                **/build-summary.txt,
                horilla-build-*.tar.gz
            ''', allowEmptyArchive: true

            // Clean workspace
            cleanWs(
                deleteDirs: true,
                patterns: [
                    [pattern: '.pytest_cache', type: 'INCLUDE'],
                    [pattern: '.coverage', type: 'INCLUDE'],
                    [pattern: 'htmlcov', type: 'INCLUDE']
                ]
            )
        }

        success {
            echo "=== Build SUCCESSFUL ==="
            updateGitHubCommitStatus(state: 'SUCCESS')
        }

        unstable {
            echo "=== Build UNSTABLE ==="
            updateGitHubCommitStatus(state: 'FAILURE')
        }

        failure {
            echo "=== Build FAILED ==="
            updateGitHubCommitStatus(state: 'FAILURE')
        }

        aborted {
            echo "=== Build ABORTED ==="
            updateGitHubCommitStatus(state: 'ERROR')
        }
    }
}

// Helper function to update GitHub commit status
def updateGitHubCommitStatus(String state) {
    try {
        sh '''
            curl -H "Authorization: token ${GITHUB_TOKEN}" \
                -X POST \
                -d "{\"state\":\"${state}\",\"target_url\":\"${BUILD_URL}\",\"description\":\"Jenkins build\",\"context\":\"continuous-integration/jenkins\"}" \
                https://api.github.com/repos/${GITHUB_REPOSITORY}/statuses/${GIT_COMMIT}
        ''' || true
    } catch (Exception e) {
        echo "Failed to update GitHub status: ${e}"
    }
}
