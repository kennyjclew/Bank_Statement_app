#!/bin/bash
set -e  # Exit immediately if a command exits with a non-zero status

APP_NAME="bank-pdf-app"
IMAGE_NAME="bank-statement-pdf-app"
HOST_PORT=5000
CONTAINER_PORT=5002

echo "📥 Pulling latest code..."
git pull

echo "🐳 Building Docker image..."
docker build -t $IMAGE_NAME .

echo "🛑 Stopping and removing old container (if exists)..."
if [ "$(docker ps -aq -f name=$APP_NAME)" ]; then
    docker stop $APP_NAME
    docker rm $APP_NAME
fi

echo "🚀 Running new container..."
docker run -d -p $HOST_PORT:$CONTAINER_PORT \
    --name $APP_NAME \
    -v $(pwd)/.env:/app/.env \
    -v $(pwd)/credentials.json:/app/credentials.json \
    -v $(pwd)/token.json:/app/token.json \
    $IMAGE_NAME

echo "✅ Deployment complete! App running on port $HOST_PORT."
