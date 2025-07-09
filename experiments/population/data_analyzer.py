"""
World Bank Data Statistical Analyzer
Performs comprehensive statistical analysis on population data.
"""

import pandas as pd
import numpy as np
import json
import logging
from typing import Dict, List, Tuple, Optional
from scipy import stats
from datetime import datetime
import os

class PopulationDataAnalyzer:
    """
    Comprehensive statistical analyzer for World Bank population data.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.results = {}
        
        # Load data
        self.countries_df = None
        self.population_df = None
        self.regional_df = None
        self.indicators_data = {}
        
        self._load_data()
    
    def _load_data(self):
        """Load all JSON data into pandas DataFrames."""
        self.logger.info("Loading data files...")
        
        try:
            # Load countries metadata
            with open('data/countries_metadata.json', 'r') as f:
                countries_data = json.load(f)
            self.countries_df = pd.DataFrame(countries_data)
            
            # Load population timeseries
            with open('data/population_timeseries.json', 'r') as f:
                population_data = json.load(f)
            
            # Convert to DataFrame and clean
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
            
            self.logger.info(f"Loaded {len(self.population_df)} population records")
            self.logger.info(f"Loaded {len(self.regional_df)} regional records")
            
        except Exception as e:
            self.logger.error(f"Error loading data: {e}")
            raise
    
    def calculate_basic_statistics(self) -> Dict:
        """Calculate basic population statistics."""
        self.logger.info("Calculating basic statistics...")
        
        # World population by year (from regional data)
        world_data = self.regional_df[self.regional_df['region_code'] == 'WLD'].copy()
        world_data = world_data.sort_values('year')
        
        # Country-level statistics for latest year
        latest_year = self.population_df['year'].max()
        latest_pop = self.population_df[self.population_df['year'] == latest_year]
        
        stats_dict = {
            'world_population_latest': world_data['population'].iloc[-1] if not world_data.empty else 0,
            'world_population_growth_2023': self._calculate_growth_rate(world_data),
            'total_countries_with_data': len(latest_pop),
            'population_statistics': {
                'mean': latest_pop['population'].mean(),
                'median': latest_pop['population'].median(),
                'std': latest_pop['population'].std(),
                'min': latest_pop['population'].min(),
                'max': latest_pop['population'].max(),
                'q25': latest_pop['population'].quantile(0.25),
                'q75': latest_pop['population'].quantile(0.75)
            },
            'population_distribution': self._calculate_population_distribution(latest_pop),
            'outliers': self._identify_outliers(latest_pop)
        }
        
        self.results['basic_statistics'] = stats_dict
        return stats_dict
    
    def _calculate_growth_rate(self, df: pd.DataFrame) -> float:
        """Calculate most recent growth rate."""
        if len(df) < 2:
            return 0.0
        
        df_sorted = df.sort_values('year')
        latest = df_sorted.iloc[-1]['population']
        previous = df_sorted.iloc[-2]['population']
        
        return ((latest - previous) / previous) * 100
    
    def _calculate_population_distribution(self, df: pd.DataFrame) -> Dict:
        """Calculate population distribution brackets."""
        bins = [0, 1e6, 10e6, 50e6, 100e6, 500e6, float('inf')]
        labels = ['<1M', '1M-10M', '10M-50M', '50M-100M', '100M-500M', '>500M']
        
        df['bracket'] = pd.cut(df['population'], bins=bins, labels=labels, right=False)
        distribution = df['bracket'].value_counts().to_dict()
        
        return {str(k): int(v) for k, v in distribution.items()}
    
    def _identify_outliers(self, df: pd.DataFrame) -> Dict:
        """Identify population outliers using IQR method."""
        Q1 = df['population'].quantile(0.25)
        Q3 = df['population'].quantile(0.75)
        IQR = Q3 - Q1
        
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        
        outliers_high = df[df['population'] > upper_bound].nlargest(10, 'population')
        outliers_low = df[df['population'] < lower_bound].nsmallest(10, 'population')
        
        return {
            'high_outliers': outliers_high[['country_name', 'population']].to_dict('records'),
            'low_outliers': outliers_low[['country_name', 'population']].to_dict('records')
        }
    
    def analyze_growth_patterns(self) -> Dict:
        """Analyze population growth patterns."""
        self.logger.info("Analyzing growth patterns...")
        
        # Calculate year-over-year growth for each country
        growth_data = []
        
        for country in self.population_df['country_code'].unique():
            country_data = self.population_df[
                self.population_df['country_code'] == country
            ].sort_values('year')
            
            if len(country_data) < 2:
                continue
            
            country_data['growth_rate'] = country_data['population'].pct_change() * 100
            country_data['cagr_10yr'] = self._calculate_cagr(country_data, 10)
            country_data['cagr_20yr'] = self._calculate_cagr(country_data, 20)
            
            growth_data.append(country_data)
        
        all_growth = pd.concat(growth_data, ignore_index=True)
        
        # Latest year analysis
        latest_year = all_growth['year'].max()
        latest_growth = all_growth[all_growth['year'] == latest_year]
        
        growth_analysis = {
            'fastest_growing': latest_growth.nlargest(10, 'growth_rate')[
                ['country_name', 'growth_rate', 'population']
            ].to_dict('records'),
            'declining_populations': latest_growth[latest_growth['growth_rate'] < 0].nsmallest(10, 'growth_rate')[
                ['country_name', 'growth_rate', 'population']
            ].to_dict('records'),
            'most_volatile': self._find_most_volatile_countries(all_growth),
            'average_growth_by_decade': self._calculate_growth_by_decade(all_growth),
            'growth_rate_statistics': {
                'mean': latest_growth['growth_rate'].mean(),
                'median': latest_growth['growth_rate'].median(),
                'std': latest_growth['growth_rate'].std()
            }
        }
        
        self.results['growth_analysis'] = growth_analysis
        return growth_analysis
    
    def _calculate_cagr(self, df: pd.DataFrame, years: int) -> float:
        """Calculate Compound Annual Growth Rate."""
        if len(df) < years:
            return np.nan
        
        df_sorted = df.sort_values('year')
        if len(df_sorted) < 2:
            return np.nan
        
        start_val = df_sorted.iloc[0]['population']
        end_val = df_sorted.iloc[-1]['population']
        periods = len(df_sorted) - 1
        
        if start_val <= 0 or periods <= 0:
            return np.nan
        
        return (((end_val / start_val) ** (1/periods)) - 1) * 100
    
    def _find_most_volatile_countries(self, df: pd.DataFrame) -> List[Dict]:
        """Find countries with most volatile growth."""
        volatility_by_country = df.groupby('country_code').agg({
            'growth_rate': 'std',
            'country_name': 'first',
            'population': 'last'
        }).reset_index()
        
        volatility_by_country = volatility_by_country.dropna()
        most_volatile = volatility_by_country.nlargest(10, 'growth_rate')
        
        return most_volatile[['country_name', 'growth_rate', 'population']].to_dict('records')
    
    def _calculate_growth_by_decade(self, df: pd.DataFrame) -> Dict:
        """Calculate average growth by decade."""
        df['decade'] = (df['year'] // 10) * 10
        decade_growth = df.groupby('decade')['growth_rate'].mean().to_dict()
        
        return {str(int(k)): v for k, v in decade_growth.items() if not np.isnan(v)}
    
    def analyze_regional_patterns(self) -> Dict:
        """Analyze regional population patterns."""
        self.logger.info("Analyzing regional patterns...")
        
        # Regional growth over time
        regional_analysis = {}
        
        for region in self.regional_df['region_code'].unique():
            if region == 'WLD':  # Skip world total
                continue
            
            region_data = self.regional_df[
                self.regional_df['region_code'] == region
            ].sort_values('year')
            
            if len(region_data) < 2:
                continue
            
            region_data['growth_rate'] = region_data['population'].pct_change() * 100
            
            regional_analysis[region] = {
                'name': region_data['region_name'].iloc[0],
                'current_population': region_data['population'].iloc[-1],
                'growth_rate_latest': region_data['growth_rate'].iloc[-1],
                'average_growth': region_data['growth_rate'].mean(),
                'population_2000': region_data[region_data['year'] == 2000]['population'].iloc[0] if len(region_data[region_data['year'] == 2000]) > 0 else None,
                'cagr_since_2000': self._calculate_cagr(region_data[region_data['year'] >= 2000], 23)
            }
        
        # Calculate share of world population
        world_pop_latest = self.regional_df[
            (self.regional_df['region_code'] == 'WLD') & 
            (self.regional_df['year'] == self.regional_df['year'].max())
        ]['population'].iloc[0]
        
        for region in regional_analysis:
            regional_analysis[region]['world_share_percent'] = (
                regional_analysis[region]['current_population'] / world_pop_latest
            ) * 100
        
        self.results['regional_analysis'] = regional_analysis
        return regional_analysis
    
    def analyze_rankings(self) -> Dict:
        """Analyze country rankings over time."""
        self.logger.info("Analyzing country rankings...")
        
        ranking_analysis = {}
        
        # Top 10 by decade
        decades = [1970, 1980, 1990, 2000, 2010, 2020]
        
        for decade in decades:
            decade_data = self.population_df[
                (self.population_df['year'] >= decade) & 
                (self.population_df['year'] < decade + 10)
            ]
            
            if decade_data.empty:
                continue
            
            # Get average population for the decade
            decade_avg = decade_data.groupby('country_code').agg({
                'population': 'mean',
                'country_name': 'first'
            }).reset_index()
            
            top_10 = decade_avg.nlargest(10, 'population')
            
            ranking_analysis[f"top_10_{decade}s"] = top_10[
                ['country_name', 'population']
            ].to_dict('records')
        
        # Ranking changes analysis
        ranking_changes = self._analyze_ranking_changes()
        ranking_analysis['ranking_changes'] = ranking_changes
        
        # China vs India analysis
        china_india_analysis = self._analyze_china_india_crossover()
        ranking_analysis['china_india_crossover'] = china_india_analysis
        
        self.results['ranking_analysis'] = ranking_analysis
        return ranking_analysis
    
    def _analyze_ranking_changes(self) -> Dict:
        """Analyze which countries moved up/down in rankings most."""
        # Compare 2000 vs 2020 rankings
        year_2000 = self.population_df[self.population_df['year'] == 2000].copy()
        year_2020 = self.population_df[self.population_df['year'] == 2020].copy()
        
        if year_2000.empty or year_2020.empty:
            return {}
        
        year_2000['rank_2000'] = year_2000['population'].rank(method='dense', ascending=False)
        year_2020['rank_2020'] = year_2020['population'].rank(method='dense', ascending=False)
        
        # Merge and calculate change
        ranking_change = pd.merge(
            year_2000[['country_code', 'country_name', 'rank_2000']],
            year_2020[['country_code', 'rank_2020']],
            on='country_code'
        )
        
        ranking_change['rank_change'] = ranking_change['rank_2000'] - ranking_change['rank_2020']
        
        return {
            'biggest_climbers': ranking_change.nlargest(10, 'rank_change')[
                ['country_name', 'rank_2000', 'rank_2020', 'rank_change']
            ].to_dict('records'),
            'biggest_fallers': ranking_change.nsmallest(10, 'rank_change')[
                ['country_name', 'rank_2000', 'rank_2020', 'rank_change']
            ].to_dict('records')
        }
    
    def _analyze_china_india_crossover(self) -> Dict:
        """Analyze when India surpassed/will surpass China."""
        china_data = self.population_df[self.population_df['country_code'] == 'CHN'].sort_values('year')
        india_data = self.population_df[self.population_df['country_code'] == 'IND'].sort_values('year')
        
        if china_data.empty or india_data.empty:
            return {}
        
        # Merge data
        comparison = pd.merge(
            china_data[['year', 'population']].rename(columns={'population': 'china_pop'}),
            india_data[['year', 'population']].rename(columns={'population': 'india_pop'}),
            on='year'
        )
        
        comparison['india_larger'] = comparison['india_pop'] > comparison['china_pop']
        
        # Find crossover point
        crossover_years = comparison[comparison['india_larger']]['year'].tolist()
        
        return {
            'crossover_occurred': len(crossover_years) > 0,
            'crossover_year': crossover_years[0] if crossover_years else None,
            'latest_gap': abs(comparison.iloc[-1]['china_pop'] - comparison.iloc[-1]['india_pop']),
            'gap_direction': 'India ahead' if comparison.iloc[-1]['india_pop'] > comparison.iloc[-1]['china_pop'] else 'China ahead'
        }
    
    def perform_statistical_tests(self) -> Dict:
        """Perform various statistical tests on the data."""
        self.logger.info("Performing statistical tests...")
        
        # Test for exponential vs linear growth
        world_data = self.regional_df[self.regional_df['region_code'] == 'WLD'].sort_values('year')
        
        if len(world_data) < 10:
            return {}
        
        # Linear regression
        years = world_data['year'].values
        population = world_data['population'].values
        
        # Linear fit
        linear_slope, linear_intercept, linear_r, linear_p, _ = stats.linregress(years, population)
        
        # Exponential fit (log transformation)
        log_pop = np.log(population)
        exp_slope, exp_intercept, exp_r, exp_p, _ = stats.linregress(years, log_pop)
        
        # Correlation between population size and growth rate
        latest_year = self.population_df['year'].max()
        latest_data = self.population_df[self.population_df['year'] == latest_year]
        
        # Calculate growth rates
        growth_rates = []
        for country in latest_data['country_code']:
            country_data = self.population_df[
                self.population_df['country_code'] == country
            ].sort_values('year')
            
            if len(country_data) >= 2:
                recent_growth = ((country_data.iloc[-1]['population'] - country_data.iloc[-2]['population']) / 
                               country_data.iloc[-2]['population']) * 100
                growth_rates.append({
                    'country_code': country,
                    'population': country_data.iloc[-1]['population'],
                    'growth_rate': recent_growth
                })
        
        growth_df = pd.DataFrame(growth_rates)
        
        correlation_coef, correlation_p = stats.pearsonr(
            growth_df['population'], growth_df['growth_rate']
        ) if len(growth_df) > 0 else (0, 1)
        
        statistical_tests = {
            'world_population_trends': {
                'linear_fit': {
                    'r_squared': linear_r ** 2,
                    'p_value': linear_p,
                    'slope': linear_slope
                },
                'exponential_fit': {
                    'r_squared': exp_r ** 2,
                    'p_value': exp_p,
                    'growth_rate': exp_slope
                },
                'best_fit': 'exponential' if exp_r ** 2 > linear_r ** 2 else 'linear'
            },
            'size_growth_correlation': {
                'correlation_coefficient': correlation_coef,
                'p_value': correlation_p,
                'significant': correlation_p < 0.05
            }
        }
        
        self.results['statistical_tests'] = statistical_tests
        return statistical_tests
    
    def generate_summary_report(self) -> Dict:
        """Generate a comprehensive summary of all analysis."""
        self.logger.info("Generating summary report...")
        
        summary = {
            'analysis_timestamp': datetime.now().isoformat(),
            'data_summary': {
                'total_countries': len(self.population_df['country_code'].unique()),
                'year_range': f"{self.population_df['year'].min()}-{self.population_df['year'].max()}",
                'total_records': len(self.population_df)
            },
            'key_findings': self._extract_key_findings(),
            'data_quality_score': self._calculate_data_quality_score(),
            'recommended_visualizations': self._recommend_visualizations()
        }
        
        # Combine all results
        summary.update(self.results)
        
        # Save to file
        with open('outputs/analysis_summary.json', 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        
        return summary
    
    def _extract_key_findings(self) -> List[str]:
        """Extract key findings from analysis results."""
        findings = []
        
        if 'basic_statistics' in self.results:
            world_pop = self.results['basic_statistics']['world_population_latest']
            findings.append(f"Current world population: {world_pop:,.0f}")
        
        if 'growth_analysis' in self.results:
            avg_growth = self.results['growth_analysis']['growth_rate_statistics']['mean']
            findings.append(f"Average global population growth rate: {avg_growth:.2f}%")
        
        if 'regional_analysis' in self.results:
            fastest_region = max(
                self.results['regional_analysis'].items(),
                key=lambda x: x[1]['growth_rate_latest']
            )
            findings.append(f"Fastest growing region: {fastest_region[1]['name']}")
        
        return findings
    
    def _calculate_data_quality_score(self) -> float:
        """Calculate overall data quality score."""
        total_possible = len(self.population_df['country_code'].unique()) * len(range(1960, 2024))
        actual_records = len(self.population_df)
        
        return (actual_records / total_possible) * 100
    
    def _recommend_visualizations(self) -> List[str]:
        """Recommend visualization types based on data patterns."""
        recommendations = [
            "Time series line chart for world population growth",
            "Animated bar chart race for top 10 countries over time",
            "Geographic choropleth map for population density",
            "Scatter plot: population size vs growth rate",
            "Regional comparison pie charts for different decades"
        ]
        
        return recommendations


def main():
    """Main function to run all analyses."""
    analyzer = PopulationDataAnalyzer()
    
    print("Starting comprehensive population data analysis...")
    print("=" * 50)
    
    analyses = [
        ("Basic Statistics", analyzer.calculate_basic_statistics),
        ("Growth Patterns", analyzer.analyze_growth_patterns),
        ("Regional Analysis", analyzer.analyze_regional_patterns),
        ("Ranking Analysis", analyzer.analyze_rankings),
        ("Statistical Tests", analyzer.perform_statistical_tests),
        ("Summary Report", analyzer.generate_summary_report)
    ]
    
    for analysis_name, analysis_func in analyses:
        print(f"\n{analysis_name}...")
        try:
            result = analysis_func()
            print(f"✓ {analysis_name} completed")
        except Exception as e:
            print(f"✗ {analysis_name} failed: {e}")
    
    print("\n" + "=" * 50)
    print("Analysis complete! Results saved to outputs/analysis_summary.json")


if __name__ == "__main__":
    main()
