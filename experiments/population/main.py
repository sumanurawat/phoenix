"""
World Bank Population Data Analysis Pipeline
Main orchestrator script that runs the complete analysis pipeline.
"""

import logging
import time
import sys
import os
from datetime import datetime
from typing import Dict, List, Tuple

# Import our modules
from data_fetcher import WorldBankAPI
from data_analyzer import PopulationDataAnalyzer
from data_profiler import DataQualityProfiler
from visualizer import PopulationDataVisualizer
from report_generator import ReportGenerator

class AnalysisPipeline:
    """
    Main pipeline orchestrator for World Bank population data analysis.
    """
    
    def __init__(self, skip_data_collection: bool = False):
        self.skip_data_collection = skip_data_collection
        self.results = {}
        self.execution_log = []
        
        # Set up logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('outputs/pipeline_execution.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Ensure output directory exists
        os.makedirs('outputs', exist_ok=True)
        
        self.logger.info("Population Data Analysis Pipeline initialized")
    
    def _log_phase(self, phase_name: str, start_time: float, success: bool, error: str = None):
        """Log phase execution results."""
        duration = time.time() - start_time
        
        log_entry = {
            'phase': phase_name,
            'duration': duration,
            'success': success,
            'error': error,
            'timestamp': datetime.now().isoformat()
        }
        
        self.execution_log.append(log_entry)
        
        status = "✓" if success else "✗"
        self.logger.info(f"{status} {phase_name} completed in {duration:.2f}s")
        
        if error:
            self.logger.error(f"Error in {phase_name}: {error}")
    
    def run_data_collection(self) -> bool:
        """Run data collection phase."""
        if self.skip_data_collection:
            self.logger.info("Skipping data collection (using existing data)")
            return True
        
        self.logger.info("Starting data collection phase...")
        start_time = time.time()
        
        try:
            api = WorldBankAPI()
            
            # Define collection tasks
            collection_tasks = [
                ("Countries metadata", api.get_all_countries),
                ("Current population", api.get_population_current),
                ("Population timeseries", api.get_population_timeseries),
                ("Regional population", api.get_population_by_regions),
                ("Related indicators", api.get_related_indicators),
                ("Data availability matrix", api.get_data_availability_matrix),
            ]
            
            success_count = 0
            total_tasks = len(collection_tasks)
            
            for task_name, task_func in collection_tasks:
                self.logger.info(f"Executing: {task_name}")
                task_start = time.time()
                
                try:
                    success = task_func()
                    if success:
                        success_count += 1
                    
                    task_duration = time.time() - task_start
                    self.logger.info(f"  {task_name}: {'✓' if success else '✗'} ({task_duration:.2f}s)")
                    
                except Exception as e:
                    self.logger.error(f"  {task_name}: ✗ Error: {e}")
            
            overall_success = success_count == total_tasks
            self._log_phase("Data Collection", start_time, overall_success)
            
            self.logger.info(f"Data collection: {success_count}/{total_tasks} tasks successful")
            return overall_success
            
        except Exception as e:
            self._log_phase("Data Collection", start_time, False, str(e))
            return False
    
    def run_data_analysis(self) -> bool:
        """Run statistical analysis phase."""
        self.logger.info("Starting data analysis phase...")
        start_time = time.time()
        
        try:
            analyzer = PopulationDataAnalyzer()
            
            analysis_tasks = [
                ("Basic Statistics", analyzer.calculate_basic_statistics),
                ("Growth Patterns", analyzer.analyze_growth_patterns),
                ("Regional Analysis", analyzer.analyze_regional_patterns),
                ("Ranking Analysis", analyzer.analyze_rankings),
                ("Statistical Tests", analyzer.perform_statistical_tests),
                ("Summary Report", analyzer.generate_summary_report)
            ]
            
            success_count = 0
            total_tasks = len(analysis_tasks)
            
            for task_name, task_func in analysis_tasks:
                self.logger.info(f"Executing: {task_name}")
                task_start = time.time()
                
                try:
                    result = task_func()
                    success_count += 1
                    
                    task_duration = time.time() - task_start
                    self.logger.info(f"  {task_name}: ✓ ({task_duration:.2f}s)")
                    
                except Exception as e:
                    self.logger.error(f"  {task_name}: ✗ Error: {e}")
            
            overall_success = success_count > 0  # Allow partial success
            self._log_phase("Data Analysis", start_time, overall_success)
            
            self.logger.info(f"Data analysis: {success_count}/{total_tasks} tasks successful")
            return overall_success
            
        except Exception as e:
            self._log_phase("Data Analysis", start_time, False, str(e))
            return False
    
    def run_quality_profiling(self) -> bool:
        """Run data quality profiling phase."""
        self.logger.info("Starting data quality profiling phase...")
        start_time = time.time()
        
        try:
            profiler = DataQualityProfiler()
            
            profiling_tasks = [
                ("Completeness Analysis", profiler.analyze_completeness),
                ("Consistency Analysis", profiler.analyze_consistency),
                ("Timeliness Analysis", profiler.analyze_timeliness),
                ("Accuracy Analysis", profiler.analyze_accuracy_indicators),
                ("Quality Summary", profiler.generate_quality_summary)
            ]
            
            success_count = 0
            total_tasks = len(profiling_tasks)
            
            for task_name, task_func in profiling_tasks:
                self.logger.info(f"Executing: {task_name}")
                task_start = time.time()
                
                try:
                    result = task_func()
                    success_count += 1
                    
                    task_duration = time.time() - task_start
                    self.logger.info(f"  {task_name}: ✓ ({task_duration:.2f}s)")
                    
                except Exception as e:
                    self.logger.error(f"  {task_name}: ✗ Error: {e}")
            
            overall_success = success_count > 0
            self._log_phase("Quality Profiling", start_time, overall_success)
            
            self.logger.info(f"Quality profiling: {success_count}/{total_tasks} tasks successful")
            return overall_success
            
        except Exception as e:
            self._log_phase("Quality Profiling", start_time, False, str(e))
            return False
    
    def run_visualizations(self) -> bool:
        """Run visualization generation phase."""
        self.logger.info("Starting visualization generation phase...")
        start_time = time.time()
        
        try:
            visualizer = PopulationDataVisualizer()
            
            successful, total = visualizer.generate_all_visualizations()
            overall_success = successful > 0
            
            self._log_phase("Visualization Generation", start_time, overall_success)
            
            self.logger.info(f"Visualization generation: {successful}/{total} charts successful")
            return overall_success
            
        except Exception as e:
            self._log_phase("Visualization Generation", start_time, False, str(e))
            return False
    
    def run_report_generation(self) -> bool:
        """Run report generation phase."""
        self.logger.info("Starting report generation phase...")
        start_time = time.time()
        
        try:
            generator = ReportGenerator()
            
            # Generate comprehensive report
            report_file = generator.save_report()
            
            # Generate key insights
            with open('outputs/key_insights.md', 'w') as f:
                f.write("# Key Insights Summary\n\n")
                f.write(generator.generate_executive_summary())
                f.write(generator.generate_statistical_insights())
            
            self._log_phase("Report Generation", start_time, True)
            
            self.logger.info(f"Reports generated: {report_file}, outputs/key_insights.md")
            return True
            
        except Exception as e:
            self._log_phase("Report Generation", start_time, False, str(e))
            return False
    
    def generate_execution_summary(self) -> Dict:
        """Generate summary of pipeline execution."""
        total_duration = sum(entry['duration'] for entry in self.execution_log)
        successful_phases = sum(1 for entry in self.execution_log if entry['success'])
        total_phases = len(self.execution_log)
        
        summary = {
            'execution_timestamp': datetime.now().isoformat(),
            'total_duration': total_duration,
            'successful_phases': successful_phases,
            'total_phases': total_phases,
            'success_rate': (successful_phases / total_phases * 100) if total_phases > 0 else 0,
            'phase_details': self.execution_log,
            'recommendations': self._generate_execution_recommendations()
        }
        
        return summary
    
    def _generate_execution_recommendations(self) -> List[str]:
        """Generate recommendations based on execution results."""
        recommendations = []
        
        failed_phases = [entry for entry in self.execution_log if not entry['success']]
        
        if failed_phases:
            recommendations.append("Some phases failed - check logs for details")
            
            for phase in failed_phases:
                if 'Data Collection' in phase['phase']:
                    recommendations.append("Consider using cached data or checking API connectivity")
                elif 'Visualization' in phase['phase']:
                    recommendations.append("Visualization failures may be due to missing dependencies")
        
        long_phases = [entry for entry in self.execution_log if entry['duration'] > 300]  # 5 minutes
        if long_phases:
            recommendations.append("Consider optimizing long-running phases for production use")
        
        if not recommendations:
            recommendations.append("All phases completed successfully - pipeline is ready for production")
        
        return recommendations
    
    def run_complete_pipeline(self) -> Dict:
        """Run the complete analysis pipeline."""
        self.logger.info("="*70)
        self.logger.info("STARTING WORLD BANK POPULATION DATA ANALYSIS PIPELINE")
        self.logger.info("="*70)
        
        pipeline_start = time.time()
        
        # Define pipeline phases
        phases = [
            ("Data Collection", self.run_data_collection),
            ("Data Analysis", self.run_data_analysis),
            ("Quality Profiling", self.run_quality_profiling),
            ("Visualization Generation", self.run_visualizations),
            ("Report Generation", self.run_report_generation)
        ]
        
        # Execute each phase
        for phase_name, phase_func in phases:
            self.logger.info(f"\n📊 PHASE: {phase_name}")
            self.logger.info("-" * 50)
            
            try:
                success = phase_func()
                if not success:
                    self.logger.warning(f"Phase '{phase_name}' completed with errors")
            except Exception as e:
                self.logger.error(f"Phase '{phase_name}' failed with exception: {e}")
        
        # Generate execution summary
        execution_summary = self.generate_execution_summary()
        
        # Save execution summary
        import json
        with open('outputs/execution_summary.json', 'w') as f:
            json.dump(execution_summary, f, indent=2)
        
        pipeline_duration = time.time() - pipeline_start
        
        self.logger.info("\n" + "="*70)
        self.logger.info("PIPELINE EXECUTION COMPLETE")
        self.logger.info("="*70)
        self.logger.info(f"Total Duration: {pipeline_duration:.2f} seconds")
        self.logger.info(f"Successful Phases: {execution_summary['successful_phases']}/{execution_summary['total_phases']}")
        self.logger.info(f"Success Rate: {execution_summary['success_rate']:.1f}%")
        
        if execution_summary['recommendations']:
            self.logger.info("\nRecommendations:")
            for rec in execution_summary['recommendations']:
                self.logger.info(f"  • {rec}")
        
        self.logger.info(f"\nResults saved to: outputs/ directory")
        self.logger.info(f"Execution log: outputs/pipeline_execution.log")
        self.logger.info(f"Execution summary: outputs/execution_summary.json")
        
        return execution_summary


def main():
    """Main function with command line argument handling."""
    import argparse
    
    parser = argparse.ArgumentParser(description='World Bank Population Data Analysis Pipeline')
    parser.add_argument('--skip-data-collection', action='store_true',
                       help='Skip data collection phase (use existing data)')
    parser.add_argument('--phase', choices=['collection', 'analysis', 'quality', 'visualization', 'report'],
                       help='Run only a specific phase')
    
    args = parser.parse_args()
    
    # Create pipeline
    pipeline = AnalysisPipeline(skip_data_collection=args.skip_data_collection)
    
    if args.phase:
        # Run specific phase
        phase_functions = {
            'collection': pipeline.run_data_collection,
            'analysis': pipeline.run_data_analysis,
            'quality': pipeline.run_quality_profiling,
            'visualization': pipeline.run_visualizations,
            'report': pipeline.run_report_generation
        }
        
        print(f"Running {args.phase} phase only...")
        success = phase_functions[args.phase]()
        print(f"Phase completed: {'✓' if success else '✗'}")
        
    else:
        # Run complete pipeline
        summary = pipeline.run_complete_pipeline()
        
        # Print final summary
        print("\n" + "="*50)
        print("PIPELINE SUMMARY")
        print("="*50)
        print(f"Duration: {summary['total_duration']:.1f} seconds")
        print(f"Success Rate: {summary['success_rate']:.1f}%")
        print("Check outputs/ directory for results")
        print("="*50)


if __name__ == "__main__":
    main()
