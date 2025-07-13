"""
Dataset Download Service for Phoenix Dataset Discovery.
Handles temporary downloading and processing of Kaggle datasets.
"""
import os
import shutil
import tempfile
import zipfile
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

import pandas as pd

from .config import DatasetConfig
from .kaggle_service import KaggleSearchService
from .exceptions import DatasetDiscoveryError, ConfigurationError

logger = logging.getLogger(__name__)


class DatasetDownloadService:
    """Service for downloading and temporarily processing Kaggle datasets."""
    
    def __init__(self, config: Optional[DatasetConfig] = None):
        """Initialize the download service."""
        self.config = config or DatasetConfig()
        self.kaggle_service = KaggleSearchService(self.config)
        
        # Create temporary download directory
        self.download_dir = self._create_download_directory()
        
        logger.info(f"🔽 Dataset download service initialized - Download dir: {self.download_dir}")
    
    def _create_download_directory(self) -> Path:
        """Create and return the download directory path."""
        # Use different directories based on environment
        env = self.config.get_environment()
        
        if env == 'local':
            # Local development - use project directory
            base_dir = Path(__file__).parent.parent.parent  # Go up to project root
            download_dir = base_dir / 'temp_datasets'
        else:
            # Cloud environments - use temporary directory
            download_dir = Path(tempfile.gettempdir()) / 'phoenix_datasets'
        
        download_dir.mkdir(exist_ok=True)
        
        # Create subdirectories
        (download_dir / 'raw').mkdir(exist_ok=True)
        (download_dir / 'processed').mkdir(exist_ok=True)
        
        return download_dir
    
    def check_download_feasibility(self, dataset_ref: str, size_mb: float) -> Dict[str, Any]:
        """
        Check if a dataset can be downloaded in the current environment.
        
        Args:
            dataset_ref: Dataset reference (owner/name)
            size_mb: Dataset size in megabytes
            
        Returns:
            Dictionary with feasibility info
        """
        allowed, message = self.config.is_download_allowed(size_mb)
        warning_size = self.config.get_download_warning_size_mb()
        
        return {
            'allowed': allowed,
            'message': message,
            'size_mb': size_mb,
            'max_allowed_mb': self.config.get_max_download_size_mb(),
            'environment': self.config.get_environment(),
            'show_warning': size_mb > warning_size,
            'estimated_memory_usage_mb': size_mb * 3,  # Conservative estimate for pandas
            'estimated_download_time_seconds': max(10, size_mb / 10)  # ~10 MB/s
        }
    
    def download_dataset(self, dataset_ref: str, size_mb: float, force: bool = False) -> Dict[str, Any]:
        """
        Download a dataset temporarily for analysis.
        
        Args:
            dataset_ref: Dataset reference (owner/name)
            size_mb: Dataset size in megabytes
            force: Force download even if size exceeds limits (for local dev only)
            
        Returns:
            Dictionary with download results and file info
        """
        # Check feasibility
        feasibility = self.check_download_feasibility(dataset_ref, size_mb)
        
        if not feasibility['allowed'] and not force:
            raise DatasetDiscoveryError(
                f"Download not allowed: {feasibility['message']}",
                details=f"Dataset {dataset_ref} ({size_mb:.1f} MB) exceeds size limits"
            )
        
        if force and self.config.get_environment() != 'local':
            raise DatasetDiscoveryError(
                "Force download only allowed in local development environment",
                details="Cannot override size limits in cloud environments"
            )
        
        logger.info(f"🔽 Starting download of {dataset_ref} ({size_mb:.1f} MB)")
        
        try:
            # Clear all existing datasets before downloading new one
            # This ensures we only have one dataset at a time during development
            cleanup_result = self.cleanup_all_downloads()
            if cleanup_result['cleaned_count'] > 0:
                logger.info(
                    f"🗑️ Cleared {cleanup_result['cleaned_count']} existing datasets "
                    f"({cleanup_result['size_freed_mb']:.1f} MB freed) before new download"
                )
            
            # Ensure authentication
            self.kaggle_service.authenticate()
            
            # Create dataset-specific directory
            dataset_dir = self.download_dir / 'raw' / dataset_ref.replace('/', '_')
            dataset_dir.mkdir(exist_ok=True)
            
            # Download dataset
            download_start = datetime.now()
            
            # Parse dataset reference
            if '/' not in dataset_ref:
                raise ValueError("Dataset ref must be in format 'owner/dataset-name'")
            
            owner, dataset_name = dataset_ref.split('/', 1)
            
            # Use Kaggle API to download
            self.kaggle_service.api.dataset_download_files(
                dataset_ref,
                path=str(dataset_dir),
                unzip=True
            )
            
            download_duration = (datetime.now() - download_start).total_seconds()
            
            # Analyze downloaded files
            file_info = self._analyze_downloaded_files(dataset_dir)
            
            # Set cleanup time (1 hour from now)
            cleanup_time = datetime.now() + timedelta(hours=1)
            
            result = {
                'success': True,
                'dataset_ref': dataset_ref,
                'download_path': str(dataset_dir),
                'download_duration_seconds': download_duration,
                'download_size_mb': size_mb,
                'files': file_info,
                'cleanup_time': cleanup_time.isoformat(),
                'environment': self.config.get_environment(),
                'one_dataset_policy': True,
                'note': 'Previous datasets were automatically cleared. Only one dataset is kept at a time during development.'
            }
            
            logger.info(f"✅ Download completed in {download_duration:.1f}s - {len(file_info)} files")
            return result
            
        except Exception as e:
            logger.error(f"❌ Download failed for {dataset_ref}: {e}")
            raise DatasetDiscoveryError(
                f"Failed to download dataset {dataset_ref}",
                details=str(e)
            )
    
    def _analyze_downloaded_files(self, dataset_dir: Path) -> List[Dict[str, Any]]:
        """Analyze downloaded files and return metadata."""
        files = []
        
        for file_path in dataset_dir.rglob('*'):
            if file_path.is_file():
                try:
                    file_info = {
                        'name': file_path.name,
                        'path': str(file_path.relative_to(dataset_dir)),
                        'size_bytes': file_path.stat().st_size,
                        'size_mb': round(file_path.stat().st_size / (1024 * 1024), 2),
                        'extension': file_path.suffix.lower(),
                        'can_preview': self._can_preview_file(file_path),
                        'estimated_rows': None
                    }
                    
                    # Try to get row count for CSV files
                    if file_info['extension'] == '.csv' and file_info['size_mb'] < 50:
                        try:
                            # Quick row count without loading full file
                            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                row_count = sum(1 for _ in f) - 1  # Subtract header
                                file_info['estimated_rows'] = row_count
                        except Exception:
                            pass
                    
                    files.append(file_info)
                    
                except Exception as e:
                    logger.warning(f"⚠️ Error analyzing file {file_path}: {e}")
                    continue
        
        return sorted(files, key=lambda x: x['size_bytes'], reverse=True)
    
    def _can_preview_file(self, file_path: Path) -> bool:
        """Check if file can be previewed safely."""
        extension = file_path.suffix.lower()
        size_mb = file_path.stat().st_size / (1024 * 1024)
        
        # Only preview small text-based files
        previewable_extensions = {'.csv', '.tsv', '.txt', '.json', '.xml', '.yaml', '.yml'}
        
        return extension in previewable_extensions and size_mb < 10
    
    def preview_file(self, file_path: str, max_rows: int = 10) -> Dict[str, Any]:
        """
        Preview a downloaded file safely.
        
        Args:
            file_path: Path to the file relative to download directory
            max_rows: Maximum number of rows to preview
            
        Returns:
            Dictionary with preview data
        """
        full_path = Path(file_path)
        
        if not full_path.exists():
            raise DatasetDiscoveryError(f"File not found: {file_path}")
        
        if not self._can_preview_file(full_path):
            raise DatasetDiscoveryError(f"File cannot be previewed: {file_path}")
        
        try:
            extension = full_path.suffix.lower()
            
            if extension == '.csv':
                # Use pandas for CSV preview
                df = pd.read_csv(full_path, nrows=max_rows, encoding='utf-8', on_bad_lines='skip')
                
                return {
                    'type': 'dataframe',
                    'shape': df.shape,
                    'columns': df.columns.tolist(),
                    'dtypes': df.dtypes.astype(str).to_dict(),
                    'preview': df.to_dict('records'),
                    'sample_values': {col: df[col].value_counts().head(3).to_dict() 
                                    for col in df.columns if df[col].dtype == 'object'}
                }
            
            else:
                # Plain text preview
                with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = [f.readline().strip() for _ in range(max_rows)]
                
                return {
                    'type': 'text',
                    'lines': lines,
                    'encoding': 'utf-8'
                }
        
        except Exception as e:
            logger.error(f"❌ Preview failed for {file_path}: {e}")
            raise DatasetDiscoveryError(f"Failed to preview file: {str(e)}")
    
    def cleanup_old_downloads(self, max_age_hours: int = 1) -> Dict[str, Any]:
        """Clean up old downloaded datasets."""
        cleanup_count = 0
        total_size_freed = 0
        errors = []
        
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        try:
            raw_dir = self.download_dir / 'raw'
            
            for dataset_dir in raw_dir.iterdir():
                if dataset_dir.is_dir():
                    try:
                        # Check modification time
                        mod_time = datetime.fromtimestamp(dataset_dir.stat().st_mtime)
                        
                        if mod_time < cutoff_time:
                            # Calculate size before deletion
                            size_bytes = sum(f.stat().st_size for f in dataset_dir.rglob('*') if f.is_file())
                            
                            # Remove directory
                            shutil.rmtree(dataset_dir)
                            
                            cleanup_count += 1
                            total_size_freed += size_bytes
                            
                            logger.info(f"🗑️ Cleaned up {dataset_dir.name} ({size_bytes / (1024*1024):.1f} MB)")
                    
                    except Exception as e:
                        errors.append(f"Failed to cleanup {dataset_dir}: {e}")
                        logger.warning(f"⚠️ Cleanup error: {e}")
        
        except Exception as e:
            errors.append(f"Cleanup operation failed: {e}")
            logger.error(f"❌ Cleanup failed: {e}")
        
        return {
            'cleaned_count': cleanup_count,
            'size_freed_mb': round(total_size_freed / (1024 * 1024), 2),
            'errors': errors
        }
    
    def cleanup_all_downloads(self) -> Dict[str, Any]:
        """
        Clean up ALL downloaded datasets immediately.
        Used for one-dataset-at-a-time policy during development.
        """
        cleanup_count = 0
        total_size_freed = 0
        errors = []
        
        try:
            raw_dir = self.download_dir / 'raw'
            
            if not raw_dir.exists():
                return {
                    'cleaned_count': 0,
                    'size_freed_mb': 0.0,
                    'errors': []
                }
            
            for dataset_dir in raw_dir.iterdir():
                if dataset_dir.is_dir():
                    try:
                        # Calculate size before deletion
                        size_bytes = sum(f.stat().st_size for f in dataset_dir.rglob('*') if f.is_file())
                        
                        # Remove directory
                        shutil.rmtree(dataset_dir)
                        
                        cleanup_count += 1
                        total_size_freed += size_bytes
                        
                        logger.info(f"🗑️ Cleared {dataset_dir.name} ({size_bytes / (1024*1024):.1f} MB)")
                    
                    except Exception as e:
                        errors.append(f"Failed to cleanup {dataset_dir}: {e}")
                        logger.warning(f"⚠️ Cleanup error: {e}")
        
        except Exception as e:
            errors.append(f"Cleanup operation failed: {e}")
            logger.error(f"❌ Cleanup failed: {e}")
        
        return {
            'cleaned_count': cleanup_count,
            'size_freed_mb': round(total_size_freed / (1024 * 1024), 2),
            'errors': errors
        }
    
    def get_download_status(self) -> Dict[str, Any]:
        """Get current download directory status."""
        try:
            raw_dir = self.download_dir / 'raw'
            
            datasets = []
            total_size = 0
            
            for dataset_dir in raw_dir.iterdir():
                if dataset_dir.is_dir():
                    try:
                        size_bytes = sum(f.stat().st_size for f in dataset_dir.rglob('*') if f.is_file())
                        file_count = len([f for f in dataset_dir.rglob('*') if f.is_file()])
                        mod_time = datetime.fromtimestamp(dataset_dir.stat().st_mtime)
                        
                        datasets.append({
                            'name': dataset_dir.name,
                            'size_mb': round(size_bytes / (1024 * 1024), 2),
                            'file_count': file_count,
                            'last_modified': mod_time.isoformat(),
                            'age_hours': round((datetime.now() - mod_time).total_seconds() / 3600, 1)
                        })
                        
                        total_size += size_bytes
                    
                    except Exception as e:
                        logger.warning(f"⚠️ Error reading {dataset_dir}: {e}")
            
            return {
                'download_dir': str(self.download_dir),
                'environment': self.config.get_environment(),
                'max_size_mb': self.config.get_max_download_size_mb(),
                'datasets': sorted(datasets, key=lambda x: x['last_modified'], reverse=True),
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'total_datasets': len(datasets)
            }
        
        except Exception as e:
            logger.error(f"❌ Failed to get download status: {e}")
            return {
                'error': str(e),
                'download_dir': str(self.download_dir),
                'environment': self.config.get_environment()
            }