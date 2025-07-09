"""
Professional Population Visualization Core Module

This module provides core infrastructure for World Bank population data
visualization including data loading, theme management, and base chart classes.
"""

__version__ = "1.0.0"
__author__ = "Population Analytics Team"

from .data_loader import PopulationDataLoader
from .theme_manager import VisualizationTheme
from .chart_base import BaseChart

__all__ = [
    'PopulationDataLoader',
    'VisualizationTheme', 
    'BaseChart'
]
