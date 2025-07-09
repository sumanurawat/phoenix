"""
Sample Population Charts for Popular Use Cases

This module provides ready-to-use chart implementations for common
population analysis scenarios, showcasing the power of our data.
"""

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Union
import seaborn as sns
from pathlib import Path
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from core.chart_base import BaseChart
    from core.data_loader import PopulationDataLoader
    from core.theme_manager import VisualizationTheme
except ImportError:
    # Fallback for direct execution
    from chart_base import BaseChart
    from data_loader import PopulationDataLoader
    from theme_manager import VisualizationTheme

class PopulationGrowthAnalysisChart(BaseChart):
    """
    Professional chart showing population growth patterns with key insights.
    
    Use Cases:
    - Compare growth rates between countries/regions
    - Identify demographic transitions
    - Highlight fastest growing and declining populations
    - Show historical trends and projections
    """
    
    def __init__(self, theme_manager=None, figure_size: str = 'large'):
        """Initialize growth analysis chart."""
        super().__init__(theme_manager, figure_size)
        
    def prepare_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Prepare data for growth analysis visualization.
        
        Args:
            data: Population data with columns ['country', 'year', 'population']
            
        Returns:
            Processed data with growth rates and categories
        """
        self.logger.info("Preparing data for growth analysis...")
        
        # Calculate growth rates
        data = data.sort_values(['country', 'year'])
        data['growth_rate'] = data.groupby('country')['population'].pct_change() * 100
        
        # Get latest year data for current growth rates
        latest_year = data['year'].max()
        latest_data = data[data['year'] == latest_year].copy()
        
        # Remove aggregates and focus on countries
        exclude_patterns = [
            'World', 'income', 'Dividend', 'OECD', 'Union', 'fragile',
            'Small states', 'Least developed', 'income countries',
            'Fragile', 'Europe', 'Asia', 'Africa', 'America', 'Middle East',
            'Sub-Saharan', 'East Asia', 'South Asia', 'Latin America'
        ]
        
        mask = ~latest_data['country'].str.contains('|'.join(exclude_patterns), case=False, na=False)
        latest_data = latest_data[mask].copy()
        
        # Remove countries with invalid growth rates
        latest_data = latest_data.dropna(subset=['growth_rate'])
        latest_data = latest_data[abs(latest_data['growth_rate']) < 20]  # Remove extreme outliers
        
        # Categorize growth rates
        def categorize_growth(rate):
            if rate >= 3:
                return 'High Growth (>3%)'
            elif rate >= 1:
                return 'Moderate Growth (1-3%)'
            elif rate >= 0:
                return 'Low Growth (0-1%)'
            else:
                return 'Declining (<0%)'
        
        latest_data['growth_category'] = latest_data['growth_rate'].apply(categorize_growth)
        
        # Add population size categories for bubble sizing
        def categorize_size(pop):
            if pop >= 100_000_000:
                return 'Very Large (>100M)'
            elif pop >= 50_000_000:
                return 'Large (50-100M)'
            elif pop >= 10_000_000:
                return 'Medium (10-50M)'
            else:
                return 'Small (<10M)'
        
        latest_data['size_category'] = latest_data['population'].apply(categorize_size)
        
        self.logger.info(f"Prepared growth analysis data: {len(latest_data)} countries")
        return latest_data
    
    def render(self) -> plt.Figure:
        """
        Create the growth analysis visualization.
        
        Returns:
            Matplotlib figure
        """
        if self.processed_data is None:
            raise ValueError("Must prepare data before rendering")
        
        self.logger.info("Creating population growth analysis chart...")
        
        # Create figure with subplots
        self.fig = plt.figure(figsize=self.theme.layout['figure_sizes'][self.figure_size])
        
        # Create 2x2 subplot layout
        gs = self.fig.add_gridspec(2, 2, hspace=0.3, wspace=0.3)
        
        # 1. Growth Rate Distribution (Top Left)
        ax1 = self.fig.add_subplot(gs[0, 0])
        self._plot_growth_distribution(ax1)
        
        # 2. Population vs Growth Scatter (Top Right)
        ax2 = self.fig.add_subplot(gs[0, 1])
        self._plot_population_vs_growth(ax2)
        
        # 3. Top Growers vs Decliners (Bottom Left)
        ax3 = self.fig.add_subplot(gs[1, 0])
        self._plot_top_growers_decliners(ax3)
        
        # 4. Growth by Region (Bottom Right)
        ax4 = self.fig.add_subplot(gs[1, 1])
        self._plot_growth_by_category(ax4)
        
        # Overall title
        self.fig.suptitle(
            'Global Population Growth Analysis 2023',
            fontsize=18, fontweight='bold', y=0.95
        )
        
        # Add source attribution
        self.add_source_attribution()
        
        return self.fig
    
    def _plot_growth_distribution(self, ax):
        """Plot distribution of growth rates."""
        data = self.processed_data
        
        # Create histogram
        colors = self.theme.get_sequential_palette(3)
        ax.hist(data['growth_rate'], bins=30, color=colors[1], alpha=0.7, 
                edgecolor='white', linewidth=1)
        
        # Add vertical line at 0
        ax.axvline(x=0, color=self.theme.themes['alert']['colors']['danger'], 
                  linestyle='--', alpha=0.8, label='Zero Growth')
        
        # Styling
        ax.set_title('Distribution of Growth Rates', fontweight='bold')
        ax.set_xlabel('Annual Growth Rate (%)')
        ax.set_ylabel('Number of Countries')
        ax.grid(True, alpha=0.3)
        
        # Add statistics
        mean_growth = data['growth_rate'].mean()
        ax.text(0.02, 0.95, f'Global Average: {mean_growth:.1f}%', 
                transform=ax.transAxes, va='top',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))
    
    def _plot_population_vs_growth(self, ax):
        """Plot population size vs growth rate scatter."""
        data = self.processed_data
        
        # Create bubble chart
        categories = data['growth_category'].unique()
        colors = self.theme.get_categorical_palette(len(categories))
        
        for i, category in enumerate(categories):
            cat_data = data[data['growth_category'] == category]
            ax.scatter(cat_data['population'], cat_data['growth_rate'],
                      s=80, c=colors[i], alpha=0.7, label=category, edgecolors='white')
        
        # Highlight interesting countries
        for _, row in data.head(5).iterrows():
            ax.annotate(row['country'], 
                       (row['population'], row['growth_rate']),
                       xytext=(5, 5), textcoords='offset points',
                       fontsize=8, alpha=0.8)
        
        # Styling
        ax.set_title('Population Size vs Growth Rate', fontweight='bold')
        ax.set_xlabel('Population (log scale)')
        ax.set_ylabel('Growth Rate (%)')
        ax.set_xscale('log')
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8, loc='upper right')
        
        # Format x-axis
        ax.xaxis.set_major_formatter(plt.FuncFormatter(
            lambda x, p: f'{x/1e6:.0f}M' if x >= 1e6 else f'{x/1e3:.0f}K'
        ))
    
    def _plot_top_growers_decliners(self, ax):
        """Plot top growing and declining countries."""
        data = self.processed_data.sort_values('growth_rate')
        
        # Get top 5 and bottom 5
        top_growers = data.tail(5)
        top_decliners = data.head(5)
        
        combined = pd.concat([top_decliners, top_growers])
        
        # Create horizontal bar chart
        y_pos = range(len(combined))
        colors = ['#e74c3c' if x < 0 else '#27ae60' for x in combined['growth_rate']]
        
        bars = ax.barh(y_pos, combined['growth_rate'], color=colors, alpha=0.8)
        
        # Add country labels
        ax.set_yticks(y_pos)
        ax.set_yticklabels(combined['country'], fontsize=8)
        
        # Add value labels
        for i, (bar, value) in enumerate(zip(bars, combined['growth_rate'])):
            ax.text(value + 0.1 if value > 0 else value - 0.1, i, f'{value:.1f}%',
                   ha='left' if value > 0 else 'right', va='center', fontsize=8)
        
        # Styling
        ax.set_title('Fastest Growing vs Declining', fontweight='bold')
        ax.set_xlabel('Annual Growth Rate (%)')
        ax.axvline(x=0, color='black', linestyle='-', alpha=0.3)
        ax.grid(True, alpha=0.3, axis='x')
    
    def _plot_growth_by_category(self, ax):
        """Plot growth rates by population size category."""
        data = self.processed_data
        
        # Group by size category
        category_growth = data.groupby('size_category')['growth_rate'].agg(['mean', 'std', 'count'])
        category_growth = category_growth.sort_values('mean', ascending=False)
        
        # Create bar chart with error bars
        colors = self.theme.get_categorical_palette(len(category_growth))
        
        bars = ax.bar(range(len(category_growth)), category_growth['mean'], 
                     yerr=category_growth['std'], capsize=5,
                     color=colors, alpha=0.8, edgecolor='white')
        
        # Add count labels on bars
        for i, (bar, count) in enumerate(zip(bars, category_growth['count'])):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2, height + 0.1,
                   f'n={count}', ha='center', va='bottom', fontsize=8)
        
        # Styling
        ax.set_title('Growth by Population Size', fontweight='bold')
        ax.set_xlabel('Population Size Category')
        ax.set_ylabel('Average Growth Rate (%)')
        ax.set_xticks(range(len(category_growth)))
        ax.set_xticklabels(category_growth.index, rotation=45, ha='right', fontsize=8)
        ax.grid(True, alpha=0.3, axis='y')
        ax.axhline(y=0, color='black', linestyle='-', alpha=0.3)


class ChinaIndiaComparisonChart(BaseChart):
    """
    Chart highlighting the historic China-India population crossover.
    
    This chart tells the story of the most significant demographic
    transition in modern history.
    """
    
    def __init__(self, theme_manager=None, figure_size: str = 'large'):
        """Initialize China-India comparison chart."""
        super().__init__(theme_manager, figure_size)
        
    def prepare_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Prepare China and India comparison data.
        
        Args:
            data: Population data
            
        Returns:
            Processed data for China and India
        """
        self.logger.info("Preparing China-India comparison data...")
        
        # Filter for China and India
        china_india_data = data[data['country'].isin(['China', 'India'])].copy()
        
        # Ensure we have both countries
        if len(china_india_data['country'].unique()) < 2:
            raise ValueError("Data must contain both China and India")
        
        # Calculate the crossover point
        pivot_data = china_india_data.pivot(index='year', columns='country', values='population')
        
        if 'China' in pivot_data.columns and 'India' in pivot_data.columns:
            # Find crossover year
            crossover_mask = pivot_data['India'] > pivot_data['China']
            if crossover_mask.any():
                crossover_year = pivot_data[crossover_mask].index[0]
                self.crossover_year = crossover_year
                self.logger.info(f"Crossover detected in year: {crossover_year}")
            else:
                self.crossover_year = None
                self.logger.info("No crossover detected in data")
        
        return china_india_data
    
    def render(self) -> plt.Figure:
        """
        Create the China-India comparison visualization.
        
        Returns:
            Matplotlib figure
        """
        if self.processed_data is None:
            raise ValueError("Must prepare data before rendering")
        
        self.logger.info("Creating China-India comparison chart...")
        
        # Create figure
        self.fig, self.ax = self._create_figure()
        
        # Pivot data for easier plotting
        pivot_data = self.processed_data.pivot(index='year', columns='country', values='population')
        
        # Get colors
        china_color = '#d62728'  # Red
        india_color = '#ff7f0e'  # Orange
        
        # Plot lines
        if 'China' in pivot_data.columns:
            self.ax.plot(pivot_data.index, pivot_data['China'], 
                        color=china_color, linewidth=3, label='China', alpha=0.9)
        
        if 'India' in pivot_data.columns:
            self.ax.plot(pivot_data.index, pivot_data['India'], 
                        color=india_color, linewidth=3, label='India', alpha=0.9)
        
        # Highlight crossover if it exists
        if hasattr(self, 'crossover_year') and self.crossover_year:
            crossover_pop = pivot_data.loc[self.crossover_year, 'India']
            
            # Add vertical line at crossover
            self.ax.axvline(x=self.crossover_year, color='#2c3e50', 
                           linestyle='--', alpha=0.7, linewidth=2)
            
            # Add crossover annotation
            self.ax.annotate(
                f'India surpasses China\n{self.crossover_year}',
                xy=(self.crossover_year, crossover_pop),
                xytext=(self.crossover_year + 5, crossover_pop + 100_000_000),
                arrowprops=dict(arrowstyle='->', color='#2c3e50', lw=2),
                fontsize=12, fontweight='bold', ha='center',
                bbox=dict(boxstyle='round,pad=0.5', facecolor='white', 
                         edgecolor='#2c3e50', alpha=0.9)
            )
            
            # Highlight the crossover point
            self.ax.scatter([self.crossover_year], [crossover_pop], 
                          s=200, color='#2c3e50', zorder=10, alpha=0.8)
        
        # Professional styling
        self.add_professional_labels(
            title="The Great Population Crossover: China vs India",
            subtitle="Historic demographic transition (1960-2023)",
            xlabel="Year",
            ylabel="Population"
        )
        
        # Format y-axis for population
        self.ax.yaxis.set_major_formatter(plt.FuncFormatter(
            lambda x, p: f'{x/1e9:.1f}B' if x >= 1e9 else f'{x/1e6:.0f}M'
        ))
        
        # Add legend
        self.ax.legend(loc='upper left', fontsize=12, frameon=True, 
                      fancybox=True, shadow=True)
        
        # Remove chart junk and add effects
        self.remove_chart_junk()
        self.add_subtle_effects()
        
        # Add key statistics
        if hasattr(self, 'crossover_year') and self.crossover_year:
            current_year = pivot_data.index.max()
            china_current = pivot_data.loc[current_year, 'China']
            india_current = pivot_data.loc[current_year, 'India']
            gap = india_current - china_current
            
            stats_text = (
                f"Current Gap ({current_year}):\n"
                f"India leads by {gap/1e6:.0f} million people\n"
                f"India: {india_current/1e9:.2f}B\n"
                f"China: {china_current/1e9:.2f}B"
            )
            
            self.ax.text(0.02, 0.98, stats_text, transform=self.ax.transAxes,
                        va='top', ha='left', fontsize=10,
                        bbox=dict(boxstyle='round,pad=0.5', facecolor='white', 
                                 alpha=0.9, edgecolor='#bdc3c7'))
        
        return self.fig


# Example usage and testing
if __name__ == "__main__":
    print("📊 Testing Sample Population Charts")
    print("=" * 50)
    
    try:
        # Load data
        loader = PopulationDataLoader(data_dir="../../data")
        data = loader.load_population_data()
        print(f"✅ Loaded data: {data.shape}")
        
        # Test 1: Population Growth Analysis Chart
        print("\n🔄 Testing Population Growth Analysis Chart...")
        growth_chart = PopulationGrowthAnalysisChart()
        growth_chart.validate_inputs(data)
        growth_chart.processed_data = growth_chart.prepare_data(data)
        
        fig1 = growth_chart.render()
        if fig1:
            print("✅ Growth analysis chart created successfully")
            
            # Export chart
            export_paths = growth_chart.export('population_growth_analysis', ['png'])
            print(f"✅ Exported: {export_paths}")
            
            # Generate insights
            insights = growth_chart.get_insights()
            print("💡 Key Insights:")
            for insight in insights[:3]:
                print(f"   • {insight}")
            
            plt.close(fig1)
        
        # Test 2: China-India Comparison Chart
        print("\n🔄 Testing China-India Comparison Chart...")
        china_india_chart = ChinaIndiaComparisonChart()
        china_india_chart.validate_inputs(data)
        china_india_chart.processed_data = china_india_chart.prepare_data(data)
        
        fig2 = china_india_chart.render()
        if fig2:
            print("✅ China-India comparison chart created successfully")
            
            # Export chart
            export_paths = china_india_chart.export('china_india_comparison', ['png'])
            print(f"✅ Exported: {export_paths}")
            
            # Report crossover
            if hasattr(china_india_chart, 'crossover_year'):
                print(f"📈 Historic crossover detected: {china_india_chart.crossover_year}")
            
            plt.close(fig2)
        
        # Clean up test files
        test_files = ['population_growth_analysis.png', 'china_india_comparison.png']
        for file in test_files:
            if os.path.exists(file):
                os.remove(file)
                print(f"🧹 Cleaned up: {file}")
        
        print("\n🎉 All sample chart tests passed!")
        print("\n💡 Usage Examples:")
        print("   # Growth Analysis")
        print("   chart = PopulationGrowthAnalysisChart()")
        print("   fig = chart.create_visualization(data)")
        print("   chart.export('growth_analysis', ['png', 'pdf'])")
        print()
        print("   # China-India Comparison") 
        print("   chart = ChinaIndiaComparisonChart()")
        print("   fig = chart.create_visualization(data)")
        print("   plt.show()")
        
    except Exception as e:
        print(f"❌ Sample chart test failed: {e}")
        import traceback
        traceback.print_exc()
        raise
