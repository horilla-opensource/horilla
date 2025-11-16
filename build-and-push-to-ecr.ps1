# PowerShell script to build and push Horilla Docker image to AWS ECR
# Usage: .\build-and-push-to-ecr.ps1 -AccountId "123456789012" [-Region "us-east-1"] [-ImageTag "latest"]

param(
    [Parameter(Mandatory=$true)]
    [string]$AccountId,
    
    [Parameter(Mandatory=$false)]
    [string]$Region = "us-east-1",
    
    [Parameter(Mandatory=$false)]
    [string]$ImageTag = "latest",
    
    [Parameter(Mandatory=$false)]
    [string]$RepositoryName = "horilla"
)

# Set error action preference
$ErrorActionPreference = "Stop"

# Colors for output
function Write-Info {
    param([string]$Message)
    Write-Host $Message -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Message)
    Write-Host $Message -ForegroundColor Green
}

function Write-Error-Custom {
    param([string]$Message)
    Write-Host $Message -ForegroundColor Red
}

# Validate account ID format (12 digits)
if ($AccountId -notmatch '^\d{12}$') {
    Write-Error-Custom "Error: Account ID must be 12 digits. Provided: $AccountId"
    exit 1
}

# Set ECR repository URI
$ECRRepositoryUri = "${AccountId}.dkr.ecr.${Region}.amazonaws.com/${RepositoryName}"
$FullImageTag = "${ECRRepositoryUri}:${ImageTag}"

Write-Info "=========================================="
Write-Info "Horilla Docker Build and Push to ECR"
Write-Info "=========================================="
Write-Info "Account ID: $AccountId"
Write-Info "Region: $Region"
Write-Info "Repository: $RepositoryName"
Write-Info "Image Tag: $ImageTag"
Write-Info "Full Image URI: $FullImageTag"
Write-Info "=========================================="
Write-Host ""

# Check if Docker is running
Write-Info "Checking Docker..."
try {
    $dockerVersion = docker --version
    Write-Success "Docker found: $dockerVersion"
} catch {
    Write-Error-Custom "Error: Docker is not installed or not running. Please install Docker Desktop."
    exit 1
}

# Check if AWS CLI is installed
Write-Info "Checking AWS CLI..."
try {
    $awsVersion = aws --version
    Write-Success "AWS CLI found: $awsVersion"
} catch {
    Write-Error-Custom "Error: AWS CLI is not installed. Please install AWS CLI."
    Write-Info "Download from: https://aws.amazon.com/cli/"
    exit 1
}

# Check AWS credentials
Write-Info "Checking AWS credentials..."
try {
    $callerIdentity = aws sts get-caller-identity 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Error-Custom "Error: AWS credentials not configured or invalid."
        Write-Info "Run: aws configure"
        exit 1
    }
    Write-Success "AWS credentials validated"
    Write-Info "Current AWS Identity:"
    Write-Host $callerIdentity
} catch {
    Write-Error-Custom "Error: Failed to validate AWS credentials"
    exit 1
}

# Create ECR repository if it doesn't exist
Write-Info "Checking ECR repository..."
try {
    $repoExists = aws ecr describe-repositories --repository-names $RepositoryName --region $Region 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Success "ECR repository '$RepositoryName' already exists"
    }
} catch {
    Write-Info "ECR repository '$RepositoryName' does not exist. Creating..."
    try {
        $createRepo = aws ecr create-repository --repository-name $RepositoryName --region $Region
        Write-Success "ECR repository '$RepositoryName' created successfully"
    } catch {
        Write-Error-Custom "Error: Failed to create ECR repository"
        Write-Host $createRepo
        exit 1
    }
}

# Authenticate Docker to ECR
Write-Info "Authenticating Docker to ECR..."
try {
    $loginPassword = aws ecr get-login-password --region $Region
    $loginPassword | docker login --username AWS --password-stdin $ECRRepositoryUri
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Docker authenticated to ECR successfully"
    } else {
        Write-Error-Custom "Error: Docker authentication failed"
        exit 1
    }
} catch {
    Write-Error-Custom "Error: Failed to authenticate Docker to ECR"
    exit 1
}

# Build Docker image
Write-Info "Building Docker image..."
Write-Info "This may take several minutes..."
try {
    docker build -t "${RepositoryName}:${ImageTag}" -t $FullImageTag .
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Docker image built successfully"
    } else {
        Write-Error-Custom "Error: Docker build failed"
        exit 1
    }
} catch {
    Write-Error-Custom "Error: Failed to build Docker image"
    exit 1
}

# Push Docker image to ECR
Write-Info "Pushing Docker image to ECR..."
Write-Info "This may take several minutes depending on image size..."
try {
    docker push $FullImageTag
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Docker image pushed to ECR successfully"
    } else {
        Write-Error-Custom "Error: Docker push failed"
        exit 1
    }
} catch {
    Write-Error-Custom "Error: Failed to push Docker image to ECR"
    exit 1
}

# Summary
Write-Host ""
Write-Info "=========================================="
Write-Success "Build and Push Completed Successfully!"
Write-Info "=========================================="
Write-Info "Image URI: $FullImageTag"
Write-Info ""
Write-Info "You can now use this image in your Terraform configuration:"
Write-Host "  container_image = `"$FullImageTag`"" -ForegroundColor Yellow
Write-Info ""

