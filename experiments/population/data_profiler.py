"""
World Bank Data Quality Profiler
Analyzes data completeness, consistency, timeliness, and accuracy.
"""

import pandas as pd
import numpy as np
import json
import logging
from typing import Dict, List, Tuple
from datetime import datetime
import os

class DataQualityProfiler:
    """
    Comprehensive data quality profiler for World Bank population data.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.quality_report = {}
        
        # Load data
        self.population_df = None
        self.countries_df = None
        self.availability_matrix = None
        
        self._load_data()
    
    def _load_data(self):
        """Load all necessary data files."""
        self.logger.info("Loading data for quality profiling...")
        
        try:
            # Load population timeseries
            with open('data/population_timeseries.json', 'r') as f:
                population_data = json.load(f)
            
            # Convert to DataFrame
            pop_records = []
            for record in population_data:
                pop_records.append({
                    'country_code': record.get('countryiso3code', record.get('country', {}).get('id')),
                    'country_name': record.get('country', {}).get('value', 'Unknown'),
                    'year': int(record.get('date', 0)),
                    'population': record.get('value'),  # Keep None values for quality analysis
                    'decimal': record.get('decimal', 0)
                })
            
            self.population_df = pd.DataFrame(pop_records)
            
            # Load countries metadata
            with open('data/countries_metadata.json', 'r') as f:
                countries_data = json.load(f)
            self.countries_df = pd.DataFrame(countries_data)
            
            # Load availability matrix if exists
            try:
                with open('data/data_availability_matrix.json', 'r') as f:
                    self.availability_matrix = json.load(f)
            except FileNotFoundError:
                self.availability_matrix = None
            
            self.logger.info(f"Loaded {len(self.population_df)} population records for quality analysis")
            
        except Exception as e:
            self.logger.error(f"Error loading data: {e}")
            raise
    
    def analyze_completeness(self) -> Dict:
        """Analyze data completeness across countries and years."""
        self.logger.info("Analyzing data completeness...")
        
        # Calculate missing values
        total_records = len(self.population_df)
        missing_values = self.population_df['population'].isna().sum()
        completeness_percentage = ((total_records - missing_values) / total_records) * 100
        
        # Missing values by country
        missing_by_country = self.population_df.groupby('country_code').agg({
            'population': ['count', lambda x: x.isna().sum()]
        }).round(2)
        
        missing_by_country.columns = ['total_records', 'missing_records']
        missing_by_country['missing_percentage'] = (
            missing_by_country['missing_records'] / missing_by_country['total_records'] * 100
        ).round(2)
        
        # Countries with most missing data
        worst_countries = missing_by_country.nlargest(10, 'missing_percentage')
        
        # Missing values by year
        missing_by_year = self.population_df.groupby('year').agg({
            'population': ['count', lambda x: x.isna().sum()]
        })
        missing_by_year.columns = ['total_records', 'missing_records']
        missing_by_year['missing_percentage'] = (
            missing_by_year['missing_records'] / missing_by_year['total_records'] * 100
        ).round(2)
        
        # Years with most missing data
        worst_years = missing_by_year.nlargest(10, 'missing_percentage')
        
        # Calculate year ranges with data for each country
        country_year_ranges = self.population_df[self.population_df['population'].notna()].groupby('country_code').agg({
            'year': ['min', 'max', 'count'],
            'country_name': 'first'
        })
        country_year_ranges.columns = ['first_year', 'last_year', 'years_with_data', 'country_name']
        country_year_ranges['data_span'] = country_year_ranges['last_year'] - country_year_ranges['first_year'] + 1
        country_year_ranges['data_coverage'] = (
            country_year_ranges['years_with_data'] / country_year_ranges['data_span'] * 100
        ).round(2)
        
        completeness_analysis = {
            'overall_completeness_percentage': round(completeness_percentage, 2),
            'total_records': total_records,
            'missing_records': int(missing_values),
            'countries_with_most_missing_data': worst_countries.reset_index().to_dict('records')[:10],
            'years_with_most_missing_data': worst_years.reset_index().to_dict('records')[:10],
            'country_data_coverage': {
                'best_coverage': country_year_ranges.nlargest(10, 'data_coverage').reset_index().to_dict('records'),
                'worst_coverage': country_year_ranges.nsmallest(10, 'data_coverage').reset_index().to_dict('records')
            },
            'missing_data_patterns': self._analyze_missing_patterns()
        }
        
        self.quality_report['completeness'] = completeness_analysis
        return completeness_analysis
    
    def _analyze_missing_patterns(self) -> Dict:
        """Analyze patterns in missing data."""
        # Group consecutive missing years
        patterns = {}
        
        for country in self.population_df['country_code'].unique():
            country_data = self.population_df[
                self.population_df['country_code'] == country
            ].sort_values('year')
            
            missing_years = country_data[country_data['population'].isna()]['year'].tolist()
            
            if missing_years:
                # Find consecutive sequences
                consecutive_groups = []
                current_group = [missing_years[0]]
                
                for i in range(1, len(missing_years)):
                    if missing_years[i] == missing_years[i-1] + 1:
                        current_group.append(missing_years[i])
                    else:
                        consecutive_groups.append(current_group)
                        current_group = [missing_years[i]]
                
                consecutive_groups.append(current_group)
                
                patterns[country] = {
                    'total_missing': len(missing_years),
                    'consecutive_groups': consecutive_groups,
                    'longest_gap': max(len(group) for group in consecutive_groups)
                }
        
        return patterns
    
    def analyze_consistency(self) -> Dict:
        """Analyze data consistency and identify anomalies."""
        self.logger.info("Analyzing data consistency...")
        
        # Remove missing values for consistency checks
        clean_data = self.population_df.dropna(subset=['population']).copy()
        
        # Check for impossible values
        negative_populations = clean_data[clean_data['population'] < 0]
        zero_populations = clean_data[clean_data['population'] == 0]
        
        # Check for unrealistic growth rates
        unrealistic_growth = []
        
        for country in clean_data['country_code'].unique():
            country_data = clean_data[
                clean_data['country_code'] == country
            ].sort_values('year')
            
            if len(country_data) < 2:
                continue
            
            country_data['growth_rate'] = country_data['population'].pct_change() * 100
            
            # Flag growth rates > 10% or < -10% as potentially unrealistic
            extreme_growth = country_data[
                (country_data['growth_rate'].abs() > 10) & 
                (country_data['growth_rate'].notna())
            ]
            
            if not extreme_growth.empty:
                unrealistic_growth.extend(extreme_growth.to_dict('records'))
        
        # Check for data corrections (sudden jumps that might indicate revisions)
        potential_corrections = []
        
        for country in clean_data['country_code'].unique():
            country_data = clean_data[
                clean_data['country_code'] == country
            ].sort_values('year')
            
            if len(country_data) < 3:
                continue
            
            # Look for sudden jumps followed by corrections
            country_data['growth_rate'] = country_data['population'].pct_change() * 100
            country_data['next_growth'] = country_data['growth_rate'].shift(-1)
            
            # Flag cases where extreme positive growth is followed by extreme negative growth
            corrections = country_data[
                (country_data['growth_rate'] > 5) & 
                (country_data['next_growth'] < -5)
            ]
            
            if not corrections.empty:
                potential_corrections.extend(corrections.to_dict('records'))
        
        # Regional totals consistency (if regional data is available)
        regional_consistency = self._check_regional_consistency()
        
        consistency_analysis = {
            'impossible_values': {
                'negative_populations': len(negative_populations),
                'zero_populations': len(zero_populations),
                'negative_examples': negative_populations.to_dict('records')[:5]
            },
            'unrealistic_growth_rates': {
                'total_instances': len(unrealistic_growth),
                'examples': unrealistic_growth[:10]
            },
            'potential_data_corrections': {
                'total_instances': len(potential_corrections),
                'examples': potential_corrections[:10]
            },
            'regional_consistency': regional_consistency
        }
        
        self.quality_report['consistency'] = consistency_analysis
        return consistency_analysis
    
    def _check_regional_consistency(self) -> Dict:
        """Check if regional totals are consistent with country totals."""
        try:
            with open('data/population_regions.json', 'r') as f:
                regional_data = json.load(f)
            
            # Convert to DataFrame
            regional_records = []
            for record in regional_data:
                if record.get('value') is not None:
                    regional_records.append({
                        'region_code': record.get('countryiso3code'),
                        'year': int(record.get('date')),
                        'population': float(record.get('value'))
                    })
            
            regional_df = pd.DataFrame(regional_records)
            
            # Compare world total with sum of regions
            world_data = regional_df[regional_df['region_code'] == 'WLD']
            
            # This is a simplified check - in reality, regions overlap
            return {
                'world_data_available': len(world_data) > 0,
                'latest_world_population': world_data[world_data['year'] == world_data['year'].max()]['population'].iloc[0] if not world_data.empty else None
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def analyze_timeliness(self) -> Dict:
        """Analyze data timeliness and recency."""
        self.logger.info("Analyzing data timeliness...")
        
        clean_data = self.population_df.dropna(subset=['population'])
        
        # Latest available year for each country
        latest_by_country = clean_data.groupby('country_code').agg({
            'year': 'max',
            'country_name': 'first'
        }).reset_index()
        
        latest_by_country.columns = ['country_code', 'latest_year', 'country_name']
        
        # Overall latest year in dataset
        global_latest_year = clean_data['year'].max()
        
        # Calculate staleness (years behind latest)
        latest_by_country['years_behind'] = global_latest_year - latest_by_country['latest_year']
        
        # Countries with stale data
        stale_data = latest_by_country[latest_by_country['years_behind'] > 0]
        
        # Update frequency analysis
        update_frequency = clean_data.groupby('country_code')['year'].apply(
            lambda x: x.sort_values().diff().dropna().mode().iloc[0] if len(x.sort_values().diff().dropna().mode()) > 0 else None
        ).reset_index()
        update_frequency.columns = ['country_code', 'typical_update_interval']
        
        timeliness_analysis = {
            'global_latest_year': int(global_latest_year),
            'countries_with_current_data': int((latest_by_country['years_behind'] == 0).sum()),
            'countries_with_stale_data': len(stale_data),
            'stalest_data': stale_data.nlargest(10, 'years_behind').to_dict('records'),
            'average_staleness': float(latest_by_country['years_behind'].mean()),
            'update_patterns': {
                'annual_updates': int((update_frequency['typical_update_interval'] == 1).sum()),
                'biennial_updates': int((update_frequency['typical_update_interval'] == 2).sum()),
                'irregular_updates': int((update_frequency['typical_update_interval'] > 2).sum())
            }
        }
        
        self.quality_report['timeliness'] = timeliness_analysis
        return timeliness_analysis
    
    def analyze_accuracy_indicators(self) -> Dict:
        """Analyze indicators of data accuracy."""
        self.logger.info("Analyzing accuracy indicators...")
        
        # Check decimal places (indicator of precision)
        decimal_analysis = self.population_df['decimal'].value_counts().to_dict()
        
        # Countries with footnotes or special indicators (from metadata)
        countries_with_notes = []
        if not self.countries_df.empty:
            # Look for special country types that might indicate data issues
            special_countries = self.countries_df[
                self.countries_df['incomeLevel'].apply(
                    lambda x: x.get('value', '') if isinstance(x, dict) else str(x)
                ).str.contains('Not classified|Small states', na=False)
            ]
            
            countries_with_notes = special_countries[['id', 'name']].to_dict('records')
        
        # Identify estimated vs census data based on update patterns
        estimated_data_indicators = self._identify_estimated_data()
        
        accuracy_analysis = {
            'decimal_precision_distribution': decimal_analysis,
            'countries_with_special_status': len(countries_with_notes),
            'special_status_examples': countries_with_notes[:10],
            'estimated_data_indicators': estimated_data_indicators,
            'data_source_reliability': self._assess_data_reliability()
        }
        
        self.quality_report['accuracy'] = accuracy_analysis
        return accuracy_analysis
    
    def _identify_estimated_data(self) -> Dict:
        """Identify countries that likely use estimated rather than census data."""
        clean_data = self.population_df.dropna(subset=['population'])
        
        # Countries with very regular updates might be using estimates
        regular_update_countries = []
        irregular_update_countries = []
        
        for country in clean_data['country_code'].unique():
            country_data = clean_data[
                clean_data['country_code'] == country
            ].sort_values('year')
            
            if len(country_data) < 5:  # Need sufficient data
                continue
            
            year_gaps = country_data['year'].diff().dropna()
            
            # Very regular updates (every year) might indicate estimates
            if (year_gaps == 1).all():
                regular_update_countries.append(country)
            # Irregular updates might indicate census-based data
            elif year_gaps.var() > 1:
                irregular_update_countries.append(country)
        
        return {
            'likely_estimated_data_countries': len(regular_update_countries),
            'likely_census_based_countries': len(irregular_update_countries),
            'estimated_examples': regular_update_countries[:10],
            'census_examples': irregular_update_countries[:10]
        }
    
    def _assess_data_reliability(self) -> Dict:
        """Assess overall data reliability by country."""
        clean_data = self.population_df.dropna(subset=['population'])
        
        reliability_scores = {}
        
        for country in clean_data['country_code'].unique():
            country_data = clean_data[
                clean_data['country_code'] == country
            ].sort_values('year')
            
            if len(country_data) < 3:
                continue
            
            # Calculate reliability score based on multiple factors
            score = 100
            
            # Penalize for missing data
            total_possible_years = 2023 - 1960 + 1
            actual_years = len(country_data)
            completeness_score = (actual_years / total_possible_years) * 100
            
            # Penalize for extreme volatility
            country_data['growth_rate'] = country_data['population'].pct_change() * 100
            volatility = country_data['growth_rate'].std()
            volatility_penalty = min(volatility * 2, 50) if not np.isnan(volatility) else 0
            
            # Penalize for staleness
            latest_year = country_data['year'].max()
            staleness_penalty = (2023 - latest_year) * 5
            
            final_score = max(0, completeness_score - volatility_penalty - staleness_penalty)
            
            reliability_scores[country] = {
                'score': round(final_score, 2),
                'completeness': round(completeness_score, 2),
                'volatility_penalty': round(volatility_penalty, 2),
                'staleness_penalty': round(staleness_penalty, 2)
            }
        
        # Sort by reliability score
        sorted_scores = sorted(reliability_scores.items(), key=lambda x: x[1]['score'], reverse=True)
        
        return {
            'most_reliable_countries': sorted_scores[:10],
            'least_reliable_countries': sorted_scores[-10:],
            'average_reliability_score': np.mean([score['score'] for score in reliability_scores.values()])
        }
    
    def generate_quality_summary(self) -> Dict:
        """Generate overall data quality summary."""
        self.logger.info("Generating data quality summary...")
        
        # Calculate overall quality metrics
        completeness_score = self.quality_report.get('completeness', {}).get('overall_completeness_percentage', 0)
        timeliness_score = 100 - (self.quality_report.get('timeliness', {}).get('average_staleness', 0) * 10)
        timeliness_score = max(0, timeliness_score)
        
        consistency_issues = (
            len(self.quality_report.get('consistency', {}).get('unrealistic_growth_rates', {}).get('examples', [])) +
            len(self.quality_report.get('consistency', {}).get('potential_data_corrections', {}).get('examples', []))
        )
        consistency_score = max(0, 100 - consistency_issues)
        
        overall_score = (completeness_score + timeliness_score + consistency_score) / 3
        
        # Recommendations
        recommendations = self._generate_recommendations()
        
        # Best countries for demo
        demo_countries = self._recommend_demo_countries()
        
        quality_summary = {
            'overall_quality_score': round(overall_score, 2),
            'component_scores': {
                'completeness': round(completeness_score, 2),
                'timeliness': round(timeliness_score, 2),
                'consistency': round(consistency_score, 2)
            },
            'total_data_issues': consistency_issues,
            'recommendations': recommendations,
            'recommended_demo_countries': demo_countries,
            'quality_grade': self._assign_quality_grade(overall_score)
        }
        
        self.quality_report['summary'] = quality_summary
        
        # Save complete quality report
        with open('outputs/data_quality_report.json', 'w') as f:
            json.dump(self.quality_report, f, indent=2, default=str)
        
        return quality_summary
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on quality analysis."""
        recommendations = []
        
        completeness = self.quality_report.get('completeness', {}).get('overall_completeness_percentage', 100)
        if completeness < 80:
            recommendations.append("Consider implementing data interpolation for missing values")
        
        staleness = self.quality_report.get('timeliness', {}).get('average_staleness', 0)
        if staleness > 2:
            recommendations.append("Focus on countries with recent data for real-time analysis")
        
        consistency_issues = len(self.quality_report.get('consistency', {}).get('unrealistic_growth_rates', {}).get('examples', []))
        if consistency_issues > 10:
            recommendations.append("Implement data validation rules for extreme growth rates")
        
        recommendations.extend([
            "Use data reliability scores to weight country comparisons",
            "Highlight data limitations in user interface",
            "Implement confidence intervals for projections"
        ])
        
        return recommendations
    
    def _recommend_demo_countries(self) -> List[str]:
        """Recommend best countries for demo based on data quality."""
        accuracy_data = self.quality_report.get('accuracy', {}).get('data_source_reliability', {})
        most_reliable = accuracy_data.get('most_reliable_countries', [])
        
        demo_countries = []
        for country_code, scores in most_reliable[:15]:  # Top 15 most reliable
            clean_data = self.population_df.dropna(subset=['population'])
            country_data = clean_data[clean_data['country_code'] == country_code]
            
            if not country_data.empty:
                country_name = country_data['country_name'].iloc[0]
                demo_countries.append(f"{country_name} ({country_code})")
        
        return demo_countries[:10]  # Return top 10
    
    def _assign_quality_grade(self, score: float) -> str:
        """Assign letter grade based on quality score."""
        if score >= 90:
            return "A (Excellent)"
        elif score >= 80:
            return "B (Good)"
        elif score >= 70:
            return "C (Fair)"
        elif score >= 60:
            return "D (Poor)"
        else:
            return "F (Failing)"


def main():
    """Main function to run data quality profiling."""
    profiler = DataQualityProfiler()
    
    print("Starting data quality profiling...")
    print("=" * 50)
    
    analyses = [
        ("Completeness Analysis", profiler.analyze_completeness),
        ("Consistency Analysis", profiler.analyze_consistency),
        ("Timeliness Analysis", profiler.analyze_timeliness),
        ("Accuracy Analysis", profiler.analyze_accuracy_indicators),
        ("Quality Summary", profiler.generate_quality_summary)
    ]
    
    for analysis_name, analysis_func in analyses:
        print(f"\n{analysis_name}...")
        try:
            result = analysis_func()
            print(f"✓ {analysis_name} completed")
        except Exception as e:
            print(f"✗ {analysis_name} failed: {e}")
    
    print("\n" + "=" * 50)
    print("Data quality profiling complete!")
    print("Results saved to outputs/data_quality_report.json")


if __name__ == "__main__":
    main()
