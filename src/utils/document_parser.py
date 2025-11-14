"""Document parsing utilities using Tika and OCR"""
from typing import Optional, Dict, Any
import logging
import requests
from io import BytesIO
import magic
from PIL import Image
import pytesseract

from src.core.config import settings

logger = logging.getLogger(__name__)


class DocumentParser:
    """Parser for various document formats"""

    def __init__(self):
        self.tika_url = settings.TIKA_SERVER_URL

    def parse_file(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """
        Parse file content using Apache Tika

        Args:
            file_content: File content as bytes
            filename: Original filename

        Returns:
            Dictionary with extracted text and metadata
        """
        try:
            # Detect MIME type
            mime_type = self._detect_mime_type(file_content)
            logger.info(f"Parsing file {filename} (MIME: {mime_type})")

            # Try Tika first
            result = self._parse_with_tika(file_content, filename)

            # If text is empty or it's an image, try OCR
            if (not result["text"] or len(result["text"].strip()) < 50) and \
               mime_type.startswith("image/"):
                logger.info(f"Attempting OCR for {filename}")
                ocr_text = self._extract_text_ocr(file_content)
                if ocr_text:
                    result["text"] = ocr_text
                    result["ocr_used"] = True

            return result

        except Exception as e:
            logger.error(f"Error parsing file {filename}: {e}", exc_info=True)
            return {
                "text": "",
                "metadata": {},
                "error": str(e)
            }

    def _detect_mime_type(self, content: bytes) -> str:
        """Detect MIME type from file content"""
        try:
            mime = magic.Magic(mime=True)
            return mime.from_buffer(content)
        except Exception as e:
            logger.warning(f"MIME detection failed: {e}")
            return "application/octet-stream"

    def _parse_with_tika(self, content: bytes, filename: str) -> Dict[str, Any]:
        """
        Parse document using Apache Tika Server

        Args:
            content: File content
            filename: Original filename

        Returns:
            Parsed content and metadata
        """
        try:
            # Call Tika Server for text extraction
            headers = {
                "Accept": "application/json",
                "Content-Disposition": f'attachment; filename="{filename}"'
            }

            response = requests.put(
                f"{self.tika_url}/tika",
                data=content,
                headers=headers,
                timeout=60
            )

            if response.status_code == 200:
                text = response.text
            else:
                logger.error(f"Tika returned status {response.status_code}")
                text = ""

            # Get metadata
            metadata_response = requests.put(
                f"{self.tika_url}/meta",
                data=content,
                headers={"Accept": "application/json"},
                timeout=30
            )

            metadata = {}
            if metadata_response.status_code == 200:
                try:
                    metadata = metadata_response.json()
                except Exception:
                    pass

            return {
                "text": text,
                "metadata": metadata,
                "ocr_used": False
            }

        except Exception as e:
            logger.error(f"Tika parsing failed: {e}")
            return {
                "text": "",
                "metadata": {},
                "error": str(e)
            }

    def _extract_text_ocr(self, image_content: bytes) -> str:
        """
        Extract text from image using Tesseract OCR

        Args:
            image_content: Image file content

        Returns:
            Extracted text
        """
        try:
            # Open image
            image = Image.open(BytesIO(image_content))

            # Run OCR
            text = pytesseract.image_to_string(
                image,
                config='--oem 3 --psm 1'  # Use LSTM OCR, auto page segmentation
            )

            return text.strip()

        except Exception as e:
            logger.error(f"OCR failed: {e}")
            return ""

    def parse_text(self, text: str, content_type: str = "text/plain") -> Dict[str, Any]:
        """
        Parse plain text content

        Args:
            text: Text content
            content_type: Content type

        Returns:
            Parsed result
        """
        return {
            "text": text,
            "metadata": {"Content-Type": content_type},
            "ocr_used": False
        }


# Global instance
document_parser = DocumentParser()
