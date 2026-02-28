# backend/app/llm/prompts.py
"""
Prompt templates for LLM interactions.
"""

COMPLIANCE_ANALYSIS_SYSTEM_PROMPT = """You are an expert medical insurance claim compliance analyst. Your role is to analyze medical claims against insurance policy documents and provide detailed compliance assessments.

You must:
1. Carefully analyze the medical claim details against policy coverage
2. Identify any compliance risks or potential issues
3. Reference specific policy clauses that apply
4. Provide clear, actionable recommendations
5. Give an honest assessment of approval likelihood

Always respond with structured JSON output following the exact schema provided."""

COMPLIANCE_ANALYSIS_PROMPT = """Analyze the following medical insurance claim for compliance with the policy.

## Medical Claim Information
{claim_info}

## Relevant Policy Clauses
{policy_clauses}

## Billing Information
{billing_info}

Based on this information, provide a comprehensive compliance analysis in the following JSON format:

{{
    "approval_score": <number 0-100>,
    "approval_likelihood": "<high|medium|low|very_low>",
    "compliance_risks": [
        {{
            "risk_id": "<unique_id>",
            "severity": "<high|medium|low>",
            "description": "<detailed description>",
            "affected_clause": "<clause reference if applicable>"
        }}
    ],
    "clause_references": [
        {{
            "clause_id": "<clause identifier>",
            "clause_text": "<relevant clause text>",
            "relevance_score": <0.0-1.0>,
            "source_document": "<document name>"
        }}
    ],
    "missing_documentation": [
        "<list of missing documents or information>"
    ],
    "recommendations": [
        {{
            "recommendation_id": "<unique_id>",
            "priority": "<high|medium|low>",
            "action": "<specific action to take>",
            "rationale": "<why this is recommended>"
        }}
    ],
    "reasoning": "<detailed explanation of the analysis and conclusions>"
}}

Ensure your analysis is thorough, accurate, and based solely on the provided information."""

MEDICAL_EXTRACTION_PROMPT = """Extract structured medical information from the following discharge summary.

## Discharge Summary
{discharge_summary}

Extract and return the following information in JSON format:

{{
    "patient_info": {{
        "name": "<patient name>",
        "age": <age>,
        "gender": "<male|female>",
        "mrn": "<medical record number>",
        "date_of_birth": "<DOB>"
    }},
    "admission_info": {{
        "admission_date": "<date>",
        "discharge_date": "<date>",
        "length_of_stay": <days>,
        "admission_type": "<emergency|elective|urgent>"
    }},
    "diagnoses": [
        {{
            "description": "<diagnosis description>",
            "icd_code": "<ICD-10 code if available>",
            "is_primary": <true|false>
        }}
    ],
    "procedures": [
        {{
            "description": "<procedure description>",
            "cpt_code": "<CPT code if available>",
            "date_performed": "<date if available>"
        }}
    ],
    "medications": [
        {{
            "name": "<medication name>",
            "dosage": "<dosage>",
            "frequency": "<frequency>",
            "route": "<route of administration>"
        }}
    ],
    "attending_physician": "<physician name>",
    "hospital": "<hospital name>"
}}

Extract only information that is explicitly stated in the document. Use null for missing fields."""
