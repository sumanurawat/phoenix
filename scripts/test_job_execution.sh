#!/bin/bash
set -e

# Test Cloud Run Jobs execution
# This script tests the job orchestration system end-to-end

# Configuration
PROJECT_ID=${GOOGLE_CLOUD_PROJECT:-"phoenix-project-386"}
REGION=${GCP_REGION:-"us-central1"}
TEST_USER_ID="test_user_123"
TEST_PROJECT_ID="test_proj_456"

echo "🧪 Testing Cloud Run Jobs for Reel Maker"
echo "Project: $PROJECT_ID"
echo "Region: $REGION"

# Function to make API request
make_api_request() {
    local method=$1
    local endpoint=$2
    local data=$3
    local expected_status=${4:-200}

    echo "📡 $method $endpoint"

    if [ -n "$data" ]; then
        response=$(curl -s -w "HTTPSTATUS:%{http_code}" \
            -X "$method" \
            -H "Content-Type: application/json" \
            -d "$data" \
            "http://localhost:8080$endpoint")
    else
        response=$(curl -s -w "HTTPSTATUS:%{http_code}" \
            -X "$method" \
            "http://localhost:8080$endpoint")
    fi

    # Extract HTTP status code
    http_code=$(echo "$response" | grep -o "HTTPSTATUS:[0-9]*" | cut -d: -f2)
    response_body=$(echo "$response" | sed -E 's/HTTPSTATUS:[0-9]*$//')

    echo "Status: $http_code"
    echo "Response: $response_body" | jq . 2>/dev/null || echo "Response: $response_body"

    if [ "$http_code" != "$expected_status" ]; then
        echo "❌ Expected status $expected_status, got $http_code"
        return 1
    fi

    echo "✅ Request successful"
    echo ""
    return 0
}

# Function to wait for job completion
wait_for_job() {
    local job_id=$1
    local max_wait=${2:-600}  # 10 minutes default
    local start_time=$(date +%s)

    echo "⏳ Waiting for job $job_id to complete (max ${max_wait}s)..."

    while true; do
        current_time=$(date +%s)
        elapsed=$((current_time - start_time))

        if [ $elapsed -ge $max_wait ]; then
            echo "❌ Job did not complete within ${max_wait} seconds"
            return 1
        fi

        response=$(curl -s "http://localhost:8080/api/jobs/$job_id/status")
        status=$(echo "$response" | jq -r '.job.status' 2>/dev/null || echo "unknown")

        case $status in
            "completed")
                echo "✅ Job completed successfully"
                echo "$response" | jq . 2>/dev/null || echo "$response"
                return 0
                ;;
            "failed")
                echo "❌ Job failed"
                echo "$response" | jq . 2>/dev/null || echo "$response"
                return 1
                ;;
            "cancelled")
                echo "❌ Job was cancelled"
                return 1
                ;;
            "running"|"queued")
                echo "⏳ Job status: $status (${elapsed}s elapsed)"
                sleep 10
                ;;
            *)
                echo "❓ Unknown job status: $status"
                sleep 5
                ;;
        esac
    done
}

# Function to test stitching job
test_stitching_job() {
    echo "🎬 Testing Video Stitching Job"

    # Test data
    local test_data='{
        "project_id": "'$TEST_PROJECT_ID'",
        "clip_paths": [
            "gs://phoenix-videos/reel-maker/test/clip1.mp4",
            "gs://phoenix-videos/reel-maker/test/clip2.mp4"
        ],
        "output_path": "gs://phoenix-videos/reel-maker/test/output_stitched.mp4",
        "orientation": "portrait",
        "compression": "optimized",
        "force_restart": true
    }'

    # Trigger stitching job
    response=$(make_api_request "POST" "/api/jobs/trigger/stitching" "$test_data")
    if [ $? -ne 0 ]; then
        echo "❌ Failed to trigger stitching job"
        return 1
    fi

    # Extract job ID
    job_id=$(echo "$response" | jq -r '.job.job_id' 2>/dev/null || echo "")
    if [ -z "$job_id" ] || [ "$job_id" = "null" ]; then
        echo "❌ No job ID returned"
        return 1
    fi

    echo "📋 Job ID: $job_id"

    # Wait for completion
    wait_for_job "$job_id" 900  # 15 minutes for stitching

    return $?
}

# Function to test job status API
test_job_status_api() {
    echo "📊 Testing Job Status API"

    # Test health check
    make_api_request "GET" "/api/jobs/health"

    # Test job statistics (might be empty)
    make_api_request "GET" "/api/jobs/stats?days=7"

    echo "✅ Job Status API tests completed"
}

# Function to test error conditions
test_error_conditions() {
    echo "⚠️ Testing Error Conditions"

    # Test insufficient clips
    local bad_data='{
        "project_id": "'$TEST_PROJECT_ID'",
        "clip_paths": ["gs://phoenix-videos/single_clip.mp4"],
        "output_path": "gs://phoenix-videos/output.mp4"
    }'

    echo "Testing insufficient clips error..."
    make_api_request "POST" "/api/jobs/trigger/stitching" "$bad_data" 400

    # Test missing required fields
    local incomplete_data='{"project_id": "'$TEST_PROJECT_ID'"}'

    echo "Testing missing fields error..."
    make_api_request "POST" "/api/jobs/trigger/stitching" "$incomplete_data" 400

    echo "✅ Error condition tests completed"
}

# Function to test Cloud Run Job directly
test_cloud_run_job_direct() {
    echo "☁️ Testing Cloud Run Job Direct Execution"

    # Test payload
    local job_payload='{
        "job_id": "test_direct_'$(date +%s)'",
        "project_id": "'$TEST_PROJECT_ID'",
        "user_id": "'$TEST_USER_ID'",
        "clip_paths": [
            "gs://phoenix-videos/reel-maker/test/sample1.mp4",
            "gs://phoenix-videos/reel-maker/test/sample2.mp4"
        ],
        "output_path": "gs://phoenix-videos/reel-maker/test/direct_test_output.mp4",
        "orientation": "portrait",
        "compression": "optimized",
        "retry_attempt": 0
    }'

    echo "📋 Test payload:"
    echo "$job_payload" | jq .

    # Create a test execution (this would normally be done by Cloud Tasks)
    echo "🚀 Creating test job execution..."

    gcloud run jobs execute reel-stitching-job \
        --region=$REGION \
        --task-timeout=900 \
        --env-vars="JOB_PAYLOAD=$job_payload"

    echo "✅ Cloud Run Job execution triggered"
    echo "📋 Monitor execution with:"
    echo "  gcloud run jobs executions list --region=$REGION"
    echo "  gcloud run jobs executions logs <EXECUTION_NAME> --region=$REGION"
}

# Main test execution
main() {
    echo "🏁 Starting Cloud Run Jobs Test Suite"
    echo "Timestamp: $(date)"
    echo ""

    # Check prerequisites
    if ! command -v curl &> /dev/null; then
        echo "❌ curl is required for testing"
        exit 1
    fi

    if ! command -v jq &> /dev/null; then
        echo "❌ jq is required for JSON parsing"
        exit 1
    fi

    if ! command -v gcloud &> /dev/null; then
        echo "❌ gcloud CLI is required"
        exit 1
    fi

    # Check if Phoenix app is running
    if ! curl -s http://localhost:8080/api/jobs/health > /dev/null; then
        echo "❌ Phoenix app is not running on localhost:8080"
        echo "Please start the app with: ./start_local.sh"
        exit 1
    fi

    # Determine test type
    test_type=${1:-"api"}

    case $test_type in
        "api")
            echo "🧪 Running API Tests Only"
            test_job_status_api
            test_error_conditions
            echo ""
            echo "ℹ️ To test actual stitching, use: $0 stitching"
            echo "ℹ️ To test Cloud Run Job directly, use: $0 direct"
            ;;
        "stitching")
            echo "🧪 Running Full Stitching Test"
            test_job_status_api
            test_stitching_job
            ;;
        "direct")
            echo "🧪 Running Direct Cloud Run Job Test"
            test_cloud_run_job_direct
            ;;
        "all")
            echo "🧪 Running All Tests"
            test_job_status_api
            test_error_conditions
            test_stitching_job
            ;;
        *)
            echo "❌ Unknown test type: $test_type"
            echo "Usage: $0 [api|stitching|direct|all]"
            exit 1
            ;;
    esac

    echo ""
    echo "🎉 Test suite completed!"
    echo "Timestamp: $(date)"
}

# Run main function with all arguments
main "$@"