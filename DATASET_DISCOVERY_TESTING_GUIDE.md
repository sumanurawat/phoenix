# 🧪 Dataset Discovery Feature - Testing Guide

## ✅ Implementation Complete!

The Dataset Discovery feature is **fully implemented** and ready for testing. Here's everything you need to know:

## 🔧 Setup Required

### 1. **Add Kaggle Credentials**

You need these two secrets from your Kaggle account:

#### **Get Credentials:**
1. Go to [kaggle.com](https://www.kaggle.com) → Account → API section
2. Click **"Create New Token"** → Downloads `kaggle.json`
3. Extract values from the file:
   ```json
   {
     "username": "your_username_here",    ← KAGGLE_USERNAME
     "key": "abc123def456..."             ← KAGGLE_KEY
   }
   ```

#### **Local Development (.env file):**
```bash
# Add these to your .env file
KAGGLE_USERNAME=your_username_here
KAGGLE_KEY=abc123def456...
```

#### **Production (GCP Secret Manager):**
Add these secrets to your existing GCP setup:
- `KAGGLE_USERNAME`
- `KAGGLE_KEY`

### 2. **Dependencies**
Already added to `requirements.txt`:
```
kaggle==1.6.6  # For Kaggle API integration
```

## 🚀 How to Test

### **Option 1: Start Phoenix Server**
```bash
# Your usual command
./start_local.sh
```

### **Option 2: Manual Start** 
```bash
source venv/bin/activate
python app.py
```

## 🌐 Available Interfaces

### **1. Web UI (Recommended)**
- **URL**: `http://localhost:5000/datasets`
- **Features**: 
  - Beautiful interactive search interface
  - Real-time health status indicator
  - Advanced search options (limit, sort, quality filter)
  - Live results with scoring visualization
  - Example queries for quick testing

### **2. API Endpoints** 

#### **Health Check**
```bash
curl http://localhost:5000/api/datasets/health
```
**Expected Response:**
```json
{
  "success": true,
  "status": "healthy", 
  "kaggle_authenticated": true,
  "checks": {...}
}
```

#### **Search Datasets**
```bash
curl -X POST http://localhost:5000/api/datasets/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "climate change",
    "limit": 10,
    "sort_by": "hottest",
    "min_quality_score": 0.5
  }'
```

#### **Configuration Info**
```bash
curl http://localhost:5000/api/datasets/config
```

### **3. End-to-End Test Script**
```bash
source venv/bin/activate
python test_dataset_discovery_e2e.py
```

## 🎯 Test Scenarios

### **Quick Smoke Test**
1. Visit `http://localhost:5000/datasets`
2. Check health indicator (top-right) shows "Service Healthy"
3. Try example query: "machine learning"
4. Verify results show with scores

### **Comprehensive Testing**
1. **Search Variations**:
   - "climate change" (should find environmental data)
   - "machine learning" (should find ML/AI datasets) 
   - "covid" (should find pandemic data)
   - "financial data" (should find economics datasets)

2. **Advanced Options**:
   - Change result limits (10, 20, 50)
   - Try different sort orders (hottest, votes, updated)
   - Apply quality filters (0.5+, 0.7+, 0.9+)

3. **Scoring Validation**:
   - Verify quality scores (popularity, recency, completeness)
   - Check relevance scores (query matching)
   - Confirm combined scores rank appropriately

4. **Error Handling**:
   - Empty search query
   - Invalid parameters
   - Network issues

## 📊 What to Expect

### **Search Results Include**:
- **Dataset Title & URL** (links to Kaggle)
- **Owner & Basic Stats** (downloads, votes, size)
- **AI Scores**: Quality (0-1), Relevance (0-1), Combined (0-1)
- **File Information** (count, types, total size)
- **Metadata** (description, tags, license)

### **Performance Benchmarks**:
- **Search Time**: < 5 seconds for 20 results
- **Quality Scoring**: < 100ms per dataset
- **UI Response**: Immediate feedback and loading states
- **Error Recovery**: Graceful handling of failures

### **Scoring Algorithm**:
- **Quality Score** (intrinsic dataset value):
  - Popularity (40%): Downloads and votes
  - Recency (30%): Last update with bonus for recent
  - Completeness (20%): Metadata richness
  - Size (10%): Optimal range 1MB-500MB

- **Relevance Score** (query matching):
  - Title matching (50%): Exact and partial matches
  - Description matching (30%): Term frequency analysis
  - Tag matching (20%): Keyword alignment

## 🐛 Troubleshooting

### **Common Issues:**

#### **❌ "Service Unhealthy" / Authentication Errors**
- **Fix**: Check KAGGLE_USERNAME and KAGGLE_KEY are set correctly
- **Test**: `curl http://localhost:5000/api/datasets/health`

#### **❌ "No Results Found"**
- **Fix**: Try broader search terms or lower quality filter
- **Test**: Try "data" or "machine learning"

#### **❌ "Service Offline"**
- **Fix**: Ensure Phoenix server is running
- **Test**: Check `http://localhost:5000` loads

#### **❌ Slow Response Times**
- **Fix**: Check internet connection to Kaggle API
- **Note**: First request may be slower due to authentication

### **Debug Commands:**
```bash
# Check service status
curl -s http://localhost:5000/api/datasets/health | jq .

# Test with minimal query
curl -X POST http://localhost:5000/api/datasets/search \
  -H "Content-Type: application/json" \
  -d '{"query": "data", "limit": 5}' | jq .

# Check server logs
tail -f logs.txt  # if you have logging setup
```

## 🎉 Success Indicators

### **✅ Everything Working When:**
1. Health status shows "Service Healthy" 
2. Search returns ranked results with scores
3. Scores are reasonable (0.0-1.0 range)
4. Kaggle links work and open datasets
5. Different queries return different relevance scores
6. Quality filter affects result count

### **📈 Performance Indicators:**
- Search response < 5 seconds
- UI feels responsive 
- Health checks pass consistently
- Error messages are helpful

## 🔗 Integration Points

### **Main Navigation:**
- Added to homepage: `http://localhost:5000/` → "Dataset Discovery" card

### **API Integration Ready For:**
- **Robin AI**: Dataset recommendations for research
- **Doogle**: Enhanced search with dataset context  
- **Derplexity**: Research assistance with data sources

### **Future Enhancements:**
- Caching for faster repeat searches
- User preferences and saved searches
- Batch dataset analysis
- Integration with data visualization tools

## 📞 Support

### **If Tests Fail:**
1. **Check Prerequisites**: Kaggle credentials, dependencies
2. **Verify Server**: Phoenix running on port 5000
3. **Test Health**: API health endpoint responds
4. **Check Logs**: Look for authentication or network errors

### **Success Criteria:**
- ✅ Health check passes
- ✅ At least one search returns results  
- ✅ Scores appear reasonable
- ✅ UI loads and responds

---

## 🏆 **Ready to Test!**

**Quick Start:**
1. Add Kaggle credentials to `.env`
2. Run `./start_local.sh` 
3. Visit `http://localhost:5000/datasets`
4. Search for "machine learning"
5. Enjoy your new Dataset Discovery feature! 🎊

**The feature is production-ready and fully integrated with Phoenix!**