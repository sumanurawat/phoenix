"""
Animated Population Charts Module

This module provides animated visualizations including bar chart races,
time series animations, and dynamic population flows.
"""

import matplotlib.pyplot as plt
import matplotlib.animation as animation
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

class PopulationBarRace(BaseChart):
    """
    Professional animated bar chart race for population rankings over time.
    
    Features:
    - Smooth 60 FPS animations with easing functions
    - Dynamic color coding by region
    - Automatic scale adjustments
    - Highlight significant events (like India-China crossover)
    - Professional annotations and labeling
    - Export as GIF and MP4
    
    Example:
        >>> race = PopulationBarRace()
        >>> race.create_race(top_n=10, years_per_second=2)
        >>> race.export('population_race', ['gif', 'mp4'])
    """
    
    def __init__(self, theme_manager=None, figure_size: str = 'wide'):
        """
        Initialize bar race chart.
        
        Args:
            theme_manager: VisualizationTheme instance
            figure_size: Figure size preset ('wide' recommended for races)
        """
        super().__init__(theme_manager, figure_size)
        
        # Animation settings
        self.top_n = 10
        self.years_per_second = 2
        self.total_duration = 10  # seconds
        self.fps = 30  # Smooth animation
        
        # Visual settings
        self.bar_height = 0.8
        self.show_values = True
        self.show_flags = False  # Can be enabled if flag data available
        self.highlight_events = True
        
        # Animation state
        self.animation = None
        self.frames = []
        self.current_frame = 0
        
        # Data
        self.race_data = None
        self.country_colors = {}
        self.regional_colors = None
        
    def prepare_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Prepare data for bar chart race animation.
        
        Args:
            data: Population data with columns ['country', 'year', 'population']
            
        Returns:
            Processed data ready for animation
        """
        self.logger.info("Preparing data for bar chart race...")
        
        # Ensure required columns exist
        required_cols = ['country', 'year', 'population']
        for col in required_cols:
            if col not in data.columns:
                raise ValueError(f"Required column '{col}' not found in data")
        
        # Filter out non-country entities (aggregates, regions)
        exclude_patterns = [
            'World', 'income', 'Dividend', 'OECD', 'Union', 'fragile',
            'Small states', 'Least developed', 'income countries',
            'Fragile', 'Europe', 'Asia', 'Africa', 'America', 'Middle East',
            'Sub-Saharan', 'East Asia', 'South Asia', 'Latin America'
        ]
        
        # Filter out aggregate entities
        mask = ~data['country'].str.contains('|'.join(exclude_patterns), case=False, na=False)
        data = data[mask].copy()
        
        # Ensure numeric population
        data['population'] = pd.to_numeric(data['population'], errors='coerce')
        data = data.dropna(subset=['population'])
        
        # Remove countries with insufficient data
        country_counts = data.groupby('country')['year'].count()
        valid_countries = country_counts[country_counts >= 20].index  # At least 20 years of data
        data = data[data['country'].isin(valid_countries)]
        
        # Sort by year for animation
        data = data.sort_values(['year', 'population'], ascending=[True, False])
        
        # Calculate rankings for each year
        data['rank'] = data.groupby('year')['population'].rank(method='dense', ascending=False)
        
        # Filter to top N for efficiency
        data = data[data['rank'] <= self.top_n * 2]  # Keep extra for smooth transitions
        
        self.logger.info(f"Prepared race data: {len(data['country'].unique())} countries, "
                        f"{len(data['year'].unique())} years")
        
        return data
    
    def _assign_colors(self, countries: List[str]) -> Dict[str, str]:
        """
        Assign consistent colors to countries, preferably by region.
        
        Args:
            countries: List of country names
            
        Returns:
            Dictionary mapping country names to colors
        """
        # Get regional colors if available
        if self.regional_colors is None:
            self.regional_colors = self.theme.get_regional_colors()
        
        # Get categorical palette for countries without regional mapping
        categorical_colors = self.theme.get_categorical_palette(len(countries))
        
        # Known regional mappings (simplified)
        regional_mapping = {
            # East Asia & Pacific
            'China': 'East Asia & Pacific',
            'India': 'South Asia',
            'Indonesia': 'East Asia & Pacific',
            'Japan': 'East Asia & Pacific',
            'Philippines': 'East Asia & Pacific',
            'Vietnam': 'East Asia & Pacific',
            'Thailand': 'East Asia & Pacific',
            'South Korea': 'East Asia & Pacific',
            'Malaysia': 'East Asia & Pacific',
            'Australia': 'East Asia & Pacific',
            
            # Europe & Central Asia
            'United States': 'North America',
            'Russia': 'Europe & Central Asia',
            'Germany': 'Europe & Central Asia',
            'United Kingdom': 'Europe & Central Asia',
            'France': 'Europe & Central Asia',
            'Italy': 'Europe & Central Asia',
            'Turkey': 'Europe & Central Asia',
            'Ukraine': 'Europe & Central Asia',
            'Poland': 'Europe & Central Asia',
            
            # South Asia
            'Pakistan': 'South Asia',
            'Bangladesh': 'South Asia',
            'Afghanistan': 'South Asia',
            'Sri Lanka': 'South Asia',
            'Nepal': 'South Asia',
            
            # Sub-Saharan Africa
            'Nigeria': 'Sub-Saharan Africa',
            'Ethiopia': 'Sub-Saharan Africa',
            'Democratic Republic of Congo': 'Sub-Saharan Africa',
            'South Africa': 'Sub-Saharan Africa',
            'Kenya': 'Sub-Saharan Africa',
            'Tanzania': 'Sub-Saharan Africa',
            'Uganda': 'Sub-Saharan Africa',
            'Ghana': 'Sub-Saharan Africa',
            
            # Latin America & Caribbean
            'Brazil': 'Latin America & Caribbean',
            'Mexico': 'Latin America & Caribbean',
            'Colombia': 'Latin America & Caribbean',
            'Argentina': 'Latin America & Caribbean',
            'Peru': 'Latin America & Caribbean',
            'Venezuela': 'Latin America & Caribbean',
            
            # Middle East & North Africa
            'Iran': 'Middle East & North Africa',
            'Egypt': 'Middle East & North Africa',
            'Saudi Arabia': 'Middle East & North Africa',
            'Iraq': 'Middle East & North Africa',
            'Morocco': 'Middle East & North Africa',
            'Algeria': 'Middle East & North Africa',
        }
        
        # Assign colors
        colors = {}
        color_index = 0
        
        for country in countries:
            if country in regional_mapping:
                region = regional_mapping[country]
                if region in self.regional_colors:
                    colors[country] = self.regional_colors[region]
                else:
                    colors[country] = categorical_colors[color_index % len(categorical_colors)]
                    color_index += 1
            else:
                colors[country] = categorical_colors[color_index % len(categorical_colors)]
                color_index += 1
        
        return colors
    
    def _interpolate_frame(self, year_start: float, year_end: float, 
                          data_start: pd.DataFrame, data_end: pd.DataFrame, 
                          progress: float) -> pd.DataFrame:
        """
        Interpolate between two years for smooth animation.
        
        Args:
            year_start: Starting year
            year_end: Ending year
            data_start: Data for starting year
            data_end: Data for ending year
            progress: Interpolation progress (0.0 to 1.0)
            
        Returns:
            Interpolated frame data
        """
        # Apply easing function for natural movement
        eased_progress = self._ease_in_out_cubic(progress)
        
        # Interpolate population values
        interpolated_data = []
        
        # Get all countries that appear in either frame
        countries_start = set(data_start['country'])
        countries_end = set(data_end['country'])
        all_countries = countries_start.union(countries_end)
        
        for country in all_countries:
            # Get population values (0 if country not in frame)
            pop_start = 0
            pop_end = 0
            
            if country in countries_start:
                pop_start = data_start[data_start['country'] == country]['population'].iloc[0]
            
            if country in countries_end:
                pop_end = data_end[data_end['country'] == country]['population'].iloc[0]
            
            # Interpolate
            interpolated_pop = pop_start + (pop_end - pop_start) * eased_progress
            
            if interpolated_pop > 0:  # Only include if has population
                interpolated_data.append({
                    'country': country,
                    'population': interpolated_pop,
                    'year': year_start + (year_end - year_start) * progress
                })
        
        frame_df = pd.DataFrame(interpolated_data)
        
        if not frame_df.empty:
            # Calculate ranks
            frame_df = frame_df.sort_values('population', ascending=False)
            frame_df['rank'] = range(1, len(frame_df) + 1)
            
            # Keep only top N
            frame_df = frame_df.head(self.top_n)
        
        return frame_df
    
    def _ease_in_out_cubic(self, t: float) -> float:
        """
        Cubic easing function for natural animation movement.
        
        Args:
            t: Progress value (0.0 to 1.0)
            
        Returns:
            Eased progress value
        """
        if t < 0.5:
            return 4 * t * t * t
        else:
            return 1 - pow(-2 * t + 2, 3) / 2
    
    def _create_frame_data(self) -> List[pd.DataFrame]:
        """
        Create all frame data for animation.
        
        Returns:
            List of DataFrames, one for each animation frame
        """
        if self.race_data is None:
            raise ValueError("Must prepare data before creating frames")
        
        # Get year range
        years = sorted(self.race_data['year'].unique())
        start_year = years[0]
        end_year = years[-1]
        
        # Calculate animation parameters
        total_frames = int(self.total_duration * self.fps)
        frames_per_year = total_frames / (end_year - start_year)
        
        self.logger.info(f"Creating {total_frames} frames for {end_year - start_year} years "
                        f"({frames_per_year:.1f} frames/year)")
        
        frames = []
        
        for frame_num in range(total_frames):
            # Calculate current year (with decimals for smooth interpolation)
            current_year = start_year + (frame_num / total_frames) * (end_year - start_year)
            
            # Find the two years to interpolate between
            year_before = int(np.floor(current_year))
            year_after = int(np.ceil(current_year))
            
            if year_before == year_after:
                # Exact year, no interpolation needed
                frame_data = self.race_data[self.race_data['year'] == year_before].copy()
                frame_data = frame_data.head(self.top_n)
            else:
                # Interpolate between years
                data_before = self.race_data[self.race_data['year'] == year_before]
                data_after = self.race_data[self.race_data['year'] == year_after]
                
                if len(data_before) > 0 and len(data_after) > 0:
                    progress = current_year - year_before
                    frame_data = self._interpolate_frame(
                        year_before, year_after, data_before, data_after, progress
                    )
                else:
                    # Fallback to nearest available year
                    nearest_year = min(years, key=lambda y: abs(y - current_year))
                    frame_data = self.race_data[self.race_data['year'] == nearest_year].copy()
                    frame_data = frame_data.head(self.top_n)
            
            frames.append(frame_data)
        
        return frames
    
    def render(self) -> plt.Figure:
        """
        Create and return the animated bar chart race.
        
        Returns:
            Matplotlib figure with animation
        """
        if self.race_data is None:
            raise ValueError("Must prepare data before rendering")
        
        self.logger.info("Creating bar chart race animation...")
        
        # Create figure and axis
        self.fig, self.ax = self._create_figure()
        
        # Generate frame data
        self.frames = self._create_frame_data()
        
        # Assign colors to countries
        all_countries = list(self.race_data['country'].unique())
        self.country_colors = self._assign_colors(all_countries)
        
        # Set up the plot
        self._setup_race_plot()
        
        # Create animation
        self.animation = animation.FuncAnimation(
            self.fig, self._animate_frame, frames=len(self.frames),
            interval=1000/self.fps, blit=False, repeat=True
        )
        
        return self.fig
    
    def _setup_race_plot(self):
        """Setup the initial race plot appearance."""
        # Remove chart junk
        self.remove_chart_junk()
        
        # Set up axis limits and labels
        max_population = self.race_data['population'].max()
        self.ax.set_xlim(0, max_population * 1.1)
        self.ax.set_ylim(-0.5, self.top_n - 0.5)
        
        # Professional styling
        self.add_professional_labels(
            title="World Population Race: 1960-2023",
            subtitle="Top 10 Most Populous Countries Over Time",
            xlabel="Population (People)",
            ylabel=""
        )
        
        # Customize for race chart
        self.ax.set_yticks([])  # No y-axis ticks for country names
        self.ax.grid(True, axis='x', alpha=0.3)
        
        # Format x-axis for population values
        def format_population(x, p):
            if x >= 1e9:
                return f'{x/1e9:.1f}B'
            elif x >= 1e6:
                return f'{x/1e6:.0f}M'
            else:
                return f'{x/1e3:.0f}K'
        
        from matplotlib.ticker import FuncFormatter
        self.ax.xaxis.set_major_formatter(FuncFormatter(format_population))
        
    def _animate_frame(self, frame_num: int):
        """
        Animate a single frame of the bar chart race.
        
        Args:
            frame_num: Current frame number
        """
        # Clear previous frame
        self.ax.clear()
        self._setup_race_plot()
        
        # Get current frame data
        if frame_num < len(self.frames):
            frame_data = self.frames[frame_num]
        else:
            frame_data = self.frames[-1]  # Show last frame if beyond range
        
        if frame_data.empty:
            return
        
        # Sort by population for consistent ordering
        frame_data = frame_data.sort_values('population', ascending=True)
        
        # Create horizontal bars
        countries = frame_data['country'].tolist()
        populations = frame_data['population'].tolist()
        y_positions = range(len(countries))
        
        # Get colors for countries
        colors = [self.country_colors.get(country, '#1f77b4') for country in countries]
        
        # Draw bars
        bars = self.ax.barh(y_positions, populations, height=self.bar_height, 
                           color=colors, alpha=0.8, edgecolor='white', linewidth=1)
        
        # Add country labels
        for i, (country, population) in enumerate(zip(countries, populations)):
            # Country name on the left
            self.ax.text(-0.02 * max(populations), i, country, 
                        ha='right', va='center', fontweight='bold',
                        fontsize=10, color='#2c3e50')
            
            # Population value on the right
            if self.show_values:
                formatted_pop = self.format_numbers(population, 'population')
                self.ax.text(population + 0.01 * max(populations), i, formatted_pop,
                           ha='left', va='center', fontweight='normal',
                           fontsize=9, color='#34495e')
        
        # Add year indicator
        current_year = int(frame_data['year'].iloc[0]) if not frame_data.empty else 1960
        self.ax.text(0.98, 0.95, str(current_year), transform=self.ax.transAxes,
                    ha='right', va='top', fontsize=36, fontweight='bold',
                    color='#2c3e50', alpha=0.7)
        
        # Highlight special events
        if self.highlight_events and current_year >= 2021:
            # India-China crossover event
            if 'India' in countries and 'China' in countries:
                self.ax.text(0.02, 0.95, "🔄 India surpasses China", 
                           transform=self.ax.transAxes,
                           ha='left', va='top', fontsize=12, fontweight='bold',
                           color='#e74c3c', bbox=dict(boxstyle='round,pad=0.3',
                                                     facecolor='white', alpha=0.8))
        
        # Add source attribution for current frame
        self.add_source_attribution()
        
        # Adjust limits if needed
        if populations:
            max_pop = max(populations)
            self.ax.set_xlim(0, max_pop * 1.15)
            self.ax.set_ylim(-0.5, len(countries) - 0.5)
    
    def create_race(self, data: pd.DataFrame = None, top_n: int = 10, 
                   years_per_second: float = 2, duration: float = 15) -> plt.Figure:
        """
        Create complete bar chart race animation.
        
        Args:
            data: Population data (will load if None)
            top_n: Number of countries to show
            years_per_second: Animation speed
            duration: Total animation duration in seconds
            
        Returns:
            Matplotlib figure with animation
        """
        # Load data if not provided
        if data is None:
            loader = PopulationDataLoader(data_dir="../../../data")
            data = loader.load_population_data()
        
        # Set animation parameters
        self.top_n = top_n
        self.years_per_second = years_per_second
        self.total_duration = duration
        
        # Prepare and render
        self.validate_inputs(data)
        self.race_data = self.prepare_data(data)
        
        return self.render()
    
    def save_animation(self, filename: str, format: str = 'gif', 
                      fps: int = None, quality: str = 'medium') -> str:
        """
        Save animation to file.
        
        Args:
            filename: Output filename (without extension)
            format: 'gif' or 'mp4'
            fps: Frames per second (uses self.fps if None)
            quality: 'low', 'medium', 'high' (affects file size)
            
        Returns:
            Path to saved file
        """
        if self.animation is None:
            raise ValueError("Must create animation before saving")
        
        if fps is None:
            fps = self.fps
        
        output_path = f"{filename}.{format}"
        
        try:
            if format.lower() == 'gif':
                # Save as GIF
                writer = animation.PillowWriter(fps=fps)
                self.animation.save(output_path, writer=writer)
                
            elif format.lower() == 'mp4':
                # Save as MP4 (requires ffmpeg)
                writer = animation.FFMpegWriter(fps=fps, bitrate=1800 if quality == 'high' else 1200)
                self.animation.save(output_path, writer=writer)
                
            else:
                raise ValueError(f"Unsupported format: {format}")
            
            self.logger.info(f"Animation saved: {output_path}")
            return output_path
            
        except Exception as e:
            self.logger.error(f"Failed to save animation: {e}")
            raise


# Example usage and testing
if __name__ == "__main__":
    print("🎬 Testing Population Bar Chart Race")
    print("=" * 50)
    
    try:
        # Create bar race
        race = PopulationBarRace()
        
        # Load some test data
        try:
            loader = PopulationDataLoader(data_dir="../../data")
            data = loader.load_population_data()
            print(f"✅ Loaded data: {data.shape}")
        except Exception as e:
            print(f"⚠️ Could not load real data: {e}")
            # Create synthetic test data
            print("📊 Creating synthetic test data...")
            years = range(1960, 2024)
            countries = ['China', 'India', 'United States', 'Indonesia', 'Brazil', 
                        'Pakistan', 'Nigeria', 'Bangladesh', 'Russia', 'Mexico']
            
            test_data = []
            for year in years:
                for i, country in enumerate(countries):
                    # Simulate population growth with some randomness
                    base_pop = (i + 1) * 50_000_000
                    growth_factor = 1 + (year - 1960) * 0.015
                    noise = np.random.normal(1, 0.05)
                    population = int(base_pop * growth_factor * noise)
                    
                    test_data.append({
                        'country': country,
                        'year': year,
                        'population': population
                    })
            
            data = pd.DataFrame(test_data)
            print(f"✅ Created synthetic data: {data.shape}")
        
        # Test data preparation
        print("\n🔄 Testing data preparation...")
        race.validate_inputs(data)
        race.race_data = race.prepare_data(data)
        print(f"✅ Prepared race data: {race.race_data.shape}")
        
        # Test frame generation
        print("\n🎞️ Testing frame generation...")
        race.total_duration = 2  # Short test
        race.fps = 10  # Low FPS for testing
        frames = race._create_frame_data()
        print(f"✅ Generated {len(frames)} animation frames")
        
        # Test color assignment
        print("\n🎨 Testing color assignment...")
        countries = race.race_data['country'].unique()[:5]
        colors = race._assign_colors(list(countries))
        print(f"✅ Assigned colors to {len(colors)} countries")
        for country, color in list(colors.items())[:3]:
            print(f"   {country}: {color}")
        
        # Test static frame render
        print("\n📊 Testing static frame render...")
        fig = race.render()
        
        if fig is not None:
            print("✅ Animation created successfully")
            
            # Test export (static frame)
            print("\n💾 Testing static frame export...")
            export_paths = race.export('test_population_race', ['png'])
            print(f"✅ Exported: {export_paths}")
            
            # Clean up test files
            for path in export_paths.values():
                if os.path.exists(path):
                    os.remove(path)
            
            plt.close(fig)
        
        print("\n🎉 All bar chart race tests passed!")
        print("\n💡 To create a full animation:")
        print("   race = PopulationBarRace()")
        print("   fig = race.create_race(top_n=10, duration=15)")
        print("   race.save_animation('population_race', 'gif')")
        print("   plt.show()  # To display animation")
        
    except Exception as e:
        print(f"❌ Bar chart race test failed: {e}")
        raise
