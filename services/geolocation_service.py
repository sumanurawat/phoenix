"""
Geolocation service for detecting location from IP addresses.
Uses free geolocation APIs with fallback options.
"""

import requests
import logging
from typing import Dict, Optional
import hashlib
import time

logger = logging.getLogger(__name__)

class GeolocationService:
    """Service for detecting user location from IP addresses."""
    
    def __init__(self):
        self.cache = {}  # Simple in-memory cache
        self.cache_ttl = 3600  # 1 hour cache
        
        # Free geolocation APIs (in order of preference)
        self.apis = [
            {
                'name': 'ipapi.co',
                'url': 'https://ipapi.co/{ip}/json/',
                'free_limit': 1000,  # per day
                'fields': {
                    'country': 'country_name',
                    'country_code': 'country_code',
                    'city': 'city',
                    'region': 'region',
                    'latitude': 'latitude',
                    'longitude': 'longitude',
                    'timezone': 'timezone'
                }
            },
            {
                'name': 'ip-api.com',
                'url': 'http://ip-api.com/json/{ip}',
                'free_limit': 1000,  # per minute
                'fields': {
                    'country': 'country',
                    'country_code': 'countryCode', 
                    'city': 'city',
                    'region': 'regionName',
                    'latitude': 'lat',
                    'longitude': 'lon',
                    'timezone': 'timezone'
                }
            },
            {
                'name': 'ipinfo.io',
                'url': 'https://ipinfo.io/{ip}/json',
                'free_limit': 50000,  # per month
                'fields': {
                    'country': 'country',
                    'city': 'city',
                    'region': 'region',
                    'latitude': None,  # Requires parsing loc field
                    'longitude': None,
                    'timezone': 'timezone'
                }
            }
        ]
    
    def get_location_from_ip(self, ip_address: str) -> Dict[str, str]:
        """
        Get location information from IP address.
        Returns dict with country, city, region, etc.
        """
        if not ip_address or ip_address in ['127.0.0.1', 'localhost', '::1']:
            return self._get_default_location()
        
        # Check cache first
        cache_key = self._get_cache_key(ip_address)
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            return cached_result
        
        # Try each API until one works
        for api in self.apis:
            try:
                location = self._query_api(api, ip_address)
                if location and location.get('country'):
                    # Cache the result
                    self._cache_result(cache_key, location)
                    return location
            except Exception as e:
                logger.warning(f"Failed to get location from {api['name']}: {e}")
                continue
        
        # If all APIs fail, return default
        default_location = self._get_default_location()
        self._cache_result(cache_key, default_location)
        return default_location
    
    def _query_api(self, api: dict, ip_address: str) -> Optional[Dict[str, str]]:
        """Query a specific geolocation API."""
        url = api['url'].format(ip=ip_address)
        
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            # Handle API-specific error responses
            if api['name'] == 'ip-api.com' and data.get('status') == 'fail':
                return None
            
            # Map API response to our standard format
            location = {}
            for our_field, api_field in api['fields'].items():
                if api_field and api_field in data:
                    value = data[api_field]
                    if value and value != 'Unknown':
                        location[our_field] = str(value)
            
            # Special handling for ipinfo.io coordinates
            if api['name'] == 'ipinfo.io' and 'loc' in data:
                try:
                    lat, lon = data['loc'].split(',')
                    location['latitude'] = lat.strip()
                    location['longitude'] = lon.strip()
                except (ValueError, AttributeError):
                    pass
            
            return location
            
        except requests.RequestException as e:
            logger.warning(f"Request failed for {api['name']}: {e}")
            return None
        except (ValueError, KeyError) as e:
            logger.warning(f"Invalid response from {api['name']}: {e}")
            return None
    
    def _get_cache_key(self, ip_address: str) -> str:
        """Generate cache key from IP address."""
        return hashlib.md5(ip_address.encode()).hexdigest()
    
    def _get_from_cache(self, cache_key: str) -> Optional[Dict[str, str]]:
        """Get location from cache if not expired."""
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if time.time() - timestamp < self.cache_ttl:
                return cached_data
            else:
                # Remove expired entry
                del self.cache[cache_key]
        return None
    
    def _cache_result(self, cache_key: str, location: Dict[str, str]):
        """Cache location result with timestamp."""
        self.cache[cache_key] = (location, time.time())
        
        # Simple cache cleanup - remove old entries if cache gets too large
        if len(self.cache) > 1000:
            # Remove oldest 10% of entries
            oldest_keys = sorted(self.cache.keys(), 
                               key=lambda k: self.cache[k][1])[:100]
            for key in oldest_keys:
                del self.cache[key]
    
    def _get_default_location(self) -> Dict[str, str]:
        """Return default location when detection fails."""
        return {
            'country': 'Unknown',
            'country_code': 'XX',
            'city': 'Unknown',
            'region': 'Unknown'
        }
    
    def get_location_display(self, location: Dict[str, str]) -> str:
        """Get a human-readable location string."""
        if not location or location.get('country') == 'Unknown':
            return 'Unknown'
        
        parts = []
        
        # Add city if available
        if location.get('city') and location['city'] != 'Unknown':
            parts.append(location['city'])
        
        # Add region if available and different from city
        if (location.get('region') and 
            location['region'] != 'Unknown' and 
            location['region'] != location.get('city')):
            parts.append(location['region'])
        
        # Always add country
        if location.get('country') and location['country'] != 'Unknown':
            parts.append(location['country'])
        
        return ', '.join(parts) if parts else 'Unknown'
