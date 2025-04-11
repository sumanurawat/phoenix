"""
Document Service module for handling document uploads and text extraction.
This service provides functionality to extract text from uploaded documents.
"""
import os
import logging
import tempfile
from typing import Dict, Any, Optional
import uuid

# Document processors
import PyPDF2
from docx import Document

from services.utils import format_timestamp, truncate_text

# Configure logging
logger = logging.getLogger(__name__)

# Define supported file types
SUPPORTED_FILE_TYPES = {
    'application/pdf': '.pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
    'text/plain': '.txt'
}

class DocumentService:
    """Service for handling document uploads and text extraction."""
    
    def __init__(self):
        """Initialize the document service."""
        # Create temp directory for uploads if it doesn't exist
        self.temp_dir = os.path.join(tempfile.gettempdir(), 'phoenix_uploads')
        os.makedirs(self.temp_dir, exist_ok=True)
        logger.info(f"Document service initialized with temp directory: {self.temp_dir}")
    
    def is_supported_filetype(self, mimetype: str) -> bool:
        """
        Check if the file type is supported.
        
        Args:
            mimetype: MIME type of the file
            
        Returns:
            Boolean indicating if the file type is supported
        """
        return mimetype in SUPPORTED_FILE_TYPES
    
    def save_document(self, file_data) -> Dict[str, Any]:
        """
        Save an uploaded document to a temporary location.
        
        Args:
            file_data: File data from request.files
            
        Returns:
            Dictionary with document information
        """
        try:
            # Generate a unique filename
            original_filename = file_data.filename
            file_ext = os.path.splitext(original_filename)[1]
            if not file_ext and file_data.mimetype in SUPPORTED_FILE_TYPES:
                file_ext = SUPPORTED_FILE_TYPES[file_data.mimetype]
                
            unique_filename = f"{uuid.uuid4()}{file_ext}"
            file_path = os.path.join(self.temp_dir, unique_filename)
            
            # Save the file
            file_data.save(file_path)
            
            logger.info(f"Document saved: {original_filename} -> {file_path}")
            
            return {
                "id": str(uuid.uuid4()),
                "original_filename": original_filename,
                "saved_filename": unique_filename,
                "file_path": file_path,
                "mimetype": file_data.mimetype,
                "uploaded_at": format_timestamp()
            }
            
        except Exception as e:
            logger.error(f"Error saving document: {str(e)}", exc_info=True)
            raise e
    
    def extract_text(self, document_info: Dict[str, Any]) -> Optional[str]:
        """
        Extract text from a document.
        
        Args:
            document_info: Document information dictionary
            
        Returns:
            Extracted text or None if extraction failed
        """
        try:
            file_path = document_info["file_path"]
            mimetype = document_info["mimetype"]
            
            if mimetype == 'application/pdf':
                return self._extract_text_from_pdf(file_path)
            elif mimetype == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
                return self._extract_text_from_docx(file_path)
            elif mimetype == 'text/plain':
                return self._extract_text_from_txt(file_path)
            else:
                logger.warning(f"Unsupported mime type for text extraction: {mimetype}")
                return None
                
        except Exception as e:
            logger.error(f"Error extracting text: {str(e)}", exc_info=True)
            return None
    
    def _extract_text_from_pdf(self, file_path: str) -> str:
        """
        Extract text from a PDF file.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Extracted text
        """
        text = ""
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            for page_num in range(len(reader.pages)):
                page = reader.pages[page_num]
                text += page.extract_text() + "\n\n"
        return text
    
    def _extract_text_from_docx(self, file_path: str) -> str:
        """
        Extract text from a DOCX file.
        
        Args:
            file_path: Path to the DOCX file
            
        Returns:
            Extracted text
        """
        doc = Document(file_path)
        text = ""
        for para in doc.paragraphs:
            text += para.text + "\n"
        return text
    
    def _extract_text_from_txt(self, file_path: str) -> str:
        """
        Extract text from a plain text file.
        
        Args:
            file_path: Path to the text file
            
        Returns:
            File contents
        """
        with open(file_path, 'r', encoding='utf-8', errors='replace') as file:
            return file.read()
    
    def process_document(self, file_data) -> Dict[str, Any]:
        """
        Process an uploaded document - save it and extract text.
        
        Args:
            file_data: File data from request.files
            
        Returns:
            Dictionary with document information and extracted text
        """
        # Save the document
        document_info = self.save_document(file_data)
        
        # Extract text from the document
        extracted_text = self.extract_text(document_info)
        
        # Add extracted text to document info
        document_info["extracted_text"] = extracted_text
        document_info["text_preview"] = truncate_text(extracted_text, 200) if extracted_text else "No text extracted"
        
        return document_info
    
    def cleanup_old_documents(self, max_age_hours: int = 24) -> int:
        """
        Clean up documents older than the specified age.
        
        Args:
            max_age_hours: Maximum age in hours
            
        Returns:
            Number of files deleted
        """
        # Implementation would remove files older than max_age_hours
        # This is a stub for now
        return 0