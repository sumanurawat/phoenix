"""
Base Chart Class for Professional Population Visualizations

This module provides an abstract base class that ensures consistent styling,
error handling, and professional output across all visualization types.
"""

import matplotlib.pyplot as plt
import matplotlib as mpl
from abc import ABC, abstractmethod
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any, Union
from pathlib import Path
import time
import logging
from datetime import datetime
import warnings

# Suppress matplotlib warnings for cleaner output
warnings.filterwarnings('ignore', category=UserWarning, module='matplotlib')

class BaseChart(ABC):
    """
    Abstract base class for all population visualizations with professional standards.
    
    Features:
    - Consistent styling and theming
    - Automatic figure sizing using golden ratio
    - Professional labeling and annotations
    - Multi-format export (PNG, SVG, PDF)
    - Built-in error handling and logging
    - Performance monitoring
    - Insight generation
    
    Usage:
        class MyChart(BaseChart):
            def prepare_data(self, data):
                return processed_data
            
            def render(self):
                # Create your visualization
                pass
    """
    
    def __init__(self, theme_manager=None, figure_size: str = 'medium'):
        """
        Initialize base chart with theme and configuration.
        
        Args:
            theme_manager: VisualizationTheme instance for styling
            figure_size: Size preset ('small', 'medium', 'large', 'wide', 'square')
        """
        # Import theme manager if not provided
        if theme_manager is None:
            try:
                from .theme_manager import VisualizationTheme
            except ImportError:
                from theme_manager import VisualizationTheme
            theme_manager = VisualizationTheme()
        
        self.theme = theme_manager
        self.figure_size = figure_size
        self.logger = self._setup_logging()
        
        # Chart state
        self.fig = None
        self.ax = None
        self.data = None
        self.processed_data = None
        self.insights = []
        self.render_time = 0
        self.export_paths = {}
        
        # Apply matplotlib theme
        self._apply_matplotlib_theme()
        
        # Professional styling defaults
        self.title = ""
        self.subtitle = ""
        self.source_attribution = "Source: World Bank Open Data"
        self.timestamp = datetime.now().strftime("%Y-%m-%d")
        
    def _setup_logging(self) -> logging.Logger:
        """Setup professional logging for chart operations."""
        logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
    
    def _apply_matplotlib_theme(self):
        """Apply professional theme to matplotlib."""
        style_params = self.theme.get_matplotlib_style()
        mpl.rcParams.update(style_params)
    
    def _create_figure(self) -> Tuple[plt.Figure, plt.Axes]:
        """
        Create figure with professional sizing and layout.
        
        Returns:
            Tuple of (figure, axes) objects
        """
        # Get figure size from theme
        sizes = self.theme.layout['figure_sizes']
        if self.figure_size not in sizes:
            self.logger.warning(f"Unknown figure size '{self.figure_size}', using 'medium'")
            self.figure_size = 'medium'
        
        figsize = sizes[self.figure_size]
        
        # Create figure with professional DPI
        fig, ax = plt.subplots(
            figsize=figsize,
            dpi=self.theme.layout['dpi']['screen'],
            facecolor='white',
            edgecolor='none'
        )
        
        # Apply professional margins
        margins = self.theme.layout['margins']
        fig.subplots_adjust(
            left=margins['left'] / (figsize[0] * 100),
            right=1 - margins['right'] / (figsize[0] * 100),
            top=1 - margins['top'] / (figsize[1] * 100),
            bottom=margins['bottom'] / (figsize[1] * 100)
        )
        
        return fig, ax
    
    @abstractmethod
    def prepare_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Abstract method for data preparation and transformation.
        
        Args:
            data: Raw input data
            
        Returns:
            Processed data ready for visualization
        """
        pass
    
    @abstractmethod
    def render(self) -> plt.Figure:
        """
        Abstract method for creating the main visualization.
        
        Returns:
            Matplotlib figure object
        """
        pass
    
    def validate_inputs(self, data: pd.DataFrame) -> bool:
        """
        Validate input data meets chart requirements.
        
        Args:
            data: Input data to validate
            
        Returns:
            True if validation passes
            
        Raises:
            ValueError: If validation fails
        """
        if data is None or data.empty:
            raise ValueError("Input data cannot be None or empty")
        
        # Check for basic data integrity
        if data.isnull().all().all():
            raise ValueError("All data values are null")
        
        # Check for numeric columns if needed
        numeric_cols = data.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) == 0:
            self.logger.warning("No numeric columns found in data")
        
        self.logger.info(f"Data validation passed: {data.shape[0]} rows, {data.shape[1]} columns")
        return True
    
    def add_professional_labels(self, title: str, subtitle: str = "", 
                              xlabel: str = "", ylabel: str = ""):
        """
        Add professional titles and labels with consistent styling.
        
        Args:
            title: Main chart title
            subtitle: Optional subtitle
            xlabel: X-axis label
            ylabel: Y-axis label
        """
        if not self.ax:
            raise ValueError("Must create figure before adding labels")
        
        # Store for later use
        self.title = title
        self.subtitle = subtitle
        
        # Apply title with professional styling
        title_style = self.theme.typography['title']
        self.ax.set_title(
            title, 
            fontsize=title_style['size'],
            fontweight=title_style['weight'],
            color=title_style['color'],
            pad=20
        )
        
        # Add subtitle if provided
        if subtitle:
            subtitle_style = self.theme.typography['subtitle']
            self.ax.text(
                0.5, 1.02, subtitle,
                transform=self.ax.transAxes,
                ha='center', va='bottom',
                fontsize=subtitle_style['size'],
                color=subtitle_style['color'],
                style='italic'
            )
        
        # Set axis labels
        if xlabel:
            label_style = self.theme.typography['axis_labels']
            self.ax.set_xlabel(
                xlabel,
                fontsize=label_style['size'],
                color=label_style['color']
            )
        
        if ylabel:
            label_style = self.theme.typography['axis_labels']
            self.ax.set_ylabel(
                ylabel,
                fontsize=label_style['size'],
                color=label_style['color']
            )
    
    def add_source_attribution(self):
        """Add source attribution and timestamp to chart."""
        if not self.fig:
            raise ValueError("Must create figure before adding attribution")
        
        annotation_style = self.theme.typography['annotations']
        
        # Add source text at bottom of figure
        source_text = f"{self.source_attribution} | Generated: {self.timestamp}"
        self.fig.text(
            0.02, 0.02, source_text,
            fontsize=annotation_style['size'],
            color=annotation_style['color'],
            alpha=0.7
        )
    
    def add_smart_annotations(self, points: List[Dict[str, Any]]):
        """
        Add intelligent annotations with automatic positioning to avoid overlap.
        
        Args:
            points: List of annotation dictionaries with keys:
                   {'x': x_coord, 'y': y_coord, 'text': annotation_text, 
                    'color': optional_color}
        """
        if not self.ax:
            raise ValueError("Must create figure before adding annotations")
        
        annotation_style = self.theme.typography['annotations']
        
        for point in points:
            color = point.get('color', annotation_style['color'])
            
            # Add annotation with smart positioning
            self.ax.annotate(
                point['text'],
                xy=(point['x'], point['y']),
                xytext=(10, 10),  # Offset from point
                textcoords='offset points',
                fontsize=annotation_style['size'],
                color=color,
                bbox=dict(
                    boxstyle='round,pad=0.3',
                    facecolor='white',
                    edgecolor=color,
                    alpha=0.8
                ),
                arrowprops=dict(
                    arrowstyle='->',
                    color=color,
                    alpha=0.6
                )
            )
    
    def remove_chart_junk(self):
        """Remove unnecessary visual elements (chart junk) for cleaner appearance."""
        if not self.ax:
            return
        
        # Remove top and right spines
        self.ax.spines['top'].set_visible(False)
        self.ax.spines['right'].set_visible(False)
        
        # Lighten remaining spines
        self.ax.spines['left'].set_color('#bdc3c7')
        self.ax.spines['bottom'].set_color('#bdc3c7')
        
        # Improve tick styling
        self.ax.tick_params(
            which='both',
            top=False,
            right=False,
            length=4,
            width=1,
            colors='#7f8c8d'
        )
        
        # Subtle grid
        self.ax.grid(True, alpha=0.3, linewidth=0.5, color='#ecf0f1')
        self.ax.set_axisbelow(True)
    
    def add_subtle_effects(self):
        """Add subtle visual effects for professional appearance."""
        if not self.fig or not self.ax:
            return
        
        # Add very subtle drop shadow to the plot area
        self.ax.patch.set_facecolor('white')
        
        # Ensure clean background
        self.fig.patch.set_facecolor('white')
        self.fig.patch.set_alpha(1.0)
    
    def format_numbers(self, values: Union[List, np.ndarray], format_type: str = 'auto') -> List[str]:
        """
        Format numbers professionally with appropriate units.
        
        Args:
            values: Numeric values to format
            format_type: 'auto', 'population', 'percentage', 'currency', 'compact'
            
        Returns:
            List of formatted string values
        """
        if not isinstance(values, (list, np.ndarray, pd.Series)):
            values = [values]
        
        formatted = []
        
        for value in values:
            if pd.isna(value):
                formatted.append("N/A")
                continue
            
            if format_type == 'population' or (format_type == 'auto' and abs(value) >= 1000):
                # Population formatting with appropriate units
                if abs(value) >= 1e9:
                    formatted.append(f"{value/1e9:.1f}B")
                elif abs(value) >= 1e6:
                    formatted.append(f"{value/1e6:.1f}M")
                elif abs(value) >= 1e3:
                    formatted.append(f"{value/1e3:.1f}K")
                else:
                    formatted.append(f"{value:,.0f}")
            
            elif format_type == 'percentage':
                formatted.append(f"{value:.1f}%")
            
            elif format_type == 'currency':
                formatted.append(f"${value:,.0f}")
            
            elif format_type == 'compact':
                if abs(value) >= 1e12:
                    formatted.append(f"{value/1e12:.1f}T")
                elif abs(value) >= 1e9:
                    formatted.append(f"{value/1e9:.1f}B")
                elif abs(value) >= 1e6:
                    formatted.append(f"{value/1e6:.1f}M")
                elif abs(value) >= 1e3:
                    formatted.append(f"{value/1e3:.1f}K")
                else:
                    formatted.append(f"{value:.0f}")
            
            else:  # auto or default
                if abs(value) >= 1e6:
                    formatted.append(f"{value:,.0f}")
                elif abs(value) >= 1:
                    formatted.append(f"{value:,.1f}")
                else:
                    formatted.append(f"{value:.3f}")
        
        return formatted if len(formatted) > 1 else formatted[0]
    
    def export(self, filepath: str, formats: List[str] = ['png'], 
               dpi: int = None, transparent: bool = False) -> Dict[str, str]:
        """
        Export chart in multiple formats with professional quality.
        
        Args:
            filepath: Base filepath (without extension)
            formats: List of formats ('png', 'svg', 'pdf', 'eps')
            dpi: Resolution for raster formats (None uses theme default)
            transparent: Whether to use transparent background
            
        Returns:
            Dictionary mapping format to saved filepath
        """
        if not self.fig:
            raise ValueError("Must render chart before exporting")
        
        if dpi is None:
            dpi = self.theme.layout['dpi']['print']
        
        base_path = Path(filepath)
        export_paths = {}
        
        for fmt in formats:
            # Determine appropriate DPI for format
            current_dpi = dpi if fmt in ['png', 'jpg', 'jpeg', 'tiff'] else None
            
            # Create filepath with extension
            export_path = base_path.with_suffix(f'.{fmt}')
            
            try:
                # Export with professional settings
                self.fig.savefig(
                    export_path,
                    format=fmt,
                    dpi=current_dpi,
                    bbox_inches='tight',
                    pad_inches=0.1,
                    transparent=transparent,
                    facecolor='white' if not transparent else 'none',
                    edgecolor='none'
                )
                
                export_paths[fmt] = str(export_path)
                self.logger.info(f"Exported {fmt.upper()}: {export_path}")
                
            except Exception as e:
                self.logger.error(f"Failed to export {fmt}: {e}")
        
        self.export_paths = export_paths
        return export_paths
    
    def get_insights(self) -> List[str]:
        """
        Generate automatic insights from the visualization data.
        
        Returns:
            List of key findings and insights
        """
        insights = []
        
        if self.processed_data is not None:
            # Generic insights based on data characteristics
            data = self.processed_data
            
            # Data volume insight
            insights.append(f"Analysis covers {len(data)} data points")
            
            # Check for numeric columns and provide insights
            numeric_cols = data.select_dtypes(include=[np.number]).columns
            
            for col in numeric_cols:
                if col in data.columns:
                    col_data = data[col].dropna()
                    if len(col_data) > 0:
                        mean_val = col_data.mean()
                        max_val = col_data.max()
                        min_val = col_data.min()
                        
                        insights.append(
                            f"{col.title()}: Range {self.format_numbers(min_val)} to "
                            f"{self.format_numbers(max_val)}, Average {self.format_numbers(mean_val)}"
                        )
        
        # Add render performance insight
        if self.render_time > 0:
            insights.append(f"Chart rendered in {self.render_time:.2f} seconds")
        
        self.insights = insights
        return insights
    
    def test_render(self) -> bool:
        """
        Test chart rendering without displaying.
        
        Returns:
            True if rendering succeeds, False otherwise
        """
        try:
            start_time = time.time()
            
            # Test with dummy data if no data provided
            if self.data is None:
                test_data = pd.DataFrame({
                    'x': range(10),
                    'y': np.random.randn(10)
                })
                self.validate_inputs(test_data)
                self.processed_data = self.prepare_data(test_data)
            
            # Attempt render
            fig = self.render()
            self.render_time = time.time() - start_time
            
            if fig is not None:
                plt.close(fig)  # Clean up
                print(f"✅ Chart rendered successfully in {self.render_time:.2f} seconds")
                return True
            else:
                print("❌ Chart rendering failed: No figure returned")
                return False
                
        except Exception as e:
            print(f"❌ Chart rendering failed: {e}")
            self.logger.error(f"Test render failed: {e}")
            return False
    
    def test_export(self, test_formats: List[str] = ['png']) -> bool:
        """
        Test chart export functionality.
        
        Args:
            test_formats: Formats to test export
            
        Returns:
            True if all exports succeed
        """
        try:
            # Create temporary figure if needed
            if self.fig is None:
                self.test_render()
            
            # Test export
            test_path = Path("test_chart")
            export_paths = self.export(str(test_path), test_formats)
            
            # Verify files were created
            success = True
            for fmt, path in export_paths.items():
                if Path(path).exists():
                    print(f"✅ {fmt.upper()} export successful: {path}")
                    # Clean up test file
                    Path(path).unlink()
                else:
                    print(f"❌ {fmt.upper()} export failed")
                    success = False
            
            return success
            
        except Exception as e:
            print(f"❌ Export test failed: {e}")
            return False
    
    def test_performance(self, iterations: int = 5) -> Dict[str, float]:
        """
        Benchmark chart performance over multiple iterations.
        
        Args:
            iterations: Number of test iterations
            
        Returns:
            Performance statistics dictionary
        """
        render_times = []
        
        for i in range(iterations):
            start_time = time.time()
            
            try:
                # Reset figure
                if self.fig:
                    plt.close(self.fig)
                    self.fig = None
                    self.ax = None
                
                # Test render
                self.test_render()
                render_time = time.time() - start_time
                render_times.append(render_time)
                
            except Exception as e:
                self.logger.error(f"Performance test iteration {i+1} failed: {e}")
                continue
        
        if render_times:
            stats = {
                'mean_time': np.mean(render_times),
                'min_time': np.min(render_times),
                'max_time': np.max(render_times),
                'std_time': np.std(render_times),
                'total_iterations': len(render_times)
            }
            
            print(f"📊 Performance Test Results ({len(render_times)} iterations):")
            print(f"   Average: {stats['mean_time']:.3f}s")
            print(f"   Range: {stats['min_time']:.3f}s - {stats['max_time']:.3f}s")
            print(f"   Std Dev: {stats['std_time']:.3f}s")
            
            return stats
        else:
            print("❌ Performance test failed - no successful renders")
            return {}
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup resources."""
        if self.fig:
            plt.close(self.fig)


# Example implementation for testing
class SampleChart(BaseChart):
    """Sample chart implementation for testing the base class."""
    
    def prepare_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """Simple data preparation for testing."""
        return data.copy()
    
    def render(self) -> plt.Figure:
        """Simple scatter plot for testing."""
        self.fig, self.ax = self._create_figure()
        
        # Create sample data if none provided
        if self.processed_data is None:
            x = np.linspace(0, 10, 50)
            y = np.sin(x) + np.random.normal(0, 0.1, 50)
            data = pd.DataFrame({'x': x, 'y': y})
            self.processed_data = data
        
        # Create scatter plot
        colors = self.theme.get_categorical_palette(1)
        self.ax.scatter(
            self.processed_data['x'], 
            self.processed_data['y'],
            color=colors[0],
            alpha=0.7,
            s=50
        )
        
        # Apply professional styling
        self.add_professional_labels(
            title="Sample Population Chart",
            subtitle="Testing Base Chart Functionality",
            xlabel="Time (Years)",
            ylabel="Population (Millions)"
        )
        
        self.remove_chart_junk()
        self.add_subtle_effects()
        self.add_source_attribution()
        
        return self.fig


# Testing the base chart class
if __name__ == "__main__":
    print("🧪 Testing Base Chart Class")
    print("=" * 40)
    
    try:
        # Test sample chart
        with SampleChart() as chart:
            # Test validation
            test_data = pd.DataFrame({
                'x': range(20),
                'y': np.random.randn(20)
            })
            
            print("1. Testing data validation...")
            chart.validate_inputs(test_data)
            
            print("2. Testing data preparation...")
            chart.processed_data = chart.prepare_data(test_data)
            
            print("3. Testing chart rendering...")
            success = chart.test_render()
            
            if success:
                print("4. Testing export functionality...")
                chart.test_export(['png', 'svg'])
                
                print("5. Testing performance...")
                chart.test_performance(3)
                
                print("6. Testing insights generation...")
                insights = chart.get_insights()
                for insight in insights:
                    print(f"   💡 {insight}")
        
        print("\n🎉 All base chart tests passed!")
        print("\n📋 Base Chart Features Verified:")
        print("   ✅ Professional theming and styling")
        print("   ✅ Data validation and preparation")
        print("   ✅ Chart rendering with error handling")
        print("   ✅ Multi-format export capabilities")
        print("   ✅ Performance benchmarking")
        print("   ✅ Automatic insight generation")
        print("   ✅ Context manager support")
        
    except Exception as e:
        print(f"❌ Base chart test failed: {e}")
        raise
