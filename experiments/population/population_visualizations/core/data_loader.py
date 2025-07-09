"""
Professional Data Loader Module for World Bank Population Data

This module provides robust data loading capabilities with caching, validation,
and quality assessment for population demographic analysis.
"""

import pandas as pd
import numpy as np
import json
import os
from typing import Dict, List, Optional, Tuple, Union
from functools import lru_cache
from pathlib import Path
import logging
from tqdm import tqdm
from datetime import datetime

class PopulationDataLoader:
    """
    Professional data loader for World Bank population data with advanced
    caching, validation, and quality assessment capabilities.
    
    Features:
    - Intelligent caching with LRU eviction
    - Comprehensive data validation
    - Quality scoring and reporting
    - Missing value handling
    - Metadata enrichment
    
    Example:
        >>> loader = PopulationDataLoader()
        >>> data = loader.load_population_data()
        >>> quality_report = loader.get_data_quality_report()
        >>> print(f"Data quality: {quality_report['completeness_percentage']:.1f}%")
    """
    
    def __init__(self, data_dir: str = "../data", cache_size: int = 128):
        """
        Initialize the data loader with configuration.
        
        Args:
            data_dir: Directory containing population data files
            cache_size: Maximum number of cached queries (LRU eviction)
        """
        self.data_dir = Path(data_dir)
        self.cache_size = cache_size
        self.logger = self._setup_logging()
        
        # Data storage
        self._population_data: Optional[pd.DataFrame] = None
        self._metadata: Optional[pd.DataFrame] = None
        self._quality_report: Optional[Dict] = None
        
        # Cache statistics
        self.cache_hits = 0
        self.cache_misses = 0
        
    def _setup_logging(self) -> logging.Logger:
        """Setup professional logging configuration."""
        logger = logging.getLogger(f"{__name__}.PopulationDataLoader")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
    
    def load_population_data(self, force_reload: bool = False) -> pd.DataFrame:
        """
        Load population data with intelligent caching and validation.
        
        Args:
            force_reload: Force reload from disk, bypassing cache
            
        Returns:
            DataFrame with population data (countries × years)
            
        Raises:
            FileNotFoundError: If data files are not found
            ValueError: If data validation fails
        """
        if self._population_data is not None and not force_reload:
            self.cache_hits += 1
            self.logger.info(f"Cache hit: Population data loaded from memory")
            return self._population_data
        
        self.cache_misses += 1
        self.logger.info("Loading population data from disk...")
        
        # Try multiple data sources
        data_files = [
            self.data_dir / "population_timeseries.json",
            self.data_dir / "population_current.json",
            self.data_dir / "population_data.csv",
            self.data_dir / "population_timeseries.csv"
        ]
        
        data = None
        for file_path in data_files:
            if file_path.exists():
                try:
                    if file_path.suffix == '.json':
                        data = self._load_from_json(file_path)
                    else:
                        data = self._load_from_csv(file_path)
                    break
                except Exception as e:
                    self.logger.warning(f"Failed to load {file_path}: {e}")
                    continue
        
        if data is None:
            raise FileNotFoundError(
                f"No valid population data files found in {self.data_dir}. "
                f"Expected: {[f.name for f in data_files]}"
            )
        
        # Validate and process data
        data = self.validate_data(data)
        self._population_data = data
        
        # Print terminal summary
        countries = len(data['country'].unique()) if 'country' in data.columns else len(data)
        years = len(data['year'].unique()) if 'year' in data.columns else data.shape[1]
        completeness = self._calculate_completeness(data)
        
        print(f"✅ Data loaded: {countries} countries, {years} years, {completeness:.1f}% complete")
        self.logger.info(f"Population data loaded successfully: {data.shape}")
        
        return data
    
    def _load_from_json(self, file_path: Path) -> pd.DataFrame:
        """Load data from JSON format."""
        with open(file_path, 'r') as f:
            json_data = json.load(f)
        
        if isinstance(json_data, list):
            # World Bank API format
            records = []
            for item in json_data:
                if 'date' in item and 'value' in item and 'country' in item:
                    records.append({
                        'country': item['country'].get('value', 'Unknown'),
                        'country_code': item['country'].get('id', 'UNK'),
                        'year': int(item['date']),
                        'population': item['value']
                    })
            return pd.DataFrame(records)
        else:
            # Direct dictionary format
            return pd.DataFrame(json_data)
    
    def _load_from_csv(self, file_path: Path) -> pd.DataFrame:
        """Load data from CSV format with automatic format detection."""
        # Try different separators and encodings
        for sep in [',', ';', '\t']:
            for encoding in ['utf-8', 'utf-8-sig', 'latin1']:
                try:
                    data = pd.read_csv(file_path, sep=sep, encoding=encoding)
                    if data.shape[1] > 1:  # Successfully parsed
                        return data
                except Exception:
                    continue
        
        # Fallback to default pandas behavior
        return pd.read_csv(file_path)
    
    def validate_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Comprehensive data validation with detailed error reporting.
        
        Args:
            data: Raw population data
            
        Returns:
            Validated and cleaned data
            
        Raises:
            ValueError: If critical validation failures occur
        """
        self.logger.info("Starting data validation...")
        validation_errors = []
        warnings = []
        
        # 1. Check required columns
        required_cols = ['country', 'year', 'population']
        missing_cols = [col for col in required_cols if col not in data.columns]
        
        if missing_cols and len(data.columns) >= 3:
            # Try to infer column names
            data.columns = list(data.columns[:3]) + list(data.columns[3:])
            if len(data.columns) >= 3:
                data.columns = ['country', 'year', 'population'] + list(data.columns[3:])
                warnings.append("Inferred column names from data structure")
        elif missing_cols:
            validation_errors.append(f"Missing required columns: {missing_cols}")
        
        # 2. Check for negative populations
        if 'population' in data.columns:
            negative_pops = data[data['population'] < 0]
            if len(negative_pops) > 0:
                validation_errors.append(f"Found {len(negative_pops)} negative population values")
        
        # 3. Check year range
        if 'year' in data.columns:
            year_range = data['year'].min(), data['year'].max()
            if year_range[0] < 1800 or year_range[1] > 2030:
                warnings.append(f"Unusual year range: {year_range}")
        
        # 4. Check for reasonable population values
        if 'population' in data.columns:
            max_pop = data['population'].max()
            if max_pop > 2e9:  # More than 2 billion for any single country
                warnings.append(f"Unusually large population value: {max_pop:,.0f}")
        
        # 5. Check for missing values
        missing_pct = data.isnull().sum().sum() / (data.shape[0] * data.shape[1]) * 100
        if missing_pct > 10:
            warnings.append(f"High missing data percentage: {missing_pct:.1f}%")
        
        # Log validation results
        if validation_errors:
            error_msg = "; ".join(validation_errors)
            self.logger.error(f"Validation failed: {error_msg}")
            raise ValueError(f"Data validation failed: {error_msg}")
        
        if warnings:
            for warning in warnings:
                self.logger.warning(warning)
        
        # Clean and standardize data
        if 'population' in data.columns:
            # Remove rows with null populations
            initial_rows = len(data)
            data = data.dropna(subset=['population'])
            removed_rows = initial_rows - len(data)
            if removed_rows > 0:
                self.logger.info(f"Removed {removed_rows} rows with missing population data")
            
            # Convert population to numeric
            data['population'] = pd.to_numeric(data['population'], errors='coerce')
            data = data.dropna(subset=['population'])
        
        if 'year' in data.columns:
            data['year'] = pd.to_numeric(data['year'], errors='coerce')
            data = data.dropna(subset=['year'])
            data['year'] = data['year'].astype(int)
        
        self.logger.info(f"Data validation completed successfully: {data.shape}")
        return data
    
    def _calculate_completeness(self, data: pd.DataFrame) -> float:
        """Calculate data completeness percentage."""
        if 'population' in data.columns:
            total_possible = len(data)
            actual_values = len(data.dropna(subset=['population']))
            return (actual_values / total_possible) * 100
        else:
            # For wide format data
            total_cells = data.select_dtypes(include=[np.number]).size
            non_null_cells = data.select_dtypes(include=[np.number]).notna().sum().sum()
            return (non_null_cells / total_cells) * 100 if total_cells > 0 else 0
    
    def get_country_data(self, countries: Union[str, List[str]], 
                        start_year: int = 1960, end_year: int = 2023) -> pd.DataFrame:
        """
        Get data for specific countries with intelligent caching.
        
        Args:
            countries: Single country name or list of country names
            start_year: Starting year for data
            end_year: Ending year for data
            
        Returns:
            Filtered DataFrame for specified countries and years
        """
        if self._population_data is None:
            self.load_population_data()
        
        if isinstance(countries, str):
            countries = [countries]
        
        # Convert list to tuple for hashing in cache
        countries_tuple = tuple(sorted(countries))
        
        # Use internal cached method
        return self._get_country_data_cached(countries_tuple, start_year, end_year)
    
    @lru_cache(maxsize=32)
    def _get_country_data_cached(self, countries_tuple: Tuple[str, ...], 
                                start_year: int = 1960, end_year: int = 2023) -> pd.DataFrame:
        """
        Get data for specific countries with intelligent caching (internal method).
        
        Args:
            countries_tuple: Tuple of country names (for caching)
            start_year: Starting year for data
            end_year: Ending year for data
            
        Returns:
            Filtered DataFrame for specified countries and years
        """
        data = self._population_data.copy()
        countries = list(countries_tuple)
        
        # Filter by countries
        if 'country' in data.columns:
            data = data[data['country'].isin(countries)]
        
        # Filter by years
        if 'year' in data.columns:
            data = data[(data['year'] >= start_year) & (data['year'] <= end_year)]
        
        self.logger.info(f"Filtered data: {len(countries)} countries, "
                        f"{end_year - start_year + 1} years, {len(data)} records")
        
        return data
    
    def get_time_series(self, country: str, interpolate: bool = True) -> pd.Series:
        """
        Extract time series for a single country with optional interpolation.
        
        Args:
            country: Country name
            interpolate: Whether to interpolate missing values
            
        Returns:
            Time series with years as index, population as values
        """
        country_data = self.get_country_data(country)
        
        if 'year' in country_data.columns and 'population' in country_data.columns:
            series = country_data.set_index('year')['population'].sort_index()
        else:
            # Handle wide format
            series = country_data.iloc[0] if len(country_data) > 0 else pd.Series()
        
        if interpolate and len(series) > 0:
            series = series.interpolate(method='linear')
        
        return series
    
    def get_growth_rates(self, country: Optional[str] = None) -> pd.DataFrame:
        """
        Calculate year-over-year growth rates.
        
        Args:
            country: Specific country (None for all countries)
            
        Returns:
            DataFrame with growth rates
        """
        if country:
            data = self.get_country_data(country)
        else:
            data = self._population_data.copy() if self._population_data is not None else self.load_population_data()
        
        if 'year' in data.columns and 'population' in data.columns:
            # Long format
            data = data.sort_values(['country', 'year'])
            data['growth_rate'] = data.groupby('country')['population'].pct_change() * 100
        else:
            # Wide format - calculate growth between consecutive year columns
            numeric_cols = data.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) > 1:
                growth_data = data[numeric_cols].pct_change(axis=1) * 100
                data = pd.concat([data.select_dtypes(exclude=[np.number]), growth_data], axis=1)
        
        return data
    
    def get_data_quality_report(self) -> Dict:
        """
        Generate comprehensive data quality assessment.
        
        Returns:
            Dictionary with quality metrics and recommendations
        """
        if self._population_data is None:
            self.load_population_data()
        
        data = self._population_data
        
        # Calculate quality metrics
        report = {
            'timestamp': datetime.now().isoformat(),
            'data_shape': data.shape,
            'completeness_percentage': self._calculate_completeness(data),
            'cache_performance': {
                'hits': self.cache_hits,
                'misses': self.cache_misses,
                'hit_rate': self.cache_hits / max(1, self.cache_hits + self.cache_misses) * 100
            }
        }
        
        if 'country' in data.columns:
            report['countries'] = {
                'total_countries': len(data['country'].unique()),
                'countries_with_recent_data': len(data[data['year'] >= 2020]['country'].unique()) if 'year' in data.columns else 'N/A'
            }
        
        if 'year' in data.columns:
            report['temporal_coverage'] = {
                'year_range': (int(data['year'].min()), int(data['year'].max())),
                'years_covered': len(data['year'].unique()),
                'data_recency': 2023 - int(data['year'].max()) if data['year'].max() < 2023 else 0
            }
        
        if 'population' in data.columns:
            report['population_statistics'] = {
                'total_records': len(data),
                'missing_values': int(data['population'].isnull().sum()),
                'zero_populations': int((data['population'] == 0).sum()),
                'negative_populations': int((data['population'] < 0).sum()),
                'max_population': int(data['population'].max()),
                'min_population': int(data['population'].min())
            }
        
        # Quality scoring
        completeness_score = min(100, report['completeness_percentage'])
        recency_score = max(0, 100 - report['temporal_coverage']['data_recency'] * 10) if 'temporal_coverage' in report else 100
        integrity_score = 100 - (report['population_statistics']['negative_populations'] * 5) if 'population_statistics' in report else 100
        
        report['quality_score'] = (completeness_score + recency_score + integrity_score) / 3
        
        # Generate recommendations
        recommendations = []
        if report['completeness_percentage'] < 95:
            recommendations.append("Consider data imputation for missing values")
        if 'temporal_coverage' in report and report['temporal_coverage']['data_recency'] > 2:
            recommendations.append("Update dataset with more recent data")
        if 'population_statistics' in report and report['population_statistics']['negative_populations'] > 0:
            recommendations.append("Investigate and correct negative population values")
        
        report['recommendations'] = recommendations
        
        # Terminal-friendly summary
        print("\n" + "="*50)
        print("📊 DATA QUALITY REPORT")
        print("="*50)
        print(f"📈 Overall Quality Score: {report['quality_score']:.1f}/100")
        print(f"📋 Data Shape: {report['data_shape'][0]:,} rows × {report['data_shape'][1]} columns")
        print(f"✅ Completeness: {report['completeness_percentage']:.1f}%")
        
        if 'countries' in report:
            print(f"🌍 Countries: {report['countries']['total_countries']}")
        
        if 'temporal_coverage' in report:
            year_range = report['temporal_coverage']['year_range']
            print(f"📅 Years: {year_range[0]}-{year_range[1]} ({report['temporal_coverage']['years_covered']} years)")
        
        if 'cache_performance' in report:
            hit_rate = report['cache_performance']['hit_rate']
            print(f"⚡ Cache Hit Rate: {hit_rate:.1f}%")
        
        if recommendations:
            print("\n💡 Recommendations:")
            for i, rec in enumerate(recommendations, 1):
                print(f"   {i}. {rec}")
        
        print("="*50)
        
        self._quality_report = report
        return report

# Example usage and testing
if __name__ == "__main__":
    # Test the data loader
    loader = PopulationDataLoader(data_dir="../../data")
    
    try:
        # Load data
        data = loader.load_population_data()
        print(f"✅ Successfully loaded data: {data.shape}")
        
        # Generate quality report
        quality_report = loader.get_data_quality_report()
        
        # Test country filtering
        if 'country' in data.columns:
            sample_countries = data['country'].unique()[:5]
            country_data = loader.get_country_data(list(sample_countries))
            print(f"✅ Country filtering test passed: {len(country_data)} records")
        
        # Test time series extraction
        if 'country' in data.columns:
            first_country = data['country'].iloc[0]
            time_series = loader.get_time_series(first_country)
            print(f"✅ Time series extraction test passed: {len(time_series)} data points")
        
        print("\n🎉 All tests passed! Data loader is ready for use.")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        raise
