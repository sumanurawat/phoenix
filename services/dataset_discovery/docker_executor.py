"""
Docker-based code execution service for secure and isolated analysis
"""
try:
    import docker
    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False
    docker = None

import tempfile
import os
import time
import logging
from pathlib import Path
from typing import Dict, Any, List
import json

logger = logging.getLogger(__name__)


class DockerCodeExecutor:
    """Execute Python code in isolated Docker containers."""
    
    def __init__(self):
        """Initialize Docker client."""
        if not DOCKER_AVAILABLE:
            logger.warning("⚠️ Docker Python module not installed")
            self.client = None
            return
            
        try:
            self.client = docker.from_env()
            # Test Docker connection
            self.client.ping()
            logger.info("🐳 Docker client initialized successfully")
        except Exception as e:
            logger.error(f"❌ Docker initialization failed: {e}")
            self.client = None
    
    def execute_code(self, code: str, dataset_files: List[Path], timeout: int = 120) -> Dict[str, Any]:
        """
        Execute Python code in a Docker container.
        
        Args:
            code: Python code to execute
            dataset_files: List of dataset file paths to mount
            timeout: Execution timeout in seconds
            
        Returns:
            Dictionary with execution results
        """
        if not self.client:
            error_msg = "Docker not available"
            if not DOCKER_AVAILABLE:
                error_msg += " (docker module not installed)"
            else:
                error_msg += " (docker daemon not running)"
            error_msg += " - falling back to local execution"
            
            return {
                "success": False,
                "error": error_msg,
                "output": ""
            }
        
        container = None
        temp_dir = None
        
        try:
            # Create temporary directory for code and data
            temp_dir = Path(tempfile.mkdtemp(prefix="phoenix_docker_"))
            logger.info(f"📁 Created temp directory: {temp_dir}")
            
            # Prepare the execution environment
            script_path, volumes = self._prepare_execution_environment(code, dataset_files, temp_dir)
            
            # Create and run container
            container = self._create_container(script_path, volumes, timeout)
            
            logger.info("🚀 Starting Docker container execution...")
            start_time = time.time()
            
            # Start container and wait for completion
            container.start()
            result = container.wait(timeout=timeout)
            execution_time = time.time() - start_time
            
            # Get container logs (stdout/stderr)
            logs = container.logs(stdout=True, stderr=True).decode('utf-8')
            
            # Determine success based on exit code
            success = result['StatusCode'] == 0
            
            logger.info(f"✅ Container execution completed ({execution_time:.2f}s)")
            logger.info(f"🔢 Exit code: {result['StatusCode']}")
            
            if success:
                return {
                    "success": True,
                    "output": logs,
                    "execution_time": execution_time,
                    "exit_code": result['StatusCode']
                }
            else:
                return {
                    "success": False,
                    "output": logs.split('\n')[-50:] if logs else "",  # Last 50 lines
                    "error": logs,
                    "execution_time": execution_time,
                    "exit_code": result['StatusCode']
                }
                
        except Exception as e:
            # Handle both docker-specific errors and general exceptions
            if DOCKER_AVAILABLE and hasattr(e, '__module__') and 'docker' in str(e.__module__):
                logger.error(f"❌ Container execution error: {e}")
                return {
                    "success": False,
                    "error": f"Container error: {str(e)}",
                    "output": ""
                }
            else:
                logger.error(f"❌ Docker execution failed: {e}")
                return {
                    "success": False,
                    "error": f"Docker execution error: {str(e)}",
                    "output": ""
                }
        finally:
            # Cleanup
            if container:
                try:
                    container.remove(force=True)
                    logger.info("🗑️ Container cleaned up")
                except Exception as e:
                    logger.warning(f"⚠️ Container cleanup failed: {e}")
            
            # Cleanup temp directory
            if temp_dir and temp_dir.exists():
                try:
                    import shutil
                    shutil.rmtree(temp_dir)
                    logger.info("🗑️ Temp directory cleaned up")
                except Exception as e:
                    logger.warning(f"⚠️ Temp directory cleanup failed: {e}")
    
    def _prepare_execution_environment(self, code: str, dataset_files: List[Path], temp_dir: Path) -> tuple:
        """Prepare the execution environment with code and data files."""
        
        # Create script file
        script_path = temp_dir / "analysis_script.py"
        
        # Add imports and setup to the code
        full_code = self._prepare_full_code(code, dataset_files)
        
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(full_code)
        
        # Copy dataset files to temp directory
        data_dir = temp_dir / "data"
        data_dir.mkdir(exist_ok=True)
        
        for file_path in dataset_files:
            if file_path.exists():
                import shutil
                dest_path = data_dir / file_path.name
                shutil.copy2(file_path, dest_path)
                logger.info(f"📋 Copied dataset: {file_path.name}")
        
        # Setup volume mounts
        volumes = {
            str(temp_dir): {'bind': '/workspace', 'mode': 'rw'}
        }
        
        return script_path, volumes
    
    def _prepare_full_code(self, user_code: str, dataset_files: List[Path]) -> str:
        """Prepare complete Python code with imports and file paths."""
        
        imports = """
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import warnings
import sys
import os
import traceback

# Suppress warnings
warnings.filterwarnings('ignore')

# Configure pandas display
pd.set_option('display.max_columns', 20)
pd.set_option('display.max_rows', 100)
pd.set_option('display.width', 1000)

# Change to data directory
os.chdir('/workspace/data')
print(f"📁 Working directory: {os.getcwd()}")
print(f"📋 Available files: {os.listdir('.')}")

"""
        
        # Add file path variables
        file_vars = "\n# Dataset file paths\n"
        for i, file_path in enumerate(dataset_files):
            file_vars += f"file_{i+1} = '{file_path.name}'\n"
            file_vars += f"print(f'File {i+1}: {{file_{i+1}}}')\n"
        
        if dataset_files:
            file_vars += f"main_file = file_1  # Primary data file\n"
            file_vars += f"print(f'Main file: {{main_file}}')\n"
        
        file_vars += "\n"
        
        # Wrap user code in try-catch for better error reporting
        wrapped_code = f"""
print("🚀 Starting analysis execution...")
print("=" * 50)

try:
{self._indent_code(user_code, '    ')}
    
    print("\\n" + "=" * 50)
    print("🏁 Analysis completed successfully!")
    print("=" * 50)
    
except Exception as e:
    print("\\n" + "=" * 50)
    print("❌ ANALYSIS EXECUTION FAILED")
    print("=" * 50)
    print(f"📍 Error Type: {{type(e).__name__}}")
    print(f"💬 Error Message: {{str(e)}}")
    
    # Get the line number where error occurred
    import traceback
    tb = traceback.extract_tb(e.__traceback__)
    if tb:
        error_line = tb[-1].lineno
        print(f"📍 Error Line: {{error_line}}")
        print(f"🔍 Error Context: {{tb[-1].line}}")
    
    print("\\n📚 Full Traceback:")
    print("-" * 30)
    traceback.print_exc()
    print("-" * 30)
    
    # Provide helpful debugging info
    print("\\n🔧 Debug Information:")
    print(f"🐍 Python Version: {{sys.version}}")
    print(f"📁 Working Directory: {{os.getcwd()}}")
    print(f"📋 Available Files: {{os.listdir('.')}}")
    
    sys.exit(1)
"""
        
        return imports + file_vars + wrapped_code
    
    def _indent_code(self, code: str, indent: str) -> str:
        """Indent code block."""
        lines = code.split('\n')
        indented_lines = [indent + line if line.strip() else line for line in lines]
        return '\n'.join(indented_lines)
    
    def _create_container(self, script_path: Path, volumes: dict, timeout: int) -> Any:
        """Create Docker container for code execution."""
        
        # Use Python 3.11 with data science libraries
        image = "python:3.11-slim"
        
        # Install required packages
        command = [
            "bash", "-c",
            """
            pip install --no-cache-dir pandas numpy matplotlib seaborn scipy scikit-learn &&
            cd /workspace &&
            python analysis_script.py
            """
        ]
        
        # Create container
        container = self.client.containers.create(
            image=image,
            command=command,
            volumes=volumes,
            working_dir="/workspace",
            mem_limit="512m",  # 512MB memory limit
            cpu_quota=50000,   # 50% CPU limit
            network_disabled=True,  # No network access for security
            remove=False,  # We'll remove manually after getting logs
            environment={
                "PYTHONUNBUFFERED": "1",
                "MPLBACKEND": "Agg"
            }
        )
        
        logger.info(f"🐳 Created container: {container.id[:12]}")
        return container
    
    def is_available(self) -> bool:
        """Check if Docker is available."""
        return DOCKER_AVAILABLE and self.client is not None


# Global instance
docker_executor = DockerCodeExecutor()