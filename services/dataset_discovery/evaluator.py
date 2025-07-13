"""
Dataset evaluator for scoring datasets based on quality and relevance.
Implements algorithms to evaluate dataset quality and search relevance.
"""
import math
import re
import logging
from datetime import datetime, timezone
from typing import Dict, List, Tuple
from collections import Counter

from .models import DatasetInfo

logger = logging.getLogger(__name__)


class DatasetEvaluator:
    """Evaluates and scores datasets for quality and relevance."""
    
    # Scoring weights for quality components
    QUALITY_WEIGHTS = {
        'popularity': 0.40,
        'recency': 0.30,
        'completeness': 0.20,
        'size_appropriateness': 0.10
    }
    
    # Scoring weights for relevance components
    RELEVANCE_WEIGHTS = {
        'title_match': 0.50,
        'description_match': 0.30,
        'tag_match': 0.20
    }
    
    # Expected maximum values for logarithmic scaling
    MAX_EXPECTED_VOTES = 10000
    MAX_EXPECTED_DOWNLOADS = 1000000
    
    def __init__(self):
        """Initialize the evaluator with default settings."""
        logger.debug("🎯 Dataset evaluator initialized")
    
    def calculate_quality_score(self, dataset: DatasetInfo) -> float:
        """
        Calculate intrinsic quality score (0.0 to 1.0) based on various factors.
        
        Args:
            dataset: DatasetInfo object to evaluate
            
        Returns:
            Quality score between 0.0 and 1.0
        """
        try:
            # Calculate component scores
            popularity_score = self._calculate_popularity_score(dataset)
            recency_score = self._calculate_recency_score(dataset)
            completeness_score = self._calculate_completeness_score(dataset)
            size_score = self._calculate_size_appropriateness_score(dataset)
            
            # Combine with weights
            quality_score = (
                popularity_score * self.QUALITY_WEIGHTS['popularity'] +
                recency_score * self.QUALITY_WEIGHTS['recency'] +
                completeness_score * self.QUALITY_WEIGHTS['completeness'] +
                size_score * self.QUALITY_WEIGHTS['size_appropriateness']
            )
            
            # Ensure score is between 0 and 1
            quality_score = max(0.0, min(1.0, quality_score))
            
            logger.debug(
                f"📊 Quality score for {dataset.ref}: {quality_score:.3f} "
                f"(pop: {popularity_score:.2f}, rec: {recency_score:.2f}, "
                f"comp: {completeness_score:.2f}, size: {size_score:.2f})"
            )
            
            return quality_score
            
        except Exception as e:
            logger.warning(f"⚠️ Error calculating quality score for {dataset.ref}: {e}")
            return 0.5  # Return neutral score on error
    
    def calculate_relevance_score(self, dataset: DatasetInfo, query: str) -> float:
        """
        Calculate query relevance score (0.0 to 1.0) based on text matching.
        
        Args:
            dataset: DatasetInfo object to evaluate
            query: Search query string
            
        Returns:
            Relevance score between 0.0 and 1.0
        """
        try:
            query_lower = query.lower().strip()
            query_words = self._tokenize_text(query_lower)
            
            if not query_words:
                return 0.0
            
            # Calculate component scores
            title_score = self._calculate_title_match_score(dataset.title, query_words)
            description_score = self._calculate_description_match_score(dataset.description, query_words)
            tag_score = self._calculate_tag_match_score(dataset.tags, query_words)
            
            # Combine with weights
            relevance_score = (
                title_score * self.RELEVANCE_WEIGHTS['title_match'] +
                description_score * self.RELEVANCE_WEIGHTS['description_match'] +
                tag_score * self.RELEVANCE_WEIGHTS['tag_match']
            )
            
            # Ensure score is between 0 and 1
            relevance_score = max(0.0, min(1.0, relevance_score))
            
            logger.debug(
                f"🎯 Relevance score for {dataset.ref} vs '{query}': {relevance_score:.3f} "
                f"(title: {title_score:.2f}, desc: {description_score:.2f}, tags: {tag_score:.2f})"
            )
            
            return relevance_score
            
        except Exception as e:
            logger.warning(f"⚠️ Error calculating relevance score for {dataset.ref}: {e}")
            return 0.0  # Return zero relevance on error
    
    def combine_scores(self, quality: float, relevance: float, weights: Tuple[float, float] = (0.4, 0.6)) -> float:
        """
        Combine quality and relevance scores with configurable weights.
        
        Args:
            quality: Quality score (0.0 to 1.0)
            relevance: Relevance score (0.0 to 1.0)
            weights: Tuple of (quality_weight, relevance_weight)
            
        Returns:
            Combined score between 0.0 and 1.0
        """
        quality_weight, relevance_weight = weights
        
        # Normalize weights
        total_weight = quality_weight + relevance_weight
        if total_weight > 0:
            quality_weight /= total_weight
            relevance_weight /= total_weight
        else:
            quality_weight = relevance_weight = 0.5
        
        combined = quality * quality_weight + relevance * relevance_weight
        return max(0.0, min(1.0, combined))
    
    def _calculate_popularity_score(self, dataset: DatasetInfo) -> float:
        """Calculate popularity score based on votes and downloads."""
        # Use logarithmic scaling for votes and downloads
        votes_score = 0.0
        if dataset.vote_count > 0:
            votes_score = math.log10(dataset.vote_count + 1) / math.log10(self.MAX_EXPECTED_VOTES + 1)
        
        downloads_score = 0.0
        if dataset.download_count > 0:
            downloads_score = math.log10(dataset.download_count + 1) / math.log10(self.MAX_EXPECTED_DOWNLOADS + 1)
        
        # Combine votes (60%) and downloads (40%)
        popularity_score = votes_score * 0.6 + downloads_score * 0.4
        return min(1.0, popularity_score)
    
    def _calculate_recency_score(self, dataset: DatasetInfo) -> float:
        """Calculate recency score based on last update date."""
        if not dataset.updated_date:
            return 0.3  # Default score for unknown update date
        
        now = datetime.now(timezone.utc)
        if dataset.updated_date.tzinfo is None:
            # Assume UTC if no timezone info
            updated_date = dataset.updated_date.replace(tzinfo=timezone.utc)
        else:
            updated_date = dataset.updated_date
        
        days_old = (now - updated_date).days
        
        # Recent bonus: extra points if updated in last 30 days
        recent_bonus = 0.2 if days_old < 30 else 0.0
        
        # Base recency score: decay over 1 year
        base_score = max(0.0, 1.0 - (days_old / 365.0))
        
        return min(1.0, base_score + recent_bonus)
    
    def _calculate_completeness_score(self, dataset: DatasetInfo) -> float:
        """Calculate completeness score based on available metadata."""
        score = 0.0
        
        # Has meaningful description (not empty or too short)
        if dataset.description and len(dataset.description.strip()) > 20:
            score += 0.3
        
        # Has multiple files (only count if we have file info)
        if dataset.file_count > 1:
            score += 0.3
        elif dataset.file_count == 0 and dataset.total_bytes > 0:
            # If we have size but no file count, assume it has files
            score += 0.2
        
        # Has tags
        if dataset.tags and len(dataset.tags) > 0:
            score += 0.2
        
        # Has license information
        if dataset.license_name and dataset.license_name.lower() not in ['unknown', 'none', '']:
            score += 0.2
        
        return min(1.0, score)
    
    def _calculate_size_appropriateness_score(self, dataset: DatasetInfo) -> float:
        """Calculate size appropriateness score using bell curve."""
        size_mb = dataset.size_mb
        
        if size_mb == 0:
            return 0.3  # Neutral score for unknown size
        
        # Optimal range: 1MB - 500MB
        if 1.0 <= size_mb <= 500.0:
            return 1.0
        
        # Bell curve scoring for sizes outside optimal range
        if size_mb < 1.0:
            # Penalize very small datasets
            return max(0.1, size_mb / 1.0)
        else:
            # Penalize very large datasets
            return max(0.1, 500.0 / size_mb)
    
    def _calculate_title_match_score(self, title: str, query_words: List[str]) -> float:
        """Calculate title matching score."""
        if not title or not query_words:
            return 0.0
        
        title_lower = title.lower()
        title_words = self._tokenize_text(title_lower)
        
        # Check for exact phrase match
        query_phrase = ' '.join(query_words)
        if query_phrase in title_lower:
            return 1.0
        
        # Check for all words present
        matched_words = sum(1 for word in query_words if word in title_words)
        if matched_words == len(query_words):
            return 0.8
        
        # Partial word matching
        partial_score = matched_words / len(query_words)
        return partial_score * 0.5
    
    def _calculate_description_match_score(self, description: str, query_words: List[str]) -> float:
        """Calculate description matching score using TF-IDF-like approach."""
        if not description or not query_words:
            return 0.0
        
        description_lower = description.lower()
        description_words = self._tokenize_text(description_lower)
        
        if not description_words:
            return 0.0
        
        # Count occurrences of query words in description
        word_counts = Counter(description_words)
        total_words = len(description_words)
        
        score = 0.0
        for query_word in query_words:
            if query_word in word_counts:
                # TF-IDF-like scoring: frequency normalized by document length
                tf = word_counts[query_word] / total_words
                score += min(0.25, tf * 10)  # Cap individual word contribution
        
        # Normalize by number of query words
        return min(1.0, score / len(query_words))
    
    def _calculate_tag_match_score(self, tags: List[str], query_words: List[str]) -> float:
        """Calculate tag matching score."""
        if not tags or not query_words:
            return 0.0
        
        # Safely convert tags to lowercase strings
        tags_lower = []
        for tag in tags:
            try:
                if hasattr(tag, 'lower'):
                    tags_lower.append(tag.lower())
                else:
                    tags_lower.append(str(tag).lower())
            except Exception:
                # Skip invalid tags
                continue
        
        if not tags_lower:
            return 0.0
        
        exact_matches = 0
        partial_matches = 0
        
        for query_word in query_words:
            # Check for exact tag matches
            if query_word in tags_lower:
                exact_matches += 1
            else:
                # Check for partial matches
                for tag in tags_lower:
                    if query_word in tag or tag in query_word:
                        partial_matches += 1
                        break
        
        # Score: 1.0 per exact match, 0.5 per partial match
        total_score = exact_matches + (partial_matches * 0.5)
        
        # Normalize by number of query words
        return min(1.0, total_score / len(query_words))
    
    def _tokenize_text(self, text: str) -> List[str]:
        """Tokenize text into words, removing punctuation and splitting on whitespace."""
        if not text:
            return []
        
        # Remove punctuation and split on whitespace
        cleaned = re.sub(r'[^\w\s]', ' ', text)
        words = cleaned.split()
        
        # Filter out very short words
        return [word.lower() for word in words if len(word) > 1]