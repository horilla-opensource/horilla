#!/bin/bash

# Exit immediately if any command fails
set -e

# Function to print usage information
usage() {
  echo "Usage: $0 <folder_name> <commit_hash> <env>"
  exit 1
}

# Ensure correct number of arguments
if [ $# -ne 3 ]; then
  usage
fi

FOLDER_NAME="$1"
COMMIT_HASH="$2"
ENV="$3"
CONTAINER_NAME="$FOLDER_NAME"
IMAGE_NAME=$1:$ENV-$COMMIT_HASH
echo "$CONTAINER_NAME, $COMMIT_HASH, $ENV"

# Function to check and clone/pull the repository
update_repo() {
  echo "##############################"
  echo "Updating repository"
  if [ ! -d "$FOLDER_NAME" ]; then
    git clone "git@github.com:hrms-rapid/django-python-hrms.git" -b "$ENV" "$FOLDER_NAME"
    cd "$FOLDER_NAME"
  else
    cd "$FOLDER_NAME" || exit 1
    git checkout "$ENV"
    git pull origin "$ENV"
  fi
}

# Function to build and push Docker image
build_image() {
  echo "##############################"
  echo "Building Docker image"
  docker build -t "$IMAGE_NAME" .
  #docker push "$IMAGE_NAME"
}

# Function to stop and remove old Docker container
stop_and_remove_container() {
  echo "##############################"
  echo "Stopping and removing old Docker container"
  if docker ps -a --format '{{.Names}}' | grep -Eq "^$CONTAINER_NAME$"; then
    echo "Stopping existing container: $CONTAINER_NAME"
    docker stop "$CONTAINER_NAME" || true
    echo "Removing existing container: $CONTAINER_NAME"
    docker rm "$CONTAINER_NAME" || true
  else
    echo "No existing container named $CONTAINER_NAME to stop or remove."
  fi
}

# Function to run the new Docker container
run_new_container() {
  echo "##############################"
  echo "Running new Docker container"
  docker run -d --restart always --network=horilla -p 8000:8000 \
  -v /home/ec2-user/env/.env:/app/.env \
  --name "$CONTAINER_NAME" "$IMAGE_NAME"
}

# Function to remove previous Docker images of the same app
remove_previous_images() {
  echo "##############################"
  echo "Removing old images"

  # Remove previous Docker images that do not match the current commit hash
  docker images --format '{{.Repository}}:{{.Tag}}' | grep "^$FOLDER_NAME:" | grep -v "$COMMIT_HASH" | xargs -r docker rmi -f || true
}

# Update repository
update_repo

# Build Docker image
build_image

# Stop and remove old Docker container
stop_and_remove_container

# Run new Docker container
run_new_container

# Remove unused images
remove_previous_images