# backend/app/services/analysis_service.py
"""
Analysis service for claim compliance analysis.
"""

import logging
import json
from typing import Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.claim import Claim, ClaimStatus
from app.models.document import Document, DocumentType, DocumentStatus
from app.models.analysis import AnalysisResult
from app.models.user import User
from app.schemas.analysis import AnalysisResponse
from app.services.document_service import DocumentService
from app.ingestion.medical_extractor import MedicalExtractor
from app.llm.reasoning_engine import ReasoningEngine
from app.core.exceptions import (
    ResourceNotFoundError,
    ValidationError,
    DocumentProcessingError
)
from app.auth.permissions import check_resource_ownership

logger = logging.getLogger(__name__)


class AnalysisService:
    """
    Service for claim compliance analysis.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.document_service = DocumentService(db)
        self.medical_extractor = MedicalExtractor()
        self.reasoning_engine = ReasoningEngine(db)

    async def analyze_claim(
        self,
        claim_id: UUID,
        user: User
    ) -> AnalysisResult:
        """
        Perform comprehensive compliance analysis on a claim.

        Args:
            claim_id: Claim ID
            user: Requesting user

        Returns:
            Analysis result
        """
        # Get claim with documents
        result = await self.db.execute(
            select(Claim)
            .where(Claim.id == claim_id)
            .options(selectinload(Claim.documents))
        )
        claim = result.scalar_one_or_none()

        if not claim:
            raise ResourceNotFoundError("Claim", claim_id)

        if not check_resource_ownership(user, str(claim.user_id)):
            raise ValidationError("Not authorized to analyze this claim")

        # Validate documents are ready
        await self._validate_documents(claim)

        # Update claim status
        claim.status = ClaimStatus.PROCESSING
        await self.db.flush()

        try:
            # Get documents by type
            discharge_doc = self._get_document_by_type(
                claim.documents,
                DocumentType.DISCHARGE_SUMMARY
            )
            policy_docs = [
                doc for doc in claim.documents
                if doc.document_type == DocumentType.INSURANCE_POLICY
                and doc.status == DocumentStatus.PROCESSED
            ]
            billing_doc = self._get_document_by_type(
                claim.documents,
                DocumentType.BILLING_DATA
            )

            # Extract medical information
            medical_extraction = await self._extract_medical_info(discharge_doc)

            # Parse billing data
            billing_data = await self._parse_billing_data(billing_doc)

            # Get policy document IDs for RAG
            policy_doc_ids = [doc.id for doc in policy_docs]

            # Perform AI analysis
            analysis_result = await self.reasoning_engine.analyze_claim(
                claim_id=claim_id,
                medical_extraction=medical_extraction,
                billing_data=billing_data,
                policy_document_ids=policy_doc_ids
            )

            # Update claim status
            claim.status = ClaimStatus.ANALYZED
            await self.db.flush()

            logger.info(f"Completed analysis for claim {claim.claim_number}")
            return analysis_result

        except Exception as e:
            logger.error(f"Analysis failed for claim {claim_id}: {str(e)}")
            claim.status = ClaimStatus.FAILED
            await self.db.flush()
            raise

    async def get_analysis_result(
        self,
        claim_id: UUID,
        user: User
    ) -> Optional[AnalysisResult]:
        """
        Get the latest analysis result for a claim.

        Args:
            claim_id: Claim ID
            user: Requesting user

        Returns:
            Analysis result or None
        """
        # Verify access
        result = await self.db.execute(
            select(Claim).where(Claim.id == claim_id)
        )
        claim = result.scalar_one_or_none()

        if not claim:
            raise ResourceNotFoundError("Claim", claim_id)

        if not check_resource_ownership(user, str(claim.user_id)):
            raise ValidationError("Not authorized to access this analysis")

        # Get latest analysis
        result = await self.db.execute(
            select(AnalysisResult)
            .where(AnalysisResult.claim_id == claim_id)
            .order_by(AnalysisResult.created_at.desc())
            .limit(1)
        )

        return result.scalar_one_or_none()

    async def get_analysis_history(
        self,
        claim_id: UUID,
        user: User
    ) -> List[AnalysisResult]:
        """
        Get all analysis results for a claim.
        """
        result = await self.db.execute(
            select(Claim).where(Claim.id == claim_id)
        )
        claim = result.scalar_one_or_none()

        if not claim:
            raise ResourceNotFoundError("Claim", claim_id)

        if not check_resource_ownership(user, str(claim.user_id)):
            raise ValidationError("Not authorized to access this analysis")

        result = await self.db.execute(
            select(AnalysisResult)
            .where(AnalysisResult.claim_id == claim_id)
            .order_by(AnalysisResult.created_at.desc())
        )

        return list(result.scalars().all())

    async def _validate_documents(self, claim: Claim) -> None:
        """Validate that required documents are present and processed."""
        doc_types = {doc.document_type for doc in claim.documents}

        required_types = {
            DocumentType.DISCHARGE_SUMMARY,
            DocumentType.INSURANCE_POLICY
        }

        missing = required_types - doc_types
        if missing:
            raise ValidationError(
                "Missing required documents",
                details={"missing": [t.value for t in missing]}
            )

        # Check processing status
        for doc in claim.documents:
            if doc.document_type in required_types:
                if doc.status == DocumentStatus.FAILED:
                    raise DocumentProcessingError(
                        f"Document {doc.filename} failed processing"
                    )
                if doc.status != DocumentStatus.PROCESSED:
                    raise ValidationError(
                        f"Document {doc.filename} is still processing"
                    )

    def _get_document_by_type(
        self,
        documents: List[Document],
        doc_type: DocumentType
    ) -> Optional[Document]:
        """Get first document of a specific type."""
        for doc in documents:
            if doc.document_type == doc_type:
                return doc
        return None

    async def _extract_medical_info(
        self,
        document: Optional[Document]
    ) -> dict:
        """Extract medical information from discharge summary."""
        if not document or not document.extracted_text:
            return {}

        # Use pattern-based extraction
        extraction = await self.medical_extractor.extract(document.extracted_text)

        # Convert to dict
        return {
            "patient_info": extraction.patient_info,
            "diagnoses": extraction.diagnoses,
            "procedures": extraction.procedures,
            "medications": extraction.medications,
            "vital_signs": extraction.vital_signs,
            "lab_results": extraction.lab_results,
            "admission_date": extraction.admission_date,
            "discharge_date": extraction.discharge_date,
            "attending_physician": extraction.attending_physician,
            "hospital_name": extraction.hospital_name
        }

    async def _parse_billing_data(
        self,
        document: Optional[Document]
    ) -> dict:
        """Parse billing data from JSON document."""
        if not document or not document.extracted_text:
            return {}

        try:
            return json.loads(document.extracted_text)
        except json.JSONDecodeError:
            logger.warning(
                f"Failed to parse billing JSON for document {document.id}")
            return {}
