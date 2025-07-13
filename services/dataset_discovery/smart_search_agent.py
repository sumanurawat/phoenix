"""
Smart Search Agent for Dataset Discovery

Uses Gemini AI to generate intelligent search terms and performs parallel searches
to find the most relevant datasets on Kaggle.
"""

import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any, Set
from dataclasses import dataclass
from .curated_datasets import get_curated_suggestions

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Container for search results with metadata."""
    datasets: List[Dict[str, Any]]
    search_terms_used: List[str]
    total_found: int
    search_time_ms: int
    ai_generated_terms: bool


class SmartSearchAgent:
    """
    AI-powered search agent that generates intelligent search terms
    and performs parallel searches for better dataset discovery.
    """
    
    def __init__(self, kaggle_service, llm_service):
        """Initialize the smart search agent."""
        self.kaggle_service = kaggle_service
        self.llm_service = llm_service
        self.max_workers = 3  # Parallel search threads
        self.max_terms_per_search = 5  # Limit terms to avoid API overuse
    
    def smart_search(self, user_query: str, limit: int = 20) -> SearchResult:
        """
        Perform intelligent dataset search using AI-generated terms.
        
        Args:
            user_query: Original user search query
            limit: Maximum number of results to return
            
        Returns:
            SearchResult with combined and deduplicated results
        """
        start_time = time.time()
        
        try:
            # Generate smart search terms using AI
            search_terms = self._generate_search_terms(user_query)
            logger.info(f"🤖 Generated {len(search_terms)} search terms for '{user_query}': {search_terms}")
            
            # Perform parallel searches
            all_datasets = self._parallel_search(search_terms, limit)
            
            # Deduplicate and filter results
            unique_datasets = self._deduplicate_datasets(all_datasets)
            filtered_datasets = self._filter_downloadable(unique_datasets)
            
            # Sort by relevance and quality
            sorted_datasets = self._sort_by_relevance(filtered_datasets, user_query)
            
            # Add curated suggestions if we have very few results
            if len(sorted_datasets) < 3:
                curated = get_curated_suggestions(user_query, max_results=3)
                logger.info(f"🎯 Adding {len(curated)} curated suggestions for '{user_query}'")
                # Add curated datasets to the beginning
                sorted_datasets = curated + sorted_datasets
            
            # Limit results
            final_datasets = sorted_datasets[:limit]
            
            search_time = int((time.time() - start_time) * 1000)
            
            logger.info(f"✅ Smart search completed: {len(final_datasets)} results in {search_time}ms")
            
            return SearchResult(
                datasets=final_datasets,
                search_terms_used=search_terms,
                total_found=len(final_datasets),
                search_time_ms=search_time,
                ai_generated_terms=True
            )
            
        except Exception as e:
            logger.error(f"❌ Smart search failed: {e}")
            # Fallback to original search
            return self._fallback_search(user_query, limit, start_time)
    
    def _generate_search_terms(self, user_query: str) -> List[str]:
        """Use Gemini AI to generate intelligent search terms."""
        
        prompt = f"""
You are a dataset search expert. Generate 4-5 different search terms to find datasets on Kaggle for this user query: "{user_query}"

Rules:
1. Include the original query
2. Add variations with synonyms and related terms
3. Include domain-specific terms (e.g., for "iris" add "flower classification", "uciml")
4. Add broader category terms (e.g., for "population" add "demographics", "census")
5. Keep terms concise (1-3 words each)

Return only the search terms, one per line, no explanations.

Example for "iris":
iris
iris flower
classification
uciml iris
flower dataset

Search terms for "{user_query}":
"""
        
        try:
            response = self.llm_service.generate_text(prompt)
            response_text = response.get('text', '') if isinstance(response, dict) else str(response)
            
            # Parse search terms from response
            terms = []
            for line in response_text.strip().split('\n'):
                term = line.strip()
                if term and not term.startswith('#') and len(term) > 0:
                    terms.append(term)
            
            # Always include original query as first term
            if user_query not in terms:
                terms.insert(0, user_query)
            
            # Limit number of terms
            return terms[:self.max_terms_per_search]
            
        except Exception as e:
            logger.warning(f"⚠️ AI term generation failed: {e}, using fallback terms")
            return self._fallback_terms(user_query)
    
    def _fallback_terms(self, user_query: str) -> List[str]:
        """Generate fallback search terms without AI."""
        terms = [user_query]
        
        # Add some common variations
        if ' ' in user_query:
            # Try without spaces
            terms.append(user_query.replace(' ', ''))
        
        # Add common suffixes
        if not any(suffix in user_query.lower() for suffix in ['data', 'dataset']):
            terms.extend([f"{user_query} data", f"{user_query} dataset"])
        
        return terms[:self.max_terms_per_search]
    
    def _parallel_search(self, search_terms: List[str], limit_per_term: int) -> List[Dict[str, Any]]:
        """Perform parallel searches with all terms."""
        all_datasets = []
        
        # Calculate limit per search to avoid too many results
        adjusted_limit = max(5, limit_per_term // len(search_terms))
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all search tasks
            future_to_term = {
                executor.submit(self._single_search, term, adjusted_limit): term 
                for term in search_terms
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_term):
                term = future_to_term[future]
                try:
                    datasets = future.result()
                    if datasets:
                        # Add search term metadata to each dataset
                        for dataset in datasets:
                            dataset['_search_term'] = term
                        all_datasets.extend(datasets)
                        logger.info(f"🔍 '{term}' found {len(datasets)} datasets")
                    else:
                        logger.info(f"🔍 '{term}' found 0 datasets")
                        
                except Exception as e:
                    logger.warning(f"⚠️ Search term '{term}' failed: {e}")
        
        return all_datasets
    
    def _single_search(self, term: str, limit: int) -> List[Dict[str, Any]]:
        """Perform a single search with one term."""
        try:
            return self.kaggle_service.search_datasets(term, limit=limit)
        except Exception as e:
            logger.warning(f"⚠️ Single search failed for '{term}': {e}")
            return []
    
    def _deduplicate_datasets(self, datasets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate datasets based on ref."""
        seen_refs: Set[str] = set()
        unique_datasets = []
        
        for dataset in datasets:
            ref = dataset.get('ref', '')
            if ref and ref not in seen_refs:
                seen_refs.add(ref)
                unique_datasets.append(dataset)
        
        logger.info(f"🔧 Deduplicated: {len(datasets)} → {len(unique_datasets)} datasets")
        return unique_datasets
    
    def _filter_downloadable(self, datasets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter out datasets that are likely not downloadable."""
        downloadable = []
        
        for dataset in datasets:
            # Skip datasets with 0 size (likely broken or external links)
            size_mb = dataset.get('size_mb', 0)
            download_count = dataset.get('download_count', 0)
            vote_count = dataset.get('vote_count', 0)
            
            # More strict filtering - require non-zero size AND some popularity
            if size_mb > 0 and (download_count > 10 or vote_count > 5):
                downloadable.append(dataset)
            # Also keep datasets with very high download counts even if size is 0
            elif download_count > 100:
                downloadable.append(dataset)
        
        logger.info(f"🔧 Filtered downloadable: {len(datasets)} → {len(downloadable)} datasets")
        return downloadable
    
    def _sort_by_relevance(self, datasets: List[Dict[str, Any]], original_query: str) -> List[Dict[str, Any]]:
        """Sort datasets by relevance to original query."""
        
        def relevance_score(dataset):
            score = 0
            title = dataset.get('title', '').lower()
            ref = dataset.get('ref', '').lower()
            query_lower = original_query.lower()
            
            # Exact match in title gets highest score
            if query_lower in title:
                score += 100
            
            # Exact match in ref gets high score
            if query_lower in ref:
                score += 80
            
            # Partial word matches
            query_words = query_lower.split()
            for word in query_words:
                if word in title:
                    score += 20
                if word in ref:
                    score += 15
            
            # Boost score based on download count and votes
            score += min(dataset.get('download_count', 0) / 100, 50)  # Max 50 points
            score += min(dataset.get('vote_count', 0) / 10, 30)       # Max 30 points
            
            # Prefer datasets from original search term
            if dataset.get('_search_term') == original_query:
                score += 25
            
            return score
        
        sorted_datasets = sorted(datasets, key=relevance_score, reverse=True)
        logger.info(f"🔧 Sorted by relevance: top dataset score = {relevance_score(sorted_datasets[0]) if sorted_datasets else 0}")
        
        return sorted_datasets
    
    def _fallback_search(self, user_query: str, limit: int, start_time: float) -> SearchResult:
        """Fallback to original search method if smart search fails."""
        try:
            logger.info(f"🔄 Falling back to original search for '{user_query}'")
            datasets = self.kaggle_service.search_datasets(user_query, limit=limit)
            
            search_time = int((time.time() - start_time) * 1000)
            
            return SearchResult(
                datasets=datasets,
                search_terms_used=[user_query],
                total_found=len(datasets),
                search_time_ms=search_time,
                ai_generated_terms=False
            )
            
        except Exception as e:
            logger.error(f"❌ Fallback search also failed: {e}")
            return SearchResult(
                datasets=[],
                search_terms_used=[user_query],
                total_found=0,
                search_time_ms=int((time.time() - start_time) * 1000),
                ai_generated_terms=False
            )