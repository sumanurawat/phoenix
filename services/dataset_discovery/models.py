"""
Data models for dataset discovery service.
Defines structured data models for datasets, search requests, and responses.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
import re


@dataclass
class DatasetFile:
    """Represents a file within a dataset."""
    name: str
    size_bytes: int
    
    @property
    def extension(self) -> str:
        """Get file extension from name."""
        return '.' + self.name.split('.')[-1].lower() if '.' in self.name else ''
    
    @property
    def size_mb(self) -> float:
        """Get file size in megabytes."""
        return round(self.size_bytes / (1024 * 1024), 2)


@dataclass
class DatasetInfo:
    """Complete information about a dataset."""
    ref: str
    title: str
    subtitle: str
    description: str
    owner: str
    vote_count: int
    download_count: int
    view_count: int
    total_bytes: int
    file_count: int
    version_count: int
    created_date: datetime
    updated_date: datetime
    license_name: str
    tags: List[str] = field(default_factory=list)
    files: List[DatasetFile] = field(default_factory=list)
    quality_score: float = 0.0
    relevance_score: float = 0.0
    combined_score: float = 0.0
    
    @property
    def url(self) -> str:
        """Get the Kaggle dataset URL."""
        return f"https://www.kaggle.com/datasets/{self.ref}"
    
    @property
    def size_mb(self) -> float:
        """Get total dataset size in megabytes."""
        return round(self.total_bytes / (1024 * 1024), 2)
    
    @property
    def file_types(self) -> List[str]:
        """Get unique file extensions in the dataset."""
        extensions = set()
        for file in self.files:
            if file.extension:
                extensions.add(file.extension)
        return sorted(list(extensions))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "ref": self.ref,
            "title": self.title,
            "subtitle": self.subtitle,
            "description": self.description,
            "url": self.url,
            "owner": self.owner,
            "vote_count": self.vote_count,
            "download_count": self.download_count,
            "view_count": self.view_count,
            "size_mb": self.size_mb,
            "file_count": self.file_count,
            "file_types": self.file_types,
            "version_count": self.version_count,
            "created_date": self.created_date.isoformat() if self.created_date else None,
            "updated_date": self.updated_date.isoformat() if self.updated_date else None,
            "license_name": self.license_name,
            "tags": self.tags,
            "quality_score": round(self.quality_score, 3),
            "relevance_score": round(self.relevance_score, 3),
            "combined_score": round(self.combined_score, 3)
        }
    
    @classmethod
    def from_kaggle_dataset(cls, kaggle_dataset: Dict[str, Any], files: List[DatasetFile] = None) -> 'DatasetInfo':
        """Create DatasetInfo from Kaggle API response."""
        files = files or []
        
        # Handle both dict and object types from Kaggle API
        def safe_get(obj, key, default=None):
            if hasattr(obj, key):
                value = getattr(obj, key)
                # Convert API objects to serializable types
                if hasattr(value, '__dict__'):
                    return str(value)
                return value
            elif isinstance(obj, dict):
                return obj.get(key, default)
            return default
        
        # Parse dates
        created_date = None
        updated_date = None
        
        try:
            creation_date = safe_get(kaggle_dataset, 'creationDate') or safe_get(kaggle_dataset, 'creation_date')
            if creation_date:
                created_date = datetime.fromisoformat(str(creation_date).replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            pass
            
        try:
            last_updated = safe_get(kaggle_dataset, 'lastUpdated') or safe_get(kaggle_dataset, 'last_updated')
            if last_updated:
                updated_date = datetime.fromisoformat(str(last_updated).replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            pass
        
        # Extract tags safely - handle API objects properly
        tags = safe_get(kaggle_dataset, 'tags', [])
        if tags and not isinstance(tags, list):
            if hasattr(tags, '__iter__') and not isinstance(tags, str):
                # Handle iterable of API objects
                tags = [str(tag) for tag in tags]
            else:
                # Handle single tag or string
                tags = [str(tags)]
        elif tags and isinstance(tags, list):
            # Ensure all tags are strings, not API objects
            tags = [str(tag) for tag in tags]
        
        return cls(
            ref=safe_get(kaggle_dataset, 'ref', ''),
            title=safe_get(kaggle_dataset, 'title', ''),
            subtitle=safe_get(kaggle_dataset, 'subtitle', ''),
            description=safe_get(kaggle_dataset, 'description', ''),
            owner=safe_get(kaggle_dataset, 'ownerName', '') or safe_get(kaggle_dataset, 'owner_name', ''),
            vote_count=safe_get(kaggle_dataset, 'voteCount', 0) or safe_get(kaggle_dataset, 'vote_count', 0),
            download_count=safe_get(kaggle_dataset, 'downloadCount', 0) or safe_get(kaggle_dataset, 'download_count', 0),
            view_count=safe_get(kaggle_dataset, 'viewCount', 0) or safe_get(kaggle_dataset, 'view_count', 0),
            total_bytes=safe_get(kaggle_dataset, 'totalBytes', 0) or safe_get(kaggle_dataset, 'total_bytes', 0),
            file_count=safe_get(kaggle_dataset, 'fileCount', len(files)) or safe_get(kaggle_dataset, 'file_count', len(files)) or len(files),
            version_count=safe_get(kaggle_dataset, 'versionCount', 1) or safe_get(kaggle_dataset, 'version_count', 1),
            created_date=created_date,
            updated_date=updated_date,
            license_name=safe_get(kaggle_dataset, 'licenseName', 'Unknown') or safe_get(kaggle_dataset, 'license_name', 'Unknown'),
            tags=tags,
            files=files
        )


@dataclass
class SearchRequest:
    """Request parameters for dataset search."""
    query: str
    limit: int = 20
    sort_by: str = 'votes'
    min_quality_score: float = 0.0
    
    def __post_init__(self):
        """Validate search parameters after initialization."""
        if not self.query or len(self.query.strip()) < 2:
            from .exceptions import SearchValidationError
            raise SearchValidationError("Query must be at least 2 characters long")
        
        if self.limit < 1 or self.limit > 100:
            from .exceptions import SearchValidationError
            raise SearchValidationError("Limit must be between 1 and 100")
        
        if self.sort_by not in ['hottest', 'votes', 'updated', 'active']:
            from .exceptions import SearchValidationError
            raise SearchValidationError("sort_by must be one of: hottest, votes, updated, active")
        
        if self.min_quality_score < 0.0 or self.min_quality_score > 1.0:
            from .exceptions import SearchValidationError
            raise SearchValidationError("min_quality_score must be between 0.0 and 1.0")
    
    @property
    def sanitized_query(self) -> str:
        """Get sanitized query string for safe API usage."""
        # Remove special characters except spaces, hyphens, and underscores
        sanitized = re.sub(r'[^a-zA-Z0-9\s\-_]', '', self.query.strip())
        # Replace multiple spaces with single space
        sanitized = re.sub(r'\s+', ' ', sanitized)
        return sanitized


@dataclass
class SearchResponse:
    """Response from dataset search operation."""
    query: str
    total_found: int
    returned_count: int
    datasets: List[DatasetInfo]
    search_time_ms: int
    cached: bool = False
    search_metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        result = {
            "query": self.query,
            "total_found": self.total_found,
            "returned_count": self.returned_count,
            "datasets": [dataset.to_dict() for dataset in self.datasets],
            "search_time_ms": self.search_time_ms,
            "cached": self.cached
        }
        if self.search_metadata:
            result["search_metadata"] = self.search_metadata
        return result


@dataclass
class ServiceHealth:
    """Health check response for the dataset service."""
    status: str  # 'healthy', 'degraded', 'unhealthy'
    timestamp: datetime
    kaggle_authenticated: bool
    version: str = "1.0.0"
    checks: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "status": self.status,
            "timestamp": self.timestamp.isoformat(),
            "kaggle_authenticated": self.kaggle_authenticated,
            "version": self.version,
            "checks": self.checks
        }