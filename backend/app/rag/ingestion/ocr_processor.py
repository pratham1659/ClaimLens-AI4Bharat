# backend/app/ingestion/ocr_processor.py
"""
OCR processing for image-based PDFs using AWS Textract.
"""

import logging
from typing import List, Dict, Any
import boto3
from botocore.exceptions import ClientError

from app.core.config import settings
from app.core.exceptions import DocumentProcessingError

logger = logging.getLogger(__name__)


class OCRProcessor:
    """
    OCR processor using AWS Textract for image-based documents.
    """

    def __init__(self):
        self.client = boto3.client(
            "textract",
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
        )

    async def process_document(self, document_bytes: bytes) -> str:
        """
        Process document with OCR.

        Args:
            document_bytes: Raw document bytes

        Returns:
            Extracted text
        """
        try:
            response = self.client.detect_document_text(
                Document={"Bytes": document_bytes}
            )

            return self._extract_text_from_response(response)

        except ClientError as e:
            logger.error(f"Textract error: {str(e)}")
            raise DocumentProcessingError(
                f"OCR processing failed: {str(e)}"
            )

    async def process_document_from_s3(
        self,
        bucket: str,
        key: str
    ) -> str:
        """
        Process document from S3 with OCR.

        Args:
            bucket: S3 bucket name
            key: S3 object key

        Returns:
            Extracted text
        """
        try:
            response = self.client.detect_document_text(
                Document={
                    "S3Object": {
                        "Bucket": bucket,
                        "Name": key
                    }
                }
            )

            return self._extract_text_from_response(response)

        except ClientError as e:
            logger.error(f"Textract S3 error: {str(e)}")
            raise DocumentProcessingError(
                f"OCR processing failed: {str(e)}"
            )

    def _extract_text_from_response(self, response: Dict[str, Any]) -> str:
        """Extract text from Textract response."""
        lines = []

        for block in response.get("Blocks", []):
            if block["BlockType"] == "LINE":
                lines.append(block.get("Text", ""))

        return "\n".join(lines)

    async def analyze_document(self, document_bytes: bytes) -> Dict[str, Any]:
        """
        Analyze document for forms and tables.

        Args:
            document_bytes: Raw document bytes

        Returns:
            Structured analysis results
        """
        try:
            response = self.client.analyze_document(
                Document={"Bytes": document_bytes},
                FeatureTypes=["FORMS", "TABLES"]
            )

            return self._parse_analysis_response(response)

        except ClientError as e:
            logger.error(f"Textract analysis error: {str(e)}")
            raise DocumentProcessingError(
                f"Document analysis failed: {str(e)}"
            )

    def _parse_analysis_response(
        self,
        response: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Parse Textract analysis response."""
        result = {
            "text": "",
            "forms": [],
            "tables": []
        }

        blocks_map = {
            block["Id"]: block
            for block in response.get("Blocks", [])
        }

        for block in response.get("Blocks", []):
            if block["BlockType"] == "LINE":
                result["text"] += block.get("Text", "") + "\n"

            elif block["BlockType"] == "KEY_VALUE_SET":
                if "KEY" in block.get("EntityTypes", []):
                    key_text = self._get_text_from_block(block, blocks_map)
                    value_block_id = self._get_value_block_id(block)
                    if value_block_id:
                        value_text = self._get_text_from_block(
                            blocks_map.get(value_block_id, {}),
                            blocks_map
                        )
                        result["forms"].append({
                            "key": key_text,
                            "value": value_text
                        })

        return result

    def _get_text_from_block(
        self,
        block: Dict[str, Any],
        blocks_map: Dict[str, Any]
    ) -> str:
        """Get text from block and its children."""
        text = ""

        if "Relationships" in block:
            for relationship in block["Relationships"]:
                if relationship["Type"] == "CHILD":
                    for child_id in relationship["Ids"]:
                        child_block = blocks_map.get(child_id, {})
                        if child_block.get("BlockType") == "WORD":
                            text += child_block.get("Text", "") + " "

        return text.strip()

    def _get_value_block_id(self, block: Dict[str, Any]) -> str:
        """Get value block ID from key block."""
        if "Relationships" in block:
            for relationship in block["Relationships"]:
                if relationship["Type"] == "VALUE":
                    return relationship["Ids"][0] if relationship["Ids"] else None
        return None
