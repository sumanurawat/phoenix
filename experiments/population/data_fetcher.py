"""
World Bank API Data Fetcher
Handles all API calls to World Bank API with rate limiting and error handling.
"""

import requests
import json
import time
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import os
from tqdm import tqdm

class WorldBankAPI:
    """
    A robust client for the World Bank API with rate limiting and error handling.
    """
    
    def __init__(self, base_url: str = "https://api.worldbank.org/v2/", max_requests_per_second: int = 5):
        self.base_url = base_url
        self.max_requests_per_second = max_requests_per_second
        self.last_request_time = 0
        self.session = requests.Session()
        
        # Set up logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)
        
        # Ensure data directory exists
        os.makedirs('data', exist_ok=True)
    
    def _rate_limit(self):
        """Implement rate limiting to respect API limits."""
        time_since_last_request = time.time() - self.last_request_time
        min_interval = 1.0 / self.max_requests_per_second
        
        if time_since_last_request < min_interval:
            time.sleep(min_interval - time_since_last_request)
        
        self.last_request_time = time.time()
    
    def _make_request(self, endpoint: str, params: Dict[str, Any] = None, max_retries: int = 3) -> Optional[Dict]:
        """
        Make a request to the World Bank API with retry logic.
        
        Args:
            endpoint: API endpoint
            params: Query parameters
            max_retries: Maximum number of retry attempts
            
        Returns:
            JSON response data or None if failed
        """
        if params is None:
            params = {}
        
        # Default parameters for JSON format
        params.update({
            'format': 'json',
            'per_page': 300
        })
        
        url = f"{self.base_url}{endpoint}"
        
        for attempt in range(max_retries):
            try:
                self._rate_limit()
                
                response = self.session.get(url, params=params, timeout=30)
                response.raise_for_status()
                
                data = response.json()
                self.logger.info(f"Successfully fetched: {endpoint}")
                return data
                
            except requests.exceptions.RequestException as e:
                self.logger.warning(f"Attempt {attempt + 1} failed for {endpoint}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    self.logger.error(f"All attempts failed for {endpoint}")
                    return None
    
    def get_all_countries(self) -> bool:
        """
        Fetch all countries with their metadata.
        
        Returns:
            True if successful, False otherwise
        """
        self.logger.info("Fetching all countries metadata...")
        
        all_countries = []
        page = 1
        
        while True:
            data = self._make_request("country", {"page": page, "per_page": 300})
            if not data or len(data) < 2:
                break
            
            countries_data = data[1]
            if not countries_data:
                break
            
            all_countries.extend(countries_data)
            
            # Check if we have more pages
            pagination_info = data[0]
            if pagination_info['page'] >= pagination_info['pages']:
                break
            
            page += 1
        
        # Save to file
        with open('data/countries_metadata.json', 'w') as f:
            json.dump(all_countries, f, indent=2)
        
        self.logger.info(f"Saved {len(all_countries)} countries to data/countries_metadata.json")
        return True
    
    def get_population_current(self) -> bool:
        """
        Get most recent population for all countries.
        
        Returns:
            True if successful, False otherwise
        """
        self.logger.info("Fetching current population data...")
        
        data = self._make_request("country/all/indicator/SP.POP.TOTL", {
            "date": "2023",
            "per_page": 300
        })
        
        if not data:
            return False
        
        population_data = data[1] if len(data) > 1 else []
        
        # Save to file
        with open('data/population_current.json', 'w') as f:
            json.dump(population_data, f, indent=2)
        
        self.logger.info(f"Saved current population data for {len(population_data)} entries")
        return True
    
    def get_population_timeseries(self) -> bool:
        """
        Get population timeseries from 1960-2023 for all countries.
        
        Returns:
            True if successful, False otherwise
        """
        self.logger.info("Fetching population timeseries (1960-2023)...")
        
        all_data = []
        page = 1
        
        while True:
            data = self._make_request("country/all/indicator/SP.POP.TOTL", {
                "date": "1960:2023",
                "page": page,
                "per_page": 1000
            })
            
            if not data or len(data) < 2:
                break
            
            page_data = data[1]
            if not page_data:
                break
            
            all_data.extend(page_data)
            
            # Check pagination
            pagination_info = data[0]
            self.logger.info(f"Fetched page {page} of {pagination_info['pages']}")
            
            if pagination_info['page'] >= pagination_info['pages']:
                break
            
            page += 1
        
        # Save to file
        with open('data/population_timeseries.json', 'w') as f:
            json.dump(all_data, f, indent=2)
        
        self.logger.info(f"Saved {len(all_data)} population timeseries records")
        return True
    
    def get_population_by_regions(self) -> bool:
        """
        Get aggregated population data for regions.
        
        Returns:
            True if successful, False otherwise
        """
        self.logger.info("Fetching regional population data...")
        
        # Get regional aggregates (these have special country codes)
        regional_codes = [
            "EAS",  # East Asia & Pacific
            "ECS",  # Europe & Central Asia
            "LCN",  # Latin America & Caribbean
            "MEA",  # Middle East & North Africa
            "NAC",  # North America
            "SAS",  # South Asia
            "SSF",  # Sub-Saharan Africa
            "WLD",  # World
        ]
        
        all_regional_data = []
        
        for region_code in tqdm(regional_codes, desc="Fetching regional data"):
            data = self._make_request(f"country/{region_code}/indicator/SP.POP.TOTL", {
                "date": "1960:2023"
            })
            
            if data and len(data) > 1:
                region_data = data[1]
                all_regional_data.extend(region_data)
        
        # Save to file
        with open('data/population_regions.json', 'w') as f:
            json.dump(all_regional_data, f, indent=2)
        
        self.logger.info(f"Saved {len(all_regional_data)} regional population records")
        return True
    
    def get_related_indicators(self) -> bool:
        """
        Fetch related population indicators for top 20 populous countries.
        
        Returns:
            True if successful, False otherwise
        """
        self.logger.info("Fetching related indicators...")
        
        # Top 20 most populous countries (approximate)
        top_countries = [
            "CHN", "IND", "USA", "IDN", "PAK", "BRA", "NGA", "BGD", 
            "RUS", "MEX", "JPN", "ETH", "PHL", "EGY", "VNM", "TUR", 
            "IRN", "DEU", "THA", "GBR"
        ]
        
        indicators = {
            "SP.POP.GROW": "population_growth.json",
            "SP.URB.TOTL": "urban_population.json", 
            "SP.RUR.TOTL": "rural_population.json",
            "SP.POP.DPND": "age_dependency_ratio.json",
            "EN.POP.DNST": "population_density.json"
        }
        
        for indicator_code, filename in indicators.items():
            self.logger.info(f"Fetching {indicator_code}...")
            
            countries_str = ";".join(top_countries)
            data = self._make_request(f"country/{countries_str}/indicator/{indicator_code}", {
                "date": "2000:2023"
            })
            
            if data and len(data) > 1:
                indicator_data = data[1]
                
                with open(f'data/{filename}', 'w') as f:
                    json.dump(indicator_data, f, indent=2)
                
                self.logger.info(f"Saved {len(indicator_data)} records for {indicator_code}")
            
            time.sleep(0.5)  # Extra delay for multiple indicators
        
        return True
    
    def get_data_availability_matrix(self) -> bool:
        """
        Check data availability for each country across years.
        
        Returns:
            True if successful, False otherwise
        """
        self.logger.info("Creating data availability matrix...")
        
        # Load population timeseries if it exists
        try:
            with open('data/population_timeseries.json', 'r') as f:
                timeseries_data = json.load(f)
        except FileNotFoundError:
            self.logger.error("Population timeseries data not found. Run get_population_timeseries first.")
            return False
        
        # Create availability matrix
        availability_matrix = {}
        
        for record in timeseries_data:
            country_code = record.get('countryiso3code', record.get('country', {}).get('id', 'Unknown'))
            year = record.get('date')
            value = record.get('value')
            
            if country_code not in availability_matrix:
                availability_matrix[country_code] = {}
            
            availability_matrix[country_code][year] = 1 if value is not None else 0
        
        # Save matrix
        with open('data/data_availability_matrix.json', 'w') as f:
            json.dump(availability_matrix, f, indent=2)
        
        self.logger.info(f"Created availability matrix for {len(availability_matrix)} countries")
        return True


def main():
    """Main function to fetch all data."""
    api = WorldBankAPI()
    
    print("Starting World Bank data collection...")
    print("=" * 50)
    
    tasks = [
        ("Countries metadata", api.get_all_countries),
        ("Current population", api.get_population_current),
        ("Population timeseries", api.get_population_timeseries),
        ("Regional population", api.get_population_by_regions),
        ("Related indicators", api.get_related_indicators),
        ("Data availability matrix", api.get_data_availability_matrix),
    ]
    
    results = {}
    
    for task_name, task_func in tasks:
        print(f"\n{task_name}...")
        start_time = time.time()
        success = task_func()
        end_time = time.time()
        
        results[task_name] = {
            "success": success,
            "duration": end_time - start_time
        }
        
        status = "✓" if success else "✗"
        print(f"{status} {task_name} completed in {end_time - start_time:.2f}s")
    
    print("\n" + "=" * 50)
    print("Data collection summary:")
    for task_name, result in results.items():
        status = "✓" if result["success"] else "✗"
        print(f"{status} {task_name}: {result['duration']:.2f}s")
    
    print(f"\nTotal time: {sum(r['duration'] for r in results.values()):.2f}s")
    print("Data saved to ./data/ directory")


if __name__ == "__main__":
    main()
