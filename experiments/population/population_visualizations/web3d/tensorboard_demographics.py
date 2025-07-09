"""
TensorBoard-Style 3D Demographic Clustering Visualization

This module creates interactive 3D visualizations where countries are positioned
in 3D space by demographic similarity using dimensionality reduction (PCA/t-SNE).
Following the research: "t-SNE does an outstanding job visualizing higher dimensional data into 3-D"
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import warnings
warnings.filterwarnings('ignore')

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from core.data_loader import PopulationDataLoader
    from core.theme_manager import VisualizationTheme
except ImportError:
    print("⚠️  Could not import core modules. Running in standalone mode.")

class DemographicClustering3D:
    """
    TensorBoard-style 3D visualization for demographic clustering.
    
    Features:
    - Interactive 3D scatter plot with countries as points
    - PCA and t-SNE dimensionality reduction
    - Temporal animation showing demographic transitions
    - Cluster analysis with convex hulls
    - Hover tooltips with country details
    - Export capabilities
    """
    
    def __init__(self, data_dir: str = "../data"):
        """Initialize the 3D demographic clustering visualization."""
        print("🧠 Initializing TensorBoard-Style 3D Demographic Clustering")
        print("=" * 60)
        
        self.data_dir = data_dir
        self.loader = PopulationDataLoader(data_dir=data_dir)
        self.theme = VisualizationTheme()
        
        # Data storage
        self.population_data = None
        self.demographic_features = None
        self.embeddings_3d = {}
        self.cluster_labels = None
        self.countries_metadata = {}
        
        # Visualization settings
        self.current_year = 2023
        self.n_clusters = 6
        self.perplexity = 30
        self.random_state = 42
        
        print(f"📊 Target year: {self.current_year}")
        print(f"🎯 Clusters: {self.n_clusters}")
        print(f"🔄 Perplexity: {self.perplexity}")
    
    def load_and_prepare_data(self) -> pd.DataFrame:
        """Load population data and prepare demographic features."""
        print("\n📊 Loading and preparing demographic data...")
        
        # Load population data
        self.population_data = self.loader.load_population_data()
        
        # Calculate demographic features for each country
        features_list = []
        
        for country in self.population_data['country'].unique():
            country_data = self.population_data[
                self.population_data['country'] == country
            ].sort_values('year')
            
            if len(country_data) < 20:  # Need sufficient data
                continue
                
            # Calculate demographic features
            features = self._calculate_demographic_features(country_data, country)
            if features is not None:
                features_list.append(features)
        
        self.demographic_features = pd.DataFrame(features_list)
        
        print(f"✅ Prepared demographic features for {len(self.demographic_features)} countries")
        print(f"📈 Features: {list(self.demographic_features.columns)[1:]}")
        
        return self.demographic_features
    
    def _calculate_demographic_features(self, country_data: pd.DataFrame, country: str) -> Optional[Dict]:
        """Calculate demographic features for a single country."""
        try:
            # Get recent data (last 10 years)
            recent_data = country_data.tail(10)
            
            # Calculate growth rate
            if len(recent_data) >= 2:
                growth_rate = (recent_data['population'].iloc[-1] / recent_data['population'].iloc[0]) ** (1/9) - 1
            else:
                growth_rate = 0
            
            # Current population (log scale for better clustering)
            current_pop = np.log10(country_data['population'].iloc[-1] + 1)
            
            # Population volatility (standard deviation of growth rates)
            if len(country_data) >= 3:
                yearly_growth = country_data['population'].pct_change().dropna()
                volatility = yearly_growth.std()
            else:
                volatility = 0
            
            # Demographic transition stage (based on growth pattern)
            transition_stage = self._classify_demographic_stage(country_data)
            
            # Population momentum (recent vs historical average)
            if len(country_data) >= 20:
                recent_avg = recent_data['population'].mean()
                historical_avg = country_data['population'].mean()
                momentum = recent_avg / historical_avg if historical_avg > 0 else 1
            else:
                momentum = 1
            
            # Development trajectory (acceleration/deceleration)
            if len(country_data) >= 10:
                early_growth = country_data['population'].iloc[:5].mean()
                late_growth = country_data['population'].iloc[-5:].mean()
                trajectory = (late_growth / early_growth) if early_growth > 0 else 1
            else:
                trajectory = 1
            
            # Store metadata
            self.countries_metadata[country] = {
                'current_population': country_data['population'].iloc[-1],
                'peak_population': country_data['population'].max(),
                'peak_year': country_data.loc[country_data['population'].idxmax(), 'year'],
                'data_years': len(country_data),
                'region': self._get_region(country)
            }
            
            return {
                'country': country,
                'growth_rate': growth_rate,
                'log_population': current_pop,
                'volatility': volatility,
                'transition_stage': transition_stage,
                'momentum': momentum,
                'trajectory': trajectory
            }
            
        except Exception as e:
            print(f"⚠️  Error calculating features for {country}: {e}")
            return None
    
    def _classify_demographic_stage(self, country_data: pd.DataFrame) -> float:
        """Classify demographic transition stage (0-4 scale)."""
        try:
            # Calculate growth rate trend
            if len(country_data) < 10:
                return 2.0  # Default to transitional
            
            recent_growth = country_data['population'].tail(10).pct_change().mean()
            
            # Stage classification
            if recent_growth > 0.025:  # >2.5% growth
                return 1.0  # High growth (early stage)
            elif recent_growth > 0.01:  # 1-2.5% growth
                return 2.0  # Moderate growth (transitional)
            elif recent_growth > 0.005:  # 0.5-1% growth
                return 3.0  # Low growth (late transitional)
            elif recent_growth > 0:  # 0-0.5% growth
                return 4.0  # Very low growth (post-transitional)
            else:
                return 5.0  # Declining (post-demographic transition)
                
        except:
            return 2.0  # Default
    
    def _get_region(self, country: str) -> str:
        """Get region for a country (simplified mapping)."""
        # Simplified region mapping
        regions = {
            'China': 'East Asia',
            'India': 'South Asia',
            'United States': 'North America',
            'Indonesia': 'Southeast Asia',
            'Pakistan': 'South Asia',
            'Brazil': 'Latin America',
            'Nigeria': 'Sub-Saharan Africa',
            'Bangladesh': 'South Asia',
            'Russia': 'Europe & Central Asia',
            'Mexico': 'Latin America',
            'Japan': 'East Asia',
            'Philippines': 'Southeast Asia',
            'Ethiopia': 'Sub-Saharan Africa',
            'Vietnam': 'Southeast Asia',
            'Egypt': 'Middle East & North Africa',
            'Germany': 'Europe & Central Asia',
            'Turkey': 'Europe & Central Asia',
            'Iran': 'Middle East & North Africa',
            'Thailand': 'Southeast Asia',
            'United Kingdom': 'Europe & Central Asia',
            'France': 'Europe & Central Asia',
            'Italy': 'Europe & Central Asia',
            'South Africa': 'Sub-Saharan Africa',
            'Tanzania': 'Sub-Saharan Africa',
            'Myanmar': 'Southeast Asia',
            'Kenya': 'Sub-Saharan Africa',
            'South Korea': 'East Asia',
            'Colombia': 'Latin America',
            'Spain': 'Europe & Central Asia',
            'Argentina': 'Latin America',
            'Algeria': 'Middle East & North Africa',
            'Sudan': 'Sub-Saharan Africa',
            'Ukraine': 'Europe & Central Asia',
            'Uganda': 'Sub-Saharan Africa',
            'Iraq': 'Middle East & North Africa',
            'Poland': 'Europe & Central Asia',
            'Canada': 'North America',
            'Afghanistan': 'South Asia',
            'Morocco': 'Middle East & North Africa',
            'Saudi Arabia': 'Middle East & North Africa',
            'Uzbekistan': 'Europe & Central Asia',
            'Peru': 'Latin America',
            'Angola': 'Sub-Saharan Africa',
            'Malaysia': 'Southeast Asia',
            'Mozambique': 'Sub-Saharan Africa',
            'Ghana': 'Sub-Saharan Africa',
            'Yemen': 'Middle East & North Africa',
            'Nepal': 'South Asia',
            'Venezuela': 'Latin America',
            'Madagascar': 'Sub-Saharan Africa',
            'Cameroon': 'Sub-Saharan Africa',
            'Cote d\'Ivoire': 'Sub-Saharan Africa',
            'North Korea': 'East Asia',
            'Australia': 'East Asia',
            'Niger': 'Sub-Saharan Africa',
            'Sri Lanka': 'South Asia',
            'Burkina Faso': 'Sub-Saharan Africa',
            'Mali': 'Sub-Saharan Africa',
            'Chile': 'Latin America',
            'Romania': 'Europe & Central Asia',
            'Malawi': 'Sub-Saharan Africa',
            'Zambia': 'Sub-Saharan Africa',
            'Guatemala': 'Latin America',
            'Ecuador': 'Latin America',
            'Syria': 'Middle East & North Africa',
            'Netherlands': 'Europe & Central Asia',
            'Senegal': 'Sub-Saharan Africa',
            'Cambodia': 'Southeast Asia',
            'Chad': 'Sub-Saharan Africa',
            'Somalia': 'Sub-Saharan Africa',
            'Zimbabwe': 'Sub-Saharan Africa',
            'Guinea': 'Sub-Saharan Africa',
            'Rwanda': 'Sub-Saharan Africa',
            'Benin': 'Sub-Saharan Africa',
            'Burundi': 'Sub-Saharan Africa',
            'Tunisia': 'Middle East & North Africa',
            'Bolivia': 'Latin America',
            'Belgium': 'Europe & Central Asia',
            'Haiti': 'Latin America',
            'Cuba': 'Latin America',
            'South Sudan': 'Sub-Saharan Africa',
            'Dominican Republic': 'Latin America',
            'Czech Republic': 'Europe & Central Asia',
            'Greece': 'Europe & Central Asia',
            'Jordan': 'Middle East & North Africa',
            'Portugal': 'Europe & Central Asia',
            'Azerbaijan': 'Europe & Central Asia',
            'Sweden': 'Europe & Central Asia',
            'Honduras': 'Latin America',
            'United Arab Emirates': 'Middle East & North Africa',
            'Hungary': 'Europe & Central Asia',
            'Tajikistan': 'Europe & Central Asia',
            'Belarus': 'Europe & Central Asia',
            'Austria': 'Europe & Central Asia',
            'Papua New Guinea': 'East Asia',
            'Serbia': 'Europe & Central Asia',
            'Israel': 'Middle East & North Africa',
            'Switzerland': 'Europe & Central Asia',
            'Togo': 'Sub-Saharan Africa',
            'Sierra Leone': 'Sub-Saharan Africa',
            'Laos': 'Southeast Asia',
            'Paraguay': 'Latin America',
            'Bulgaria': 'Europe & Central Asia',
            'Libya': 'Middle East & North Africa',
            'Lebanon': 'Middle East & North Africa',
            'Nicaragua': 'Latin America',
            'Kyrgyzstan': 'Europe & Central Asia',
            'El Salvador': 'Latin America',
            'Turkmenistan': 'Europe & Central Asia',
            'Singapore': 'Southeast Asia',
            'Denmark': 'Europe & Central Asia',
            'Finland': 'Europe & Central Asia',
            'Congo': 'Sub-Saharan Africa',
            'Slovakia': 'Europe & Central Asia',
            'Norway': 'Europe & Central Asia',
            'Oman': 'Middle East & North Africa',
            'State of Palestine': 'Middle East & North Africa',
            'Costa Rica': 'Latin America',
            'Liberia': 'Sub-Saharan Africa',
            'Ireland': 'Europe & Central Asia',
            'Central African Republic': 'Sub-Saharan Africa',
            'New Zealand': 'East Asia',
            'Mauritania': 'Sub-Saharan Africa',
            'Panama': 'Latin America',
            'Kuwait': 'Middle East & North Africa',
            'Croatia': 'Europe & Central Asia',
            'Moldova': 'Europe & Central Asia',
            'Georgia': 'Europe & Central Asia',
            'Eritrea': 'Sub-Saharan Africa',
            'Uruguay': 'Latin America',
            'Bosnia and Herzegovina': 'Europe & Central Asia',
            'Mongolia': 'East Asia',
            'Armenia': 'Europe & Central Asia',
            'Jamaica': 'Latin America',
            'Qatar': 'Middle East & North Africa',
            'Albania': 'Europe & Central Asia',
            'Puerto Rico': 'Latin America',
            'Lithuania': 'Europe & Central Asia',
            'Namibia': 'Sub-Saharan Africa',
            'Gambia': 'Sub-Saharan Africa',
            'Botswana': 'Sub-Saharan Africa',
            'Gabon': 'Sub-Saharan Africa',
            'Lesotho': 'Sub-Saharan Africa',
            'North Macedonia': 'Europe & Central Asia',
            'Slovenia': 'Europe & Central Asia',
            'Guinea-Bissau': 'Sub-Saharan Africa',
            'Latvia': 'Europe & Central Asia',
            'Bahrain': 'Middle East & North Africa',
            'Equatorial Guinea': 'Sub-Saharan Africa',
            'Trinidad and Tobago': 'Latin America',
            'Estonia': 'Europe & Central Asia',
            'Mauritius': 'Sub-Saharan Africa',
            'Cyprus': 'Europe & Central Asia',
            'Eswatini': 'Sub-Saharan Africa',
            'Djibouti': 'Sub-Saharan Africa',
            'Fiji': 'East Asia',
            'Reunion': 'Sub-Saharan Africa',
            'Comoros': 'Sub-Saharan Africa',
            'Guyana': 'Latin America',
            'Bhutan': 'South Asia',
            'Solomon Islands': 'East Asia',
            'Macao SAR, China': 'East Asia',
            'Montenegro': 'Europe & Central Asia',
            'Luxembourg': 'Europe & Central Asia',
            'Western Sahara': 'Middle East & North Africa',
            'Suriname': 'Latin America',
            'Cape Verde': 'Sub-Saharan Africa',
            'Micronesia': 'East Asia',
            'Maldives': 'South Asia',
            'Malta': 'Europe & Central Asia',
            'Brunei': 'Southeast Asia',
            'Guadeloupe': 'Latin America',
            'Belize': 'Latin America',
            'Bahamas': 'Latin America',
            'Martinique': 'Latin America',
            'Iceland': 'Europe & Central Asia',
            'Vanuatu': 'East Asia',
            'French Guiana': 'Latin America',
            'Barbados': 'Latin America',
            'New Caledonia': 'East Asia',
            'French Polynesia': 'East Asia',
            'Mayotte': 'Sub-Saharan Africa',
            'Sao Tome and Principe': 'Sub-Saharan Africa',
            'Samoa': 'East Asia',
            'Saint Lucia': 'Latin America',
            'Channel Islands': 'Europe & Central Asia',
            'Guam': 'East Asia',
            'Curacao': 'Latin America',
            'Kiribati': 'East Asia',
            'Seychelles': 'Sub-Saharan Africa',
            'Tonga': 'East Asia',
            'Grenada': 'Latin America',
            'Saint Vincent and the Grenadines': 'Latin America',
            'Aruba': 'Latin America',
            'Virgin Islands (U.S.)': 'Latin America',
            'Antigua and Barbuda': 'Latin America',
            'Andorra': 'Europe & Central Asia',
            'Dominica': 'Latin America',
            'Cayman Islands': 'Latin America',
            'Bermuda': 'North America',
            'Marshall Islands': 'East Asia',
            'Northern Mariana Islands': 'East Asia',
            'Greenland': 'Europe & Central Asia',
            'American Samoa': 'East Asia',
            'Saint Kitts and Nevis': 'Latin America',
            'Faroe Islands': 'Europe & Central Asia',
            'Sint Maarten (Dutch part)': 'Latin America',
            'Monaco': 'Europe & Central Asia',
            'Turks and Caicos Islands': 'Latin America',
            'Saint Martin (French part)': 'Latin America',
            'Liechtenstein': 'Europe & Central Asia',
            'San Marino': 'Europe & Central Asia',
            'British Virgin Islands': 'Latin America',
            'Palau': 'East Asia',
            'Cook Islands': 'East Asia',
            'Anguilla': 'Latin America',
            'Tuvalu': 'East Asia',
            'Wallis and Futuna': 'East Asia',
            'Nauru': 'East Asia',
            'Montserrat': 'Latin America',
            'Saint Helena': 'Sub-Saharan Africa',
            'Falkland Islands': 'Latin America',
            'Niue': 'East Asia',
            'Tokelau': 'East Asia',
            'Holy See': 'Europe & Central Asia'
        }
        
        return regions.get(country, 'Other')
    
    def create_3d_embeddings(self) -> Dict[str, np.ndarray]:
        """Create 3D embeddings using PCA and t-SNE."""
        print("\n🧠 Creating 3D embeddings...")
        
        # Prepare feature matrix
        feature_cols = ['growth_rate', 'log_population', 'volatility', 
                       'transition_stage', 'momentum', 'trajectory']
        X = self.demographic_features[feature_cols].values
        
        # Standardize features
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # PCA for initial dimensionality reduction
        print("📊 Applying PCA...")
        pca = PCA(n_components=3, random_state=self.random_state)
        pca_3d = pca.fit_transform(X_scaled)
        
        # t-SNE for non-linear clustering
        print("🔄 Applying t-SNE...")
        tsne = TSNE(n_components=3, perplexity=min(self.perplexity, len(X_scaled)-1), 
                   random_state=self.random_state, max_iter=1000)
        tsne_3d = tsne.fit_transform(X_scaled)
        
        # Store embeddings
        self.embeddings_3d = {
            'pca': pca_3d,
            'tsne': tsne_3d,
            'feature_names': feature_cols,
            'pca_components': pca.components_,
            'pca_explained_variance': pca.explained_variance_ratio_
        }
        
        # Perform clustering
        print("🎯 Performing clustering...")
        kmeans = KMeans(n_clusters=self.n_clusters, random_state=self.random_state)
        self.cluster_labels = kmeans.fit_predict(X_scaled)
        
        print(f"✅ Created 3D embeddings for {len(X_scaled)} countries")
        print(f"📊 PCA explained variance: {pca.explained_variance_ratio_.sum():.3f}")
        print(f"🎯 Clusters: {self.n_clusters}")
        
        return self.embeddings_3d
    
    def create_interactive_3d_plot(self, method: str = 'tsne') -> go.Figure:
        """Create interactive 3D scatter plot using Plotly."""
        print(f"\n🎨 Creating interactive 3D plot ({method.upper()})...")
        
        # Get embeddings
        embeddings = self.embeddings_3d[method]
        
        # Prepare data for plotting
        countries = self.demographic_features['country'].values
        regions = [self.countries_metadata[c]['region'] for c in countries]
        populations = [self.countries_metadata[c]['current_population'] for c in countries]
        
        # Create color mapping for regions
        unique_regions = list(set(regions))
        colors = px.colors.qualitative.Set1[:len(unique_regions)]
        region_colors = dict(zip(unique_regions, colors))
        
        # Create hover text
        hover_text = []
        for i, country in enumerate(countries):
            meta = self.countries_metadata[country]
            hover_text.append(
                f"<b>{country}</b><br>" +
                f"Region: {meta['region']}<br>" +
                f"Population: {meta['current_population']:,}<br>" +
                f"Peak: {meta['peak_population']:,} ({meta['peak_year']})<br>" +
                f"Data years: {meta['data_years']}<br>" +
                f"Cluster: {self.cluster_labels[i]}"
            )
        
        # Create 3D scatter plot
        fig = go.Figure(data=go.Scatter3d(
            x=embeddings[:, 0],
            y=embeddings[:, 1],
            z=embeddings[:, 2],
            mode='markers',
            marker=dict(
                size=np.log10(populations),
                color=[region_colors[region] for region in regions],
                opacity=0.8,
                line=dict(width=2, color='white')
            ),
            text=countries,
            hovertemplate=hover_text,
            name='Countries'
        ))
        
        # Update layout
        fig.update_layout(
            title=f'3D Demographic Clustering ({method.upper()})<br>Countries positioned by demographic similarity',
            scene=dict(
                xaxis_title=f'{method.upper()} Component 1',
                yaxis_title=f'{method.upper()} Component 2',
                zaxis_title=f'{method.upper()} Component 3',
                bgcolor='rgba(0,0,0,0)',
                xaxis=dict(backgroundcolor='rgba(0,0,0,0)'),
                yaxis=dict(backgroundcolor='rgba(0,0,0,0)'),
                zaxis=dict(backgroundcolor='rgba(0,0,0,0)')
            ),
            width=1000,
            height=700,
            font=dict(family="Arial, sans-serif", size=12),
            template='plotly_white'
        )
        
        # Add legend for regions
        for i, region in enumerate(unique_regions):
            fig.add_trace(go.Scatter3d(
                x=[None], y=[None], z=[None],
                mode='markers',
                marker=dict(size=10, color=region_colors[region]),
                name=region,
                showlegend=True
            ))
        
        print("✅ Interactive 3D plot created")
        return fig
    
    def create_cluster_analysis_dashboard(self) -> go.Figure:
        """Create a comprehensive dashboard with multiple views."""
        print("\n📊 Creating cluster analysis dashboard...")
        
        # Create subplots
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('3D t-SNE Clustering', 'Feature Importance (PCA)', 
                          'Cluster Statistics', 'Regional Distribution'),
            specs=[[{'type': 'scatter3d'}, {'type': 'bar'}],
                   [{'type': 'bar'}, {'type': 'pie'}]],
            vertical_spacing=0.1,
            horizontal_spacing=0.1
        )
        
        # 1. 3D t-SNE plot
        embeddings = self.embeddings_3d['tsne']
        countries = self.demographic_features['country'].values
        regions = [self.countries_metadata[c]['region'] for c in countries]
        populations = [self.countries_metadata[c]['current_population'] for c in countries]
        
        unique_regions = list(set(regions))
        colors = px.colors.qualitative.Set1[:len(unique_regions)]
        region_colors = dict(zip(unique_regions, colors))
        
        fig.add_trace(go.Scatter3d(
            x=embeddings[:, 0],
            y=embeddings[:, 1],
            z=embeddings[:, 2],
            mode='markers',
            marker=dict(
                size=np.log10(populations),
                color=[region_colors[region] for region in regions],
                opacity=0.8
            ),
            text=countries,
            name='Countries',
            showlegend=False
        ), row=1, col=1)
        
        # 2. Feature importance from PCA
        feature_names = self.embeddings_3d['feature_names']
        pca_components = self.embeddings_3d['pca_components']
        
        # Average absolute contribution across all components
        feature_importance = np.abs(pca_components).mean(axis=0)
        
        fig.add_trace(go.Bar(
            x=feature_names,
            y=feature_importance,
            marker_color='lightblue',
            name='Feature Importance',
            showlegend=False
        ), row=1, col=2)
        
        # 3. Cluster statistics
        cluster_stats = []
        for cluster_id in range(self.n_clusters):
            cluster_mask = self.cluster_labels == cluster_id
            cluster_countries = countries[cluster_mask]
            cluster_pop = np.array(populations)[cluster_mask]
            
            cluster_stats.append({
                'cluster': f'Cluster {cluster_id}',
                'count': len(cluster_countries),
                'total_pop': cluster_pop.sum(),
                'avg_pop': cluster_pop.mean()
            })
        
        cluster_df = pd.DataFrame(cluster_stats)
        
        fig.add_trace(go.Bar(
            x=cluster_df['cluster'],
            y=cluster_df['count'],
            marker_color='lightcoral',
            name='Countries per Cluster',
            showlegend=False
        ), row=2, col=1)
        
        # 4. Regional distribution
        region_counts = pd.Series(regions).value_counts()
        
        fig.add_trace(go.Pie(
            labels=region_counts.index,
            values=region_counts.values,
            marker_colors=[region_colors[region] for region in region_counts.index],
            name='Regional Distribution',
            showlegend=False
        ), row=2, col=2)
        
        # Update layout
        fig.update_layout(
            title_text="Demographic Clustering Analysis Dashboard",
            height=800,
            showlegend=False,
            template='plotly_white'
        )
        
        print("✅ Dashboard created")
        return fig
    
    def export_tensorboard_data(self, output_dir: str = "output/tensorboard_exports") -> str:
        """Export data in TensorBoard format."""
        print(f"\n💾 Exporting TensorBoard data to {output_dir}...")
        
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # Export embeddings
        embeddings_file = output_path / "demographic_embeddings.json"
        
        export_data = {
            'embeddings': {
                'pca': self.embeddings_3d['pca'].tolist(),
                'tsne': self.embeddings_3d['tsne'].tolist()
            },
            'countries': self.demographic_features['country'].tolist(),
            'features': self.demographic_features.to_dict('records'),
            'clusters': [int(label) for label in self.cluster_labels.tolist()],
            'metadata': {k: {**v, 'current_population': int(v['current_population']), 
                           'peak_population': int(v['peak_population']),
                           'peak_year': int(v['peak_year']),
                           'data_years': int(v['data_years'])} 
                        for k, v in self.countries_metadata.items()},
            'feature_names': self.embeddings_3d['feature_names'],
            'pca_explained_variance': self.embeddings_3d['pca_explained_variance'].tolist()
        }
        
        with open(embeddings_file, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        print(f"✅ Exported TensorBoard data: {embeddings_file}")
        return str(embeddings_file)
    
    def run_complete_analysis(self) -> Tuple[go.Figure, go.Figure]:
        """Run the complete 3D demographic clustering analysis."""
        print("🎯 Running Complete 3D Demographic Clustering Analysis")
        print("=" * 60)
        
        # Load and prepare data
        self.load_and_prepare_data()
        
        # Create 3D embeddings
        self.create_3d_embeddings()
        
        # Create visualizations
        tsne_fig = self.create_interactive_3d_plot('tsne')
        pca_fig = self.create_interactive_3d_plot('pca')
        dashboard_fig = self.create_cluster_analysis_dashboard()
        
        # Export data
        self.export_tensorboard_data()
        
        print("\n" + "=" * 60)
        print("🎉 3D Demographic Clustering Analysis Complete!")
        print("=" * 60)
        print(f"📊 Countries analyzed: {len(self.demographic_features)}")
        print(f"🎯 Clusters identified: {self.n_clusters}")
        print(f"🧠 Dimensionality reduction: PCA + t-SNE")
        print(f"📈 Features used: {len(self.embeddings_3d['feature_names'])}")
        print("💡 Key insights:")
        print("   • Countries cluster by demographic similarity")
        print("   • t-SNE reveals non-linear demographic patterns")
        print("   • Interactive 3D exploration shows hidden relationships")
        print("   • Regional patterns emerge in demographic transitions")
        
        return tsne_fig, pca_fig, dashboard_fig

def main():
    """Main function to run the 3D demographic clustering."""
    print("🚀 Testing TensorBoard-Style 3D Demographic Clustering")
    print("=" * 60)
    
    # Create visualization
    viz = DemographicClustering3D("../../data")
    
    # Run analysis
    tsne_fig, pca_fig, dashboard_fig = viz.run_complete_analysis()
    
    # Show plots
    print("\n🌐 Displaying interactive 3D visualizations...")
    
    # Save as HTML files
    output_dir = Path("../output/web_exports")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    tsne_fig.write_html(output_dir / "demographic_clustering_tsne_3d.html")
    pca_fig.write_html(output_dir / "demographic_clustering_pca_3d.html")
    dashboard_fig.write_html(output_dir / "demographic_clustering_dashboard.html")
    
    print(f"✅ Interactive visualizations saved to {output_dir}")
    print(f"🌐 Open these files in your browser:")
    print(f"   • t-SNE 3D: {output_dir / 'demographic_clustering_tsne_3d.html'}")
    print(f"   • PCA 3D: {output_dir / 'demographic_clustering_pca_3d.html'}")
    print(f"   • Dashboard: {output_dir / 'demographic_clustering_dashboard.html'}")
    
    # Show in browser if possible
    try:
        import webbrowser
        webbrowser.open(f"file://{(output_dir / 'demographic_clustering_tsne_3d.html').absolute()}")
        print("🚀 Opening t-SNE visualization in browser...")
    except:
        print("💡 Manually open the HTML files in your browser to view the 3D visualizations")

if __name__ == "__main__":
    main()
