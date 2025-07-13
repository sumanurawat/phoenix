#!/bin/bash

# Deploy Dataset Discovery Feature to Cloud Run
# This script deploys the updated Phoenix app with Kaggle credentials to both dev and prod

set -e  # Exit on any error

echo "🚀 Deploying Dataset Discovery Feature to Cloud Run"
echo "=================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if gcloud is authenticated
echo -e "${BLUE}🔐 Checking GCloud authentication...${NC}"
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo -e "${RED}❌ Not authenticated with gcloud. Please run: gcloud auth login${NC}"
    exit 1
fi

# Get current project
PROJECT_ID=$(gcloud config get-value project)
echo -e "${GREEN}✅ Project: ${PROJECT_ID}${NC}"

# Verify secrets exist
echo -e "${BLUE}🔍 Verifying Kaggle secrets...${NC}"
if gcloud secrets describe phoenix-kaggle-username --project=$PROJECT_ID &>/dev/null; then
    echo -e "${GREEN}✅ phoenix-kaggle-username exists${NC}"
else
    echo -e "${RED}❌ phoenix-kaggle-username not found${NC}"
    exit 1
fi

if gcloud secrets describe phoenix-kaggle-key --project=$PROJECT_ID &>/dev/null; then
    echo -e "${GREEN}✅ phoenix-kaggle-key exists${NC}"
else
    echo -e "${RED}❌ phoenix-kaggle-key not found${NC}"
    exit 1
fi

# Function to deploy to specific environment
deploy_environment() {
    local env=$1
    local build_file=$2
    local service_name=$3
    
    echo -e "${YELLOW}🔨 Deploying to ${env} environment...${NC}"
    echo "   Service: ${service_name}"
    echo "   Build file: ${build_file}"
    
    # Trigger Cloud Build
    gcloud builds submit --config=${build_file} --project=$PROJECT_ID
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ ${env} deployment successful!${NC}"
        
        # Get service URL
        SERVICE_URL=$(gcloud run services describe ${service_name} --region=us-central1 --format="value(status.url)")
        echo -e "${GREEN}🌐 Service URL: ${SERVICE_URL}${NC}"
        echo -e "${GREEN}🔍 Dataset Discovery: ${SERVICE_URL}/datasets${NC}"
        echo -e "${GREEN}🏥 Health Check: ${SERVICE_URL}/api/datasets/health${NC}"
        
        return 0
    else
        echo -e "${RED}❌ ${env} deployment failed!${NC}"
        return 1
    fi
}

# Ask user which environment to deploy
echo -e "${BLUE}🎯 Which environment would you like to deploy?${NC}"
echo "1) Dev only (phoenix-dev)"
echo "2) Prod only (phoenix)"  
echo "3) Both Dev and Prod"
read -p "Enter your choice (1-3): " choice

case $choice in
    1)
        echo -e "${YELLOW}📦 Deploying to DEV only...${NC}"
        deploy_environment "DEV" "cloudbuild-dev.yaml" "phoenix-dev"
        ;;
    2)
        echo -e "${YELLOW}📦 Deploying to PROD only...${NC}"
        deploy_environment "PROD" "cloudbuild.yaml" "phoenix"
        ;;
    3)
        echo -e "${YELLOW}📦 Deploying to both DEV and PROD...${NC}"
        
        # Deploy to dev first
        echo -e "${BLUE}🔄 Step 1: Deploying to DEV...${NC}"
        if deploy_environment "DEV" "cloudbuild-dev.yaml" "phoenix-dev"; then
            echo -e "${GREEN}✅ Dev deployment completed${NC}"
            
            # Ask if user wants to continue to prod
            echo -e "${YELLOW}⏳ Dev deployment successful. Continue to PROD? (y/N):${NC}"
            read -p "" continue_prod
            
            if [[ $continue_prod =~ ^[Yy]$ ]]; then
                echo -e "${BLUE}🔄 Step 2: Deploying to PROD...${NC}"
                deploy_environment "PROD" "cloudbuild.yaml" "phoenix"
            else
                echo -e "${YELLOW}⏸️ Skipping PROD deployment${NC}"
            fi
        else
            echo -e "${RED}❌ Dev deployment failed. Skipping PROD.${NC}"
            exit 1
        fi
        ;;
    *)
        echo -e "${RED}❌ Invalid choice. Exiting.${NC}"
        exit 1
        ;;
esac

echo -e "${GREEN}🎉 Deployment process completed!${NC}"
echo ""
echo -e "${BLUE}📋 Next steps:${NC}"
echo "1. Test the health endpoint: GET /api/datasets/health"
echo "2. Test dataset search: POST /api/datasets/search"
echo "3. Visit the web UI: /datasets"
echo "4. Monitor logs: gcloud logging read \"resource.type=cloud_run_revision\""
echo ""
echo -e "${GREEN}✨ Dataset Discovery feature is now live in the cloud!${NC}"