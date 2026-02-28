import json
from pathlib import Path
from uuid import uuid4

from langchain_core.documents import Document

from app.core.settings import get_settings
from app.db.models import ClaimModel, ClauseModel, DocumentModel, PolicyModel
from app.db.session import db_session
from app.schemas.claims import Citation, ClaimAnalyzeRequest, ClaimAnalyzeResponse, ClaimDecision


class ClaimService:
    def analyze(self, payload: ClaimAnalyzeRequest, trace_id: str) -> ClaimAnalyzeResponse:
        settings = get_settings()

        with db_session() as session:
            policy = session.get(PolicyModel, payload.policy_id)
            discharge = session.get(DocumentModel, payload.discharge_summary_id)

            if policy is None or discharge is None:
                decision = ClaimDecision.uncertain
                confidence = 0.2
                citations: list[Citation] = []
                explanation = "Missing policy or discharge summary record."
            elif policy.indexing_status != "active":
                decision = ClaimDecision.uncertain
                confidence = 0.3
                citations = []
                explanation = "Policy is not indexed yet. Retry after indexing completes."
            else:
                try:
                    from app.retriever.embeddings import load_embedding_model
                    from app.retriever.retriever import ClaimLensRetriever

                    clause_rows = session.query(ClauseModel).filter(ClauseModel.policy_id == policy.policy_id).all()

                    clause_documents = [
                        Document(
                            page_content=row.content,
                            metadata={
                                "clause_id": row.clause_id,
                                "insurer": row.insurer,
                                "section": row.section,
                                "clause_number": row.clause_number,
                                "clause_title": row.clause_title,
                                "start_page": row.start_page,
                                "chunk_type": row.chunk_type,
                            },
                        )
                        for row in clause_rows
                    ]

                    query = payload.notes or "Review claim eligibility based on discharge summary and policy terms."

                    embedding_model = load_embedding_model("base")
                    retriever = ClaimLensRetriever(
                        clause_documents=clause_documents,
                        embedding_model=embedding_model,
                        index_path=str(Path(settings.faiss_index_root) / payload.policy_id),
                        dense_top_k=40,
                        use_reranker=True,
                    )
                    results = retriever.retrieve(query)
                    top_results = results[:5]

                    citations = [
                        Citation(
                            clause_id=doc.metadata.get("clause_id", "unknown"),
                            relevance_score=max(0.0, 1.0 - (idx * 0.12)),
                            rationale=(doc.page_content[:220] + "...") if len(doc.page_content) > 220 else doc.page_content,
                        )
                        for idx, doc in enumerate(top_results)
                    ]

                    decision = ClaimDecision.likely_approved if citations else ClaimDecision.uncertain
                    confidence = 0.76 if citations else 0.4
                    explanation = (
                        "Decision generated using dense retrieval + BM25 hybrid + cross-encoder reranker over indexed clauses."
                        if citations
                        else "No relevant clauses were retrieved."
                    )
                except Exception as exc:
                    decision = ClaimDecision.uncertain
                    confidence = 0.2
                    citations = []
                    explanation = f"Claim analysis pipeline unavailable: {exc}"

        claim_id = f"claim_{uuid4().hex[:12]}"
        response = ClaimAnalyzeResponse(
            claim_id=claim_id,
            decision=decision,
            confidence=confidence,
            explanation=explanation,
            citations=citations,
            trace_id=trace_id,
        )

        with db_session() as session:
            session.add(
                ClaimModel(
                    claim_id=claim_id,
                    discharge_summary_id=payload.discharge_summary_id,
                    policy_id=payload.policy_id,
                    decision=response.decision.value,
                    confidence=response.confidence,
                    explanation=response.explanation,
                    citations_json=json.dumps([citation.model_dump() for citation in response.citations]),
                    trace_id=trace_id,
                )
            )

        return response

    def get_claim(self, claim_id: str) -> ClaimAnalyzeResponse | None:
        with db_session() as session:
            row = session.get(ClaimModel, claim_id)
            if row is None:
                return None
            citations = [Citation(**item) for item in json.loads(row.citations_json)]
            return ClaimAnalyzeResponse(
                claim_id=row.claim_id,
                decision=ClaimDecision(row.decision),
                confidence=row.confidence,
                explanation=row.explanation,
                citations=citations,
                trace_id=row.trace_id,
            )


claim_service = ClaimService()
