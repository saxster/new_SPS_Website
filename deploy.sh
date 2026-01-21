#!/bin/bash

# SPS Deployment Script for Hostinger VPS
# Usage: ./deploy.sh

echo "=========================================="
echo "🚀 SPS AUTOMATED DEPLOYMENT SYSTEM"
echo "=========================================="

echo "📥 1. Pulling latest code from GitHub..."
git pull origin main

echo "🏗️  2. Rebuilding Containers..."
# Ensure permissions for data volumes
mkdir -p chroma_data n8n_data
chmod 777 chroma_data n8n_data 2>/dev/null || true

docker compose -f docker-compose.prod.yml up -d --build --remove-orphans

echo "🧹 3. Cleaning up..."
docker image prune -f  # Remove old unused images to save space

echo "=========================================="
echo "✅ DEPLOYMENT COMPLETE. SYSTEM LIVE."
echo "=========================================="
