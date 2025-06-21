"""
Click Tracking Service

Service for detailed click analytics and tracking.
"""
import logging
import hashlib
from firebase_admin import firestore
from datetime import datetime
from typing import Dict, Optional
import os

from .geolocation_service import GeolocationService

logger = logging.getLogger(__name__)

class ClickTrackingService:
    def __init__(self):
        self.db = firestore.client()
        self.clicks_collection = "link_clicks"
        self.geo_service = GeolocationService()
    
    def record_click(self, short_code: str, user_id: str, request_data: Dict) -> bool:
        """Record a detailed click event."""
        try:
            # Extract request information
            ip_address = self._get_client_ip(request_data)
            user_agent = request_data.get('user_agent', '')
            referrer = request_data.get('referrer', '')
            
            # Parse user agent for device info
            device_info = self._parse_user_agent(user_agent)
            
            # Hash IP for privacy
            ip_hash = self._hash_ip(ip_address) if ip_address else None
            
            # Create click record with enhanced device information
            click_data = {
                'short_code': short_code,
                'user_id': user_id,
                'clicked_at': firestore.SERVER_TIMESTAMP,
                'ip_hash': ip_hash,
                'user_agent': user_agent,
                'referrer': referrer,
                # Basic device info (backward compatibility)
                'device_type': device_info.get('device_type', 'Unknown'),
                'browser': device_info.get('browser', 'Unknown'),
                'os': device_info.get('os', 'Unknown'),
                # Enhanced device info (new fields)
                'device_model': device_info.get('device_model', 'Unknown'),
                'device_brand': device_info.get('device_brand', 'Unknown'),
                'browser_version': device_info.get('browser_version', 'Unknown'),
                'os_version': device_info.get('os_version', 'Unknown'),
                'created_at': firestore.SERVER_TIMESTAMP
            }
            
            # Add geolocation if available (optional)
            if ip_address:
                logger.info(f"Attempting geolocation lookup for IP: {ip_address}")
                geo_info = self._get_geolocation(ip_address)
                if geo_info:
                    click_data.update(geo_info)
                    logger.info(f"Added geolocation data: {geo_info}")
                else:
                    logger.info(f"No geolocation data found for IP: {ip_address}")
            else:
                logger.info("No IP address available for geolocation lookup")
            
            # Store click record
            self.db.collection(self.clicks_collection).add(click_data)
            logger.info(f"Recorded click for short_code: {short_code}")
            return True
            
        except Exception as e:
            logger.error(f"Error recording click: {e}")
            return False
    
    def _get_client_ip(self, request_data: Dict) -> Optional[str]:
        """Extract client IP from request."""
        # Check various headers for real IP
        ip_headers = [
            'X-Forwarded-For',
            'X-Real-IP',
            'X-Client-IP',
            'CF-Connecting-IP',  # Cloudflare
            'remote_addr'
        ]
        
        for header in ip_headers:
            ip = request_data.get(header)
            if ip:
                # Take first IP if comma-separated
                return ip.split(',')[0].strip()
        
        return None
    
    def _hash_ip(self, ip_address: str) -> str:
        """Hash IP address for privacy."""
        return hashlib.sha256(ip_address.encode()).hexdigest()[:16]
    
    def _parse_user_agent(self, user_agent: str) -> Dict:
        """Parse user agent string for comprehensive device information."""
        try:
            import re
            ua_lower = user_agent.lower()
            
            # Initialize result dictionary
            result = {
                'device_type': 'Unknown',
                'device_model': 'Unknown',
                'device_brand': 'Unknown',
                'browser': 'Unknown',
                'browser_version': 'Unknown',
                'os': 'Unknown',
                'os_version': 'Unknown'
            }
            
            # ===== DEVICE TYPE & MODEL DETECTION =====
            
            # iPhone Detection
            iphone_match = re.search(r'iphone.*?os (\d+)_(\d+)', ua_lower)
            if iphone_match or 'iphone' in ua_lower:
                result['device_type'] = 'Mobile'
                result['device_brand'] = 'Apple'
                result['os'] = 'iOS'
                
                # Detect specific iPhone model
                if 'iphone15' in ua_lower or 'iphone 15' in ua_lower:
                    result['device_model'] = 'iPhone 15'
                elif 'iphone14' in ua_lower or 'iphone 14' in ua_lower:
                    result['device_model'] = 'iPhone 14'
                elif 'iphone13' in ua_lower or 'iphone 13' in ua_lower:
                    result['device_model'] = 'iPhone 13'
                elif 'iphone12' in ua_lower or 'iphone 12' in ua_lower:
                    result['device_model'] = 'iPhone 12'
                elif 'iphone11' in ua_lower or 'iphone 11' in ua_lower:
                    result['device_model'] = 'iPhone 11'
                elif 'iphonex' in ua_lower or 'iphone x' in ua_lower:
                    result['device_model'] = 'iPhone X'
                elif 'iphone se' in ua_lower:
                    result['device_model'] = 'iPhone SE'
                else:
                    result['device_model'] = 'iPhone'
                
                if iphone_match:
                    result['os_version'] = f"{iphone_match.group(1)}.{iphone_match.group(2)}"
            
            # iPad Detection
            elif 'ipad' in ua_lower:
                result['device_type'] = 'Tablet'
                result['device_brand'] = 'Apple'
                result['device_model'] = 'iPad'
                result['os'] = 'iPadOS'
                
                # Detect specific iPad model
                if 'ipad pro' in ua_lower:
                    result['device_model'] = 'iPad Pro'
                elif 'ipad air' in ua_lower:
                    result['device_model'] = 'iPad Air'
                elif 'ipad mini' in ua_lower:
                    result['device_model'] = 'iPad Mini'
            
            # Android Device Detection
            elif 'android' in ua_lower:
                result['device_type'] = 'Mobile' if 'mobile' in ua_lower else 'Tablet'
                result['os'] = 'Android'
                
                # Extract Android version
                android_match = re.search(r'android (\d+(?:\.\d+)?)', ua_lower)
                if android_match:
                    result['os_version'] = android_match.group(1)
                
                # Detect device brand and model
                if 'samsung' in ua_lower:
                    result['device_brand'] = 'Samsung'
                    # Samsung Galaxy models
                    if 'galaxy s24' in ua_lower:
                        result['device_model'] = 'Galaxy S24'
                    elif 'galaxy s23' in ua_lower:
                        result['device_model'] = 'Galaxy S23'
                    elif 'galaxy s22' in ua_lower:
                        result['device_model'] = 'Galaxy S22'
                    elif 'galaxy s21' in ua_lower:
                        result['device_model'] = 'Galaxy S21'
                    elif 'galaxy note' in ua_lower:
                        result['device_model'] = 'Galaxy Note'
                    elif 'galaxy a' in ua_lower:
                        result['device_model'] = 'Galaxy A Series'
                    else:
                        result['device_model'] = 'Samsung Galaxy'
                
                elif 'pixel' in ua_lower:
                    result['device_brand'] = 'Google'
                    if 'pixel 8' in ua_lower:
                        result['device_model'] = 'Pixel 8'
                    elif 'pixel 7' in ua_lower:
                        result['device_model'] = 'Pixel 7'
                    elif 'pixel 6' in ua_lower:
                        result['device_model'] = 'Pixel 6'
                    else:
                        result['device_model'] = 'Google Pixel'
                
                elif 'oneplus' in ua_lower:
                    result['device_brand'] = 'OnePlus'
                    result['device_model'] = 'OnePlus'
                
                elif 'xiaomi' in ua_lower or 'mi ' in ua_lower:
                    result['device_brand'] = 'Xiaomi'
                    result['device_model'] = 'Xiaomi'
                
                elif 'huawei' in ua_lower:
                    result['device_brand'] = 'Huawei'
                    result['device_model'] = 'Huawei'
                
                else:
                    result['device_brand'] = 'Android'
                    result['device_model'] = 'Android Device'
            
            # Desktop/Laptop Detection
            elif any(os_name in ua_lower for os_name in ['windows', 'mac', 'linux']):
                result['device_type'] = 'Desktop'
                
                if 'windows' in ua_lower:
                    result['os'] = 'Windows'
                    result['device_brand'] = 'PC'
                    result['device_model'] = 'Windows PC'
                    
                    # Windows version detection
                    if 'windows nt 10.0' in ua_lower:
                        result['os_version'] = '10/11'
                    elif 'windows nt 6.3' in ua_lower:
                        result['os_version'] = '8.1'
                    elif 'windows nt 6.1' in ua_lower:
                        result['os_version'] = '7'
                
                elif 'mac' in ua_lower:
                    result['os'] = 'macOS'
                    result['device_brand'] = 'Apple'
                    
                    # Detect Mac model
                    if 'macbook pro' in ua_lower:
                        result['device_model'] = 'MacBook Pro'
                    elif 'macbook air' in ua_lower:
                        result['device_model'] = 'MacBook Air'
                    elif 'imac' in ua_lower:
                        result['device_model'] = 'iMac'
                    elif 'mac pro' in ua_lower:
                        result['device_model'] = 'Mac Pro'
                    elif 'mac studio' in ua_lower:
                        result['device_model'] = 'Mac Studio'
                    else:
                        result['device_model'] = 'Mac'
                    
                    # macOS version detection
                    macos_match = re.search(r'mac os x (\d+)_(\d+)', ua_lower)
                    if macos_match:
                        result['os_version'] = f"{macos_match.group(1)}.{macos_match.group(2)}"
                
                elif 'linux' in ua_lower:
                    result['os'] = 'Linux'
                    result['device_brand'] = 'PC'
                    result['device_model'] = 'Linux PC'
                    
                    # Linux distribution detection
                    if 'ubuntu' in ua_lower:
                        result['os_version'] = 'Ubuntu'
                    elif 'fedora' in ua_lower:
                        result['os_version'] = 'Fedora'
                    elif 'debian' in ua_lower:
                        result['os_version'] = 'Debian'
            
            # ===== BROWSER DETECTION =====
            
            # Chrome detection (must be before Safari since Chrome contains "Safari")
            if 'chrome' in ua_lower and 'edge' not in ua_lower:
                result['browser'] = 'Chrome'
                chrome_match = re.search(r'chrome/(\d+\.\d+)', ua_lower)
                if chrome_match:
                    result['browser_version'] = chrome_match.group(1)
            
            # Edge detection
            elif 'edge' in ua_lower or 'edg/' in ua_lower:
                result['browser'] = 'Edge'
                edge_match = re.search(r'edg?/(\d+\.\d+)', ua_lower)
                if edge_match:
                    result['browser_version'] = edge_match.group(1)
            
            # Firefox detection
            elif 'firefox' in ua_lower:
                result['browser'] = 'Firefox'
                firefox_match = re.search(r'firefox/(\d+\.\d+)', ua_lower)
                if firefox_match:
                    result['browser_version'] = firefox_match.group(1)
            
            # Safari detection (must be after Chrome/Edge)
            elif 'safari' in ua_lower:
                result['browser'] = 'Safari'
                safari_match = re.search(r'version/(\d+\.\d+)', ua_lower)
                if safari_match:
                    result['browser_version'] = safari_match.group(1)
            
            # Opera detection
            elif 'opera' in ua_lower or 'opr/' in ua_lower:
                result['browser'] = 'Opera'
                opera_match = re.search(r'(?:opera|opr)/(\d+\.\d+)', ua_lower)
                if opera_match:
                    result['browser_version'] = opera_match.group(1)
            
            # ===== FALLBACK FOR MOBILE/TABLET =====
            if result['device_type'] == 'Unknown':
                if 'mobile' in ua_lower:
                    result['device_type'] = 'Mobile'
                elif 'tablet' in ua_lower:
                    result['device_type'] = 'Tablet'
                else:
                    result['device_type'] = 'Desktop'
            
            return result
            
        except Exception as e:
            logger.error(f"Error parsing user agent: {e}")
            return {
                'device_type': 'Unknown',
                'device_model': 'Unknown',
                'device_brand': 'Unknown',
                'browser': 'Unknown',
                'browser_version': 'Unknown',
                'os': 'Unknown',
                'os_version': 'Unknown'
            }
    
    def _get_geolocation(self, ip_address: str) -> Optional[Dict]:
        """Get geolocation data from IP address."""
        try:
            location = self.geo_service.get_location_from_ip(ip_address)
            if location and location.get('country') != 'Unknown':
                return {
                    'country': location.get('country', 'Unknown'),
                    'country_code': location.get('country_code', 'XX'),
                    'city': location.get('city', 'Unknown'),
                    'region': location.get('region', 'Unknown'),
                    'latitude': location.get('latitude'),
                    'longitude': location.get('longitude'),
                }
            else:
                # For development/testing with localhost IPs, add a development flag
                if ip_address in ['127.0.0.1', 'localhost', '::1']:
                    # Enable for development testing with environment variable
                    if os.getenv('ENABLE_DEV_GEOLOCATION', 'false').lower() == 'true':
                        return {
                            'country': 'Development',
                            'country_code': 'DEV', 
                            'city': 'Local',
                            'region': 'Testing',
                            'latitude': None,
                            'longitude': None,
                        }
                return None
        except Exception as e:
            logger.error(f"Error getting geolocation for IP {ip_address}: {e}")
            return None
    
    def get_clicks_for_link(self, short_code: str) -> list:
        """Get all clicks for a specific short link."""
        try:
            clicks = []
            docs = self.db.collection(self.clicks_collection)\
                          .where('short_code', '==', short_code)\
                          .order_by('clicked_at', direction=firestore.Query.DESCENDING)\
                          .stream()
            
            for doc in docs:
                data = doc.to_dict()
                data['id'] = doc.id
                clicks.append(data)
            
            return clicks
        except Exception as e:
            logger.error(f"Error fetching clicks for {short_code}: {e}")
            return []
    
    def get_click_analytics(self, short_code: str) -> Dict:
        """Get analytics summary for a short link."""
        try:
            clicks = self.get_clicks_for_link(short_code)
            
            if not clicks:
                return {
                    'total_clicks': 0,
                    'unique_visitors': 0,
                    'top_countries': [],
                    'device_breakdown': {},
                    'device_model_breakdown': {},
                    'device_brand_breakdown': {},
                    'browser_breakdown': {},
                    'os_breakdown': {},
                    'recent_clicks': []
                }
            
            # Analyze clicks
            unique_ips = set()
            countries = {}
            devices = {}
            device_models = {}
            device_brands = {}
            browsers = {}
            operating_systems = {}
            
            for click in clicks:
                # Unique visitors (based on IP hash)
                if click.get('ip_hash'):
                    unique_ips.add(click['ip_hash'])
                
                # Country stats
                country = click.get('country', 'Unknown')
                countries[country] = countries.get(country, 0) + 1
                
                # Device stats
                device = click.get('device_type', 'Unknown')
                devices[device] = devices.get(device, 0) + 1
                
                # Device model stats
                device_model = click.get('device_model', 'Unknown')
                device_models[device_model] = device_models.get(device_model, 0) + 1
                
                # Device brand stats
                device_brand = click.get('device_brand', 'Unknown')
                device_brands[device_brand] = device_brands.get(device_brand, 0) + 1
                
                # Browser stats
                browser = click.get('browser', 'Unknown')
                browsers[browser] = browsers.get(browser, 0) + 1
                
                # OS stats
                os_name = click.get('os', 'Unknown')
                operating_systems[os_name] = operating_systems.get(os_name, 0) + 1
            
            return {
                'total_clicks': len(clicks),
                'unique_visitors': len(unique_ips),
                'top_countries': sorted(countries.items(), key=lambda x: x[1], reverse=True)[:5],
                'device_breakdown': devices,
                'device_model_breakdown': sorted(device_models.items(), key=lambda x: x[1], reverse=True)[:10],
                'device_brand_breakdown': sorted(device_brands.items(), key=lambda x: x[1], reverse=True)[:10],
                'browser_breakdown': browsers,
                'os_breakdown': operating_systems,
                'recent_clicks': clicks[:10]  # Last 10 clicks
            }
            
        except Exception as e:
            logger.error(f"Error getting analytics for {short_code}: {e}")
            return {}
    
    def get_recent_clicks_for_user(self, user_id: str, limit: int = 50, offset: int = 0) -> dict:
        """Get recent clicks for all links belonging to a user with pagination."""
        try:
            # Query clicks for this user, ordered by clicked_at descending
            clicks_ref = self.db.collection(self.clicks_collection)
            query = clicks_ref.where('user_id', '==', user_id).order_by('clicked_at', direction=firestore.Query.DESCENDING)
            
            # Get total count for pagination info
            all_docs = list(query.stream())
            total_clicks = len(all_docs)
            
            # Apply pagination
            paginated_docs = all_docs[offset:offset + limit]
            
            clicks = []
            for doc in paginated_docs:
                click_data = doc.to_dict()
                click_data['id'] = doc.id
                
                # Format clicked_at for display
                if 'clicked_at' in click_data:
                    click_data['clicked_at_display'] = click_data['clicked_at'].strftime('%Y-%m-%d %H:%M UTC')
                
                # Create short URL display
                click_data['short_url_display'] = f"{self._get_base_url()}/{click_data.get('short_code', '')}"
                
                clicks.append(click_data)
            
            return {
                'clicks': clicks,
                'total_count': total_clicks,
                'current_page_count': len(clicks),
                'has_more': offset + limit < total_clicks,
                'offset': offset,
                'limit': limit
            }
            
        except Exception as e:
            logger.error(f"Error fetching recent clicks for user {user_id}: {e}")
            return {
                'clicks': [],
                'total_count': 0,
                'current_page_count': 0,
                'has_more': False,
                'offset': 0,
                'limit': limit
            }
    
    def _get_base_url(self) -> str:
        """Get the base URL for short links."""
        # This should match your domain configuration
        return "https://your-domain.com"  # TODO: Make this configurable
