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
from sqlalchemy import select

from app.llm.bedrock_client import BedrockClient, get_llm_client
from app.llm.prompts import (
    COMPLIANCE_ANALYSIS_SYSTEM_PROMPT,
    COMPLIANCE_ANALYSIS_PROMPT,
    MEDICAL_EXTRACTION_PROMPT
)
from app.rag.retriever import create_rag_retriever
from app.models.analysis import AnalysisResult, ApprovalLikelihood
from app.models.embedding import Embedding
from app.core.exceptions import AIServiceError
from app.core.config import settings

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

        retrieval_fallback_used = False
        claim_terms_for_fallback = self._extract_claim_terms(medical_extraction)
        if not retrieved_clauses and policy_document_ids:
            retrieved_clauses = await self._fallback_retrieve_from_embeddings(
                policy_document_ids=policy_document_ids,
                claim_terms=claim_terms_for_fallback,
                top_k=15,
            )
            retrieval_fallback_used = len(retrieved_clauses) > 0

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

        if self._should_use_grounded_analysis():
            response = self._build_grounded_analysis(
                medical_extraction=medical_extraction,
                billing_data=billing_data,
                retrieved_clauses=retrieved_clauses,
            )
        else:
            try:
                response = await self.llm_client.invoke_with_json_output(
                    prompt=prompt,
                    system_prompt=COMPLIANCE_ANALYSIS_SYSTEM_PROMPT,
                    max_tokens=4096
                )
            except AIServiceError as e:
                logger.error(f"LLM analysis failed: {str(e)}")
                raise

        if "debug_info" not in response:
            response["debug_info"] = {
                "grounded_analysis_used": self._should_use_grounded_analysis(),
                "retrieved_clause_count": len(retrieved_clauses),
                "matched_claim_terms": 0,
                "total_claim_terms": 0,
                "match_ratio": 0.0,
                "retrieval_fallback_used": retrieval_fallback_used,
                "model_id": settings.BEDROCK_MODEL_ID,
            }
        else:
            response["debug_info"]["retrieval_fallback_used"] = retrieval_fallback_used

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

    def _should_use_grounded_analysis(self) -> bool:
        use_mock_llm = os.getenv("USE_MOCK_LLM", "false").lower() == "true"
        model_is_embedding_only = settings.BEDROCK_MODEL_ID.startswith("amazon.titan-embed")
        return use_mock_llm or model_is_embedding_only

    def _build_grounded_analysis(
        self,
        medical_extraction: Dict[str, Any],
        billing_data: Dict[str, Any],
        retrieved_clauses: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        clause_entries: List[Dict[str, Any]] = []
        for chunk in retrieved_clauses:
            content = str(chunk.get("content") or "").strip()
            if not content:
                continue
            relevance_raw = chunk.get("relevance_score", 0.5)
            try:
                relevance = float(relevance_raw)
            except (TypeError, ValueError):
                relevance = 0.5
            relevance = max(0.0, min(1.0, relevance))
            clause_entries.append({"content": content, "relevance": relevance})

        all_clause_text = "\n".join([entry["content"] for entry in clause_entries]).lower()

        claim_terms = self._extract_claim_terms(medical_extraction)
        matched_terms = [term for term in claim_terms if term in all_clause_text]
        match_ratio = (len(matched_terms) / len(claim_terms)) if claim_terms else 0.0

        if clause_entries:
            avg_relevance = sum(entry["relevance"] for entry in clause_entries) / len(clause_entries)
        else:
            avg_relevance = 0.0

        score = 20.0
        evidence_count_boost = min(20.0, len(clause_entries) * 1.5)
        evidence_count_boost *= (0.25 + (0.75 * avg_relevance))
        score += evidence_count_boost
        score += avg_relevance * 20.0
        score += match_ratio * 35.0

        relevant_clause_texts = [
            entry["content"].lower()
            for entry in clause_entries
            if any(term in entry["content"].lower() for term in claim_terms)
        ]
        if not relevant_clause_texts:
            relevant_clause_texts = [entry["content"].lower() for entry in clause_entries[:3]]
        relevant_policy_text = "\n".join(relevant_clause_texts)

        risk_patterns = [
            ("pre-existing", "Pre-existing condition clauses may restrict coverage.", "high"),
            ("waiting period", "Waiting period may apply to the current treatment.", "high"),
            ("exclusion", "Exclusion clauses are present and may affect approval.", "high"),
            ("not covered", "Some services appear explicitly marked as not covered.", "high"),
            ("co-pay", "Co-pay terms may reduce payable amount.", "medium"),
            ("deductible", "Deductible terms may apply before reimbursement.", "medium"),
            ("room rent", "Room rent sub-limits may impact reimbursable amount.", "medium"),
            ("sub-limit", "Sub-limit clauses may cap specific benefits.", "medium"),
        ]

        compliance_risks: List[Dict[str, Any]] = []
        missing_documentation: List[str] = []

        for idx, (token, description, severity) in enumerate(risk_patterns, start=1):
            if token in relevant_policy_text:
                compliance_risks.append(
                    {
                        "risk_id": f"risk_{idx}",
                        "severity": severity,
                        "description": description,
                        "affected_clause": token,
                    }
                )

        severity_penalty = {"high": 4.5, "medium": 2.5, "low": 1.5}
        total_penalty = 0.0
        for risk in compliance_risks:
            total_penalty += severity_penalty.get(risk["severity"], 2.0)
        score -= min(18.0, total_penalty)

        total_amount = billing_data.get("total_amount")
        try:
            if total_amount is not None and float(total_amount) > 300000:
                score -= 5.0
                missing_documentation.append("Detailed justification for high claim amount")
        except (TypeError, ValueError):
            pass

        diagnoses = medical_extraction.get("diagnoses") or []
        procedures = medical_extraction.get("procedures") or []
        if not diagnoses:
            missing_documentation.append("Clear diagnosis details in discharge summary")
        if not procedures:
            missing_documentation.append("Procedure/treatment details with dates")

        score = max(0.0, min(100.0, score))

        if score >= 75:
            likelihood = "high"
        elif score >= 50:
            likelihood = "medium"
        elif score >= 25:
            likelihood = "low"
        else:
            likelihood = "very_low"

        clause_references: List[Dict[str, Any]] = []
        for idx, chunk in enumerate(retrieved_clauses[:5], start=1):
            relevance_raw = chunk.get("relevance_score", 0.5)
            try:
                relevance = float(relevance_raw)
            except (TypeError, ValueError):
                relevance = 0.5
            relevance = max(0.0, min(1.0, relevance))

            metadata = chunk.get("metadata") or {}
            source_document = (
                metadata.get("source_pdf")
                or metadata.get("source")
                or chunk.get("source")
                or "policy_document"
            )

            clause_references.append(
                {
                    "clause_id": str(chunk.get("chunk_id") or f"clause_{idx}"),
                    "clause_text": str(chunk.get("content") or "")[:1000],
                    "relevance_score": relevance,
                    "source_document": str(source_document),
                }
            )

        recommendations: List[Dict[str, Any]] = []
        if compliance_risks:
            recommendations.append(
                {
                    "recommendation_id": "rec_1",
                    "priority": "high",
                    "action": "Cross-check high-risk clauses against diagnosis, procedure, and treatment dates.",
                    "rationale": "High-risk policy conditions were detected in retrieved clauses.",
                }
            )
        if missing_documentation:
            recommendations.append(
                {
                    "recommendation_id": "rec_2",
                    "priority": "high",
                    "action": "Complete missing clinical and billing documentation before submission.",
                    "rationale": "Incomplete documentation reduces approval certainty.",
                }
            )
        if matched_terms:
            recommendations.append(
                {
                    "recommendation_id": "rec_3",
                    "priority": "medium",
                    "action": "Attach clause references directly in claim notes for faster adjudication.",
                    "rationale": "Retrieved clauses already align with claim terms.",
                }
            )

        reasoning = (
            f"Approval score is derived from retrieved policy-clause coverage and claim-data alignment. "
            f"Matched {len(matched_terms)} of {len(claim_terms)} key claim terms in policy clauses, "
            f"identified {len(compliance_risks)} policy risks, and considered documentation completeness."
        )

        return {
            "approval_score": round(score, 1),
            "approval_likelihood": likelihood,
            "compliance_risks": compliance_risks,
            "clause_references": clause_references,
            "missing_documentation": list(dict.fromkeys(missing_documentation)),
            "recommendations": recommendations,
            "reasoning": reasoning,
            "debug_info": {
                "grounded_analysis_used": True,
                "retrieved_clause_count": len(retrieved_clauses),
                "matched_claim_terms": len(matched_terms),
                "total_claim_terms": len(claim_terms),
                "match_ratio": round(match_ratio, 3),
                "avg_clause_relevance": round(avg_relevance, 3),
                "retrieval_fallback_used": False,
                "model_id": settings.BEDROCK_MODEL_ID,
            },
        }

    async def _fallback_retrieve_from_embeddings(
        self,
        policy_document_ids: List[UUID],
        claim_terms: List[str],
        top_k: int = 15,
    ) -> List[Dict[str, Any]]:
        """Fallback retrieval directly from stored embeddings when primary retriever returns nothing."""
        result = await self.db.execute(
            select(Embedding)
            .where(Embedding.document_id.in_(policy_document_ids))
            .order_by(Embedding.chunk_index)
            .limit(500)
        )
        embeddings = list(result.scalars().all())

        if not embeddings:
            return []

        scored_chunks: List[tuple[float, int, Embedding]] = []
        for emb in embeddings:
            text = str(emb.chunk_text or "").strip()
            if not text:
                continue

            lowered = text.lower()
            term_hits = sum(1 for term in claim_terms if term in lowered)
            relevance_score = (term_hits / max(1, len(claim_terms))) if claim_terms else 0.0
            scored_chunks.append((relevance_score, term_hits, emb))

        if not scored_chunks:
            return []

        scored_chunks.sort(key=lambda item: (item[0], item[1]), reverse=True)

        if any(score > 0 for score, _, _ in scored_chunks):
            selected = [item for item in scored_chunks if item[0] > 0][:top_k]
        else:
            selected = scored_chunks[: min(top_k, 5)]

        fallback_chunks: List[Dict[str, Any]] = []
        for relevance, _, emb in selected:
            fallback_chunks.append(
                {
                    "chunk_id": str(emb.id),
                    "document_id": str(emb.document_id),
                    "chunk_index": emb.chunk_index,
                    "content": emb.chunk_text,
                    "relevance_score": max(0.0, min(1.0, float(relevance))),
                    "metadata": {},
                    "source": "embedding_fallback",
                }
            )

        return fallback_chunks

    def _extract_claim_terms(self, medical_extraction: Dict[str, Any]) -> List[str]:
        raw_terms: List[str] = []

        for diagnosis in medical_extraction.get("diagnoses") or []:
            if isinstance(diagnosis, dict):
                raw_terms.extend(self._tokenize_text(diagnosis.get("description")))
            else:
                raw_terms.extend(self._tokenize_text(diagnosis))

        for procedure in medical_extraction.get("procedures") or []:
            if isinstance(procedure, dict):
                raw_terms.extend(self._tokenize_text(procedure.get("description")))
            else:
                raw_terms.extend(self._tokenize_text(procedure))

        for medication in (medical_extraction.get("medications") or [])[:8]:
            if isinstance(medication, dict):
                raw_terms.extend(self._tokenize_text(medication.get("name")))
            else:
                raw_terms.extend(self._tokenize_text(medication))

        unique_terms: List[str] = []
        seen = set()
        stopwords = {
            "patient", "treatment", "hospital", "medical", "doctor", "claim",
            "therapy", "tablet", "capsule", "daily", "history", "normal",
        }

        for term in raw_terms:
            if term in stopwords:
                continue
            if term not in seen:
                seen.add(term)
                unique_terms.append(term)

        return unique_terms[:30]

    def _tokenize_text(self, value: Any) -> List[str]:
        text = str(value or "").strip().lower()
        if not text:
            return []

        tokens = [piece for piece in text.replace("/", " ").replace("-", " ").split() if len(piece) >= 3]
        cleaned = ["".join(ch for ch in token if ch.isalnum()) for token in tokens]
        return [token for token in cleaned if len(token) >= 3]

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

        # Normalize complex fields to strict schema expected by AnalysisResponse
        response["compliance_risks"] = self._normalize_compliance_risks(
            response.get("compliance_risks", [])
        )
        response["clause_references"] = self._normalize_clause_references(
            response.get("clause_references", [])
        )
        response["recommendations"] = self._normalize_recommendations(
            response.get("recommendations", [])
        )
        response["missing_documentation"] = [
            str(item) for item in response.get("missing_documentation", [])
        ]
        response["reasoning"] = str(
            response.get("reasoning") or "Analysis completed with limited information."
        )

        return response

    def _normalize_compliance_risks(self, risks: Any) -> List[Dict[str, Any]]:
        """Normalize risk objects to ComplianceRisk schema."""
        if not isinstance(risks, list):
            return []

        normalized = []
        valid_severities = {"high", "medium", "low"}

        for idx, risk in enumerate(risks):
            if isinstance(risk, dict):
                severity = str(risk.get("severity", "medium")).lower()
                if severity not in valid_severities:
                    severity = "medium"

                normalized.append({
                    "risk_id": str(risk.get("risk_id") or f"risk_{idx + 1}"),
                    "severity": severity,
                    "description": str(
                        risk.get("description") or risk.get("risk") or "Compliance risk identified"
                    ),
                    "affected_clause": (
                        str(risk.get("affected_clause"))
                        if risk.get("affected_clause") is not None
                        else None
                    )
                })
            else:
                normalized.append({
                    "risk_id": f"risk_{idx + 1}",
                    "severity": "medium",
                    "description": str(risk),
                    "affected_clause": None
                })

        return normalized

    def _normalize_clause_references(self, refs: Any) -> List[Dict[str, Any]]:
        """Normalize clause references to ClauseReference schema."""
        if not isinstance(refs, list):
            return []

        normalized = []
        for idx, ref in enumerate(refs):
            if isinstance(ref, dict):
                raw_score = ref.get("relevance_score", ref.get("relevance", 0.5))
                try:
                    score = float(raw_score)
                except (TypeError, ValueError):
                    score = 0.5
                score = max(0.0, min(1.0, score))

                normalized.append({
                    "clause_id": str(ref.get("clause_id") or f"clause_{idx + 1}"),
                    "clause_text": str(ref.get("clause_text") or ref.get("content") or ""),
                    "relevance_score": score,
                    "source_document": str(
                        ref.get("source_document")
                        or ref.get("source")
                        or ref.get("insurer")
                        or "unknown"
                    )
                })
            else:
                normalized.append({
                    "clause_id": f"clause_{idx + 1}",
                    "clause_text": str(ref),
                    "relevance_score": 0.5,
                    "source_document": "unknown"
                })

        return normalized

    def _normalize_recommendations(self, recommendations: Any) -> List[Dict[str, Any]]:
        """Normalize recommendations to Recommendation schema."""
        if not isinstance(recommendations, list):
            return []

        normalized = []
        valid_priorities = {"high", "medium", "low"}

        for idx, rec in enumerate(recommendations):
            if isinstance(rec, dict):
                priority = str(rec.get("priority", "medium")).lower()
                if priority not in valid_priorities:
                    priority = "medium"

                action = str(rec.get("action") or rec.get("recommendation") or "Review claim details")
                rationale = str(
                    rec.get("rationale")
                    or rec.get("mitigation")
                    or "Recommended based on analysis findings"
                )

                normalized.append({
                    "recommendation_id": str(rec.get("recommendation_id") or f"rec_{idx + 1}"),
                    "priority": priority,
                    "action": action,
                    "rationale": rationale
                })
            else:
                normalized.append({
                    "recommendation_id": f"rec_{idx + 1}",
                    "priority": "medium",
                    "action": str(rec),
                    "rationale": "Recommended based on analysis findings"
                })

        return normalized

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
