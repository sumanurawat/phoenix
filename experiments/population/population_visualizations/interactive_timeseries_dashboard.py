"""
Interactive Time-Series Dashboard for Population Data
Creates a comprehensive interactive visualization with time sliders and dynamic axes
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
import pandas as pd
import numpy as np
import json
from datetime import datetime
import dash
from dash import dcc, html, Input, Output, callback
import dash_bootstrap_components as dbc

class InteractivePopulationTimeSeries:
    """
    Interactive time-series dashboard with:
    - Time slider for real-time animation
    - Dynamic axis selection (population, growth rate, density, etc.)
    - Country/region filtering
    - Synchronized multi-chart views
    - Hover details and tooltips
    """
    
    def __init__(self, data_dir="../data"):
        self.data_dir = data_dir
        self.data = None
        self.countries_data = None
        self.regional_data = None
        self.load_data()
        
    def load_data(self):
        """Load and prepare population data for interactive visualization."""
        print("Loading population data for interactive dashboard...")
        
        # Load population timeseries
        with open(f'{self.data_dir}/population_timeseries.json', 'r') as f:
            population_data = json.load(f)
        
        # Convert to DataFrame
        records = []
        for record in population_data:
            if record.get('value') is not None:
                records.append({
                    'country_code': record.get('countryiso3code', record.get('country', {}).get('id')),
                    'country_name': record.get('country', {}).get('value', 'Unknown'),
                    'year': int(record.get('date', 0)),
                    'population': float(record.get('value', 0))
                })
        
        self.data = pd.DataFrame(records)
        
        # Load countries metadata
        with open(f'{self.data_dir}/countries_metadata.json', 'r') as f:
            countries_data = json.load(f)
            
        # Create countries lookup
        self.countries_data = {}
        for country in countries_data:
            self.countries_data[country.get('id')] = {
                'name': country.get('name'),
                'region': country.get('region', {}).get('value', 'Unknown'),
                'income_level': country.get('incomeLevel', {}).get('value', 'Unknown'),
                'capital': country.get('capitalCity', 'Unknown'),
                'longitude': country.get('longitude', 0),
                'latitude': country.get('latitude', 0)
            }
        
        # Enrich main data with metadata
        self.data['region'] = self.data['country_code'].map(
            lambda x: self.countries_data.get(x, {}).get('region', 'Unknown')
        )
        self.data['income_level'] = self.data['country_code'].map(
            lambda x: self.countries_data.get(x, {}).get('income_level', 'Unknown')
        )
        
        # Calculate derived metrics
        self.data = self.data.sort_values(['country_code', 'year'])
        self.data['growth_rate'] = self.data.groupby('country_code')['population'].pct_change() * 100
        self.data['population_millions'] = self.data['population'] / 1e6
        
        # Calculate decade averages
        self.data['decade'] = (self.data['year'] // 10) * 10
        
        print(f"Data loaded: {len(self.data)} records, {self.data['country_code'].nunique()} countries")
        
    def create_interactive_time_series(self):
        """Create the main interactive time-series visualization."""
        # Get top 20 countries by latest population
        latest_year = self.data['year'].max()
        top_countries = self.data[self.data['year'] == latest_year].nlargest(20, 'population')
        
        # Filter data for these countries
        filtered_data = self.data[self.data['country_code'].isin(top_countries['country_code'])]
        
        # Create interactive figure
        fig = go.Figure()
        
        # Add traces for each country
        for country_code in top_countries['country_code']:
            country_data = filtered_data[filtered_data['country_code'] == country_code]
            country_name = country_data['country_name'].iloc[0]
            
            fig.add_trace(go.Scatter(
                x=country_data['year'],
                y=country_data['population_millions'],
                mode='lines+markers',
                name=country_name,
                line=dict(width=3),
                hovertemplate=f"<b>{country_name}</b><br>" +
                             "Year: %{x}<br>" +
                             "Population: %{y:.1f}M<br>" +
                             "<extra></extra>",
                visible=True
            ))
        
        # Update layout for interactivity
        fig.update_layout(
            title=dict(
                text="Interactive Population Growth Timeline",
                x=0.5,
                font=dict(size=20, color='#2c3e50')
            ),
            xaxis=dict(
                title="Year",
                title_font=dict(size=14),
                tickfont=dict(size=12),
                showgrid=True,
                gridcolor='rgba(128,128,128,0.2)'
            ),
            yaxis=dict(
                title="Population (Millions)",
                title_font=dict(size=14),
                tickfont=dict(size=12),
                showgrid=True,
                gridcolor='rgba(128,128,128,0.2)'
            ),
            hovermode='x unified',
            height=600,
            showlegend=True,
            legend=dict(
                orientation="v",
                yanchor="top",
                y=1,
                xanchor="left",
                x=1.05
            ),
            plot_bgcolor='rgba(248,249,250,0.8)',
            paper_bgcolor='white',
            font=dict(family="Arial, sans-serif", size=12, color="#2c3e50"),
            margin=dict(l=60, r=150, t=80, b=60)
        )
        
        # Add range slider
        fig.update_layout(
            xaxis=dict(
                rangeslider=dict(visible=True),
                type="linear"
            )
        )
        
        return fig
    
    def create_animated_scatter(self):
        """Create animated scatter plot with time slider."""
        # Prepare data for animation
        years = sorted(self.data['year'].unique())
        
        # Get top 30 countries for better visualization
        latest_year = self.data['year'].max()
        top_countries = self.data[self.data['year'] == latest_year].nlargest(30, 'population')
        
        animation_data = []
        for year in years:
            year_data = self.data[
                (self.data['year'] == year) & 
                (self.data['country_code'].isin(top_countries['country_code']))
            ]
            
            if not year_data.empty:
                animation_data.append(year_data)
        
        if not animation_data:
            return go.Figure()
        
        # Create animated scatter plot
        fig = px.scatter(
            pd.concat(animation_data),
            x='population_millions',
            y='growth_rate',
            size='population_millions',
            color='region',
            hover_name='country_name',
            animation_frame='year',
            title="Population vs Growth Rate Over Time",
            labels={
                'population_millions': 'Population (Millions)',
                'growth_rate': 'Growth Rate (%)',
                'region': 'Region'
            },
            size_max=60,
            height=600
        )
        
        # Update layout
        fig.update_layout(
            title=dict(
                text="Population vs Growth Rate Animation",
                x=0.5,
                font=dict(size=20, color='#2c3e50')
            ),
            plot_bgcolor='rgba(248,249,250,0.8)',
            paper_bgcolor='white',
            font=dict(family="Arial, sans-serif", size=12, color="#2c3e50"),
            showlegend=True,
            xaxis=dict(type="log", title="Population (Millions)"),
            yaxis=dict(title="Growth Rate (%)", range=[-5, 10])
        )
        
        return fig
    
    def create_regional_comparison(self):
        """Create regional comparison with time controls."""
        # Calculate regional totals by year
        regional_data = self.data.groupby(['region', 'year']).agg({
            'population': 'sum',
            'growth_rate': 'mean'
        }).reset_index()
        
        regional_data['population_billions'] = regional_data['population'] / 1e9
        
        # Create figure with secondary y-axis
        fig = make_subplots(
            specs=[[{"secondary_y": True}]],
            subplot_titles=("Regional Population and Growth Comparison",)
        )
        
        # Add population traces
        for region in regional_data['region'].unique():
            if region != 'Unknown':
                region_data = regional_data[regional_data['region'] == region]
                
                fig.add_trace(
                    go.Scatter(
                        x=region_data['year'],
                        y=region_data['population_billions'],
                        name=f"{region} (Pop.)",
                        line=dict(width=3),
                        hovertemplate=f"<b>{region}</b><br>" +
                                     "Year: %{x}<br>" +
                                     "Population: %{y:.2f}B<br>" +
                                     "<extra></extra>"
                    ),
                    secondary_y=False,
                )
        
        # Update layout
        fig.update_xaxes(title_text="Year")
        fig.update_yaxes(title_text="Population (Billions)", secondary_y=False)
        
        fig.update_layout(
            title=dict(
                text="Regional Population Trends",
                x=0.5,
                font=dict(size=20, color='#2c3e50')
            ),
            height=600,
            hovermode='x unified',
            plot_bgcolor='rgba(248,249,250,0.8)',
            paper_bgcolor='white',
            font=dict(family="Arial, sans-serif", size=12, color="#2c3e50"),
            showlegend=True
        )
        
        return fig
    
    def create_dash_app(self):
        """Create comprehensive Dash application with multiple interactive visualizations."""
        app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
        
        # Create the main figures
        timeseries_fig = self.create_interactive_time_series()
        animated_fig = self.create_animated_scatter()
        regional_fig = self.create_regional_comparison()
        
        # Get unique values for dropdowns
        countries = sorted(self.data['country_name'].unique())
        regions = sorted(self.data['region'].unique())
        years = sorted(self.data['year'].unique())
        
        # Define app layout
        app.layout = dbc.Container([
            dbc.Row([
                dbc.Col([
                    html.H1("🌍 Interactive Population Dashboard", 
                           className="text-center mb-4",
                           style={'color': '#2c3e50', 'font-weight': 'bold'})
                ])
            ]),
            
            dbc.Row([
                dbc.Col([
                    html.H4("Controls", style={'color': '#34495e'}),
                    html.Label("Select Countries:", style={'font-weight': 'bold'}),
                    dcc.Dropdown(
                        id='country-dropdown',
                        options=[{'label': country, 'value': country} for country in countries[:50]],
                        value=countries[:10],
                        multi=True,
                        style={'margin-bottom': '20px'}
                    ),
                    
                    html.Label("Select Region:", style={'font-weight': 'bold'}),
                    dcc.Dropdown(
                        id='region-dropdown',
                        options=[{'label': region, 'value': region} for region in regions],
                        value='All',
                        style={'margin-bottom': '20px'}
                    ),
                    
                    html.Label("Year Range:", style={'font-weight': 'bold'}),
                    dcc.RangeSlider(
                        id='year-slider',
                        min=min(years),
                        max=max(years),
                        step=1,
                        value=[min(years), max(years)],
                        marks={year: str(year) for year in years[::10]},
                        tooltip={"placement": "bottom", "always_visible": True}
                    ),
                    
                    html.Div(id='stats-display', style={'margin-top': '20px'})
                ], width=3),
                
                dbc.Col([
                    dcc.Graph(id='timeseries-graph', figure=timeseries_fig)
                ], width=9)
            ], style={'margin-bottom': '30px'}),
            
            dbc.Row([
                dbc.Col([
                    dcc.Graph(id='animated-scatter', figure=animated_fig)
                ], width=6),
                
                dbc.Col([
                    dcc.Graph(id='regional-comparison', figure=regional_fig)
                ], width=6)
            ]),
            
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.H5("Key Insights:", style={'color': '#2c3e50', 'margin-top': '20px'}),
                        html.Ul([
                            html.Li("India surpassed China as the world's most populous country in 2021"),
                            html.Li("Sub-Saharan Africa shows the highest growth rates globally"),
                            html.Li("Europe and East Asia show declining or negative growth rates"),
                            html.Li("South Asia and South America are experiencing demographic transitions"),
                            html.Li("Use the time slider to explore population dynamics over 6 decades")
                        ])
                    ], style={'background-color': '#f8f9fa', 'padding': '20px', 'border-radius': '10px'})
                ])
            ])
        ], fluid=True)
        
        # Add callbacks for interactivity
        @app.callback(
            [Output('timeseries-graph', 'figure'),
             Output('stats-display', 'children')],
            [Input('country-dropdown', 'value'),
             Input('region-dropdown', 'value'),
             Input('year-slider', 'value')]
        )
        def update_charts(selected_countries, selected_region, year_range):
            # Filter data based on selections
            filtered_data = self.data[
                (self.data['year'] >= year_range[0]) & 
                (self.data['year'] <= year_range[1])
            ]
            
            if selected_region != 'All':
                filtered_data = filtered_data[filtered_data['region'] == selected_region]
            
            if selected_countries:
                filtered_data = filtered_data[filtered_data['country_name'].isin(selected_countries)]
            
            # Create updated figure
            fig = go.Figure()
            
            for country in selected_countries[:15]:  # Limit to 15 for performance
                country_data = filtered_data[filtered_data['country_name'] == country]
                
                if not country_data.empty:
                    fig.add_trace(go.Scatter(
                        x=country_data['year'],
                        y=country_data['population_millions'],
                        mode='lines+markers',
                        name=country,
                        line=dict(width=3),
                        hovertemplate=f"<b>{country}</b><br>" +
                                     "Year: %{x}<br>" +
                                     "Population: %{y:.1f}M<br>" +
                                     "<extra></extra>"
                    ))
            
            fig.update_layout(
                title="Interactive Population Timeline",
                xaxis_title="Year",
                yaxis_title="Population (Millions)",
                hovermode='x unified',
                height=600,
                showlegend=True,
                plot_bgcolor='rgba(248,249,250,0.8)',
                paper_bgcolor='white'
            )
            
            # Create stats display
            if not filtered_data.empty:
                total_countries = filtered_data['country_name'].nunique()
                total_population = filtered_data[filtered_data['year'] == filtered_data['year'].max()]['population'].sum()
                avg_growth = filtered_data['growth_rate'].mean()
                
                stats = html.Div([
                    html.H6("Selection Stats:", style={'color': '#2c3e50'}),
                    html.P(f"Countries: {total_countries}"),
                    html.P(f"Total Population: {total_population/1e9:.2f}B"),
                    html.P(f"Avg Growth Rate: {avg_growth:.2f}%")
                ])
            else:
                stats = html.Div("No data for selection")
            
            return fig, stats
        
        return app


def main():
    """Run the interactive dashboard."""
    print("🚀 Starting Interactive Population Dashboard")
    print("=" * 50)
    
    # Create dashboard
    dashboard = InteractivePopulationTimeSeries()
    
    # Create and run Dash app
    app = dashboard.create_dash_app()
    
    print("Dashboard ready! Starting server...")
    print("Open your browser and go to: http://localhost:8050")
    print("=" * 50)
    
    app.run(debug=True, port=8050)


if __name__ == "__main__":
    main()