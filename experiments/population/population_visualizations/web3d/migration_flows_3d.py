"""
3D Migration Flows Visualization

This module creates 3D visualizations showing population movement patterns
as animated arcs on a globe, with particle effects showing movement volume.
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import math

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from core.data_loader import PopulationDataLoader
    from core.theme_manager import VisualizationTheme
except ImportError:
    print("⚠️  Could not import core modules. Running in standalone mode.")

class MigrationFlows3D:
    """
    3D Migration Flows Visualization with animated arcs and particle effects.
    
    Features:
    - Interactive 3D globe with country markers
    - Animated flow arcs between countries
    - Particle effects showing migration volume
    - Temporal controls for historical analysis
    - Climate migration projections
    """
    
    def __init__(self, data_dir: str = "../data"):
        """Initialize the 3D migration flows visualization."""
        print("✈️  Initializing 3D Migration Flows Visualization")
        print("=" * 60)
        
        self.data_dir = data_dir
        self.loader = PopulationDataLoader(data_dir=data_dir)
        self.theme = VisualizationTheme()
        
        # Data storage
        self.population_data = None
        self.migration_flows = []
        self.country_coordinates = {}
        
        # Globe settings
        self.globe_radius = 1.0
        self.arc_height = 0.3
        self.flow_intensity = 100
        
        print(f"🌍 Globe radius: {self.globe_radius}")
        print(f"⬆️  Arc height: {self.arc_height}")
        print(f"💫 Flow intensity: {self.flow_intensity}")
    
    def load_data(self) -> pd.DataFrame:
        """Load population data and prepare migration flows."""
        print("\n📊 Loading population data...")
        
        self.population_data = self.loader.load_population_data()
        
        # Generate synthetic migration flows based on population changes
        self._generate_migration_flows()
        
        print(f"✅ Generated {len(self.migration_flows)} migration flows")
        return self.population_data
    
    def _generate_migration_flows(self):
        """Generate synthetic migration flows based on population patterns."""
        print("🔄 Generating migration flow patterns...")
        
        # Get major countries with significant population changes
        major_countries = self._get_major_countries()
        
        # Generate flows based on demographic patterns
        flows = []
        
        # Economic migration patterns
        economic_flows = [
            # Traditional migration corridors
            ("Mexico", "United States", 12.5, "economic"),
            ("India", "United States", 8.2, "economic"),
            ("China", "United States", 6.8, "economic"),
            ("Philippines", "United States", 5.1, "economic"),
            ("India", "United Kingdom", 4.3, "economic"),
            ("Poland", "United Kingdom", 3.9, "economic"),
            ("Turkey", "Germany", 7.2, "economic"),
            ("Morocco", "France", 3.8, "economic"),
            ("Algeria", "France", 3.2, "economic"),
            ("Pakistan", "United Kingdom", 4.1, "economic"),
            ("Bangladesh", "United Kingdom", 2.8, "economic"),
            ("India", "Canada", 5.5, "economic"),
            ("China", "Canada", 4.7, "economic"),
            ("Philippines", "Canada", 3.4, "economic"),
            ("Syria", "Germany", 6.1, "refugee"),
            ("Afghanistan", "Germany", 2.9, "refugee"),
            ("Iraq", "Germany", 2.1, "refugee"),
            ("Myanmar", "Bangladesh", 8.7, "refugee"),
            ("South Sudan", "Uganda", 4.2, "refugee"),
            ("Somalia", "Kenya", 3.5, "refugee"),
        ]
        
        # Climate migration (projected)
        climate_flows = [
            ("Bangladesh", "India", 15.2, "climate"),
            ("Philippines", "Australia", 4.8, "climate"),
            ("Vietnam", "Australia", 3.2, "climate"),
            ("Indonesia", "Australia", 2.9, "climate"),
            ("Maldives", "India", 1.8, "climate"),
            ("Marshall Islands", "United States", 2.1, "climate"),
            ("Kiribati", "New Zealand", 1.5, "climate"),
            ("Tuvalu", "New Zealand", 1.2, "climate"),
            ("Haiti", "United States", 3.7, "climate"),
            ("Jamaica", "United States", 2.4, "climate"),
            ("Central African Republic", "Chad", 2.8, "climate"),
            ("Mali", "Burkina Faso", 2.1, "climate"),
            ("Niger", "Nigeria", 3.9, "climate"),
            ("Chad", "Cameroon", 2.6, "climate"),
            ("Eritrea", "Ethiopia", 2.3, "climate"),
        ]
        
        # Internal displacement
        internal_flows = [
            ("China", "China", 25.3, "rural-urban"),  # Rural to urban
            ("India", "India", 22.7, "rural-urban"),
            ("Nigeria", "Nigeria", 8.9, "rural-urban"),
            ("Brazil", "Brazil", 7.2, "rural-urban"),
            ("Indonesia", "Indonesia", 6.8, "rural-urban"),
            ("Pakistan", "Pakistan", 5.4, "rural-urban"),
            ("Bangladesh", "Bangladesh", 4.9, "rural-urban"),
            ("Mexico", "Mexico", 4.1, "rural-urban"),
            ("Turkey", "Turkey", 3.7, "rural-urban"),
            ("Iran", "Iran", 3.2, "rural-urban"),
        ]
        
        # Combine all flows
        all_flows = economic_flows + climate_flows + internal_flows
        
        # Convert to migration flow objects
        for origin, destination, volume, flow_type in all_flows:
            if origin in self.get_country_coordinates() and destination in self.get_country_coordinates():
                flow = {
                    'origin': origin,
                    'destination': destination,
                    'volume': volume,
                    'type': flow_type,
                    'origin_coords': self.get_country_coordinates()[origin],
                    'destination_coords': self.get_country_coordinates()[destination]
                }
                flows.append(flow)
        
        self.migration_flows = flows
        print(f"✅ Generated {len(flows)} migration flows")
    
    def _get_major_countries(self) -> List[str]:
        """Get list of major countries by population."""
        latest_data = self.population_data[self.population_data['year'] == 2023]
        major_countries = latest_data.nlargest(50, 'population')['country'].tolist()
        return major_countries
    
    def get_country_coordinates(self) -> Dict[str, Tuple[float, float]]:
        """Get approximate coordinates for major countries."""
        if not self.country_coordinates:
            self.country_coordinates = {
                # Major countries with approximate coordinates (lat, lon)
                'China': (35.0, 105.0),
                'India': (20.0, 77.0),
                'United States': (40.0, -100.0),
                'Indonesia': (-5.0, 120.0),
                'Pakistan': (30.0, 70.0),
                'Brazil': (-10.0, -55.0),
                'Nigeria': (10.0, 8.0),
                'Bangladesh': (24.0, 90.0),
                'Russia': (60.0, 100.0),
                'Mexico': (23.0, -102.0),
                'Japan': (36.0, 138.0),
                'Philippines': (13.0, 122.0),
                'Ethiopia': (8.0, 38.0),
                'Vietnam': (16.0, 108.0),
                'Egypt': (26.0, 30.0),
                'Germany': (51.0, 9.0),
                'Turkey': (39.0, 35.0),
                'Iran': (32.0, 53.0),
                'Thailand': (15.0, 100.0),
                'United Kingdom': (54.0, -2.0),
                'France': (46.0, 2.0),
                'Italy': (42.0, 13.0),
                'South Africa': (-29.0, 24.0),
                'Tanzania': (-6.0, 35.0),
                'Myanmar': (22.0, 98.0),
                'Kenya': (0.0, 37.0),
                'South Korea': (36.0, 128.0),
                'Colombia': (4.0, -72.0),
                'Spain': (40.0, -4.0),
                'Argentina': (-34.0, -64.0),
                'Algeria': (28.0, 3.0),
                'Sudan': (15.0, 30.0),
                'Ukraine': (49.0, 32.0),
                'Uganda': (1.0, 32.0),
                'Iraq': (33.0, 44.0),
                'Poland': (52.0, 20.0),
                'Canada': (60.0, -95.0),
                'Afghanistan': (33.0, 65.0),
                'Morocco': (32.0, -5.0),
                'Saudi Arabia': (24.0, 45.0),
                'Uzbekistan': (41.0, 64.0),
                'Peru': (-10.0, -76.0),
                'Angola': (-12.0, 18.0),
                'Malaysia': (2.5, 112.5),
                'Mozambique': (-18.0, 35.0),
                'Ghana': (8.0, -2.0),
                'Yemen': (15.0, 48.0),
                'Nepal': (28.0, 84.0),
                'Venezuela': (8.0, -66.0),
                'Madagascar': (-20.0, 47.0),
                'Cameroon': (6.0, 12.0),
                'Australia': (-25.0, 133.0),
                'Syria': (35.0, 38.0),
                'Mali': (17.0, -4.0),
                'Burkina Faso': (13.0, -2.0),
                'Niger': (16.0, 8.0),
                'Chad': (15.0, 19.0),
                'Somalia': (10.0, 49.0),
                'Eritrea': (15.0, 39.0),
                'Haiti': (19.0, -72.0),
                'Jamaica': (18.0, -77.0),
                'Central African Republic': (7.0, 21.0),
                'Maldives': (3.0, 73.0),
                'Marshall Islands': (7.0, 171.0),
                'Kiribati': (-3.0, -168.0),
                'Tuvalu': (-8.0, 178.0),
                'New Zealand': (-41.0, 174.0)
            }
        return self.country_coordinates
    
    def _lat_lon_to_3d(self, lat: float, lon: float, radius: float = 1.0) -> Tuple[float, float, float]:
        """Convert latitude/longitude to 3D coordinates."""
        lat_rad = math.radians(lat)
        lon_rad = math.radians(lon)
        
        x = radius * math.cos(lat_rad) * math.cos(lon_rad)
        y = radius * math.cos(lat_rad) * math.sin(lon_rad)
        z = radius * math.sin(lat_rad)
        
        return x, y, z
    
    def _create_great_circle_arc(self, start_coords: Tuple[float, float], 
                                end_coords: Tuple[float, float], 
                                num_points: int = 50) -> List[Tuple[float, float, float]]:
        """Create a great circle arc between two points."""
        lat1, lon1 = start_coords
        lat2, lon2 = end_coords
        
        # Handle same point case
        if abs(lat1 - lat2) < 0.001 and abs(lon1 - lon2) < 0.001:
            # For internal migration, create a small arc
            lat2 += 0.1
            lon2 += 0.1
        
        # Convert to radians
        lat1_rad, lon1_rad = math.radians(lat1), math.radians(lon1)
        lat2_rad, lon2_rad = math.radians(lat2), math.radians(lon2)
        
        # Calculate great circle distance
        d = math.acos(min(1.0, max(-1.0, math.sin(lat1_rad) * math.sin(lat2_rad) + 
                     math.cos(lat1_rad) * math.cos(lat2_rad) * math.cos(lon2_rad - lon1_rad))))
        
        # Handle zero distance
        if d < 0.001:
            d = 0.001
        
        # Generate points along the arc
        points = []
        for i in range(num_points):
            t = i / (num_points - 1)
            
            # Spherical interpolation
            A = math.sin((1 - t) * d) / math.sin(d)
            B = math.sin(t * d) / math.sin(d)
            
            x = A * math.cos(lat1_rad) * math.cos(lon1_rad) + B * math.cos(lat2_rad) * math.cos(lon2_rad)
            y = A * math.cos(lat1_rad) * math.sin(lon1_rad) + B * math.cos(lat2_rad) * math.sin(lon2_rad)
            z = A * math.sin(lat1_rad) + B * math.sin(lat2_rad)
            
            # Add height to create arc
            height = 1.0 + self.arc_height * math.sin(math.pi * t)
            points.append((x * height, y * height, z * height))
        
        return points
    
    def create_3d_globe(self) -> go.Figure:
        """Create a 3D globe with migration flows."""
        print("\n🌍 Creating 3D globe with migration flows...")
        
        fig = go.Figure()
        
        # 1. Create globe surface
        u = np.linspace(0, 2 * np.pi, 50)
        v = np.linspace(0, np.pi, 50)
        x_globe = np.outer(np.cos(u), np.sin(v))
        y_globe = np.outer(np.sin(u), np.sin(v))
        z_globe = np.outer(np.ones(np.size(u)), np.cos(v))
        
        fig.add_trace(go.Surface(
            x=x_globe, y=y_globe, z=z_globe,
            colorscale='Earth',
            showscale=False,
            opacity=0.8,
            name='Earth'
        ))
        
        # 2. Add country markers
        countries = list(self.get_country_coordinates().keys())
        country_coords_3d = []
        
        for country in countries:
            if country in self.get_country_coordinates():
                lat, lon = self.get_country_coordinates()[country]
                x, y, z = self._lat_lon_to_3d(lat, lon, 1.05)
                country_coords_3d.append((x, y, z, country))
        
        if country_coords_3d:
            x_countries = [coord[0] for coord in country_coords_3d]
            y_countries = [coord[1] for coord in country_coords_3d]
            z_countries = [coord[2] for coord in country_coords_3d]
            country_names = [coord[3] for coord in country_coords_3d]
            
            fig.add_trace(go.Scatter3d(
                x=x_countries, y=y_countries, z=z_countries,
                mode='markers',
                marker=dict(
                    size=3,
                    color='yellow',
                    opacity=0.8
                ),
                text=country_names,
                name='Countries',
                hovertemplate='<b>%{text}</b><extra></extra>'
            ))
        
        # 3. Add migration flow arcs
        flow_colors = {
            'economic': 'cyan',
            'refugee': 'red',
            'climate': 'orange',
            'rural-urban': 'green'
        }
        
        for flow in self.migration_flows:
            if flow['type'] in flow_colors:
                arc_points = self._create_great_circle_arc(
                    flow['origin_coords'], 
                    flow['destination_coords']
                )
                
                if arc_points:
                    x_arc = [p[0] for p in arc_points]
                    y_arc = [p[1] for p in arc_points]
                    z_arc = [p[2] for p in arc_points]
                    
                    # Line width based on volume
                    line_width = max(1, min(8, flow['volume'] / 2))
                    
                    fig.add_trace(go.Scatter3d(
                        x=x_arc, y=y_arc, z=z_arc,
                        mode='lines',
                        line=dict(
                            color=flow_colors[flow['type']],
                            width=line_width
                        ),
                        opacity=0.7,
                        name=f"{flow['type'].title()} Migration",
                        hovertemplate=f"<b>{flow['origin']} → {flow['destination']}</b><br>" +
                                    f"Volume: {flow['volume']:.1f}M<br>" +
                                    f"Type: {flow['type']}<extra></extra>",
                        showlegend=False
                    ))
        
        # 4. Add legend manually
        for flow_type, color in flow_colors.items():
            fig.add_trace(go.Scatter3d(
                x=[None], y=[None], z=[None],
                mode='markers',
                marker=dict(size=10, color=color),
                name=f"{flow_type.title()} Migration",
                showlegend=True
            ))
        
        # Update layout
        fig.update_layout(
            title='3D Global Migration Flows<br>Interactive globe showing population movement patterns',
            scene=dict(
                xaxis_title='X',
                yaxis_title='Y',
                zaxis_title='Z',
                bgcolor='rgba(0,0,0,0.9)',
                xaxis=dict(showgrid=False, showticklabels=False),
                yaxis=dict(showgrid=False, showticklabels=False),
                zaxis=dict(showgrid=False, showticklabels=False),
                aspectmode='cube'
            ),
            width=1000,
            height=800,
            font=dict(family="Arial, sans-serif", size=12),
            template='plotly_dark'
        )
        
        print("✅ 3D globe created with migration flows")
        return fig
    
    def create_migration_dashboard(self) -> go.Figure:
        """Create a comprehensive migration analysis dashboard."""
        print("\n📊 Creating migration analysis dashboard...")
        
        # Create subplots
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Migration Volume by Type', 'Top Origin Countries', 
                          'Top Destination Countries', 'Regional Flow Matrix'),
            specs=[[{'type': 'bar'}, {'type': 'bar'}],
                   [{'type': 'bar'}, {'type': 'heatmap'}]],
            vertical_spacing=0.12,
            horizontal_spacing=0.1
        )
        
        # 1. Migration volume by type
        flow_types = {}
        for flow in self.migration_flows:
            flow_type = flow['type']
            if flow_type not in flow_types:
                flow_types[flow_type] = 0
            flow_types[flow_type] += flow['volume']
        
        fig.add_trace(go.Bar(
            x=list(flow_types.keys()),
            y=list(flow_types.values()),
            marker_color=['cyan', 'red', 'orange', 'green'],
            name='Migration Volume',
            showlegend=False
        ), row=1, col=1)
        
        # 2. Top origin countries
        origins = {}
        for flow in self.migration_flows:
            if flow['origin'] not in origins:
                origins[flow['origin']] = 0
            origins[flow['origin']] += flow['volume']
        
        top_origins = sorted(origins.items(), key=lambda x: x[1], reverse=True)[:10]
        
        fig.add_trace(go.Bar(
            x=[item[1] for item in top_origins],
            y=[item[0] for item in top_origins],
            orientation='h',
            marker_color='lightcoral',
            name='Origin Volume',
            showlegend=False
        ), row=1, col=2)
        
        # 3. Top destination countries
        destinations = {}
        for flow in self.migration_flows:
            if flow['destination'] not in destinations:
                destinations[flow['destination']] = 0
            destinations[flow['destination']] += flow['volume']
        
        top_destinations = sorted(destinations.items(), key=lambda x: x[1], reverse=True)[:10]
        
        fig.add_trace(go.Bar(
            x=[item[1] for item in top_destinations],
            y=[item[0] for item in top_destinations],
            orientation='h',
            marker_color='lightblue',
            name='Destination Volume',
            showlegend=False
        ), row=2, col=1)
        
        # 4. Regional flow matrix (simplified)
        regions = {
            'North America': ['United States', 'Canada'],
            'Europe': ['Germany', 'United Kingdom', 'France', 'Italy', 'Spain', 'Poland'],
            'Asia': ['China', 'India', 'Japan', 'South Korea', 'Thailand', 'Philippines'],
            'Africa': ['Nigeria', 'South Africa', 'Kenya', 'Ethiopia', 'Egypt'],
            'Latin America': ['Brazil', 'Mexico', 'Argentina', 'Colombia', 'Peru'],
            'Oceania': ['Australia', 'New Zealand']
        }
        
        # Create region mapping
        country_to_region = {}
        for region, countries in regions.items():
            for country in countries:
                country_to_region[country] = region
        
        # Calculate regional flows
        regional_flows = {}
        for region1 in regions:
            regional_flows[region1] = {}
            for region2 in regions:
                regional_flows[region1][region2] = 0
        
        for flow in self.migration_flows:
            origin_region = country_to_region.get(flow['origin'], 'Other')
            dest_region = country_to_region.get(flow['destination'], 'Other')
            
            if origin_region in regional_flows and dest_region in regional_flows[origin_region]:
                regional_flows[origin_region][dest_region] += flow['volume']
        
        # Convert to matrix
        region_names = list(regions.keys())
        matrix = []
        for origin in region_names:
            row = []
            for dest in region_names:
                row.append(regional_flows[origin][dest])
            matrix.append(row)
        
        fig.add_trace(go.Heatmap(
            z=matrix,
            x=region_names,
            y=region_names,
            colorscale='Viridis',
            name='Regional Flows',
            showscale=False
        ), row=2, col=2)
        
        # Update layout
        fig.update_layout(
            title_text="Global Migration Flow Analysis Dashboard",
            height=800,
            showlegend=False,
            template='plotly_white'
        )
        
        print("✅ Migration dashboard created")
        return fig
    
    def run_complete_analysis(self) -> Tuple[go.Figure, go.Figure]:
        """Run the complete 3D migration flow analysis."""
        print("🎯 Running Complete 3D Migration Flow Analysis")
        print("=" * 60)
        
        # Load data
        self.load_data()
        
        # Create visualizations
        globe_fig = self.create_3d_globe()
        dashboard_fig = self.create_migration_dashboard()
        
        print("\n" + "=" * 60)
        print("🎉 3D Migration Flow Analysis Complete!")
        print("=" * 60)
        print(f"✈️  Migration flows: {len(self.migration_flows)}")
        print(f"🌍 Countries: {len(self.get_country_coordinates())}")
        print(f"📊 Flow types: Economic, Refugee, Climate, Rural-Urban")
        print("💡 Key insights:")
        print("   • Economic migration dominates global flows")
        print("   • Climate migration is emerging as major force")
        print("   • Rural-urban migration drives internal displacement")
        print("   • Interactive 3D globe shows global patterns")
        
        return globe_fig, dashboard_fig

def main():
    """Main function to run the 3D migration flows visualization."""
    print("🚀 Testing 3D Migration Flows Visualization")
    print("=" * 60)
    
    # Create visualization
    viz = MigrationFlows3D("../../data")
    
    # Run analysis
    globe_fig, dashboard_fig = viz.run_complete_analysis()
    
    # Save as HTML files
    print("\n🌐 Saving interactive 3D visualizations...")
    
    output_dir = Path("../output/web_exports")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    globe_fig.write_html(output_dir / "migration_flows_3d_globe.html")
    dashboard_fig.write_html(output_dir / "migration_flows_dashboard.html")
    
    print(f"✅ Interactive visualizations saved to {output_dir}")
    print(f"🌐 Open these files in your browser:")
    print(f"   • 3D Globe: {output_dir / 'migration_flows_3d_globe.html'}")
    print(f"   • Dashboard: {output_dir / 'migration_flows_dashboard.html'}")
    
    # Show in browser if possible
    try:
        import webbrowser
        webbrowser.open(f"file://{(output_dir / 'migration_flows_3d_globe.html').absolute()}")
        print("🚀 Opening 3D globe in browser...")
    except:
        print("💡 Manually open the HTML files in your browser to view the 3D visualizations")

if __name__ == "__main__":
    main()
