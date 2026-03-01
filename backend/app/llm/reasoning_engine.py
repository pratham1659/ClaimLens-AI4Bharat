# backend/app/llm/reasoning_engine.py
"""
AI reasoning engine for claim compliance analysis.
Supports both local (mock) and production (AWS Bedrock) modes.
"""

import os
import logging
from typing import Dict, Any, List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.llm.bedrock_client import BedrockClient, get_llm_client
from app.llm.prompts import (
    COMPLIANCE_ANALYSIS_SYSTEM_PROMPT,
    COMPLIANCE_ANALYSIS_PROMPT,
    MEDICAL_EXTRACTION_PROMPT
)
from app.rag.retriever import create_rag_retriever
from app.models.analysis import AnalysisResult, ApprovalLikelihood
from app.core.exceptions import AIServiceError

logger = logging.getLogger(__name__)


class ReasoningEngine:
    """
    AI reasoning engine for medical claim compliance analysis.
    Combines RAG retrieval with LLM reasoning.
    Supports both local development (mock) and production (Bedrock) modes.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm_client = get_llm_client()
        self.retriever = create_rag_retriever(db)

    async def analyze_claim(
        self,
        claim_id: UUID,
        medical_extraction: Dict[str, Any],
        billing_data: Dict[str, Any],
        policy_document_ids: List[UUID]
    ) -> AnalysisResult:
        """
        Perform comprehensive claim compliance analysis.

        Args:
            claim_id: Claim identifier
            medical_extraction: Extracted medical information
            billing_data: Billing information
            policy_document_ids: Policy document IDs

        Returns:
            Analysis result
        """
        logger.info(f"Starting compliance analysis for claim {claim_id}")

        # Retrieve relevant policy clauses
        retrieved_clauses = await self.retriever.retrieve_for_claim(
            claim_context=medical_extraction,
            policy_document_ids=policy_document_ids,
            top_k=15
        )

        # Build context
        policy_context = self.retriever.build_context(retrieved_clauses)

        # Format claim information
        claim_info = self._format_claim_info(medical_extraction)
        billing_info = self._format_billing_info(billing_data)

        # Build prompt
        prompt = COMPLIANCE_ANALYSIS_PROMPT.format(
            claim_info=claim_info,
            policy_clauses=policy_context,
            billing_info=billing_info
        )

        # Invoke LLM
        try:
            response = await self.llm_client.invoke_with_json_output(
                prompt=prompt,
                system_prompt=COMPLIANCE_ANALYSIS_SYSTEM_PROMPT,
                max_tokens=4096
            )
        except AIServiceError as e:
            logger.error(f"LLM analysis failed: {str(e)}")
            raise

        # Parse and validate response
        analysis = self._parse_analysis_response(response)

        # Create analysis result
        result = AnalysisResult(
            claim_id=claim_id,
            approval_score=analysis["approval_score"],
            approval_likelihood=ApprovalLikelihood(
                analysis["approval_likelihood"]),
            compliance_risks=analysis["compliance_risks"],
            clause_references=analysis["clause_references"],
            missing_documentation=analysis["missing_documentation"],
            recommendations=analysis["recommendations"],
            reasoning=analysis["reasoning"],
            raw_response=response
        )

        self.db.add(result)
        await self.db.flush()

        logger.info(
            f"Completed analysis for claim {claim_id}: score={result.approval_score}")
        return result

    async def extract_medical_info(
        self,
        discharge_summary_text: str
    ) -> Dict[str, Any]:
        """
        Extract structured medical information using LLM.

        Args:
            discharge_summary_text: Raw discharge summary text

        Returns:
            Structured medical information
        """
        prompt = MEDICAL_EXTRACTION_PROMPT.format(
            discharge_summary=discharge_summary_text
        )

        response = await self.llm_client.invoke_with_json_output(
            prompt=prompt,
            max_tokens=2048
        )

        return response

    def _format_claim_info(self, medical_extraction: Dict[str, Any]) -> str:
        """Format medical extraction for prompt."""
        parts = []

        # Patient info
        if patient := medical_extraction.get("patient_info"):
            parts.append(f"Patient: {patient.get('name', 'Unknown')}")
            parts.append(f"Age: {patient.get('age', 'Unknown')}")
            parts.append(f"Gender: {patient.get('gender', 'Unknown')}")

        # Admission info
        if admission := medical_extraction.get("admission_info"):
            parts.append(
                f"Admission Date: {admission.get('admission_date', 'Unknown')}")
            parts.append(
                f"Discharge Date: {admission.get('discharge_date', 'Unknown')}")
            parts.append(
                f"Length of Stay: {admission.get('length_of_stay', 'Unknown')} days")

        # Diagnoses
        if diagnoses := medical_extraction.get("diagnoses"):
            parts.append("\nDiagnoses:")
            for dx in diagnoses:
                primary = " (Primary)" if dx.get("is_primary") else ""
                icd = f" [{dx.get('icd_code')}]" if dx.get("icd_code") else ""
                parts.append(
                    f"  - {dx.get('description', 'Unknown')}{icd}{primary}")

        # Procedures
        if procedures := medical_extraction.get("procedures"):
            parts.append("\nProcedures:")
            for proc in procedures:
                cpt = f" [{proc.get('cpt_code')}]" if proc.get(
                    "cpt_code") else ""
                parts.append(f"  - {proc.get('description', 'Unknown')}{cpt}")

        # Medications
        if medications := medical_extraction.get("medications"):
            parts.append("\nMedications:")
            for med in medications[:10]:  # Limit to 10
                parts.append(
                    f"  - {med.get('name', 'Unknown')} {med.get('dosage', '')}")

        return "\n".join(parts)

    def _format_billing_info(self, billing_data: Dict[str, Any]) -> str:
        """Format billing data for prompt."""
        parts = []

        if total := billing_data.get("total_amount"):
            parts.append(f"Total Billed Amount: ${total:,.2f}")

        if items := billing_data.get("line_items"):
            parts.append("\nBilling Line Items:")
            for item in items[:20]:  # Limit items
                parts.append(
                    f"  - {item.get('description', 'Unknown')}: "
                    f"${item.get('amount', 0):,.2f}"
                )

        if insurance := billing_data.get("insurance_info"):
            parts.append(
                f"\nInsurance: {insurance.get('provider', 'Unknown')}")
            parts.append(
                f"Policy Number: {insurance.get('policy_number', 'Unknown')}")

        return "\n".join(parts) if parts else "No billing information provided"

    def _parse_analysis_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse and validate LLM analysis response."""
        # Ensure required fields
        required_fields = [
            "approval_score",
            "approval_likelihood",
            "compliance_risks",
            "clause_references",
            "missing_documentation",
            "recommendations",
            "reasoning"
        ]

        for field in required_fields:
            if field not in response:
                response[field] = self._get_default_value(field)

        # Validate approval_score
        response["approval_score"] = max(
            0, min(100, float(response["approval_score"])))

        # Validate approval_likelihood
        valid_likelihoods = ["high", "medium", "low", "very_low"]
        if response["approval_likelihood"] not in valid_likelihoods:
            if response["approval_score"] >= 75:
                response["approval_likelihood"] = "high"
            elif response["approval_score"] >= 50:
                response["approval_likelihood"] = "medium"
            elif response["approval_score"] >= 25:
                response["approval_likelihood"] = "low"
            else:
                response["approval_likelihood"] = "very_low"

        return response

    def _get_default_value(self, field: str) -> Any:
        """Get default value for missing field."""
        defaults = {
            "approval_score": 50.0,
            "approval_likelihood": "medium",
            "compliance_risks": [],
            "clause_references": [],
            "missing_documentation": [],
            "recommendations": [],
            "reasoning": "Analysis completed with limited information."
        }
        return defaults.get(field, None)
