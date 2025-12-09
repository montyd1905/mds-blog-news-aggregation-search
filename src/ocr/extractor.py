"""
OCR Text Extractor for PDFs and Images
"""

import os
from typing import Optional, List
from pathlib import Path
import pytesseract
from PIL import Image
from pdf2image import convert_from_path
import pypdf


class OCRExtractor:
    """
    Extracts text from PDFs and images using OCR.
    Supports both PDF text extraction and OCR for scanned documents.
    """
    
    def __init__(self, tesseract_cmd: Optional[str] = None):
        """
        Initialize OCR extractor.
        
        Args:
            tesseract_cmd: Path to tesseract executable (if not in PATH)
        """
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        elif os.getenv("TESSERACT_CMD"):
            pytesseract.pytesseract.tesseract_cmd = os.getenv("TESSERACT_CMD")
    
    def extract_from_image(self, image_path: str) -> str:
        """
        Extract text from an image file using OCR.
        
        Args:
            image_path: Path to image file
            
        Returns:
            Extracted text as string
        """
        try:
            image = Image.open(image_path)
            text = pytesseract.image_to_string(image)
            return text.strip()
        except Exception as e:
            raise ValueError(f"Error extracting text from image {image_path}: {str(e)}")
    
    def extract_from_pdf(self, pdf_path: str, use_ocr: bool = True) -> str:
        """
        Extract text from a PDF file.
        First tries direct text extraction, falls back to OCR if needed.
        
        Args:
            pdf_path: Path to PDF file
            use_ocr: Whether to use OCR if direct extraction fails
            
        Returns:
            Extracted text as string
        """
        text_parts = []
        
        # Try direct text extraction first
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = pypdf.PdfReader(file)
                for page_num, page in enumerate(pdf_reader.pages):
                    page_text = page.extract_text()
                    if page_text.strip():
                        text_parts.append(page_text)
        except Exception as e:
            print(f"Direct PDF extraction failed: {e}")
        
        # If no text extracted or use_ocr is True, try OCR
        if not text_parts or use_ocr:
            try:
                images = convert_from_path(pdf_path)
                for image in images:
                    ocr_text = pytesseract.image_to_string(image)
                    if ocr_text.strip():
                        text_parts.append(ocr_text)
            except Exception as e:
                print(f"OCR extraction failed: {e}")
        
        if not text_parts:
            raise ValueError(f"No text could be extracted from PDF: {pdf_path}")
        
        return "\n\n".join(text_parts).strip()
    
    def extract_from_file(self, file_path: str) -> str:
        """
        Extract text from a file (auto-detects PDF or image).
        
        Args:
            file_path: Path to file
            
        Returns:
            Extracted text as string
        """
        path = Path(file_path)
        suffix = path.suffix.lower()
        
        if suffix == '.pdf':
            return self.extract_from_pdf(file_path)
        elif suffix in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff']:
            return self.extract_from_image(file_path)
        else:
            raise ValueError(f"Unsupported file type: {suffix}")
    
    def extract_from_directory(self, directory_path: str, 
                               extensions: Optional[List[str]] = None) -> dict:
        """
        Extract text from all supported files in a directory.
        
        Args:
            directory_path: Path to directory
            extensions: List of file extensions to process (default: .pdf, .jpg, .png)
            
        Returns:
            Dictionary mapping file paths to extracted text
        """
        if extensions is None:
            extensions = ['.pdf', '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff']
        
        results = {}
        directory = Path(directory_path)
        
        for ext in extensions:
            for file_path in directory.rglob(f"*{ext}"):
                try:
                    text = self.extract_from_file(str(file_path))
                    results[str(file_path)] = text
                except Exception as e:
                    print(f"Error processing {file_path}: {e}")
        
        return results

