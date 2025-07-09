"""
World Bank Data Report Generator
Creates comprehensive markdown documentation of the analysis.
"""

import json
import logging
from typing import Dict, List, Optional
from datetime import datetime
import os

class ReportGenerator:
    """
    Generates comprehensive markdown reports from analysis results.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.analysis_results = {}
        self.quality_results = {}
        
        self._load_results()
    
    def _load_results(self):
        """Load analysis and quality results."""
        try:
            # Load analysis results
            if os.path.exists('outputs/analysis_summary.json'):
                with open('outputs/analysis_summary.json', 'r') as f:
                    self.analysis_results = json.load(f)
            
            # Load quality results
            if os.path.exists('outputs/data_quality_report.json'):
                with open('outputs/data_quality_report.json', 'r') as f:
                    self.quality_results = json.load(f)
            
            self.logger.info("Loaded analysis and quality results for reporting")
            
        except Exception as e:
            self.logger.warning(f"Could not load some results: {e}")
    
    def generate_executive_summary(self) -> str:
        """Generate executive summary section."""
        summary = "## Executive Summary\n\n"
        
        # Get key metrics
        data_summary = self.analysis_results.get('data_summary', {})
        basic_stats = self.analysis_results.get('basic_statistics', {})
        
        total_countries = data_summary.get('total_countries', 'Unknown')
        year_range = data_summary.get('year_range', 'Unknown')
        total_records = data_summary.get('total_records', 'Unknown')
        
        summary += f"**Analysis Overview:**\n"
        summary += f"- **Total Records Analyzed:** {total_records:,}\n" if isinstance(total_records, (int, float)) else f"- **Total Records Analyzed:** {total_records}\n"
        summary += f"- **Geographic Coverage:** {total_countries} countries\n"
        summary += f"- **Temporal Coverage:** {year_range}\n"
        summary += f"- **Analysis Date:** {datetime.now().strftime('%B %d, %Y')}\n\n"
        
        # Key findings
        key_findings = self.analysis_results.get('key_findings', [])
        
        if key_findings:
            summary += "**Key Findings:**\n"
            for finding in key_findings:
                summary += f"- {finding}\n"
        
        # Data quality summary
        quality_summary = self.quality_results.get('summary', {})
        overall_quality = quality_summary.get('overall_quality_score', 'N/A')
        quality_grade = quality_summary.get('quality_grade', 'N/A')
        
        summary += f"\n**Data Quality Score:** {overall_quality}/100 ({quality_grade})\n\n"
        
        return summary
    
    def generate_data_overview(self) -> str:
        """Generate data overview section."""
        overview = "## Data Overview\n\n"
        
        overview += "### Available Indicators\n\n"
        overview += "| Indicator Code | Description | Coverage |\n"
        overview += "|----------------|-------------|----------|\n"
        overview += "| SP.POP.TOTL | Total Population | Primary indicator with full coverage |\n"
        overview += "| SP.POP.GROW | Population Growth Rate | Available for top 20 countries |\n"
        overview += "| SP.URB.TOTL | Urban Population | Available for top 20 countries |\n"
        overview += "| SP.RUR.TOTL | Rural Population | Available for top 20 countries |\n"
        overview += "| SP.POP.DPND | Age Dependency Ratio | Available for top 20 countries |\n"
        overview += "| EN.POP.DNST | Population Density | Available for top 20 countries |\n\n"
        
        # Geographic coverage
        data_summary = self.analysis_results.get('data_summary', {})
        overview += "### Geographic Coverage\n\n"
        overview += f"- **Total Countries:** {data_summary.get('total_countries', 'N/A')}\n"
        overview += f"- **Regional Aggregates:** 7 major regions\n"
        overview += f"- **World Total:** Available\n\n"
        
        # Temporal coverage
        overview += "### Temporal Coverage\n\n"
        overview += f"- **Year Range:** {data_summary.get('year_range', 'N/A')}\n"
        overview += f"- **Update Frequency:** Annual\n"
        overview += f"- **Latest Available:** Most recent data varies by country\n\n"
        
        return overview
    
    def generate_quality_assessment(self) -> str:
        """Generate data quality assessment section."""
        quality = "## Data Quality Assessment\n\n"
        
        # Overall scores
        quality_summary = self.quality_results.get('summary', {})
        component_scores = quality_summary.get('component_scores', {})
        
        quality += "### Quality Scores by Component\n\n"
        quality += "| Component | Score | Grade |\n"
        quality += "|-----------|-------|-------|\n"
        
        for component, score in component_scores.items():
            grade = self._score_to_grade(score)
            quality += f"| {component.title()} | {score}/100 | {grade} |\n"
        
        overall_score = quality_summary.get('overall_quality_score', 0)
        overall_grade = quality_summary.get('quality_grade', 'N/A')
        quality += f"| **Overall** | **{overall_score}/100** | **{overall_grade}** |\n\n"
        
        # Completeness details
        completeness = self.quality_results.get('completeness', {})
        quality += "### Completeness Analysis\n\n"
        quality += f"- **Overall Completeness:** {completeness.get('overall_completeness_percentage', 'N/A')}%\n"
        quality += f"- **Total Records:** {completeness.get('total_records', 'N/A'):,}\n"
        quality += f"- **Missing Records:** {completeness.get('missing_records', 'N/A'):,}\n\n"
        
        # Countries with data issues
        worst_countries = completeness.get('countries_with_most_missing_data', [])[:5]
        if worst_countries:
            quality += "**Countries with Most Missing Data:**\n"
            for country in worst_countries:
                quality += f"- {country.get('country_code', 'N/A')}: {country.get('missing_percentage', 'N/A')}% missing\n"
            quality += "\n"
        
        # Recommended countries for demo
        demo_countries = quality_summary.get('recommended_demo_countries', [])
        if demo_countries:
            quality += "### Recommended Countries for Demo (Best Data Quality)\n\n"
            for i, country in enumerate(demo_countries[:10], 1):
                quality += f"{i}. {country}\n"
            quality += "\n"
        
        return quality
    
    def _score_to_grade(self, score: float) -> str:
        """Convert numeric score to letter grade."""
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"
    
    def generate_statistical_insights(self) -> str:
        """Generate statistical insights section."""
        insights = "## Statistical Insights\n\n"
        
        # Basic statistics
        basic_stats = self.analysis_results.get('basic_statistics', {})
        world_pop = basic_stats.get('world_population_latest', 0)
        world_growth = basic_stats.get('world_population_growth_2023', 0)
        
        insights += "### World Population Milestones\n\n"
        insights += f"- **Current World Population:** {world_pop:,.0f}\n"
        insights += f"- **Current Growth Rate:** {world_growth:.2f}%\n\n"
        
        pop_stats = basic_stats.get('population_statistics', {})
        if pop_stats:
            insights += "### Country Population Statistics\n\n"
            insights += f"- **Mean Country Population:** {pop_stats.get('mean', 0):,.0f}\n"
            insights += f"- **Median Country Population:** {pop_stats.get('median', 0):,.0f}\n"
            insights += f"- **Largest Country:** {pop_stats.get('max', 0):,.0f}\n"
            insights += f"- **Smallest Country:** {pop_stats.get('min', 0):,.0f}\n\n"
        
        # Growth analysis
        growth_analysis = self.analysis_results.get('growth_analysis', {})
        fastest_growing = growth_analysis.get('fastest_growing', [])
        declining = growth_analysis.get('declining_populations', [])
        
        if fastest_growing:
            insights += "### Fastest Growing Countries\n\n"
            insights += "| Country | Growth Rate | Population |\n"
            insights += "|---------|-------------|------------|\n"
            for country in fastest_growing[:5]:
                name = country.get('country_name', 'N/A')
                growth = country.get('growth_rate', 0)
                pop = country.get('population', 0)
                insights += f"| {name} | {growth:.2f}% | {pop:,.0f} |\n"
            insights += "\n"
        
        if declining:
            insights += "### Countries with Declining Populations\n\n"
            insights += "| Country | Growth Rate | Population |\n"
            insights += "|---------|-------------|------------|\n"
            for country in declining[:5]:
                name = country.get('country_name', 'N/A')
                growth = country.get('growth_rate', 0)
                pop = country.get('population', 0)
                insights += f"| {name} | {growth:.2f}% | {pop:,.0f} |\n"
            insights += "\n"
        
        # Regional analysis
        regional_analysis = self.analysis_results.get('regional_analysis', {})
        if regional_analysis:
            insights += "### Regional Growth Leaders\n\n"
            
            # Sort regions by growth rate
            regions_by_growth = sorted(
                regional_analysis.items(),
                key=lambda x: x[1].get('growth_rate_latest', 0),
                reverse=True
            )
            
            insights += "| Region | Current Population | Growth Rate | World Share |\n"
            insights += "|--------|-------------------|-------------|-------------|\n"
            
            for region_code, data in regions_by_growth[:5]:
                name = data.get('name', region_code)
                pop = data.get('current_population', 0)
                growth = data.get('growth_rate_latest', 0)
                share = data.get('world_share_percent', 0)
                insights += f"| {name} | {pop:,.0f} | {growth:.2f}% | {share:.1f}% |\n"
            insights += "\n"
        
        # Interesting anomalies
        insights += "### Interesting Findings\n\n"
        
        # China vs India crossover
        ranking_analysis = self.analysis_results.get('ranking_analysis', {})
        china_india = ranking_analysis.get('china_india_crossover', {})
        
        if china_india.get('crossover_occurred'):
            crossover_year = china_india.get('crossover_year')
            insights += f"- India surpassed China as the world's most populous country in {crossover_year}\n"
        else:
            gap_direction = china_india.get('gap_direction', 'Unknown')
            insights += f"- Population race: {gap_direction}\n"
        
        # Statistical tests
        stat_tests = self.analysis_results.get('statistical_tests', {})
        world_trends = stat_tests.get('world_population_trends', {})
        if world_trends:
            best_fit = world_trends.get('best_fit', 'linear')
            insights += f"- World population growth follows a {best_fit} pattern\n"
        
        insights += "\n"
        
        return insights
    
    def generate_technical_specifications(self) -> str:
        """Generate technical specifications section."""
        tech = "## Technical Specifications\n\n"
        
        tech += "### API Information\n\n"
        tech += "- **Base URL:** https://api.worldbank.org/v2/\n"
        tech += "- **Rate Limit:** 5 requests per second (implemented)\n"
        tech += "- **Response Format:** JSON\n"
        tech += "- **Pagination:** 300 records per page\n"
        tech += "- **Retry Logic:** Exponential backoff implemented\n\n"
        
        tech += "### Data Storage\n\n"
        data_summary = self.analysis_results.get('data_summary', {})
        total_records = data_summary.get('total_records', 0)
        
        tech += f"- **Total Records Processed:** {total_records:,}\n"
        tech += "- **Storage Format:** JSON files\n"
        tech += "- **Estimated Data Size:** ~50MB for full dataset\n\n"
        
        tech += "### Query Optimization Recommendations\n\n"
        tech += "1. **Batch Requests:** Use country groups (e.g., 'CHN;IND;USA') for efficiency\n"
        tech += "2. **Date Ranges:** Specify date ranges to reduce payload size\n"
        tech += "3. **Caching:** Implement local caching for frequently accessed data\n"
        tech += "4. **Pagination:** Handle pagination for large datasets\n"
        tech += "5. **Error Handling:** Implement robust retry logic for API failures\n\n"
        
        return tech
    
    def generate_visualization_recommendations(self) -> str:
        """Generate visualization recommendations section."""
        viz = "## Visualization Recommendations\n\n"
        
        viz += "### Most Impactful Visualizations\n\n"
        
        recommendations = [
            {
                "type": "World Population Growth Timeline",
                "description": "Line chart showing world population from 1960-2023 with milestone annotations",
                "impact": "High - Shows the dramatic acceleration in global population",
                "interactivity": "Hover for exact values, zoom functionality"
            },
            {
                "type": "Animated Country Rankings",
                "description": "Bar chart race showing top 10 countries over time",
                "impact": "Very High - Engaging way to show changing demographics",
                "interactivity": "Play/pause controls, year slider"
            },
            {
                "type": "Regional Comparison Dashboard",
                "description": "Multi-chart dashboard comparing regional growth patterns",
                "impact": "High - Allows users to explore regional differences",
                "interactivity": "Toggle regions, time period selection"
            },
            {
                "type": "Growth Rate Heatmap",
                "description": "Country x Year heatmap showing growth rate patterns",
                "impact": "Medium - Good for identifying patterns and anomalies",
                "interactivity": "Country selection, decade filtering"
            },
            {
                "type": "Population Bubble Chart",
                "description": "Scatter plot with population size, growth rate, and time",
                "impact": "Medium - Shows relationships between multiple variables",
                "interactivity": "Country highlighting, time animation"
            }
        ]
        
        viz += "| Visualization Type | Impact | Key Features |\n"
        viz += "|--------------------|--------|-------------|\n"
        
        for rec in recommendations:
            viz += f"| {rec['type']} | {rec['impact']} | {rec['interactivity']} |\n"
        
        viz += "\n### Interactive Features to Implement\n\n"
        viz += "1. **Time Controls:**\n"
        viz += "   - Play/pause animation\n"
        viz += "   - Year range slider\n"
        viz += "   - Speed controls\n\n"
        
        viz += "2. **Country Selection:**\n"
        viz += "   - Multi-select dropdown\n"
        viz += "   - Search functionality\n"
        viz += "   - Regional grouping\n\n"
        
        viz += "3. **Data Export:**\n"
        viz += "   - Download chart as PNG/SVG\n"
        viz += "   - Export data as CSV\n"
        viz += "   - Share chart URL\n\n"
        
        viz += "4. **Comparative Analysis:**\n"
        viz += "   - Side-by-side country comparison\n"
        viz += "   - Benchmark against regional average\n"
        viz += "   - Custom time period comparison\n\n"
        
        return viz
    
    def generate_dashboard_features(self) -> str:
        """Generate dashboard feature suggestions section."""
        features = "## Dashboard Feature Suggestions\n\n"
        
        features += "### Core Features (MVP)\n\n"
        features += "1. **Country Explorer**\n"
        features += "   - Search and select countries\n"
        features += "   - View population timeline\n"
        features += "   - Compare with regional average\n\n"
        
        features += "2. **Regional Overview**\n"
        features += "   - Regional population share pie chart\n"
        features += "   - Growth rate comparison\n"
        features += "   - Historical trends\n\n"
        
        features += "3. **Global Trends**\n"
        features += "   - World population milestone tracker\n"
        features += "   - Growth rate evolution\n"
        features += "   - Population projections\n\n"
        
        features += "4. **Top Lists**\n"
        features += "   - Most populous countries\n"
        features += "   - Fastest growing countries\n"
        features += "   - Ranking changes over time\n\n"
        
        features += "### Advanced Features\n\n"
        features += "1. **Predictive Analytics**\n"
        features += "   - Simple population projections\n"
        features += "   - Growth trajectory analysis\n"
        features += "   - Demographic transition detection\n\n"
        
        features += "2. **Data Quality Indicators**\n"
        features += "   - Data availability indicators\n"
        features += "   - Confidence levels\n"
        features += "   - Source attribution\n\n"
        
        features += "3. **Custom Analysis**\n"
        features += "   - User-defined country groups\n"
        features += "   - Custom time periods\n"
        features += "   - Statistical comparisons\n\n"
        
        features += "### User Experience Features\n\n"
        features += "1. **Onboarding**\n"
        features += "   - Interactive tutorial\n"
        features += "   - Sample analyses\n"
        features += "   - Key insights highlights\n\n"
        
        features += "2. **Accessibility**\n"
        features += "   - Color-blind friendly palettes\n"
        features += "   - Keyboard navigation\n"
        features += "   - Screen reader support\n\n"
        
        features += "3. **Performance**\n"
        features += "   - Progressive data loading\n"
        features += "   - Cached queries\n"
        features += "   - Responsive design\n\n"
        
        return features
    
    def generate_appendices(self) -> str:
        """Generate appendices section."""
        appendices = "## Appendices\n\n"
        
        # Country list with quality scores
        appendices += "### Appendix A: Country Data Quality Scores\n\n"
        
        accuracy_data = self.quality_results.get('accuracy', {})
        reliability_data = accuracy_data.get('data_source_reliability', {})
        most_reliable = reliability_data.get('most_reliable_countries', [])
        
        if most_reliable:
            appendices += "**Top 10 Most Reliable Countries:**\n\n"
            appendices += "| Rank | Country | Quality Score |\n"
            appendices += "|------|---------|---------------|\n"
            
            for i, (country_code, data) in enumerate(most_reliable[:10], 1):
                score = data.get('score', 0)
                appendices += f"| {i} | {country_code} | {score:.1f}/100 |\n"
            appendices += "\n"
        
        # API documentation
        appendices += "### Appendix B: API Endpoint Reference\n\n"
        
        endpoints = [
            {
                "endpoint": "/country",
                "description": "List all countries with metadata",
                "example": "https://api.worldbank.org/v2/country?format=json"
            },
            {
                "endpoint": "/country/all/indicator/SP.POP.TOTL",
                "description": "Population data for all countries",
                "example": "https://api.worldbank.org/v2/country/all/indicator/SP.POP.TOTL?date=2020&format=json"
            },
            {
                "endpoint": "/country/{iso3}/indicator/SP.POP.TOTL",
                "description": "Population data for specific country",
                "example": "https://api.worldbank.org/v2/country/USA/indicator/SP.POP.TOTL?format=json"
            }
        ]
        
        appendices += "| Endpoint | Description | Example |\n"
        appendices += "|----------|-------------|----------|\n"
        
        for endpoint in endpoints:
            appendices += f"| `{endpoint['endpoint']}` | {endpoint['description']} | [Link]({endpoint['example']}) |\n"
        
        appendices += "\n### Appendix C: Data Dictionary\n\n"
        
        indicators = [
            ("SP.POP.TOTL", "Total Population", "Total population count for a country/region"),
            ("SP.POP.GROW", "Population Growth Rate", "Annual population growth rate (%)"),
            ("SP.URB.TOTL", "Urban Population", "Total urban population count"),
            ("SP.RUR.TOTL", "Rural Population", "Total rural population count"),
            ("SP.POP.DPND", "Age Dependency Ratio", "Ratio of dependents to working-age population"),
            ("EN.POP.DNST", "Population Density", "Population per square kilometer")
        ]
        
        appendices += "| Indicator Code | Name | Description |\n"
        appendices += "|----------------|------|-------------|\n"
        
        for code, name, description in indicators:
            appendices += f"| `{code}` | {name} | {description} |\n"
        
        appendices += "\n"
        
        return appendices
    
    def generate_complete_report(self) -> str:
        """Generate the complete analysis report."""
        self.logger.info("Generating comprehensive analysis report...")
        
        report = "# World Bank Population Data Analysis Report\n\n"
        report += f"*Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}*\n\n"
        
        # Table of contents
        report += "## Table of Contents\n\n"
        report += "1. [Executive Summary](#executive-summary)\n"
        report += "2. [Data Overview](#data-overview)\n"
        report += "3. [Data Quality Assessment](#data-quality-assessment)\n"
        report += "4. [Statistical Insights](#statistical-insights)\n"
        report += "5. [Technical Specifications](#technical-specifications)\n"
        report += "6. [Visualization Recommendations](#visualization-recommendations)\n"
        report += "7. [Dashboard Feature Suggestions](#dashboard-feature-suggestions)\n"
        report += "8. [Appendices](#appendices)\n\n"
        
        # Generate each section
        report += self.generate_executive_summary()
        report += self.generate_data_overview()
        report += self.generate_quality_assessment()
        report += self.generate_statistical_insights()
        report += self.generate_technical_specifications()
        report += self.generate_visualization_recommendations()
        report += self.generate_dashboard_features()
        report += self.generate_appendices()
        
        # Footer
        report += "---\n\n"
        report += "*This report was automatically generated by the World Bank Population Data Analysis Pipeline.*\n"
        report += f"*For questions or issues, please refer to the analysis logs and source code.*\n"
        
        return report
    
    def save_report(self, filename: str = "outputs/comprehensive_analysis_report.md"):
        """Save the complete report to a markdown file."""
        report = self.generate_complete_report()
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(report)
        
        self.logger.info(f"Comprehensive report saved to {filename}")
        return filename


def main():
    """Main function to generate the comprehensive report."""
    generator = ReportGenerator()
    
    print("Generating comprehensive analysis report...")
    print("=" * 50)
    
    try:
        filename = generator.save_report()
        print(f"✓ Report generated successfully: {filename}")
        
        # Generate additional summary
        with open('outputs/key_insights.md', 'w') as f:
            f.write("# Key Insights Summary\n\n")
            f.write(generator.generate_executive_summary())
            f.write(generator.generate_statistical_insights())
        
        print("✓ Key insights summary saved: outputs/key_insights.md")
        
    except Exception as e:
        print(f"✗ Report generation failed: {e}")
    
    print("\n" + "=" * 50)
    print("Report generation complete!")


if __name__ == "__main__":
    main()
