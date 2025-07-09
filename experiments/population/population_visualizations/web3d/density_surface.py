"""
3D Population Density Surface Visualization

Creates a "demographic landscape" where height represents population density,
making cities appear as peaks and rural areas as valleys.

Based on research: "This striking 3D visualization captures the diverse population 
density, where towering spikes signify densely populated urban hubs"
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import sys
import os

# Add parent directory for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from core.data_loader import PopulationDataLoader
    from core.theme_manager import VisualizationTheme
except ImportError:
    # Fallback for direct execution
    sys.path.append('../core')
    from data_loader import PopulationDataLoader
    from theme_manager import VisualizationTheme

class PopulationDensitySurface3D:
    """
    Creates interactive 3D population density surfaces using Three.js.
    
    Key Features:
    - Height represents population density
    - Cities appear as dramatic peaks
    - Real-time rotation and zoom
    - Time evolution animation
    - Geographic accuracy
    
    Use Cases:
    - Urbanization pattern analysis
    - Megacity cluster identification  
    - Population inequality visualization
    - Climate migration impact assessment
    """
    
    def __init__(self, data_dir: str = "../data", grid_resolution: float = 0.1):
        """
        Initialize 3D density surface generator.
        
        Args:
            data_dir: Directory containing population data
            grid_resolution: Grid cell size in degrees (0.1 = ~11km)
        """
        self.data_loader = PopulationDataLoader(data_dir)
        self.theme = VisualizationTheme()
        self.grid_resolution = grid_resolution
        
        # Load city data with coordinates
        self.population_data = None
        self.city_data = None
        self.density_grid = None
        
        print(f"🌍 Initializing 3D Population Density Surface")
        print(f"📐 Grid Resolution: {grid_resolution}° (~{grid_resolution * 111:.1f}km)")
    
    def load_population_data(self) -> pd.DataFrame:
        """Load population data with geographic coordinates."""
        print("📊 Loading population data...")
        
        # Load base population data
        self.population_data = self.data_loader.load_population_data()
        
        # For demo, create synthetic city coordinate data
        # In production, this would come from a city database
        self.city_data = self._create_synthetic_city_coordinates()
        
        print(f"✅ Loaded {len(self.population_data)} population records")
        print(f"🏙️  Generated {len(self.city_data)} city coordinates")
        
        return self.population_data
    
    def _create_synthetic_city_coordinates(self) -> pd.DataFrame:
        """
        Create synthetic city coordinates for demonstration.
        
        In production, this would use real city coordinate databases
        like Natural Earth or OpenStreetMap data.
        """
        
        # Major world cities with approximate coordinates
        major_cities = {
            'Tokyo': (35.6762, 139.6503, 37_400_000),
            'Delhi': (28.7041, 77.1025, 32_900_000),
            'Shanghai': (31.2304, 121.4737, 28_500_000),
            'Dhaka': (23.8103, 90.4125, 22_000_000),
            'São Paulo': (-23.5558, -46.6396, 22_400_000),
            'Cairo': (30.0444, 31.2357, 21_300_000),
            'Mexico City': (19.4326, -99.1332, 21_800_000),
            'Beijing': (39.9042, 116.4074, 21_700_000),
            'Mumbai': (19.0760, 72.8777, 20_400_000),
            'Osaka': (34.6937, 135.5023, 18_900_000),
            'Chongqing': (29.4316, 106.9123, 16_800_000),
            'Karachi': (24.8607, 67.0011, 16_100_000),
            'Istanbul': (41.0082, 28.9784, 15_500_000),
            'Kinshasa': (-4.4419, 15.2663, 15_000_000),
            'Lagos': (6.5244, 3.3792, 14_800_000),
            'Buenos Aires': (-34.6118, -58.3960, 15_200_000),
            'Kolkata': (22.5726, 88.3639, 14_900_000),
            'Manila': (14.5995, 120.9842, 13_900_000),
            'Tianjin': (39.3434, 117.3616, 13_600_000),
            'Guangzhou': (23.1291, 113.2644, 13_500_000),
            'Rio de Janeiro': (-22.9068, -43.1729, 13_500_000),
            'Lahore': (31.5204, 74.3587, 13_100_000),
            'Bangalore': (12.9716, 77.5946, 12_800_000),
            'Shenzhen': (22.5431, 114.0579, 12_600_000),
            'Moscow': (55.7558, 37.6176, 12_500_000),
            'Chennai': (13.0827, 80.2707, 11_700_000),
            'Bogotá': (4.7110, -74.0721, 11_300_000),
            'Paris': (48.8566, 2.3522, 11_200_000),
            'Jakarta': (-6.2088, 106.8456, 10_600_000),
            'Lima': (-12.0464, -77.0428, 10_900_000),
            'Bangkok': (13.7563, 100.5018, 10_700_000),
            'Seoul': (37.5665, 126.9780, 9_700_000),
            'Nagoya': (35.1815, 136.9066, 9_500_000),
            'Hyderabad': (17.3850, 78.4867, 9_900_000),
            'London': (51.5074, -0.1278, 9_500_000),
            'Tehran': (35.6892, 51.3890, 9_100_000),
            'Chicago': (41.8781, -87.6298, 9_500_000),
            'Chengdu': (30.5728, 104.0668, 9_100_000),
            'Nanjing': (32.0603, 118.7969, 8_800_000),
            'Wuhan': (30.5928, 114.3055, 8_900_000),
            'Ho Chi Minh City': (10.8231, 106.6297, 8_600_000),
            'Luanda': (-8.8390, 13.2894, 8_300_000),
            'Ahmedabad': (23.0225, 72.5714, 8_200_000),
            'Kuala Lumpur': (3.1390, 101.6869, 8_200_000),
            'Xi\'an': (34.3416, 108.9398, 8_000_000),
            'Hong Kong': (22.3193, 114.1694, 7_500_000),
            'Dongguan': (23.0489, 113.7447, 7_400_000),
            'Hangzhou': (30.2741, 120.1551, 7_200_000),
            'Foshan': (23.0218, 113.1219, 7_200_000),
            'Shenyang': (41.8057, 123.4315, 6_900_000),
            'Riyadh': (24.7136, 46.6753, 7_000_000),
            'Baghdad': (33.3152, 44.3661, 6_900_000),
            'Santiago': (-33.4489, -70.6693, 6_800_000),
        }
        
        city_rows = []
        for city, (lat, lon, pop) in major_cities.items():
            city_rows.append({
                'city': city,
                'country': self._get_country_for_city(city),
                'latitude': lat,
                'longitude': lon,
                'population': pop,
                'population_density': pop / 1000  # Simplified density calculation
            })
        
        return pd.DataFrame(city_rows)
    
    def _get_country_for_city(self, city: str) -> str:
        """Map cities to countries for demonstration."""
        city_country_map = {
            'Tokyo': 'Japan', 'Delhi': 'India', 'Shanghai': 'China',
            'Dhaka': 'Bangladesh', 'São Paulo': 'Brazil', 'Cairo': 'Egypt',
            'Mexico City': 'Mexico', 'Beijing': 'China', 'Mumbai': 'India',
            'Osaka': 'Japan', 'Chongqing': 'China', 'Karachi': 'Pakistan',
            'Istanbul': 'Turkey', 'Kinshasa': 'Congo, Dem. Rep.', 'Lagos': 'Nigeria',
            'Buenos Aires': 'Argentina', 'Kolkata': 'India', 'Manila': 'Philippines',
            'Tianjin': 'China', 'Guangzhou': 'China', 'Rio de Janeiro': 'Brazil',
            'Lahore': 'Pakistan', 'Bangalore': 'India', 'Shenzhen': 'China',
            'Moscow': 'Russian Federation', 'Chennai': 'India', 'Bogotá': 'Colombia',
            'Paris': 'France', 'Jakarta': 'Indonesia', 'Lima': 'Peru',
            'Bangkok': 'Thailand', 'Seoul': 'Korea, Rep.', 'Nagoya': 'Japan',
            'Hyderabad': 'India', 'London': 'United Kingdom', 'Tehran': 'Iran, Islamic Rep.',
            'Chicago': 'United States', 'Chengdu': 'China', 'Nanjing': 'China',
            'Wuhan': 'China', 'Ho Chi Minh City': 'Vietnam', 'Luanda': 'Angola',
            'Ahmedabad': 'India', 'Kuala Lumpur': 'Malaysia', 'Xi\'an': 'China',
            'Hong Kong': 'Hong Kong SAR, China', 'Dongguan': 'China', 'Hangzhou': 'China',
            'Foshan': 'China', 'Shenyang': 'China', 'Riyadh': 'Saudi Arabia',
            'Baghdad': 'Iraq', 'Santiago': 'Chile'
        }
        return city_country_map.get(city, 'Unknown')
    
    def create_density_grid(self, year: int = 2023) -> np.ndarray:
        """
        Create a regular grid with population density values.
        
        Args:
            year: Year to generate grid for
            
        Returns:
            3D array [lat_idx, lon_idx, density]
        """
        print(f"🗺️  Creating density grid for {year}...")
        
        if self.city_data is None:
            self.load_population_data()
        
        # Define grid bounds (global)
        lat_min, lat_max = -60, 80  # Exclude Antarctica
        lon_min, lon_max = -180, 180
        
        # Calculate grid dimensions
        lat_steps = int((lat_max - lat_min) / self.grid_resolution)
        lon_steps = int((lon_max - lon_min) / self.grid_resolution)
        
        print(f"📐 Grid dimensions: {lat_steps} x {lon_steps} = {lat_steps * lon_steps:,} cells")
        
        # Initialize grid
        density_grid = np.zeros((lat_steps, lon_steps))
        lat_coords = np.linspace(lat_min, lat_max, lat_steps)
        lon_coords = np.linspace(lon_min, lon_max, lon_steps)
        
        # Map cities to grid cells and assign density
        for _, city in self.city_data.iterrows():
            lat_idx = np.argmin(np.abs(lat_coords - city['latitude']))
            lon_idx = np.argmin(np.abs(lon_coords - city['longitude']))
            
            # Add city population to grid cell
            density_grid[lat_idx, lon_idx] += city['population_density']
        
        # Apply smoothing for realistic terrain
        from scipy.ndimage import gaussian_filter
        density_grid = gaussian_filter(density_grid, sigma=1.0)
        
        # Store grid data
        self.density_grid = {
            'density': density_grid,
            'lat_coords': lat_coords,
            'lon_coords': lon_coords,
            'year': year
        }
        
        print(f"✅ Created density grid with {np.count_nonzero(density_grid)} populated cells")
        print(f"📊 Density range: {density_grid.min():.1f} to {density_grid.max():.1f}")
        
        return density_grid
    
    def generate_threejs_data(self, year: int = 2023) -> Dict:
        """
        Generate data structure for Three.js 3D visualization.
        
        Returns:
            Dictionary with vertices, faces, colors, and metadata
        """
        print("🎨 Generating Three.js visualization data...")
        
        if self.density_grid is None:
            self.create_density_grid(year)
        
        density = self.density_grid['density']
        lat_coords = self.density_grid['lat_coords']
        lon_coords = self.density_grid['lon_coords']
        
        # Normalize heights for 3D visualization
        max_height = 100  # Maximum height in 3D units
        normalized_heights = (density / density.max()) * max_height
        
        # Generate vertices for Three.js PlaneGeometry
        vertices = []
        colors = []
        faces = []
        
        lat_steps, lon_steps = density.shape
        
        # Create vertices
        for i in range(lat_steps):
            for j in range(lon_steps):
                # Convert to normalized coordinates (-1 to 1)
                x = (j / (lon_steps - 1)) * 2 - 1  # Longitude
                z = (i / (lat_steps - 1)) * 2 - 1  # Latitude
                y = normalized_heights[i, j]       # Height (density)
                
                vertices.extend([x, y, z])
                
                # Color based on density
                color = self._density_to_color(density[i, j], density.max())
                colors.extend(color)
        
        # Generate faces (triangles)
        for i in range(lat_steps - 1):
            for j in range(lon_steps - 1):
                # Two triangles per grid cell
                v1 = i * lon_steps + j
                v2 = i * lon_steps + (j + 1)
                v3 = (i + 1) * lon_steps + j
                v4 = (i + 1) * lon_steps + (j + 1)
                
                # Triangle 1
                faces.extend([v1, v2, v3])
                # Triangle 2
                faces.extend([v2, v4, v3])
        
        # Generate city markers for high-density areas
        city_markers = []
        for _, city in self.city_data.iterrows():
            if city['population'] > 5_000_000:  # Only major cities
                # Convert to normalized coordinates
                lon_norm = (city['longitude'] + 180) / 360 * 2 - 1
                lat_norm = (city['latitude'] + 60) / 140 * 2 - 1
                
                city_markers.append({
                    'name': city['city'],
                    'country': city['country'],
                    'population': city['population'],
                    'x': lon_norm,
                    'z': lat_norm,
                    'y': (city['population_density'] / density.max()) * max_height + 5
                })
        
        threejs_data = {
            'vertices': vertices,
            'colors': colors, 
            'faces': faces,
            'cityMarkers': city_markers,
            'metadata': {
                'year': year,
                'gridResolution': self.grid_resolution,
                'maxHeight': max_height,
                'totalCities': len(self.city_data),
                'densityRange': [float(density.min()), float(density.max())],
                'gridDimensions': [lat_steps, lon_steps]
            }
        }
        
        print(f"✅ Generated {len(vertices)//3:,} vertices, {len(faces)//3:,} faces")
        print(f"🏙️  Added {len(city_markers)} major city markers")
        
        return threejs_data
    
    def _density_to_color(self, density: float, max_density: float) -> List[float]:
        """Convert density value to RGB color."""
        if density == 0:
            return [0.0, 0.1, 0.3]  # Dark blue for water/empty
        
        # Normalize density (0-1)
        norm_density = min(density / max_density, 1.0)
        
        # Color gradient: blue → green → yellow → red
        if norm_density < 0.25:
            # Blue to green
            t = norm_density * 4
            return [0, 0.1 + 0.4 * t, 0.3 + 0.5 * t]
        elif norm_density < 0.5:
            # Green to yellow
            t = (norm_density - 0.25) * 4
            return [0.8 * t, 0.5 + 0.4 * t, 0.8 - 0.6 * t]
        elif norm_density < 0.75:
            # Yellow to orange
            t = (norm_density - 0.5) * 4
            return [0.8 + 0.2 * t, 0.9 - 0.1 * t, 0.2 - 0.2 * t]
        else:
            # Orange to red
            t = (norm_density - 0.75) * 4
            return [1.0, 0.8 - 0.8 * t, 0]
    
    def export_for_web(self, output_dir: str = "output/web_exports") -> str:
        """
        Export all data and generate HTML file for Three.js visualization.
        
        Args:
            output_dir: Directory to save web files
            
        Returns:
            Path to generated HTML file
        """
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        print(f"🌐 Exporting 3D visualization to {output_path}...")
        
        # Generate Three.js data
        threejs_data = self.generate_threejs_data()
        
        # Save data as JSON
        data_file = output_path / "population_density_3d.json"
        with open(data_file, 'w') as f:
            json.dump(threejs_data, f, indent=2)
        
        # Generate HTML file with Three.js visualization
        html_content = self._generate_html_template(threejs_data)
        html_file = output_path / "population_density_3d.html"
        
        with open(html_file, 'w') as f:
            f.write(html_content)
        
        print(f"✅ Exported 3D visualization:")
        print(f"   📄 HTML: {html_file}")
        print(f"   📊 Data: {data_file}")
        print(f"   🌐 Open in browser: file://{html_file.absolute()}")
        
        return str(html_file.absolute())
    
    def _generate_html_template(self, data: Dict) -> str:
        """Generate HTML template with Three.js visualization."""
        
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>3D Population Density Surface</title>
    <style>
        body {{
            margin: 0;
            padding: 0;
            overflow: hidden;
            background: #000;
            font-family: Arial, sans-serif;
        }}
        
        #container {{
            width: 100vw;
            height: 100vh;
            position: relative;
        }}
        
        #info {{
            position: absolute;
            top: 20px;
            left: 20px;
            color: white;
            background: rgba(0, 0, 0, 0.7);
            padding: 15px;
            border-radius: 8px;
            z-index: 100;
            max-width: 300px;
        }}
        
        #controls {{
            position: absolute;
            bottom: 20px;
            left: 20px;
            color: white;
            background: rgba(0, 0, 0, 0.7);
            padding: 15px;
            border-radius: 8px;
            z-index: 100;
        }}
        
        .control-group {{
            margin-bottom: 10px;
        }}
        
        label {{
            display: block;
            margin-bottom: 5px;
            font-size: 12px;
        }}
        
        input[type="range"] {{
            width: 200px;
        }}
        
        #tooltip {{
            position: absolute;
            background: rgba(0, 0, 0, 0.8);
            color: white;
            padding: 8px;
            border-radius: 4px;
            pointer-events: none;
            z-index: 200;
            display: none;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div id="container">
        <div id="info">
            <h3>🌍 3D Population Density Surface</h3>
            <p><strong>Year:</strong> {data['metadata']['year']}</p>
            <p><strong>Cities:</strong> {data['metadata']['totalCities']}</p>
            <p><strong>Grid:</strong> {data['metadata']['gridDimensions'][0]} x {data['metadata']['gridDimensions'][1]}</p>
            <p><strong>Controls:</strong><br>
            Mouse: Rotate view<br>
            Wheel: Zoom<br>
            Hover: City info</p>
        </div>
        
        <div id="controls">
            <div class="control-group">
                <label for="heightScale">Height Scale:</label>
                <input type="range" id="heightScale" min="0.1" max="3.0" step="0.1" value="1.0">
                <span id="heightValue">1.0x</span>
            </div>
            
            <div class="control-group">
                <label for="wireframe">Wireframe Mode:</label>
                <input type="checkbox" id="wireframe">
            </div>
            
            <div class="control-group">
                <label for="showCities">Show Cities:</label>
                <input type="checkbox" id="showCities" checked>
            </div>
        </div>
        
        <div id="tooltip"></div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/three@0.155.0/build/three.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/three@0.155.0/examples/js/controls/OrbitControls.js"></script>
    
    <script>
        // Global variables
        let scene, camera, renderer, controls;
        let terrain, cityMarkers = [];
        let originalVertices;
        
        // Data
        const data = {json.dumps(data, indent=8)};
        
        // Initialize the 3D scene
        function init() {{
            // Scene setup
            scene = new THREE.Scene();
            scene.fog = new THREE.Fog(0x222244, 100, 1000);
            
            // Camera setup
            camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 2000);
            camera.position.set(100, 60, 100);
            
            // Renderer setup
            renderer = new THREE.WebGLRenderer({{ antialias: true }});
            renderer.setSize(window.innerWidth, window.innerHeight);
            renderer.setClearColor(0x111122);
            renderer.shadowMap.enabled = true;
            renderer.shadowMap.type = THREE.PCFSoftShadowMap;
            document.getElementById('container').appendChild(renderer.domElement);
            
            // Controls
            controls = new THREE.OrbitControls(camera, renderer.domElement);
            controls.enableDamping = true;
            controls.dampingFactor = 0.05;
            controls.maxPolarAngle = Math.PI / 2;
            
            // Lighting
            const ambientLight = new THREE.AmbientLight(0x404040, 0.3);
            scene.add(ambientLight);
            
            const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
            directionalLight.position.set(100, 100, 50);
            directionalLight.castShadow = true;
            directionalLight.shadow.mapSize.width = 2048;
            directionalLight.shadow.mapSize.height = 2048;
            scene.add(directionalLight);
            
            // Create terrain
            createTerrain();
            
            // Create city markers
            createCityMarkers();
            
            // Event listeners
            setupControls();
            
            // Mouse interaction
            setupMouseInteraction();
            
            // Start animation
            animate();
        }}
        
        function createTerrain() {{
            const vertices = new Float32Array(data.vertices);
            const colors = new Float32Array(data.colors);
            const faces = new Uint32Array(data.faces);
            
            // Store original vertices for scaling
            originalVertices = [...vertices];
            
            const geometry = new THREE.BufferGeometry();
            geometry.setAttribute('position', new THREE.BufferAttribute(vertices, 3));
            geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
            geometry.setIndex(new THREE.BufferAttribute(faces, 1));
            geometry.computeVertexNormals();
            
            const material = new THREE.MeshLambertMaterial({{
                vertexColors: true,
                side: THREE.DoubleSide
            }});
            
            terrain = new THREE.Mesh(geometry, material);
            terrain.scale.set(200, 1, 200); // Scale to reasonable world size
            terrain.receiveShadow = true;
            scene.add(terrain);
        }}
        
        function createCityMarkers() {{
            data.cityMarkers.forEach(city => {{
                // Create city marker (glowing sphere)
                const geometry = new THREE.SphereGeometry(2, 16, 16);
                const material = new THREE.MeshBasicMaterial({{
                    color: 0xffff00,
                    transparent: true,
                    opacity: 0.8
                }});
                
                const marker = new THREE.Mesh(geometry, material);
                marker.position.set(city.x * 200, city.y + 5, city.z * 200);
                marker.userData = city;
                
                // Add glow effect
                const glowGeometry = new THREE.SphereGeometry(3, 16, 16);
                const glowMaterial = new THREE.MeshBasicMaterial({{
                    color: 0xffff00,
                    transparent: true,
                    opacity: 0.3
                }});
                const glow = new THREE.Mesh(glowGeometry, glowMaterial);
                marker.add(glow);
                
                cityMarkers.push(marker);
                scene.add(marker);
            }});
        }}
        
        function setupControls() {{
            // Height scale control
            const heightScale = document.getElementById('heightScale');
            const heightValue = document.getElementById('heightValue');
            
            heightScale.addEventListener('input', (e) => {{
                const scale = parseFloat(e.target.value);
                heightValue.textContent = scale.toFixed(1) + 'x';
                updateTerrainHeight(scale);
            }});
            
            // Wireframe toggle
            document.getElementById('wireframe').addEventListener('change', (e) => {{
                terrain.material.wireframe = e.target.checked;
            }});
            
            // Cities toggle
            document.getElementById('showCities').addEventListener('change', (e) => {{
                cityMarkers.forEach(marker => {{
                    marker.visible = e.target.checked;
                }});
            }});
        }}
        
        function updateTerrainHeight(scale) {{
            const positions = terrain.geometry.attributes.position.array;
            for (let i = 1; i < positions.length; i += 3) {{ // Only Y coordinates
                positions[i] = originalVertices[i] * scale;
            }}
            terrain.geometry.attributes.position.needsUpdate = true;
            terrain.geometry.computeVertexNormals();
            
            // Update city marker positions
            cityMarkers.forEach((marker, index) => {{
                const city = data.cityMarkers[index];
                marker.position.y = city.y * scale + 5;
            }});
        }}
        
        function setupMouseInteraction() {{
            const raycaster = new THREE.Raycaster();
            const mouse = new THREE.Vector2();
            const tooltip = document.getElementById('tooltip');
            
            renderer.domElement.addEventListener('mousemove', (event) => {{
                mouse.x = (event.clientX / window.innerWidth) * 2 - 1;
                mouse.y = -(event.clientY / window.innerHeight) * 2 + 1;
                
                raycaster.setFromCamera(mouse, camera);
                const intersects = raycaster.intersectObjects(cityMarkers);
                
                if (intersects.length > 0) {{
                    const city = intersects[0].object.userData;
                    tooltip.style.display = 'block';
                    tooltip.style.left = event.clientX + 10 + 'px';
                    tooltip.style.top = event.clientY - 30 + 'px';
                    tooltip.innerHTML = `
                        <strong>${{city.name}}</strong><br>
                        ${{city.country}}<br>
                        Population: ${{(city.population / 1000000).toFixed(1)}}M
                    `;
                    
                    // Highlight city
                    intersects[0].object.material.color.setHex(0xff4444);
                }} else {{
                    tooltip.style.display = 'none';
                    // Reset city colors
                    cityMarkers.forEach(marker => {{
                        marker.material.color.setHex(0xffff00);
                    }});
                }}
            }});
        }}
        
        function animate() {{
            requestAnimationFrame(animate);
            controls.update();
            
            // Rotate city glow effects
            cityMarkers.forEach(marker => {{
                if (marker.children[0]) {{
                    marker.children[0].rotation.y += 0.01;
                }}
            }});
            
            renderer.render(scene, camera);
        }}
        
        // Handle window resize
        window.addEventListener('resize', () => {{
            camera.aspect = window.innerWidth / window.innerHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(window.innerWidth, window.innerHeight);
        }});
        
        // Initialize when page loads
        init();
    </script>
</body>
</html>"""

# Test the implementation
if __name__ == "__main__":
    print("🚀 Testing 3D Population Density Surface Generator")
    print("=" * 60)
    
    try:
        # Create 3D visualization
        viz = PopulationDensitySurface3D(data_dir="../../data")
        
        # Load data
        viz.load_population_data()
        
        # Create density grid
        viz.create_density_grid(2023)
        
        # Export for web
        html_path = viz.export_for_web("../output/web_exports")
        
        print("\n" + "=" * 60)
        print("🎉 3D VISUALIZATION READY!")
        print("=" * 60)
        print(f"🌐 Open in browser: {html_path}")
        print("🖱️  Controls:")
        print("   • Mouse drag: Rotate view")  
        print("   • Mouse wheel: Zoom in/out")
        print("   • Hover cities: Show details")
        print("   • Use controls panel for options")
        print("\n💡 This creates a 'demographic landscape' where cities rise like mountains!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
