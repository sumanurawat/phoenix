"""
Temporary Dataset Analysis Service for Development Phase

This service generates Python code using Gemini API to analyze downloaded datasets.
It's a temporary solution for development - in production we'll have a full analysis pipeline.

Key Features:
- Uses Gemini API to generate analysis code
- Runs code in temporary files
- Provides step-by-step analysis results
- Auto-cleanup of temporary files
"""

import os
import logging
import tempfile
import subprocess
import sys
import shutil
from pathlib import Path
from typing import Dict, Any, List
import json

logger = logging.getLogger(__name__)


class TempAnalysisService:
    """
    Temporary analysis service that generates and executes Python analysis code
    using Gemini API for dataset insights.
    """
    
    def __init__(self):
        """Initialize the temporary analysis service."""
        
        # Import download service to get actual download directory
        from services.dataset_discovery.download_service import DatasetDownloadService
        download_service = DatasetDownloadService()
        self.downloads_dir = download_service.download_dir / 'raw'
        self.temp_dir = Path(tempfile.gettempdir()) / "phoenix_analysis"
        self.temp_dir.mkdir(exist_ok=True)
        
        # Import Gemini service
        try:
            from services.llm_service import LLMService
            self.llm_service = LLMService()
            
            # Use high-performance model for better code generation
            from config.gemini_models import GEMINI_MODELS
            original_model = self.llm_service.current_model
            self.llm_service.current_model = GEMINI_MODELS.HIGH_PERFORMANCE  # Gemini 2.5 Pro
            logger.info(f"🚀 Upgraded to high-performance model for analysis: {self.llm_service.current_model}")
            logger.info(f"💰 Note: Using premium model - cost is higher but code quality should be much better")
            
        except ImportError as e:
            logger.error(f"Failed to import LLM service: {e}")
            raise
    
    def run_analysis_step(self, dataset_ref: str, step: int, description: str) -> Dict[str, Any]:
        """
        Run a specific analysis step for the dataset.
        
        Args:
            dataset_ref: Reference to the dataset
            step: Step number (1-4)
            description: Description of what this step should do
            
        Returns:
            Dict containing analysis results, insights, and recommendations
        """
        try:
            logger.info(f"🔬 Running analysis step {step} for {dataset_ref}")
            
            # Find dataset files
            dataset_files = self._find_dataset_files(dataset_ref)
            if not dataset_files:
                raise ValueError(f"No files found for dataset {dataset_ref}")
            
            # Generate analysis code for this step
            analysis_code = self._generate_step_code(dataset_ref, step, description, dataset_files)
            
            # Execute the code and capture results
            output, insights, recommendations = self._execute_analysis_code(analysis_code, dataset_files)
            
            return {
                "output": output,
                "insights": insights,
                "recommendations": recommendations,
                "code_generated": True,
                "files_analyzed": len(dataset_files)
            }
            
        except Exception as e:
            logger.error(f"❌ Analysis step {step} failed: {e}")
            return {
                "output": f"Error: {str(e)}",
                "insights": [],
                "recommendations": [f"Fix error: {str(e)}"],
                "code_generated": False,
                "files_analyzed": 0
            }
    
    def generate_analysis_code(self, dataset_ref: str, analysis_results: Dict[str, Any]) -> str:
        """
        Generate complete analysis code based on previous step results.
        
        Args:
            dataset_ref: Reference to the dataset
            analysis_results: Results from previous analysis steps
            
        Returns:
            Complete Python code for dataset analysis
        """
        try:
            logger.info(f"🤖 Generating complete analysis code for {dataset_ref}")
            
            # Find dataset files
            dataset_files = self._find_dataset_files(dataset_ref)
            if not dataset_files:
                raise ValueError(f"No files found for dataset {dataset_ref}")
            
            # Create comprehensive analysis prompt
            prompt = self._create_code_generation_prompt(dataset_ref, dataset_files, analysis_results)
            
            # Generate code using Gemini API
            response = self.llm_service.generate_text(prompt)
            
            # Extract text from response dict
            response_text = response.get('text', '') if isinstance(response, dict) else str(response)
            
            # Extract code from response
            code = self._extract_code_from_response(response_text)
            
            # Save code to temporary file for reference
            code_file = self.temp_dir / f"analysis_{dataset_ref.replace('/', '_')}.py"
            with open(code_file, 'w') as f:
                f.write(code)
            
            logger.info(f"✅ Generated analysis code saved to {code_file}")
            return code
            
        except Exception as e:
            logger.error(f"❌ Code generation failed: {e}")
            raise
    
    def _find_dataset_files(self, dataset_ref: str) -> List[Path]:
        """Find all files for the given dataset."""
        # Convert dataset ref to directory name
        dataset_dir_name = dataset_ref.replace('/', '_')
        
        # Search in downloads directory
        dataset_dirs = list(self.downloads_dir.glob(f"*{dataset_dir_name}*"))
        
        if not dataset_dirs:
            return []
        
        # Get the most recent directory
        dataset_dir = max(dataset_dirs, key=lambda p: p.stat().st_mtime)
        
        # Find data files
        data_files = []
        for ext in ['*.csv', '*.json', '*.xlsx', '*.xls', '*.parquet']:
            data_files.extend(dataset_dir.rglob(ext))
        
        return sorted(data_files)[:5]  # Limit to first 5 files
    
    def _generate_step_code(self, dataset_ref: str, step: int, description: str, files: List[Path]) -> str:
        """Generate Python code for a specific analysis step."""
        
        step_prompts = {
            1: self._create_step1_prompt,
            2: self._create_step2_prompt,
            3: self._create_step3_prompt,
            4: self._create_step4_prompt
        }
        
        if step not in step_prompts:
            raise ValueError(f"Invalid step number: {step}")
        
        prompt = step_prompts[step](dataset_ref, description, files)
        
        # Generate code using Gemini API
        response = self.llm_service.generate_text(prompt)
        
        # Extract text from response dict
        response_text = response.get('text', '') if isinstance(response, dict) else str(response)
        
        return self._extract_code_from_response(response_text)
    
    def _create_step1_prompt(self, dataset_ref: str, description: str, files: List[Path]) -> str:
        """Create prompt for step 1: Data loading and overview."""
        file_list = '\n'.join([f"- {f.name} ({f.stat().st_size / 1024 / 1024:.1f} MB)" for f in files])
        
        return f"""
You are a data analysis expert. Write Python code to load and explore the dataset "{dataset_ref}".

Available files:
{file_list}

CRITICAL INSTRUCTION: You MUST use the predefined file path variables:
- file_1, file_2, etc. contain the FULL ABSOLUTE PATHS to files
- main_file points to the primary data file with FULL PATH
- NEVER use just filenames like 'IRIS.csv' or 'Iris.csv'
- ALWAYS use main_file or file_1 variables

Requirements for Step 1 - Data Loading & Overview:
1. Load the main data file using EXACTLY: df = pd.read_csv(main_file)
2. Display basic information about the dataset:
   - Shape (rows, columns)
   - Column names and data types
   - Memory usage
   - First few rows
3. Check for missing values
4. Provide a high-level overview of the data

Write clean, well-commented Python code that:
- Uses the predefined file path variables (main_file, file_1, etc.)
- Handles potential loading errors
- Prints informative output
- Provides insights about the data structure

Example (FOLLOW THIS EXACTLY):
```python
# Load the main dataset using the predefined file path
print(f"Loading data from: {{main_file}}")
df = pd.read_csv(main_file)
print(f"Dataset shape: {{df.shape}}")
print(df.head())
```

CRITICAL: You MUST use main_file variable, NOT hardcoded paths like '/content/IRIS.csv'
Only return the Python code, no explanations. Use print statements to show results.
"""
    
    def _create_step2_prompt(self, dataset_ref: str, description: str, files: List[Path]) -> str:
        """Create prompt for step 2: Data exploration and summary."""
        file_list = '\n'.join([f"- {f.name} ({f.stat().st_size / 1024 / 1024:.1f} MB)" for f in files])
        
        return f"""
You are a data analysis expert. Write Python code for statistical analysis of dataset "{dataset_ref}".

Available files:
{file_list}

CRITICAL INSTRUCTION: You MUST use the predefined file path variables:
- file_1, file_2, etc. contain the FULL ABSOLUTE PATHS to files
- main_file points to the primary data file with FULL PATH
- NEVER use just filenames like 'iris-flower-dataset.csv' or 'iris.csv'
- ALWAYS use main_file or file_1 variables

Requirements for Step 2 - Data Exploration & Summary:
1. Load data using EXACTLY: df = pd.read_csv(main_file)
2. Generate descriptive statistics for numeric columns
3. Analyze categorical columns (value counts, unique values)
4. Check data quality issues (missing values, duplicates, outliers)
5. Calculate basic correlations between numeric columns

Example (FOLLOW THIS EXACTLY):
```python
# Load the dataset using the predefined file path
df = pd.read_csv(main_file)
print("Statistical Analysis:")
print(df.describe())
```

CRITICAL: You MUST use main_file variable, NOT hardcoded paths like 'iris-flower-dataset.csv'
Only return the Python code, no explanations. Use print statements to show results.
"""
    
    def _create_step3_prompt(self, dataset_ref: str, description: str, files: List[Path]) -> str:
        """Create prompt for step 3: Column-by-column analysis."""
        file_list = '\n'.join([f"- {f.name} ({f.stat().st_size / 1024 / 1024:.1f} MB)" for f in files])
        
        return f"""
You are a data analysis expert. Write Python code for detailed column analysis of dataset "{dataset_ref}".

Available files:
{file_list}

CRITICAL INSTRUCTION: You MUST use the predefined file path variables:
- file_1, file_2, etc. contain the FULL ABSOLUTE PATHS to files
- main_file points to the primary data file with FULL PATH
- NEVER use just filenames like 'iris-flower-dataset.csv' or 'iris.csv'
- ALWAYS use main_file or file_1 variables

Requirements for Step 3 - Column-by-Column Analysis:
1. Load data using EXACTLY: df = pd.read_csv(main_file)
2. For each column, analyze based on its data type:
   - Numeric: distribution, outliers, skewness
   - Categorical: frequency, cardinality
   - DateTime: range, patterns, seasonality
   - Text: length patterns, common values
3. Identify potential data types that might be incorrectly inferred
4. Suggest data cleaning or transformation steps
5. Flag columns with quality issues

Example (FOLLOW THIS EXACTLY):
```python
# Load the dataset using the predefined file path
df = pd.read_csv(main_file)
print("Column-by-Column Analysis:")
for col in df.columns:
    print(f"\\nAnalyzing column: {col}")
    print(f"Data type: {df[col].dtype}")
```

CRITICAL: You MUST use main_file variable, NOT hardcoded paths like 'iris-flower-dataset.csv'
Only return the Python code, no explanations. Use print statements to show results.
"""
    
    def _create_step4_prompt(self, dataset_ref: str, description: str, files: List[Path]) -> str:
        """Create prompt for step 4: AI insights and recommendations."""
        file_list = '\n'.join([f"- {f.name} ({f.stat().st_size / 1024 / 1024:.1f} MB)" for f in files])
        
        return f"""
You are a data analysis expert. Write Python code to generate insights and recommendations for dataset "{dataset_ref}".

Available files:
{file_list}

CRITICAL INSTRUCTION: You MUST use the predefined file path variables:
- file_1, file_2, etc. contain the FULL ABSOLUTE PATHS to files
- main_file points to the primary data file with FULL PATH
- NEVER use just filenames like 'iris-flower-dataset.csv' or 'iris.csv'
- ALWAYS use main_file or file_1 variables

Requirements for Step 4 - AI Insights & Recommendations:
1. Load data using EXACTLY: df = pd.read_csv(main_file)
2. Identify the most interesting patterns in the data
3. Suggest potential analysis directions
4. Recommend visualizations that would be most effective
5. Identify business or research questions this data could answer
6. Highlight any data limitations or caveats

Example (FOLLOW THIS EXACTLY):
```python
# Load the dataset using the predefined file path
df = pd.read_csv(main_file)
print("AI Insights & Recommendations:")
print(f"Dataset shape: {df.shape}")
print("Key insights based on analysis...")
```

CRITICAL: You MUST use main_file variable, NOT hardcoded paths like 'iris.csv'
Only return the Python code, no explanations. Use print statements to show results.
"""
    
    def _create_code_generation_prompt(self, dataset_ref: str, files: List[Path], analysis_results: Dict[str, Any]) -> str:
        """Create prompt for generating complete analysis code."""
        file_list = '\n'.join([f"- {f.name}" for f in files])
        
        return f"""
You are a data analysis expert. Generate a complete Python script for analyzing dataset "{dataset_ref}".

Available files:
{file_list}

Create a comprehensive analysis script that includes:
1. Data loading and initial exploration
2. Statistical analysis and summaries
3. Column-by-column analysis
4. Data quality assessment
5. Insights and recommendations

Requirements:
- Use pandas, numpy, matplotlib, seaborn for analysis
- Include proper error handling
- Add informative comments
- Generate some basic visualizations
- Print results and insights throughout
- Make the code self-contained and runnable

The script should be educational and demonstrate good data analysis practices.
Only return the Python code, no explanations.
"""
    
    def _execute_analysis_code(self, code: str, files: List[Path]) -> tuple:
        """Execute the analysis code and capture results."""
        try:
            # Create temporary script file
            script_file = self.temp_dir / f"temp_analysis_{os.getpid()}.py"
            
            # Prepare the code with proper imports and file paths
            full_code = self._prepare_executable_code(code, files)
            
            # Write code to file
            with open(script_file, 'w') as f:
                f.write(full_code)
            
            # Execute the script and capture output
            result = subprocess.run(
                [sys.executable, str(script_file)],
                capture_output=True,
                text=True,
                timeout=60,  # 1 minute timeout
                cwd=str(self.downloads_dir.parent)  # Set working directory
            )
            
            # Clean up script file
            script_file.unlink(missing_ok=True)
            
            if result.returncode == 0:
                output = result.stdout
                insights = self._extract_insights_from_output(output)
                recommendations = self._extract_recommendations_from_output(output)
                return output, insights, recommendations
            else:
                error_msg = result.stderr or "Unknown execution error"
                return f"Error executing analysis code:\n{error_msg}", [], []
                
        except subprocess.TimeoutExpired:
            return "Analysis timed out after 60 seconds", [], []
        except Exception as e:
            return f"Execution error: {str(e)}", [], []
    
    def _prepare_executable_code(self, code: str, files: List[Path]) -> str:
        """Prepare code for execution with proper imports and file paths."""
        
        # Standard imports
        imports = """
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# Configure display options
pd.set_option('display.max_columns', 20)
pd.set_option('display.max_rows', 100)
pd.set_option('display.width', 1000)

"""
        
        # File path variables with explicit print statements
        file_paths = "\n# Dataset file paths\n"
        for i, file_path in enumerate(files):
            # Use absolute path to ensure file is found
            absolute_path = str(file_path)
            file_paths += f"file_{i+1} = r'{absolute_path}'\n"
            file_paths += f"print(f'File {i+1}: {{file_{i+1}}}')\n"
        
        if files:
            file_paths += f"main_file = file_1  # Primary data file\n"
            file_paths += f"print(f'Main file: {{main_file}}')\n"
        
        file_paths += "\n"
        
        # Fix common AI mistakes in generated code
        fixed_code = self._fix_generated_code(code, files)
        
        # Combine everything
        return imports + file_paths + fixed_code
    
    def _fix_generated_code(self, code: str, files: List[Path]) -> str:
        """Fix common issues in AI-generated code."""
        fixed_code = code
        
        # Fix hardcoded file paths - replace with main_file variable
        common_bad_paths = [
            "'/content/IRIS.csv'",
            '"/content/IRIS.csv"',
            "'IRIS.csv'",
            '"IRIS.csv"',
            "'/content/" + files[0].name + "'",
            '"/content/' + files[0].name + '"',
            "'" + files[0].name + "'",
            '"' + files[0].name + '"'
        ]
        
        for bad_path in common_bad_paths:
            if bad_path in fixed_code:
                fixed_code = fixed_code.replace(bad_path, "main_file")
                logger.info(f"🔧 Fixed hardcoded path {bad_path} → main_file")
        
        # Fix pd.read_csv patterns
        import re
        
        # Replace patterns like pd.read_csv('/content/...') with pd.read_csv(main_file)
        patterns = [
            r"pd\.read_csv\(['\"][^'\"]*['\"]\)",
            r"pd\.read_excel\(['\"][^'\"]*['\"]\)",
            r"pd\.read_json\(['\"][^'\"]*['\"]\)"
        ]
        
        for pattern in patterns:
            if re.search(pattern, fixed_code):
                # Extract the function name (read_csv, read_excel, etc.)
                func_match = re.search(r"pd\.(read_\w+)", fixed_code)
                if func_match:
                    func_name = func_match.group(1)
                    fixed_code = re.sub(pattern, f"pd.{func_name}(main_file)", fixed_code)
                    logger.info(f"🔧 Fixed pd.{func_name} to use main_file")
        
        return fixed_code
    
    def _extract_code_from_response(self, response: str) -> str:
        """Extract Python code from Gemini API response."""
        # Look for code blocks
        if "```python" in response:
            start = response.find("```python") + 9
            end = response.find("```", start)
            if end != -1:
                return response[start:end].strip()
        
        if "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            if end != -1:
                return response[start:end].strip()
        
        # If no code blocks, return the whole response (assume it's all code)
        return response.strip()
    
    def _extract_insights_from_output(self, output: str) -> List[str]:
        """Extract key insights from analysis output."""
        insights = []
        lines = output.split('\n')
        
        # Look for lines that contain insights
        insight_keywords = ['insight:', 'finding:', 'observation:', 'pattern:', 'trend:']
        
        for line in lines:
            line_lower = line.lower().strip()
            if any(keyword in line_lower for keyword in insight_keywords):
                insights.append(line.strip())
            elif len(line.strip()) > 50 and any(word in line_lower for word in ['shows', 'indicates', 'suggests', 'reveals']):
                insights.append(line.strip())
        
        # If no specific insights found, extract some general observations
        if not insights and len(lines) > 5:
            # Take lines that look like summary statements
            for line in lines[max(0, len(lines)-10):]:  # Last 10 lines
                if len(line.strip()) > 30 and '=' not in line and 'dtype:' not in line:
                    insights.append(line.strip())
                if len(insights) >= 3:
                    break
        
        return insights[:5]  # Limit to 5 insights
    
    def _extract_recommendations_from_output(self, output: str) -> List[str]:
        """Extract recommendations from analysis output."""
        recommendations = []
        lines = output.split('\n')
        
        # Look for recommendation keywords
        rec_keywords = ['recommend:', 'suggestion:', 'consider:', 'should:', 'could:']
        
        for line in lines:
            line_lower = line.lower().strip()
            if any(keyword in line_lower for keyword in rec_keywords):
                recommendations.append(line.strip())
            elif any(word in line_lower for word in ['clean', 'remove', 'transform', 'fix', 'improve']):
                if len(line.strip()) > 30:
                    recommendations.append(line.strip())
        
        # Add some general recommendations if none found
        if not recommendations:
            recommendations = [
                "Consider visualizing the data to identify patterns",
                "Check for data quality issues and missing values",
                "Explore correlations between variables"
            ]
        
        return recommendations[:5]  # Limit to 5 recommendations
    
    def cleanup_temp_files(self):
        """Clean up temporary analysis files."""
        try:
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
                logger.info(f"🗑️ Cleaned up temporary analysis files from {self.temp_dir}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to cleanup temp files: {e}")