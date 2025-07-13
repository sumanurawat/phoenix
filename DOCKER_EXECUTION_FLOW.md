# Docker Container Execution Flow for Dataset Analysis

## 🏗️ High-Level Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Phoenix Web   │    │  Iterative      │    │   Docker        │
│   Frontend      │────│  Coding Agent   │────│   Container     │
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
    User clicks              LLM generates           Executes code
   "Start Analysis"          Python code             securely
```

## 🔄 Detailed Execution Sequence

### Phase 1: Request Initiation
```
Frontend (JavaScript)
├── User clicks "Start Analysis"
├── Sends POST to /api/datasets/analyze/step
└── Includes: dataset_ref, model_config, description
```

### Phase 2: Agent Setup
```
Backend (Python)
├── Creates EnhancedLLMService (Claude/Gemini)
├── Initializes IterativeCodingAgent
├── Enables conversation tracking
└── Finds dataset files in temp directory
```

### Phase 3: Code Generation Loop
```
For each iteration (max 5):
├── 🤖 LLM generates Python code
├── 📝 Code logged to conversation
├── 🐳 Execute in Docker container
└── ❌ If failed → retry with error context
```

## 🐳 Docker Container Execution Details

### Container Creation
```bash
# Docker command sequence:
docker create python:3.11-slim \
  --memory=512m \
  --cpu-quota=50000 \
  --network=none \
  --volume=/tmp/phoenix_xxxxx:/workspace

# Container gets:
Memory Limit: 512MB
CPU Limit: 50% of one core
Network: DISABLED (security)
Filesystem: Isolated + mounted data
```

### Inside Container Execution
```bash
# Step 1: Install dependencies
pip install --no-cache-dir pandas numpy matplotlib seaborn scipy scikit-learn

# Step 2: Change to workspace
cd /workspace

# Step 3: Execute generated code
python analysis_script.py
```

### Generated Script Structure
```python
# File: /workspace/analysis_script.py

# 1. Imports (auto-added)
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
# ... other imports

# 2. File variables (auto-added)
file_1 = 'dataset_file.csv'
main_file = file_1

# 3. User's generated code (wrapped in try-catch)
print("🚀 Starting analysis execution...")
print("=" * 50)

try:
    # 🤖 LLM-generated code goes here
    df = pd.read_csv(main_file)
    print(f"✅ Data loaded successfully: {df.shape}")
    # ... rest of analysis code
    
    print("\n" + "=" * 50)
    print("🏁 Analysis completed successfully!")
    print("=" * 50)
    
except Exception as e:
    print("\n" + "=" * 50)
    print("❌ ANALYSIS EXECUTION FAILED")
    print("=" * 50)
    print(f"📍 Error Type: {type(e).__name__}")
    print(f"💬 Error Message: {str(e)}")
    
    # Debug information
    import traceback
    tb = traceback.extract_tb(e.__traceback__)
    if tb:
        print(f"📍 Error Line: {tb[-1].lineno}")
        print(f"🔍 Error Context: {tb[-1].line}")
    
    print("\n📚 Full Traceback:")
    traceback.print_exc()
    
    print("\n🔧 Debug Information:")
    print(f"🐍 Python Version: {sys.version}")
    print(f"📁 Working Directory: {os.getcwd()}")
    print(f"📋 Available Files: {os.listdir('.')}")
    
    sys.exit(1)
```

## 📊 Output Collection

### Success Case
```
Container Exit Code: 0
STDOUT: All print statements, analysis results, charts info
STDERR: Warnings (if any)
Result: ✅ Code execution successful
```

### Failure Case
```
Container Exit Code: 1
STDOUT: Progress prints + error details
STDERR: Python traceback, import errors
Result: ❌ Send error to LLM for fixing
```

## 🔄 Iteration & Error Handling

### Error Flow
```
┌─────────────────┐
│ Code fails      │
│ Exit code = 1   │
└─────────┬───────┘
          │
          v
┌─────────────────┐
│ Collect error   │
│ STDERR output   │
└─────────┬───────┘
          │
          v
┌─────────────────┐
│ Send to LLM:    │
│ "Fix this error │
│ [error details]"│
└─────────┬───────┘
          │
          v
┌─────────────────┐
│ Generate fixed  │
│ code version    │
└─────────┬───────┘
          │
          v
┌─────────────────┐
│ Create new      │
│ container &     │
│ try again       │
└─────────────────┘
```

## 🗑️ Cleanup Process

### After Each Execution
```bash
# Container cleanup
docker remove container_id --force

# Temp directory cleanup  
rm -rf /tmp/phoenix_docker_xxxxx/
```

### Resource Management
- Containers are ephemeral (created & destroyed per execution)
- No data persists between iterations
- Memory & CPU limits prevent resource exhaustion
- Network disabled prevents external access

## 💬 Conversation Tracking

Every step is logged to the conversation panel:

```
🤖 User: "Generate code for: Load and explore dataset"
📝 System: "Executing code using 🐳 Docker Container"
✅ AI: "```python\n[generated code]\n```\n✅ Execution Result: [output]"
```

Or in case of error:

```
🤖 User: "Fix error: FileNotFoundError"  
📝 System: "Executing code using 🐳 Docker Container"
❌ AI: "```python\n[fixed code]\n```\n❌ Execution Failed: [error details]"
```

## 🔒 Security Features

- **Network Isolation**: No internet access
- **Resource Limits**: Memory and CPU capped  
- **Filesystem Isolation**: Only sees mounted data
- **Process Isolation**: Cannot access host system
- **Temporary**: Containers destroyed after use

## 🎯 Benefits

1. **Safety**: Untrusted LLM code runs isolated
2. **Consistency**: Same environment every time
3. **Scalability**: Easy to parallelize
4. **Debuggability**: Complete logs captured
5. **Reliability**: Failed containers don't affect system