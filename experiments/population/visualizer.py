"""
World Bank Data Visualizer
Creates comprehensive visualizations for population data analysis.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import json
import logging
from typing import Dict, List, Optional
import os

class PopulationDataVisualizer:
    """
    Creates various visualizations for World Bank population data.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Set style
        plt.style.use('seaborn-v0_8')
        sns.set_palette("husl")
        
        # Ensure outputs directory exists
        os.makedirs('outputs', exist_ok=True)
        
        # Load data
        self.population_df = None
        self.regional_df = None
        self.countries_df = None
        
        self._load_data()
    
    def _load_data(self):
        """Load all necessary data files."""
        self.logger.info("Loading data for visualization...")
        
        try:
            # Load population timeseries
            with open('data/population_timeseries.json', 'r') as f:
                population_data = json.load(f)
            
            # Convert to DataFrame
            pop_records = []
            for record in population_data:
                if record.get('value') is not None:
                    pop_records.append({
                        'country_code': record.get('countryiso3code', record.get('country', {}).get('id')),
                        'country_name': record.get('country', {}).get('value', 'Unknown'),
                        'year': int(record.get('date', 0)),
                        'population': float(record.get('value', 0))
                    })
            
            self.population_df = pd.DataFrame(pop_records)
            
            # Load regional data
            with open('data/population_regions.json', 'r') as f:
                regional_data = json.load(f)
            
            regional_records = []
            for record in regional_data:
                if record.get('value') is not None:
                    regional_records.append({
                        'region_code': record.get('countryiso3code', record.get('country', {}).get('id')),
                        'region_name': record.get('country', {}).get('value', 'Unknown'),
                        'year': int(record.get('date', 0)),
                        'population': float(record.get('value', 0))
                    })
            
            self.regional_df = pd.DataFrame(regional_records)
            
            self.logger.info(f"Loaded data for visualization: {len(self.population_df)} population records")
            
        except Exception as e:
            self.logger.error(f"Error loading data: {e}")
            raise
    
    def create_world_population_growth_chart(self):
        """Create world population growth line chart."""
        self.logger.info("Creating world population growth chart...")
        
        world_data = self.regional_df[self.regional_df['region_code'] == 'WLD'].sort_values('year')
        
        if world_data.empty:
            self.logger.warning("No world data available for chart")
            return
        
        plt.figure(figsize=(12, 8))
        plt.plot(world_data['year'], world_data['population'] / 1e9, linewidth=3, color='#2E86AB')
        plt.title('World Population Growth (1960-2023)', fontsize=16, fontweight='bold', pad=20)
        plt.xlabel('Year', fontsize=12)
        plt.ylabel('Population (Billions)', fontsize=12)
        plt.grid(True, alpha=0.3)
        
        # Add milestone annotations
        milestones = [
            (1974, 4e9, '4 Billion'),
            (1987, 5e9, '5 Billion'),
            (1999, 6e9, '6 Billion'),
            (2011, 7e9, '7 Billion'),
            (2022, 8e9, '8 Billion')
        ]
        
        for year, pop, label in milestones:
            if year in world_data['year'].values:
                plt.annotate(label, xy=(year, pop/1e9), xytext=(year-5, pop/1e9+0.2),
                           arrowprops=dict(arrowstyle='->', color='red', alpha=0.7),
                           fontsize=10, ha='center')
        
        plt.tight_layout()
        plt.savefig('outputs/world_population_growth.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        self.logger.info("✓ World population growth chart saved")
    
    def create_top_countries_timeseries(self):
        """Create multi-line chart for top 10 countries over time."""
        self.logger.info("Creating top countries timeseries chart...")
        
        # Get top 10 countries by latest population
        latest_year = self.population_df['year'].max()
        top_countries = self.population_df[
            self.population_df['year'] == latest_year
        ].nlargest(10, 'population')['country_code'].tolist()
        
        plt.figure(figsize=(14, 10))
        
        colors = plt.cm.tab10(np.linspace(0, 1, len(top_countries)))
        
        for i, country in enumerate(top_countries):
            country_data = self.population_df[
                self.population_df['country_code'] == country
            ].sort_values('year')
            
            if not country_data.empty:
                country_name = country_data['country_name'].iloc[0]
                plt.plot(country_data['year'], country_data['population'] / 1e6, 
                        label=country_name, linewidth=2.5, color=colors[i])
        
        plt.title('Population Growth: Top 10 Most Populous Countries', fontsize=16, fontweight='bold', pad=20)
        plt.xlabel('Year', fontsize=12)
        plt.ylabel('Population (Millions)', fontsize=12)
        plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig('outputs/top_countries_timeseries.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        self.logger.info("✓ Top countries timeseries chart saved")
    
    def create_current_population_ranking(self):
        """Create horizontal bar chart of current top 20 countries."""
        self.logger.info("Creating current population ranking chart...")
        
        latest_year = self.population_df['year'].max()
        top_20 = self.population_df[
            self.population_df['year'] == latest_year
        ].nlargest(20, 'population')
        
        plt.figure(figsize=(12, 10))
        bars = plt.barh(range(len(top_20)), top_20['population'] / 1e6, color='skyblue')
        
        # Color the top 3 differently
        bars[0].set_color('#FFD700')  # Gold
        bars[1].set_color('#C0C0C0')  # Silver
        bars[2].set_color('#CD7F32')  # Bronze
        
        plt.yticks(range(len(top_20)), top_20['country_name'])
        plt.xlabel('Population (Millions)', fontsize=12)
        plt.title(f'Top 20 Most Populous Countries ({latest_year})', fontsize=16, fontweight='bold', pad=20)
        plt.gca().invert_yaxis()  # Largest at top
        
        # Add value labels on bars
        for i, (idx, row) in enumerate(top_20.iterrows()):
            plt.text(row['population'] / 1e6 + 10, i, f"{row['population']/1e6:.0f}M", 
                    va='center', fontsize=9)
        
        plt.grid(axis='x', alpha=0.3)
        plt.tight_layout()
        plt.savefig('outputs/current_population_ranking.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        self.logger.info("✓ Current population ranking chart saved")
    
    def create_population_distribution_histogram(self):
        """Create histogram of population distribution."""
        self.logger.info("Creating population distribution histogram...")
        
        latest_year = self.population_df['year'].max()
        latest_pop = self.population_df[self.population_df['year'] == latest_year]
        
        plt.figure(figsize=(12, 8))
        
        # Use log scale for better visualization
        log_populations = np.log10(latest_pop['population'])
        
        plt.hist(log_populations, bins=30, color='lightcoral', alpha=0.7, edgecolor='black')
        plt.title('Distribution of Country Populations (Log Scale)', fontsize=16, fontweight='bold', pad=20)
        plt.xlabel('Log10(Population)', fontsize=12)
        plt.ylabel('Number of Countries', fontsize=12)
        
        # Add reference lines
        plt.axvline(np.log10(1e6), color='red', linestyle='--', alpha=0.7, label='1 Million')
        plt.axvline(np.log10(10e6), color='orange', linestyle='--', alpha=0.7, label='10 Million')
        plt.axvline(np.log10(100e6), color='green', linestyle='--', alpha=0.7, label='100 Million')
        
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig('outputs/population_distribution.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        self.logger.info("✓ Population distribution histogram saved")
    
    def create_growth_rate_heatmap(self):
        """Create heatmap of growth rates by country and decade."""
        self.logger.info("Creating growth rate heatmap...")
        
        # Calculate growth rates for each country by decade
        growth_data = []
        
        for country in self.population_df['country_code'].unique():
            country_data = self.population_df[
                self.population_df['country_code'] == country
            ].sort_values('year')
            
            if len(country_data) < 10:  # Need sufficient data
                continue
            
            country_data['growth_rate'] = country_data['population'].pct_change() * 100
            country_data['decade'] = (country_data['year'] // 10) * 10
            
            # Average growth by decade
            decade_growth = country_data.groupby('decade')['growth_rate'].mean()
            
            for decade, growth in decade_growth.items():
                if not np.isnan(growth):
                    growth_data.append({
                        'country_code': country,
                        'country_name': country_data['country_name'].iloc[0],
                        'decade': int(decade),
                        'growth_rate': growth
                    })
        
        growth_df = pd.DataFrame(growth_data)
        
        if growth_df.empty:
            self.logger.warning("No growth data available for heatmap")
            return
        
        # Select top 20 countries by latest population for readability
        latest_year = self.population_df['year'].max()
        top_countries = self.population_df[
            self.population_df['year'] == latest_year
        ].nlargest(20, 'population')['country_code'].tolist()
        
        growth_subset = growth_df[growth_df['country_code'].isin(top_countries)]
        
        # Pivot for heatmap
        heatmap_data = growth_subset.pivot(index='country_name', columns='decade', values='growth_rate')
        
        plt.figure(figsize=(14, 10))
        sns.heatmap(heatmap_data, annot=True, fmt='.1f', cmap='RdYlBu_r', center=0,
                   cbar_kws={'label': 'Average Growth Rate (%)'})
        plt.title('Population Growth Rate by Decade\n(Top 20 Countries)', fontsize=16, fontweight='bold', pad=20)
        plt.xlabel('Decade', fontsize=12)
        plt.ylabel('Country', fontsize=12)
        plt.tight_layout()
        plt.savefig('outputs/growth_rate_heatmap.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        self.logger.info("✓ Growth rate heatmap saved")
    
    def create_regional_comparison_charts(self):
        """Create regional population comparison charts."""
        self.logger.info("Creating regional comparison charts...")
        
        # Exclude world total for regional comparison
        regional_data = self.regional_df[self.regional_df['region_code'] != 'WLD']
        
        # Create subplots for different years
        years_to_compare = [1980, 2000, 2020]
        fig, axes = plt.subplots(1, 3, figsize=(18, 6))
        
        for i, year in enumerate(years_to_compare):
            year_data = regional_data[regional_data['year'] == year]
            
            if not year_data.empty:
                # Create pie chart
                axes[i].pie(year_data['population'], labels=year_data['region_name'], 
                           autopct='%1.1f%%', startangle=90)
                axes[i].set_title(f'Regional Population Share\n{year}', fontsize=12, fontweight='bold')
        
        plt.tight_layout()
        plt.savefig('outputs/regional_comparison.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        self.logger.info("✓ Regional comparison charts saved")
    
    def create_bubble_chart(self):
        """Create bubble chart: year vs growth rate, sized by population."""
        self.logger.info("Creating bubble chart...")
        
        # Select a few interesting countries for readability
        interesting_countries = ['CHN', 'IND', 'USA', 'IDN', 'PAK', 'BRA', 'NGA', 'BGD']
        
        plt.figure(figsize=(14, 10))
        
        colors = plt.cm.Set3(np.linspace(0, 1, len(interesting_countries)))
        
        for i, country in enumerate(interesting_countries):
            country_data = self.population_df[
                self.population_df['country_code'] == country
            ].sort_values('year')
            
            if len(country_data) < 2:
                continue
            
            country_data['growth_rate'] = country_data['population'].pct_change() * 100
            country_data = country_data.dropna(subset=['growth_rate'])
            
            if not country_data.empty:
                country_name = country_data['country_name'].iloc[0]
                
                # Size bubbles by population (normalize for visibility)
                sizes = (country_data['population'] / country_data['population'].max()) * 500 + 50
                
                plt.scatter(country_data['year'], country_data['growth_rate'], 
                           s=sizes, alpha=0.6, c=[colors[i]], label=country_name)
        
        plt.title('Population Growth Rate Over Time\n(Bubble size = Population)', 
                 fontsize=16, fontweight='bold', pad=20)
        plt.xlabel('Year', fontsize=12)
        plt.ylabel('Growth Rate (%)', fontsize=12)
        plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig('outputs/bubble_chart.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        self.logger.info("✓ Bubble chart saved")
    
    def create_missing_data_heatmap(self):
        """Create heatmap showing missing data patterns."""
        self.logger.info("Creating missing data heatmap...")
        
        # Create country-year matrix
        countries = self.population_df['country_code'].unique()[:50]  # Top 50 for readability
        years = sorted(self.population_df['year'].unique())
        
        # Create matrix
        data_matrix = []
        country_names = []
        
        for country in countries:
            country_data = self.population_df[self.population_df['country_code'] == country]
            country_name = country_data['country_name'].iloc[0] if not country_data.empty else country
            country_names.append(country_name)
            
            row = []
            for year in years:
                year_data = country_data[country_data['year'] == year]
                has_data = 1 if not year_data.empty and not year_data['population'].isna().all() else 0
                row.append(has_data)
            
            data_matrix.append(row)
        
        plt.figure(figsize=(16, 12))
        sns.heatmap(data_matrix, xticklabels=years[::5], yticklabels=country_names,
                   cmap='RdYlGn', cbar_kws={'label': 'Data Available'})
        plt.title('Data Availability by Country and Year', fontsize=16, fontweight='bold', pad=20)
        plt.xlabel('Year', fontsize=12)
        plt.ylabel('Country', fontsize=12)
        plt.tight_layout()
        plt.savefig('outputs/missing_data_heatmap.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        self.logger.info("✓ Missing data heatmap saved")
    
    def create_ranking_changes_chart(self):
        """Create bump chart showing ranking changes over time."""
        self.logger.info("Creating ranking changes chart...")
        
        # Select specific years for comparison
        comparison_years = [1970, 1980, 1990, 2000, 2010, 2020]
        top_countries = ['CHN', 'IND', 'USA', 'IDN', 'PAK', 'BRA', 'NGA', 'BGD', 'RUS', 'MEX']
        
        plt.figure(figsize=(14, 10))
        
        colors = plt.cm.tab10(np.linspace(0, 1, len(top_countries)))
        
        for i, country in enumerate(top_countries):
            rankings = []
            available_years = []
            
            for year in comparison_years:
                year_data = self.population_df[self.population_df['year'] == year]
                
                if not year_data.empty:
                    year_data['rank'] = year_data['population'].rank(method='dense', ascending=False)
                    country_rank = year_data[year_data['country_code'] == country]['rank']
                    
                    if not country_rank.empty:
                        rankings.append(country_rank.iloc[0])
                        available_years.append(year)
            
            if rankings:
                country_name = self.population_df[
                    self.population_df['country_code'] == country
                ]['country_name'].iloc[0]
                
                plt.plot(available_years, rankings, marker='o', linewidth=2, 
                        label=country_name, color=colors[i])
        
        plt.title('Population Ranking Changes Over Time\n(Lower rank number = higher population)', 
                 fontsize=16, fontweight='bold', pad=20)
        plt.xlabel('Year', fontsize=12)
        plt.ylabel('Ranking', fontsize=12)
        plt.gca().invert_yaxis()  # Lower rank number at top
        plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig('outputs/ranking_changes.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        self.logger.info("✓ Ranking changes chart saved")
    
    def create_summary_dashboard(self):
        """Create a summary dashboard with key metrics."""
        self.logger.info("Creating summary dashboard...")
        
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle('World Population Analysis Dashboard', fontsize=20, fontweight='bold')
        
        # World population growth (top left)
        world_data = self.regional_df[self.regional_df['region_code'] == 'WLD'].sort_values('year')
        if not world_data.empty:
            axes[0, 0].plot(world_data['year'], world_data['population'] / 1e9, linewidth=3, color='blue')
            axes[0, 0].set_title('World Population Growth', fontweight='bold')
            axes[0, 0].set_ylabel('Population (Billions)')
            axes[0, 0].grid(True, alpha=0.3)
        
        # Top 5 countries current (top right)
        latest_year = self.population_df['year'].max()
        top_5 = self.population_df[
            self.population_df['year'] == latest_year
        ].nlargest(5, 'population')
        
        axes[0, 1].barh(range(len(top_5)), top_5['population'] / 1e6)
        axes[0, 1].set_yticks(range(len(top_5)))
        axes[0, 1].set_yticklabels(top_5['country_name'])
        axes[0, 1].set_title(f'Top 5 Countries ({latest_year})', fontweight='bold')
        axes[0, 1].set_xlabel('Population (Millions)')
        axes[0, 1].invert_yaxis()
        
        # Regional share (bottom left)
        regional_data = self.regional_df[
            (self.regional_df['region_code'] != 'WLD') & 
            (self.regional_df['year'] == latest_year)
        ]
        if not regional_data.empty:
            axes[1, 0].pie(regional_data['population'], labels=regional_data['region_name'], 
                          autopct='%1.1f%%', startangle=90)
            axes[1, 0].set_title('Regional Population Share', fontweight='bold')
        
        # Growth rate distribution (bottom right)
        growth_rates = []
        for country in self.population_df['country_code'].unique():
            country_data = self.population_df[
                self.population_df['country_code'] == country
            ].sort_values('year')
            
            if len(country_data) >= 2:
                recent_growth = ((country_data.iloc[-1]['population'] - country_data.iloc[-2]['population']) / 
                               country_data.iloc[-2]['population']) * 100
                if not np.isnan(recent_growth):
                    growth_rates.append(recent_growth)
        
        if growth_rates:
            axes[1, 1].hist(growth_rates, bins=20, color='lightgreen', alpha=0.7)
            axes[1, 1].set_title('Growth Rate Distribution', fontweight='bold')
            axes[1, 1].set_xlabel('Growth Rate (%)')
            axes[1, 1].set_ylabel('Number of Countries')
        
        plt.tight_layout()
        plt.savefig('outputs/summary_dashboard.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        self.logger.info("✓ Summary dashboard saved")
    
    def generate_all_visualizations(self):
        """Generate all visualizations."""
        self.logger.info("Generating all visualizations...")
        
        visualizations = [
            ("World Population Growth", self.create_world_population_growth_chart),
            ("Top Countries Timeseries", self.create_top_countries_timeseries),
            ("Current Population Ranking", self.create_current_population_ranking),
            ("Population Distribution", self.create_population_distribution_histogram),
            ("Growth Rate Heatmap", self.create_growth_rate_heatmap),
            ("Regional Comparison", self.create_regional_comparison_charts),
            ("Bubble Chart", self.create_bubble_chart),
            ("Missing Data Heatmap", self.create_missing_data_heatmap),
            ("Ranking Changes", self.create_ranking_changes_chart),
            ("Summary Dashboard", self.create_summary_dashboard)
        ]
        
        successful = 0
        total = len(visualizations)
        
        for viz_name, viz_func in visualizations:
            try:
                viz_func()
                successful += 1
            except Exception as e:
                self.logger.error(f"Failed to create {viz_name}: {e}")
        
        self.logger.info(f"Generated {successful}/{total} visualizations successfully")
        return successful, total


def main():
    """Main function to generate all visualizations."""
    visualizer = PopulationDataVisualizer()
    
    print("Starting visualization generation...")
    print("=" * 50)
    
    successful, total = visualizer.generate_all_visualizations()
    
    print("\n" + "=" * 50)
    print(f"Visualization generation complete!")
    print(f"Successfully created {successful}/{total} visualizations")
    print("Visualizations saved to outputs/ directory")


if __name__ == "__main__":
    main()
