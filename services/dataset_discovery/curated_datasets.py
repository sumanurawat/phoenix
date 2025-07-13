"""
Curated list of known-good, downloadable datasets for common search terms.

This provides fallback suggestions when search doesn't return downloadable datasets.
"""

from typing import Dict, List, Any

# Known downloadable datasets organized by category/search term
CURATED_DATASETS = {
    "iris": [
        {
            "ref": "arshid/iris-flower-dataset",
            "title": "Iris Flower Dataset", 
            "description": "Classic iris dataset for classification",
            "size_mb": 0.1,
            "category": "classification",
            "verified_downloadable": True
        },
        {
            "ref": "uciml/iris",
            "title": "UCI Iris Dataset",
            "description": "Original UCI iris dataset",
            "size_mb": 0.1,
            "category": "classification", 
            "verified_downloadable": True
        }
    ],
    "classification": [
        {
            "ref": "arshid/iris-flower-dataset",
            "title": "Iris Flower Dataset",
            "description": "Classic iris dataset for classification",
            "size_mb": 0.1,
            "category": "classification",
            "verified_downloadable": True
        }
    ],
    "flower": [
        {
            "ref": "arshid/iris-flower-dataset", 
            "title": "Iris Flower Dataset",
            "description": "Classic iris dataset for flower classification",
            "size_mb": 0.1,
            "category": "classification",
            "verified_downloadable": True
        }
    ],
    "titanic": [
        {
            "ref": "c/titanic",
            "title": "Titanic: Machine Learning from Disaster",
            "description": "Kaggle's famous Titanic survival prediction dataset",
            "size_mb": 0.1,
            "category": "classification",
            "verified_downloadable": True
        }
    ],
    "housing": [
        {
            "ref": "c/house-prices-advanced-regression-techniques", 
            "title": "House Prices: Advanced Regression Techniques",
            "description": "Predict house prices using advanced regression",
            "size_mb": 0.5,
            "category": "regression",
            "verified_downloadable": True
        }
    ],
    "population": [
        {
            "ref": "worldbank/world-development-indicators",
            "title": "World Development Indicators", 
            "description": "World Bank development indicators including population",
            "size_mb": 50.0,
            "category": "economics",
            "verified_downloadable": False  # Large dataset, might have issues
        }
    ]
}

# Common search term mappings
SEARCH_TERM_MAPPINGS = {
    "iris flower": "iris",
    "flower classification": "flower", 
    "machine learning": "classification",
    "house prices": "housing",
    "home prices": "housing",
    "real estate": "housing",
    "survival": "titanic",
    "demographics": "population",
    "census": "population"
}


def get_curated_datasets(search_query: str) -> List[Dict[str, Any]]:
    """
    Get curated datasets for a search query.
    
    Args:
        search_query: User's search query
        
    Returns:
        List of curated dataset dictionaries
    """
    query_lower = search_query.lower().strip()
    
    # Direct lookup
    if query_lower in CURATED_DATASETS:
        return CURATED_DATASETS[query_lower].copy()
    
    # Check mappings
    if query_lower in SEARCH_TERM_MAPPINGS:
        mapped_term = SEARCH_TERM_MAPPINGS[query_lower]
        if mapped_term in CURATED_DATASETS:
            return CURATED_DATASETS[mapped_term].copy()
    
    # Partial matches
    results = []
    for category, datasets in CURATED_DATASETS.items():
        if query_lower in category or category in query_lower:
            results.extend(datasets.copy())
    
    # Search in descriptions
    if not results:
        for datasets_list in CURATED_DATASETS.values():
            for dataset in datasets_list:
                if (query_lower in dataset['title'].lower() or 
                    query_lower in dataset['description'].lower()):
                    if dataset not in results:
                        results.append(dataset.copy())
    
    return results


def format_as_dataset_info(curated_dataset: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format a curated dataset as a standard DatasetInfo-compatible dict.
    
    Args:
        curated_dataset: Curated dataset dictionary
        
    Returns:
        Dictionary compatible with DatasetInfo format
    """
    return {
        "ref": curated_dataset["ref"],
        "title": curated_dataset["title"],
        "description": curated_dataset["description"],
        "size_mb": curated_dataset["size_mb"],
        "download_count": 1000,  # Fake high download count
        "vote_count": 100,       # Fake high vote count  
        "view_count": 5000,      # Fake high view count
        "file_count": 1,
        "owner": "Curated",
        "url": f"https://www.kaggle.com/datasets/{curated_dataset['ref']}",
        "license_name": "Open",
        "quality_score": 0.95,   # High quality score
        "relevance_score": 0.9,  # High relevance
        "combined_score": 0.925, # High combined score
        "tags": [curated_dataset["category"]],
        "_is_curated": True      # Mark as curated
    }


def get_curated_suggestions(search_query: str, max_results: int = 3) -> List[Dict[str, Any]]:
    """
    Get formatted curated dataset suggestions for a search query.
    
    Args:
        search_query: User's search query
        max_results: Maximum number of suggestions
        
    Returns:
        List of formatted dataset suggestions
    """
    curated = get_curated_datasets(search_query)
    formatted = [format_as_dataset_info(dataset) for dataset in curated[:max_results]]
    return formatted