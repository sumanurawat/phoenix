"""
3D Population Visualization Web Interface

This module creates interactive 3D visualizations using Three.js and WebGL,
following the research-backed approach for population data visualization.
"""

from .density_surface import PopulationDensitySurface3D
from .demographic_clustering import DemographicClustering3D
from .migration_flows import MigrationFlows3D

__all__ = [
    'PopulationDensitySurface3D',
    'DemographicClustering3D', 
    'MigrationFlows3D'
]
