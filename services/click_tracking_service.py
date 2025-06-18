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

logger = logging.getLogger(__name__)

class ClickTrackingService:
    def __init__(self):
        self.db = firestore.client()
        self.clicks_collection = "link_clicks"
    
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
            
            # Create click record
            click_data = {
                'short_code': short_code,
                'user_id': user_id,
                'clicked_at': firestore.SERVER_TIMESTAMP,
                'ip_hash': ip_hash,
                'user_agent': user_agent,
                'referrer': referrer,
                'device_type': device_info.get('device_type', 'Unknown'),
                'browser': device_info.get('browser', 'Unknown'),
                'os': device_info.get('os', 'Unknown'),
                'created_at': firestore.SERVER_TIMESTAMP
            }
            
            # Add geolocation if available (optional)
            if ip_address:
                geo_info = self._get_geolocation(ip_address)
                if geo_info:
                    click_data.update(geo_info)
            
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
        """Parse user agent string for device information."""
        try:
            # Simple user agent parsing without external dependencies
            ua_lower = user_agent.lower()
            
            # Determine device type
            if 'mobile' in ua_lower or 'android' in ua_lower or 'iphone' in ua_lower:
                device_type = 'Mobile'
            elif 'tablet' in ua_lower or 'ipad' in ua_lower:
                device_type = 'Tablet'
            else:
                device_type = 'Desktop'
            
            # Determine browser
            browser = 'Unknown'
            if 'chrome' in ua_lower and 'edge' not in ua_lower:
                browser = 'Chrome'
            elif 'firefox' in ua_lower:
                browser = 'Firefox'
            elif 'safari' in ua_lower and 'chrome' not in ua_lower:
                browser = 'Safari'
            elif 'edge' in ua_lower:
                browser = 'Edge'
            elif 'opera' in ua_lower:
                browser = 'Opera'
            
            # Determine OS
            os_name = 'Unknown'
            if 'windows' in ua_lower:
                os_name = 'Windows'
            elif 'mac' in ua_lower:
                os_name = 'macOS'
            elif 'linux' in ua_lower:
                os_name = 'Linux'
            elif 'android' in ua_lower:
                os_name = 'Android'
            elif 'ios' in ua_lower or 'iphone' in ua_lower or 'ipad' in ua_lower:
                os_name = 'iOS'
            
            return {
                'device_type': device_type,
                'browser': browser,
                'os': os_name
            }
        except Exception as e:
            logger.error(f"Error parsing user agent: {e}")
            return {
                'device_type': 'Unknown',
                'browser': 'Unknown',
                'os': 'Unknown'
            }
    
    def _get_geolocation(self, ip_address: str) -> Optional[Dict]:
        """Get geolocation data from IP address."""
        try:
            # For now, we'll skip geolocation to avoid external dependencies
            # This can be added later with proper API integration
            return None
        except Exception as e:
            logger.error(f"Error getting geolocation: {e}")
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
                    'browser_breakdown': {},
                    'recent_clicks': []
                }
            
            # Analyze clicks
            unique_ips = set()
            countries = {}
            devices = {}
            browsers = {}
            
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
                
                # Browser stats
                browser = click.get('browser', 'Unknown').split()[0]  # Just browser name
                browsers[browser] = browsers.get(browser, 0) + 1
            
            return {
                'total_clicks': len(clicks),
                'unique_visitors': len(unique_ips),
                'top_countries': sorted(countries.items(), key=lambda x: x[1], reverse=True)[:5],
                'device_breakdown': devices,
                'browser_breakdown': browsers,
                'recent_clicks': clicks[:10]  # Last 10 clicks
            }
            
        except Exception as e:
            logger.error(f"Error getting analytics for {short_code}: {e}")
            return {}
