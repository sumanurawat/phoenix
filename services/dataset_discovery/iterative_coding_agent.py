"""
Iterative Coding Agent for Dataset Analysis

This agent writes Python code, runs it, analyzes errors, and iterates until success.
It's designed to produce high-quality analysis code through multiple refinement cycles.
"""
import os
import logging
import tempfile
import subprocess
import sys
import re
import time
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass

from services.enhanced_llm_service import EnhancedLLMService, ModelProvider
from services.dataset_discovery.docker_executor import docker_executor
from services.dataset_discovery.conversation_tracker import ConversationTracker

logger = logging.getLogger(__name__)


@dataclass
class CodeIteration:
    """Represents one iteration of code generation and execution."""
    iteration: int
    code: str
    execution_result: str
    success: bool
    error_message: Optional[str] = None
    execution_time: float = 0.0
    model_used: str = ""
    generation_time: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    phase_description: str = ""


@dataclass
class AgentResult:
    """Final result from the iterative coding agent."""
    success: bool
    final_code: str
    final_output: str
    iterations: List[CodeIteration]
    total_iterations: int
    total_cost_estimate: float
    insights: List[str]
    recommendations: List[str]
    fallback_info: Optional[Dict[str, Any]] = None  # Track if fallback was used
    conversation_id: Optional[str] = None  # Track conversation ID for chat display


class IterativeCodingAgent:
    """
    An agent that iteratively writes and refines Python code until it works correctly.
    """
    
    def __init__(self, llm_service: EnhancedLLMService, max_iterations: int = 5, 
                 enable_conversation_tracking: bool = True, save_conversations: bool = False):
        """Initialize the coding agent."""
        self.llm_service = llm_service
        self.max_iterations = max_iterations
        self.temp_dir = Path(tempfile.gettempdir()) / "phoenix_coding_agent"
        self.temp_dir.mkdir(exist_ok=True)
        
        # Initialize conversation tracking
        self.enable_conversation_tracking = enable_conversation_tracking
        self.conversation_tracker = None
        if enable_conversation_tracking:
            self.conversation_tracker = ConversationTracker(
                save_to_db=save_conversations,
                auto_cleanup=not save_conversations  # Cleanup if not saving
            )
        
        logger.info(f"🤖 Iterative Coding Agent initialized")
        logger.info(f"🔄 Max iterations: {max_iterations}")
        logger.info(f"📁 Temp directory: {self.temp_dir}")
        logger.info(f"💬 Conversation tracking: {enable_conversation_tracking}")
        if enable_conversation_tracking:
            logger.info(f"💾 Save conversations: {save_conversations}")
    
    def generate_and_refine_code(
        self, 
        task_prompt: str, 
        dataset_files: List[Path],
        expected_outcomes: List[str] = None,
        enable_thinking: bool = False,
        thinking_budget: int = 2048
    ) -> AgentResult:
        """
        Generate and iteratively refine code until it works correctly.
        
        Args:
            task_prompt: The analysis task description
            dataset_files: List of dataset file paths
            expected_outcomes: Optional list of expected outputs/behaviors
            enable_thinking: Enable Claude thinking mode
            thinking_budget: Token budget for thinking (1024-3072)
            
        Returns:
            AgentResult with final code and execution details
        """
        logger.info(f"🚀 Starting iterative code generation for task")
        logger.info(f"📊 Dataset files: {len(dataset_files)}")
        logger.info(f"🎯 Expected outcomes: {len(expected_outcomes or [])}")
        
        # Initialize conversation tracking
        if self.conversation_tracker:
            conversation_id = self.conversation_tracker.create_conversation(
                title=f"Dataset Analysis: {task_prompt[:50]}..."
            )
            logger.info(f"💬 Created conversation: {conversation_id}")
        
        iterations: List[CodeIteration] = []
        current_code = ""
        fallback_info = None  # Track fallback usage
        
        for iteration in range(1, self.max_iterations + 1):
            logger.info(f"🔄 Starting iteration {iteration}/{self.max_iterations}")
            
            try:
                # Generate code for this iteration
                generation_start = time.time()
                if iteration == 1:
                    # First iteration - generate initial code
                    logger.info(f"🎯 Phase: Generating initial code")
                    
                    # Track conversation
                    if self.conversation_tracker:
                        initial_prompt = f"""🚀 **Iteration {iteration} - Initial Code Generation**

**Task:** {task_prompt}

**Dataset Files Available:**
{chr(10).join([f"- {f.name} ({f.stat().st_size / 1024 / 1024:.1f} MB)" for f in dataset_files])}

**Instructions:** Generate robust Python code for this analysis task. The code should:
- Use predefined file path variables (file_1, file_2, etc., main_file)
- Include comprehensive error handling
- Add informative print statements throughout
- Handle common data issues (missing files, encoding problems, data types)
- Be self-contained and executable"""
                        
                        self.conversation_tracker.add_user_prompt(
                            step=iteration, 
                            iteration=iteration,
                            task_description=initial_prompt,
                            code_type="initial"
                        )
                    
                    code, gen_info = self._generate_initial_code(task_prompt, dataset_files, enable_thinking, thinking_budget)
                    phase_desc = "Generating initial analysis code"
                else:
                    # Subsequent iterations - refine based on previous errors
                    logger.info(f"🎯 Phase: Refining code (iteration {iteration})")
                    previous_iteration = iterations[-1]
                    
                    # Track conversation
                    if self.conversation_tracker:
                        error_prompt = f"""🔧 **Iteration {iteration} - Code Refinement**

**Previous attempt failed with error:**
```
{previous_iteration.error_message}
```

**Task:** {task_prompt}

**Instructions:** Fix the error above and improve the code. Focus on:
- Resolving the specific error that occurred
- Adding better error handling
- Ensuring robust data processing
- Improving code reliability"""
                        
                        self.conversation_tracker.add_user_prompt(
                            step=iteration,
                            iteration=iteration,
                            task_description=error_prompt,
                            code_type="refinement"
                        )
                    
                    code, gen_info = self._refine_code(
                        task_prompt, 
                        dataset_files, 
                        previous_iteration.code,
                        previous_iteration.error_message,
                        iterations,
                        enable_thinking,
                        thinking_budget
                    )
                    phase_desc = f"Refining code based on iteration {iteration-1} errors"
                generation_time = time.time() - generation_start
                
                # Track execution start
                if self.conversation_tracker:
                    execution_method = "🐳 Docker Container" if docker_executor.is_available() else "💻 Local Environment"
                    self.conversation_tracker.add_message("system", f"**Executing code using {execution_method}**", {
                        "step": iteration,
                        "iteration": iteration,
                        "execution_method": execution_method,
                        "title": f"Code Execution - {execution_method}"
                    })
                
                # Execute the code (Docker if available, otherwise local)
                execution_result = self._execute_code(code, dataset_files)
                
                # Check if execution was successful
                success = execution_result["success"]
                error_message = execution_result.get("error")
                output = execution_result.get("output", "")
                execution_time = execution_result.get("execution_time", 0)
                
                # Track conversation for model response
                if self.conversation_tracker:
                    # Include the generated code in the response
                    response_content = f"```python\n{code}\n```\n\n"
                    if success:
                        response_content += f"✅ **Execution Result:**\n{output}"
                    else:
                        response_content += f"❌ **Execution Failed:**\n{error_message}"
                    
                    self.conversation_tracker.add_model_response(
                        step=iteration,
                        iteration=iteration,
                        success=success,
                        output=response_content,
                        error=error_message if not success else "",
                        execution_time=execution_time,
                        generation_time=generation_time,
                        tokens={
                            'input': gen_info.get('prompt_tokens', 0),
                            'output': gen_info.get('completion_tokens', 0)
                        },
                        code=code,  # Add code to metadata
                        model_used=f"{self.llm_service.provider.value}:{self.llm_service.model}"  # Add model info
                    )
                
                # Create iteration record
                iteration_record = CodeIteration(
                    iteration=iteration,
                    code=code,
                    execution_result=output,
                    success=success,
                    error_message=error_message,
                    execution_time=execution_time,
                    model_used=f"{self.llm_service.provider.value}:{self.llm_service.model}",
                    generation_time=generation_time,
                    prompt_tokens=gen_info.get('prompt_tokens', 0),
                    completion_tokens=gen_info.get('completion_tokens', 0),
                    phase_description=phase_desc
                )
                iterations.append(iteration_record)
                
                if success:
                    logger.info(f"✅ Code execution successful on iteration {iteration}")
                    break
                else:
                    logger.warning(f"❌ Iteration {iteration} failed: {error_message}")
                    
            except Exception as e:
                logger.error(f"❌ Iteration {iteration} crashed: {e}")
                iteration_record = CodeIteration(
                    iteration=iteration,
                    code=current_code,
                    execution_result="",
                    success=False,
                    error_message=str(e),
                    model_used=f"{self.llm_service.provider.value}:{self.llm_service.model}",
                    generation_time=locals().get('generation_time', 0),
                    prompt_tokens=0,
                    completion_tokens=0,
                    phase_description=locals().get('phase_desc', f"Iteration {iteration} crashed")
                )
                iterations.append(iteration_record)
        
        # Generate final result
        final_iteration = iterations[-1] if iterations else None
        final_success = final_iteration.success if final_iteration else False
        final_code = final_iteration.code if final_iteration else ""
        final_output = final_iteration.execution_result if final_iteration else ""
        
        # Extract insights and recommendations
        insights, recommendations = self._extract_insights_and_recommendations(
            final_output, final_success, iterations
        )
        
        # Calculate cost estimate
        cost_info = self.llm_service.get_cost_summary()
        total_cost = cost_info.get("estimated_cost_usd", 0.0)
        
        # Check if any iteration used fallback
        fallback_used_count = sum(1 for it in iterations if hasattr(it, 'used_fallback') and it.used_fallback)
        if fallback_used_count > 0:
            fallback_info = {
                "fallback_used": True,
                "fallback_iterations": fallback_used_count,
                "total_iterations": len(iterations),
                "fallback_model": "gemini-1.5-flash"
            }
        else:
            fallback_info = None

        result = AgentResult(
            success=final_success,
            final_code=final_code,
            final_output=final_output,
            iterations=iterations,
            total_iterations=len(iterations),
            total_cost_estimate=total_cost,
            insights=insights,
            recommendations=recommendations,
            fallback_info=fallback_info
        )
        
        # Add conversation ID to result if available
        if self.conversation_tracker:
            result.conversation_id = self.conversation_tracker.conversation_id
        
        logger.info(f"🏁 Agent completed after {len(iterations)} iterations")
        logger.info(f"✅ Success: {final_success}")
        logger.info(f"💰 Estimated cost: ${total_cost:.4f}")
        
        # Note: Conversation cleanup happens separately via cleanup_conversation()
        
        return result
    
    def _generate_initial_code(self, task_prompt: str, dataset_files: List[Path], 
                              enable_thinking: bool = False, thinking_budget: int = 2048) -> Tuple[str, Dict[str, Any]]:
        """Generate initial code for the task."""
        file_list = '\n'.join([f"- {f.name} ({f.stat().st_size / 1024 / 1024:.1f} MB)" for f in dataset_files])
        
        prompt = f"""
You are an expert Python data analyst. Write working Python code for this task:

{task_prompt}

Available files: {file_list}

REQUIREMENTS:
1. Use the predefined variables: main_file = "{dataset_files[0].name}" 
2. Load data with pandas, handle errors properly
3. Create visualizations with matplotlib/seaborn and SAVE as PNG files
4. For each plot, print PLOT_INFO metadata in this exact format:

PLOT_INFO_START
title: Your Plot Title  
description: What the plot shows
filename: your_plot.png
key_insights: Key findings from this plot
PLOT_INFO_END

5. Include print statements showing progress
6. Use proper error handling with try/except

EXAMPLE CODE PATTERN:
```python
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

try:
    # Load data
    print(f"Loading data from: {{main_file}}")
    df = pd.read_csv(main_file)
    print(f"✅ Data loaded: {{df.shape}}")
    
    # Analysis
    print("\\n## DATA OVERVIEW")
    print(df.head())
    print(df.info())
    
    # Create plot
    plt.figure(figsize=(10, 6))
    df['column'].hist(bins=20)
    plt.title('Distribution')
    plt.savefig('distribution.png', dpi=150, bbox_inches='tight')
    plt.close()
    
    # Plot metadata
    print("PLOT_INFO_START")
    print("title: Distribution Plot")
    print("description: Shows data distribution")  
    print("filename: distribution.png")
    print("key_insights: Data is normally distributed")
    print("PLOT_INFO_END")
    
except Exception as e:
    print(f"❌ Error: {{e}}")
```

Write complete, executable Python code. Focus on working code over complex formatting.
"""
        
        logger.info(f"🤖 Generating initial code with {self.llm_service.provider.value}:{self.llm_service.model}")
        if enable_thinking:
            logger.info(f"🧠 Using thinking mode with {thinking_budget} tokens budget")
        response = self.llm_service.generate_text(prompt, enable_fallback=True, 
                                                enable_thinking=enable_thinking, 
                                                thinking_budget=thinking_budget)
        
        if response.get("success"):
            logger.info(f"✅ LLM response received (length: {len(response['text'])})")
            
            # Check if fallback was used
            if response.get("fallback_used"):
                logger.info(f"🔄 Fallback used: {response.get('fallback_from')} → {response.get('model')}")
            
            # Log raw response for debugging
            logger.info(f"📝 Raw LLM response preview: {response['text'][:300]}...")
            
            code = self._extract_code_from_response(response["text"])
            logger.info(f"🎯 Extracted code length: {len(code)}")
            
            # Return code and generation info
            gen_info = {
                'prompt_tokens': response.get('usage', {}).get('input_tokens', 0),
                'completion_tokens': response.get('usage', {}).get('output_tokens', 0),
                'model_used': response.get('model', self.llm_service.model),
                'fallback_used': response.get('fallback_used', False)
            }
            return code, gen_info
        else:
            error_msg = f"Failed to generate initial code: {response.get('error')}"
            logger.error(f"❌ {error_msg}")
            raise Exception(error_msg)
    
    def _refine_code(
        self, 
        task_prompt: str, 
        dataset_files: List[Path], 
        previous_code: str,
        error_message: str,
        all_iterations: List[CodeIteration],
        enable_thinking: bool = False,
        thinking_budget: int = 2048
    ) -> Tuple[str, Dict[str, Any]]:
        """Refine code based on previous execution errors."""
        
        # Build context from previous iterations
        iteration_context = "\n".join([
            f"Iteration {it.iteration}: {'✅ Success' if it.success else '❌ Failed'} - {it.error_message or 'No error'}"
            for it in all_iterations[-3:]  # Last 3 iterations for context
        ])
        
        prompt = f"""
You are an expert Python debugger. The previous code failed with an error. Fix it and improve it.

ORIGINAL TASK: {task_prompt}

PREVIOUS CODE:
```python
{previous_code}
```

ERROR ENCOUNTERED:
{error_message}

ITERATION HISTORY:
{iteration_context}

INSTRUCTIONS:
1. Analyze the error and understand the root cause
2. Fix the specific issue that caused the failure
3. Improve error handling to prevent similar issues
4. Keep the same overall structure and approach
5. Add more robust validation and checks
6. Ensure the code is self-contained and executable

CRITICAL SYNTAX FIXES:
- NEVER use standalone 'pass' statements
- Fix indentation errors immediately (4 spaces per level)
- Ensure every if/for/while/try block has proper executable code
- Complete all unfinished code blocks
- Validate Python syntax before submitting

COMMON FIXES:
- File path issues: Use the predefined variables (main_file, file_1, etc.)
- Data type issues: Add explicit type conversion
- Missing data: Handle NaN/missing values properly
- Import errors: Include all necessary imports
- Encoding issues: Try different encodings for file reading
- Indentation: Fix all IndentationError issues

OUTPUT FORMATTING:
- Use proper markdown headers (## SECTION)
- Structure output clearly with line breaks
- Format all sections consistently
- Include clear error handling messages

Write the improved, fixed Python code.
Only return the Python code, no explanations.
"""
        
        logger.info(f"🔧 Refining code with {self.llm_service.provider.value}:{self.llm_service.model}")
        if enable_thinking:
            logger.info(f"🧠 Using thinking mode with {thinking_budget} tokens budget")
        response = self.llm_service.generate_text(prompt, enable_fallback=True,
                                                enable_thinking=enable_thinking,
                                                thinking_budget=thinking_budget)
        
        if response.get("success"):
            logger.info(f"✅ Refinement response received (length: {len(response['text'])})")
            
            # Log raw response for debugging
            logger.info(f"📝 Raw refinement response preview: {response['text'][:300]}...")
            
            # Add detailed iteration debugging
            logger.info(f"🔍 Attempting to extract code from iteration {len(all_iterations)} response")
            
            code = self._extract_code_from_response(response["text"])
            logger.info(f"🎯 Refined code length: {len(code)}")
            
            # Return code and generation info
            gen_info = {
                'prompt_tokens': response.get('usage', {}).get('input_tokens', 0),
                'completion_tokens': response.get('usage', {}).get('output_tokens', 0),
                'model_used': response.get('model', self.llm_service.model),
                'fallback_used': response.get('fallback_used', False)
            }
            return code, gen_info
        else:
            error_msg = f"Failed to refine code: {response.get('error')}"
            logger.error(f"❌ {error_msg}")
            raise Exception(error_msg)
    
    def _execute_code(self, code: str, dataset_files: List[Path]) -> Dict[str, Any]:
        """Execute the generated code and return results (Docker preferred, local fallback)."""
        logger.info(f"🚀 Executing code (length: {len(code)})")
        
        # Try Docker execution first (safer and isolated)
        if docker_executor.is_available():
            logger.info("🐳 Using Docker execution (isolated environment)")
            result = docker_executor.execute_code(code, dataset_files)
            if result["success"] or "Docker not available" not in result.get("error", ""):
                return result
            else:
                logger.warning("🔄 Docker execution failed, falling back to local execution")
        else:
            logger.info("💻 Using local execution (Docker not available)")
        
        # Fallback to local execution
        return self._execute_code_local(code, dataset_files)
    
    def _execute_code_local(self, code: str, dataset_files: List[Path]) -> Dict[str, Any]:
        """Execute code locally (fallback method)."""
        logger.info(f"💻 Executing code locally (length: {len(code)})")
        
        try:
            # Create temporary script file
            script_file = self.temp_dir / f"analysis_{int(time.time())}.py"
            
            # Prepare executable code with file paths and imports
            full_code = self._prepare_executable_code(code, dataset_files)
            
            # Log the full code for debugging
            logger.info(f"📝 Full executable code preview (first 500 chars):")
            logger.info(f"```python\n{full_code[:500]}...\n```")
            
            # Write code to file
            with open(script_file, 'w', encoding='utf-8') as f:
                f.write(full_code)
            
            logger.info(f"📝 Code written to: {script_file}")
            logger.info(f"📁 Working directory: {dataset_files[0].parent if dataset_files else Path.cwd()}")
            
            # Execute the script
            start_time = time.time()
            result = subprocess.run(
                [sys.executable, str(script_file)],
                capture_output=True,
                text=True,
                timeout=120,  # 2 minute timeout
                cwd=str(dataset_files[0].parent if dataset_files else Path.cwd())
            )
            execution_time = time.time() - start_time
            
            # Log execution results
            logger.info(f"⏱️ Execution completed in {execution_time:.2f}s")
            logger.info(f"🔢 Return code: {result.returncode}")
            
            # Check for plot generation in output
            if result.stdout and "PLOT_INFO_START" in result.stdout:
                plot_count = result.stdout.count("PLOT_INFO_START")
                logger.info(f"📈 Found {plot_count} plots in output")
                
                # Extract and log plot filenames
                import re
                plot_matches = re.findall(r'filename:\s*(.+)$', result.stdout, re.MULTILINE)
                if plot_matches:
                    logger.info(f"📊 Generated plot files: {plot_matches}")
                    
                    # Check if files actually exist
                    working_dir = dataset_files[0].parent if dataset_files else Path.cwd()
                    for plot_file in plot_matches:
                        plot_path = working_dir / plot_file
                        if plot_path.exists():
                            logger.info(f"✅ Plot file exists: {plot_path}")
                        else:
                            logger.warning(f"❌ Plot file NOT found: {plot_path}")
            else:
                logger.info("📊 No plots found in output")
            
            if result.stdout:
                logger.info(f"📤 STDOUT (length: {len(result.stdout)}):")
                logger.info(f"```\n{result.stdout[:1000]}{'...' if len(result.stdout) > 1000 else ''}\n```")
            
            if result.stderr:
                logger.warning(f"❌ STDERR (length: {len(result.stderr)}):")
                logger.warning(f"```\n{result.stderr[:1000]}{'...' if len(result.stderr) > 1000 else ''}\n```")
            
            # Clean up script file (but keep for debugging if failed)
            if result.returncode == 0:
                script_file.unlink(missing_ok=True)
            else:
                logger.warning(f"🔍 Failed script kept for debugging: {script_file}")
            
            if result.returncode == 0:
                logger.info(f"✅ Code executed successfully ({execution_time:.2f}s)")
                return {
                    "success": True,
                    "output": result.stdout,
                    "execution_time": execution_time
                }
            else:
                logger.warning(f"❌ Code execution failed ({execution_time:.2f}s)")
                return {
                    "success": False,
                    "output": result.stdout,
                    "error": result.stderr,
                    "execution_time": execution_time
                }
                
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Code execution timed out after 2 minutes",
                "output": ""
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Execution error: {str(e)}",
                "output": ""
            }
    
    def _prepare_executable_code(self, code: str, files: List[Path]) -> str:
        """Prepare code with imports and file paths."""
        imports = """
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import warnings
import sys
import os

warnings.filterwarnings('ignore')

# Configure display options
pd.set_option('display.max_columns', 20)
pd.set_option('display.max_rows', 100)
pd.set_option('display.width', 1000)

# Configure matplotlib for better plot saving
plt.style.use('default')
plt.rcParams['figure.dpi'] = 150
plt.rcParams['savefig.dpi'] = 150
plt.rcParams['savefig.bbox'] = 'tight'

# Ensure we're in the right directory for saving plots
current_dir = os.getcwd()
print(f"Working directory: {current_dir}")

"""
        
        # File path variables
        file_paths = "\n# Dataset file paths\n"
        for i, file_path in enumerate(files):
            absolute_path = str(file_path.resolve())
            file_paths += f"file_{i+1} = r'{absolute_path}'\n"
            file_paths += f"print(f'File {i+1}: {{file_{i+1}}}')\n"
        
        if files:
            file_paths += f"main_file = file_1  # Primary data file\n"
            file_paths += f"print(f'Main file: {{main_file}}')\n"
        
        file_paths += "\n"
        
        return imports + file_paths + code
    
    def _extract_code_from_response(self, response: str) -> str:
        """Extract Python code from LLM response with robust handling."""
        logger.info(f"🔍 Extracting code from response (length: {len(response)})")
        
        # Log first 200 chars for debugging
        logger.info(f"📝 Response preview: {response[:200]}...")
        
        # Try multiple code block patterns - more robust extraction
        patterns = [
            (r"```python\s*\n(.*?)\n```", "python block with newlines"),
            (r"```python\s*(.*?)```", "python block"),
            (r"```\s*\n(.*?)\n```", "generic block with newlines"),
            (r"```\s*(.*?)```", "generic block"),
            (r"```python\s*\n(.*?)(?:\n```|$)", "python block (end-of-string)"),
            (r"```\s*\n(.*?)(?:\n```|$)", "generic block (end-of-string)"),
        ]
        
        for pattern, description in patterns:
            matches = re.findall(pattern, response, re.DOTALL)
            if matches:
                code = matches[0].strip()
                logger.info(f"✅ Found code using {description} pattern (length: {len(code)})")
                
                # Additional cleaning for Claude 4's response format
                code = self._clean_extracted_code(code)
                return code
        
        # If no code blocks found, try to extract from whole response
        logger.warning("⚠️ No code blocks found, using whole response")
        
        # Clean the whole response
        cleaned = self._clean_extracted_code(response)
        return cleaned
    
    def _clean_extracted_code(self, code: str) -> str:
        """Clean extracted code to remove common formatting issues."""
        # Remove leading/trailing whitespace
        code = code.strip()
        
        # Remove any remaining markdown markers that might have been included
        code = re.sub(r'^```python\s*', '', code, flags=re.MULTILINE)
        code = re.sub(r'^```\s*', '', code, flags=re.MULTILINE)
        code = re.sub(r'\s*```$', '', code, flags=re.MULTILINE)
        
        # Basic syntax validation
        try:
            import ast
            ast.parse(code)
            logger.info(f"✅ Code syntax validation passed")
        except SyntaxError as e:
            logger.warning(f"⚠️ Syntax error detected in extracted code: {e}")
            logger.warning(f"🔍 Problematic line area: {code.split(chr(10))[max(0, e.lineno-3):e.lineno+2] if e.lineno else 'Unknown'}")
            
            # Try to fix common issues
            code = self._attempt_syntax_fixes(code)
        
        # Log the cleaning process
        logger.info(f"🧹 Cleaned code (length: {len(code)})")
        if "```" in code:
            logger.warning(f"⚠️ Code still contains markdown markers after cleaning!")
            logger.warning(f"🔍 Code preview: {code[:300]}...")
        
        return code
    
    def _attempt_syntax_fixes(self, code: str) -> str:
        """Attempt to fix common syntax issues in generated code."""
        logger.info(f"🔧 Attempting to fix syntax issues...")
        
        lines = code.split('\n')
        fixed_lines = []
        
        for i, line in enumerate(lines):
            fixed_lines.append(line)
            
            # Check if line ends with colon and next line is empty or missing
            if line.strip().endswith(':') and (i == len(lines) - 1 or not lines[i + 1].strip()):
                # Get proper indentation for the pass statement
                indent = len(line) - len(line.lstrip())
                if any(keyword in line for keyword in ['if ', 'for ', 'while ', 'def ', 'class ', 'try:', 'except', 'else:', 'elif ']):
                    pass_line = ' ' * (indent + 4) + 'pass'
                    logger.info(f"🔧 Adding pass statement with {indent + 4} spaces after: {line.strip()}")
                    fixed_lines.append(pass_line)
        
        # Remove trailing incomplete lines
        while fixed_lines and fixed_lines[-1].strip() and not fixed_lines[-1].strip().endswith((':', ';', ')', ']', '}')) and not fixed_lines[-1].strip().startswith(('#', '//', '"""', "'''")):
            if len(fixed_lines[-1].strip()) < 20 and any(char in fixed_lines[-1] for char in ['(', '[', '{', '"', "'"]):
                logger.warning(f"🗑️ Removing potentially incomplete line: {fixed_lines[-1]}")
                fixed_lines.pop()
            else:
                break
        
        return '\n'.join(fixed_lines)
    
    def _extract_insights_and_recommendations(
        self, 
        output: str, 
        success: bool, 
        iterations: List[CodeIteration]
    ) -> Tuple[List[str], List[str]]:
        """Extract insights and recommendations from the analysis."""
        insights = []
        recommendations = []
        
        if success and output:
            # Skip plot descriptions and extract actual insights
            lines = output.split('\n')
            in_plot_section = False
            
            for line in lines:
                line = line.strip()
                
                # Skip plot info blocks
                if 'PLOT_INFO_START' in line:
                    in_plot_section = True
                    continue
                if 'PLOT_INFO_END' in line:
                    in_plot_section = False
                    continue
                if in_plot_section:
                    continue
                
                # Skip lines that are just plot metadata
                if line.startswith(('title:', 'description:', 'filename:', 'key_insights:')):
                    continue
                
                # Look for actual analytical insights
                if len(line) > 40 and any(word in line.lower() for word in 
                    ['correlation', 'outlier', 'distribution', 'significant', 'pattern', 
                     'trend', 'relationship', 'clustering', 'variance', 'mean', 'median',
                     'detected', 'found', 'identified', 'discovered', 'analysis shows']):
                    # Avoid generic plot descriptions
                    if not any(skip in line.lower() for skip in 
                        ['shows the frequency', 'shows the relationship', 'shows the scatter']):
                        insights.append(line)
                        if len(insights) >= 5:
                            break
        
        # Add iteration-based recommendations
        if len(iterations) > 1:
            recommendations.append(f"Code required {len(iterations)} iterations to complete successfully")
        
        if not success:
            recommendations.append("Analysis failed to complete - consider manual review")
            recommendations.append("Try a different model or increase iteration limit")
        
        # Look for specific analytical findings
        if success and output:
            # Extract numeric findings
            import re
            
            # Find correlation values
            corr_matches = re.findall(r'correlation[^:]*:\s*([-\d.]+)', output, re.IGNORECASE)
            if corr_matches:
                for corr in corr_matches[:2]:
                    try:
                        corr_val = float(corr)
                        if abs(corr_val) > 0.7:
                            insights.append(f"Strong correlation detected: {corr_val:.3f}")
                    except:
                        pass
            
            # Find outlier counts
            outlier_matches = re.findall(r'(\d+)\s*outliers?\s*(detected|found|in)', output, re.IGNORECASE)
            for match in outlier_matches[:2]:
                if int(match[0]) > 0:
                    insights.append(f"{match[0]} outliers detected in the data")
            
            # Find accuracy/performance metrics
            accuracy_matches = re.findall(r'accuracy[^:]*:\s*([\d.]+)', output, re.IGNORECASE)
            for acc in accuracy_matches[:1]:
                insights.append(f"Model accuracy: {acc}")
        
        # Default insights if none found
        if not insights and success:
            insights = ["Dataset analyzed successfully", "All visualizations generated"]
        
        return insights[:5], recommendations[:5]
    
    def cleanup_temp_files(self):
        """Clean up temporary files."""
        try:
            import shutil
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
                logger.info(f"🗑️ Cleaned up temp directory: {self.temp_dir}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to cleanup temp files: {e}")
    
    def cleanup_conversation(self) -> bool:
        """Clean up conversation data (if auto-cleanup is enabled)."""
        if self.conversation_tracker:
            return self.conversation_tracker.cleanup_conversation()
        return True
    
    def get_conversation_messages(self) -> list:
        """Get all conversation messages."""
        if self.conversation_tracker:
            return self.conversation_tracker.get_messages()
        return []