"""
Advanced 3D Population Explorer
Creates immersive 3D visualizations with real-time controls and multiple perspectives
"""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplot    def create_pca_3d_visualization(self):
        """Create 3D PCA visualization."""
        # Prepare feature matrix
        features = self.feature_matrix.fillna(0.0)
        
        # Standardize features
        scaler = StandardScaler()
        features_scaled = scaler.fit_transform(features)
        
        # Apply PCA
        pca = PCA(n_components=3)
        pca_result = pca.fit_transform(features_scaled)
        
        # Get country names
        latest_year = int(self.data['year'].max())
        country_names = [str(name) for name in self.data[self.data['year'] == latest_year]['country_name'].values]as pd
import numpy as np
import json
from datetime import datetime
import dash
from dash import dcc, html, Input, Output, callback
import dash_bootstrap_components as dbc
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

class Advanced3DPopulationExplorer:
    """
    Advanced 3D explorer with:
    - Interactive 3D surface plots
    - Real-time axis switching
    - Dimensional reduction visualizations
    - Time-based 3D animations
    - Multiple 3D perspectives
    """
    
    def __init__(self, data_dir="../data"):
        self.data_dir = data_dir
        self.data = None
        self.feature_matrix = None
        self.load_and_prepare_data()
        
    def load_and_prepare_data(self):
        """Load and prepare data for 3D analysis."""
        print("Loading data for 3D exploration...")
        
        # Load population data
        with open(f'{self.data_dir}/population_timeseries.json', 'r') as f:
            population_data = json.load(f)
        
        # Load additional indicators
        try:
            with open(f'{self.data_dir}/urban_population.json', 'r') as f:
                urban_data = json.load(f)
        except:
            urban_data = []
            
        try:
            with open(f'{self.data_dir}/population_growth.json', 'r') as f:
                growth_data = json.load(f)
        except:
            growth_data = []
        
        # Process population data
        records = []
        for record in population_data:
            if record.get('value') is not None:
                records.append({
                    'country_code': str(record.get('countryiso3code', record.get('country', {}).get('id', ''))),
                    'country_name': str(record.get('country', {}).get('value', 'Unknown')),
                    'year': int(record.get('date', 0)),
                    'population': float(record.get('value', 0))
                })
        
        self.data = pd.DataFrame(records)
        
        # Calculate derived metrics
        self.data = self.data.sort_values(['country_code', 'year'])
        self.data['growth_rate'] = self.data.groupby('country_code')['population'].pct_change() * 100
        self.data['population_millions'] = self.data['population'] / 1e6
        self.data['log_population'] = np.log10(self.data['population'] + 1)
        
        # Convert numpy types to native Python types to avoid JSON serialization issues
        self.data['growth_rate'] = self.data['growth_rate'].astype('float64').fillna(0.0)
        self.data['population_millions'] = self.data['population_millions'].astype('float64')
        self.data['log_population'] = self.data['log_population'].astype('float64')
        
        # Calculate volatility (standard deviation of growth rates)
        volatility = self.data.groupby('country_code')['growth_rate'].std().fillna(0.0)
        self.data['volatility'] = self.data['country_code'].map(volatility).astype('float64')
        
        # Calculate average growth rates
        avg_growth = self.data.groupby('country_code')['growth_rate'].mean().fillna(0.0)
        self.data['avg_growth'] = self.data['country_code'].map(avg_growth).astype('float64')
        
        # Get latest year data for feature matrix
        latest_year = int(self.data['year'].max())
        latest_data = self.data[self.data['year'] == latest_year].copy()
        
        # Create feature matrix for dimensionality reduction
        self.feature_matrix = latest_data[['population_millions', 'avg_growth', 'volatility']].fillna(0.0)
        
        print(f"Data prepared: {len(self.data)} records, {self.data['country_code'].nunique()} countries")
    
    def create_3d_surface_plot(self):
        """Create interactive 3D surface plot."""
        # Create a grid for surface plot
        years = sorted([int(y) for y in self.data['year'].unique()])
        
        # Get top 20 countries for surface
        latest_year = int(self.data['year'].max())
        top_countries = self.data[self.data['year'] == latest_year].nlargest(20, 'population')
        
        # Create matrices for surface plot
        z_data = []
        country_names = []
        
        for country_code in top_countries['country_code']:
            country_data = self.data[self.data['country_code'] == country_code]
            country_name = str(country_data['country_name'].iloc[0])
            country_names.append(country_name)
            
            # Create row for this country
            row = []
            for year in years:
                year_data = country_data[country_data['year'] == year]
                if not year_data.empty:
                    row.append(float(year_data['population_millions'].iloc[0]))
                else:
                    row.append(0.0)
            z_data.append(row)
        
        # Create 3D surface
        fig = go.Figure(data=[go.Surface(
            x=years,
            y=list(range(len(country_names))),
            z=z_data,
            colorscale='Viridis',
            hovertemplate='Year: %{x}<br>Country: %{text}<br>Population: %{z:.1f}M<extra></extra>',
            text=[[name] * len(years) for name in country_names]
        )])
        
        fig.update_layout(
            title=dict(
                text='3D Population Surface: Countries × Years × Population',
                x=0.5,
                font=dict(size=18, color='#2c3e50')
            ),
            scene=dict(
                xaxis_title='Year',
                yaxis_title='Country (Index)',
                zaxis_title='Population (Millions)',
                camera=dict(
                    eye=dict(x=1.2, y=1.2, z=1.2)
                ),
                bgcolor='rgba(248,249,250,0.8)'
            ),
            height=700,
            font=dict(family="Arial, sans-serif", size=12, color="#2c3e50"),
            paper_bgcolor='white'
        )
        
        return fig
    
    def create_3d_scatter_with_time(self):
        """Create 3D scatter plot with time animation."""
        # Prepare data for 3D scatter
        years = sorted([int(y) for y in self.data['year'].unique()])[::5]  # Every 5 years for performance
        
        # Get countries with complete data
        complete_countries = self.data.groupby('country_code').size()
        complete_countries = complete_countries[complete_countries >= 20].index
        
        animation_data = []
        for year in years:
            year_data = self.data[
                (self.data['year'] == year) & 
                (self.data['country_code'].isin(complete_countries))
            ].copy()
            
            if not year_data.empty:
                # Add some randomness for Z-axis (could be another metric)
                year_data['z_metric'] = (year_data['volatility'] * 10 + 
                                       np.random.normal(0, 0.1, len(year_data))).astype('float64')
                animation_data.append(year_data)
        
        if not animation_data:
            return go.Figure()
        
        combined_data = pd.concat(animation_data)
        
        # Create 3D scatter with animation
        fig = px.scatter_3d(
            combined_data,
            x='population_millions',
            y='growth_rate',
            z='z_metric',
            color='avg_growth',
            size='population_millions',
            hover_name='country_name',
            animation_frame='year',
            title="3D Population Analysis Over Time",
            labels={
                'population_millions': 'Population (Millions)',
                'growth_rate': 'Growth Rate (%)',
                'z_metric': 'Volatility Index',
                'avg_growth': 'Avg Growth Rate'
            },
            color_continuous_scale='RdYlBu',
            size_max=30,
            height=700
        )
        
        # Update layout
        fig.update_layout(
            title=dict(
                text='3D Population Dynamics Over Time',
                x=0.5,
                font=dict(size=18, color='#2c3e50')
            ),
            scene=dict(
                xaxis_title='Population (Millions)',
                yaxis_title='Growth Rate (%)',
                zaxis_title='Volatility Index',
                camera=dict(
                    eye=dict(x=1.5, y=1.5, z=1.5)
                ),
                bgcolor='rgba(248,249,250,0.8)'
            ),
            font=dict(family="Arial, sans-serif", size=12, color="#2c3e50"),
            paper_bgcolor='white'
        )
        
        return fig
    
    def create_pca_3d_visualization(self):
        """Create 3D PCA visualization."""
        # Prepare feature matrix
        features = self.feature_matrix.fillna(0)
        
        # Standardize features
        scaler = StandardScaler()
        features_scaled = scaler.fit_transform(features)
        
        # Apply PCA
        pca = PCA(n_components=3)
        pca_result = pca.fit_transform(features_scaled)
        
        # Get country names
        latest_year = self.data['year'].max()
        country_names = self.data[self.data['year'] == latest_year]['country_name'].values
        
        # Create 3D scatter
        fig = go.Figure(data=[go.Scatter3d(
            x=pca_result[:, 0],
            y=pca_result[:, 1],
            z=pca_result[:, 2],
            mode='markers',
            marker=dict(
                size=8,
                color=features['population_millions'],
                colorscale='Viridis',
                showscale=True,
                colorbar=dict(title="Population (Millions)")
            ),
            text=country_names,
            hovertemplate='<b>%{text}</b><br>' +
                         'PC1: %{x:.2f}<br>' +
                         'PC2: %{y:.2f}<br>' +
                         'PC3: %{z:.2f}<br>' +
                         '<extra></extra>'
        )])
        
        fig.update_layout(
            title=dict(
                text='3D PCA: Countries by Demographic Similarity',
                x=0.5,
                font=dict(size=18, color='#2c3e50')
            ),
            scene=dict(
                xaxis_title=f'PC1 ({pca.explained_variance_ratio_[0]:.1%} variance)',
                yaxis_title=f'PC2 ({pca.explained_variance_ratio_[1]:.1%} variance)',
                zaxis_title=f'PC3 ({pca.explained_variance_ratio_[2]:.1%} variance)',
                camera=dict(
                    eye=dict(x=1.5, y=1.5, z=1.5)
                ),
                bgcolor='rgba(248,249,250,0.8)'
            ),
            height=700,
            font=dict(family="Arial, sans-serif", size=12, color="#2c3e50"),
            paper_bgcolor='white'
        )
        
        return fig
    
    def create_tsne_3d_visualization(self):
        """Create 3D t-SNE visualization."""
        # Prepare feature matrix
        features = self.feature_matrix.fillna(0)
        
        # Standardize features
        scaler = StandardScaler()
        features_scaled = scaler.fit_transform(features)
        
        # Apply t-SNE
        tsne = TSNE(n_components=3, random_state=42, perplexity=30)
        tsne_result = tsne.fit_transform(features_scaled)
        
        # Apply K-means clustering
        kmeans = KMeans(n_clusters=6, random_state=42)
        clusters = kmeans.fit_predict(features_scaled)
        
        # Get country names
        latest_year = self.data['year'].max()
        country_names = self.data[self.data['year'] == latest_year]['country_name'].values
        
        # Create 3D scatter
        fig = go.Figure(data=[go.Scatter3d(
            x=tsne_result[:, 0],
            y=tsne_result[:, 1],
            z=tsne_result[:, 2],
            mode='markers',
            marker=dict(
                size=8,
                color=clusters,
                colorscale='Set3',
                showscale=True,
                colorbar=dict(title="Cluster")
            ),
            text=country_names,
            hovertemplate='<b>%{text}</b><br>' +
                         'Cluster: %{marker.color}<br>' +
                         't-SNE1: %{x:.2f}<br>' +
                         't-SNE2: %{y:.2f}<br>' +
                         't-SNE3: %{z:.2f}<br>' +
                         '<extra></extra>'
        )])
        
        fig.update_layout(
            title=dict(
                text='3D t-SNE: Demographic Clustering',
                x=0.5,
                font=dict(size=18, color='#2c3e50')
            ),
            scene=dict(
                xaxis_title='t-SNE Dimension 1',
                yaxis_title='t-SNE Dimension 2',
                zaxis_title='t-SNE Dimension 3',
                camera=dict(
                    eye=dict(x=1.5, y=1.5, z=1.5)
                ),
                bgcolor='rgba(248,249,250,0.8)'
            ),
            height=700,
            font=dict(family="Arial, sans-serif", size=12, color="#2c3e50"),
            paper_bgcolor='white'
        )
        
        return fig
    
    def create_dash_app(self):
        """Create comprehensive 3D exploration dashboard."""
        app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
        
        # Create figures
        surface_fig = self.create_3d_surface_plot()
        scatter_fig = self.create_3d_scatter_with_time()
        pca_fig = self.create_pca_3d_visualization()
        tsne_fig = self.create_tsne_3d_visualization()
        
        # Define app layout
        app.layout = dbc.Container([
            dbc.Row([
                dbc.Col([
                    html.H1("🌍 Advanced 3D Population Explorer", 
                           className="text-center mb-4",
                           style={'color': '#2c3e50', 'font-weight': 'bold'})
                ])
            ]),
            
            dbc.Row([
                dbc.Col([
                    html.H4("3D Controls", style={'color': '#34495e'}),
                    
                    html.Label("Visualization Type:", style={'font-weight': 'bold'}),
                    dcc.Dropdown(
                        id='viz-type-dropdown',
                        options=[
                            {'label': '3D Surface Plot', 'value': 'surface'},
                            {'label': '3D Scatter Animation', 'value': 'scatter'},
                            {'label': 'PCA 3D Analysis', 'value': 'pca'},
                            {'label': 't-SNE 3D Clustering', 'value': 'tsne'}
                        ],
                        value='surface',
                        style={'margin-bottom': '20px'}
                    ),
                    
                    html.Label("Camera Angle:", style={'font-weight': 'bold'}),
                    dcc.Slider(
                        id='camera-angle-slider',
                        min=0,
                        max=360,
                        step=30,
                        value=45,
                        marks={i: f"{i}°" for i in range(0, 361, 90)},
                        tooltip={"placement": "bottom", "always_visible": True}
                    ),
                    
                    html.Div(id='viz-info', style={'margin-top': '20px'})
                ], width=3),
                
                dbc.Col([
                    dcc.Graph(id='main-3d-graph', figure=surface_fig)
                ], width=9)
            ], style={'margin-bottom': '30px'}),
            
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.H5("3D Visualization Guide:", style={'color': '#2c3e50'}),
                        html.Ul([
                            html.Li("🔄 Rotate: Click and drag to rotate the 3D view"),
                            html.Li("🔍 Zoom: Use mouse wheel or pinch to zoom in/out"),
                            html.Li("📊 Surface Plot: Shows population as a 3D landscape"),
                            html.Li("🎯 Scatter Animation: Watch countries move through 3D space over time"),
                            html.Li("📈 PCA Analysis: Reveals main demographic patterns"),
                            html.Li("🎨 t-SNE Clustering: Groups similar countries together"),
                            html.Li("💡 Hover over points for detailed country information")
                        ])
                    ], style={'background-color': '#f8f9fa', 'padding': '20px', 'border-radius': '10px'})
                ])
            ])
        ], fluid=True)
        
        # Add callbacks
        @app.callback(
            [Output('main-3d-graph', 'figure'),
             Output('viz-info', 'children')],
            [Input('viz-type-dropdown', 'value'),
             Input('camera-angle-slider', 'value')]
        )
        def update_3d_visualization(viz_type, camera_angle):
            # Select figure based on type
            if viz_type == 'surface':
                fig = surface_fig
                info = "3D Surface Plot showing population as height across countries and years"
            elif viz_type == 'scatter':
                fig = scatter_fig
                info = "3D Scatter Plot with time animation - use play button to animate"
            elif viz_type == 'pca':
                fig = pca_fig
                info = "PCA reduces demographic features to 3D space, showing main patterns"
            else:  # tsne
                fig = tsne_fig
                info = "t-SNE clustering groups countries by demographic similarity"
            
            # Update camera angle
            camera_x = 1.5 * np.cos(np.radians(camera_angle))
            camera_y = 1.5 * np.sin(np.radians(camera_angle))
            
            fig.update_layout(
                scene=dict(
                    camera=dict(
                        eye=dict(x=camera_x, y=camera_y, z=1.5)
                    )
                )
            )
            
            info_div = html.Div([
                html.H6("Current View:", style={'color': '#2c3e50'}),
                html.P(info),
                html.P(f"Camera Angle: {camera_angle}°")
            ])
            
            return fig, info_div
        
        return app


def main():
    """Run the advanced 3D explorer."""
    print("🚀 Starting Advanced 3D Population Explorer")
    print("=" * 50)
    
    # Create explorer
    explorer = Advanced3DPopulationExplorer()
    
    # Create and run Dash app
    app = explorer.create_dash_app()
    
    print("3D Explorer ready! Starting server...")
    print("Open your browser and go to: http://localhost:8051")
    print("=" * 50)
    
    app.run(debug=True, port=8051)


if __name__ == "__main__":
    main()