# backend/app/ingestion/medical_extractor.py
"""
Medical entity extraction from discharge summaries.
"""

import re
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class MedicalEntity:
    """Represents an extracted medical entity."""
    entity_type: str
    value: str
    confidence: float
    position: Optional[tuple] = None


@dataclass
class MedicalExtraction:
    """Complete medical extraction result."""
    patient_info: Dict[str, Any]
    diagnoses: List[Dict[str, Any]]
    procedures: List[Dict[str, Any]]
    medications: List[Dict[str, Any]]
    vital_signs: Dict[str, Any]
    lab_results: List[Dict[str, Any]]
    admission_date: Optional[str]
    discharge_date: Optional[str]
    attending_physician: Optional[str]
    hospital_name: Optional[str]
    raw_entities: List[MedicalEntity]


class MedicalExtractor:
    """
    Extracts structured medical information from discharge summaries.
    Uses pattern matching and NLP techniques.
    """

    # Common medical patterns
    DIAGNOSIS_PATTERNS = [
        r"(?:diagnosis|diagnoses|dx|impression)[\s:]+([^\n]+)",
        r"(?:primary diagnosis)[\s:]+([^\n]+)",
        r"(?:secondary diagnosis)[\s:]+([^\n]+)",
    ]

    PROCEDURE_PATTERNS = [
        r"(?:procedure|procedures|operation)[\s:]+([^\n]+)",
        r"(?:surgical procedure)[\s:]+([^\n]+)",
    ]

    MEDICATION_PATTERNS = [
        r"(?:medications?|meds|rx)[\s:]+([^\n]+)",
        r"(?:discharge medications?)[\s:]+([^\n]+)",
    ]

    DATE_PATTERNS = [
        r"(?:admission date|admitted|date of admission)[\s:]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        r"(?:discharge date|discharged|date of discharge)[\s:]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
    ]

    ICD_PATTERN = r"([A-Z]\d{2}(?:\.\d{1,2})?)"
    CPT_PATTERN = r"(\d{5})"

    def __init__(self):
        self.entities: List[MedicalEntity] = []

    async def extract(self, text: str) -> MedicalExtraction:
        """
        Extract medical entities from text.

        Args:
            text: Document text content

        Returns:
            Structured medical extraction
        """
        self.entities = []
        text_lower = text.lower()

        # Extract various components
        patient_info = self._extract_patient_info(text)
        diagnoses = self._extract_diagnoses(text)
        procedures = self._extract_procedures(text)
        medications = self._extract_medications(text)
        vital_signs = self._extract_vital_signs(text)
        lab_results = self._extract_lab_results(text)
        dates = self._extract_dates(text)

        return MedicalExtraction(
            patient_info=patient_info,
            diagnoses=diagnoses,
            procedures=procedures,
            medications=medications,
            vital_signs=vital_signs,
            lab_results=lab_results,
            admission_date=dates.get("admission"),
            discharge_date=dates.get("discharge"),
            attending_physician=self._extract_physician(text),
            hospital_name=self._extract_hospital(text),
            raw_entities=self.entities
        )

    def _extract_patient_info(self, text: str) -> Dict[str, Any]:
        """Extract patient demographic information."""
        info = {}

        # Patient name
        name_match = re.search(
            r"(?:patient name|name)[\s:]+([A-Za-z\s]+?)(?:\n|,|DOB)",
            text,
            re.IGNORECASE
        )
        if name_match:
            info["name"] = name_match.group(1).strip()
            self.entities.append(MedicalEntity(
                entity_type="PATIENT_NAME",
                value=info["name"],
                confidence=0.9
            ))

        # Date of birth
        dob_match = re.search(
            r"(?:DOB|date of birth|birth date)[\s:]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
            text,
            re.IGNORECASE
        )
        if dob_match:
            info["date_of_birth"] = dob_match.group(1)
            self.entities.append(MedicalEntity(
                entity_type="DATE_OF_BIRTH",
                value=info["date_of_birth"],
                confidence=0.95
            ))

        # MRN
        mrn_match = re.search(
            r"(?:MRN|medical record|record number)[\s:#]+(\w+)",
            text,
            re.IGNORECASE
        )
        if mrn_match:
            info["mrn"] = mrn_match.group(1)
            self.entities.append(MedicalEntity(
                entity_type="MRN",
                value=info["mrn"],
                confidence=0.95
            ))

        # Age
        age_match = re.search(
            r"(?:age)[\s:]+(\d+)[\s-]*(?:year|yr|y\.?o\.?)?",
            text,
            re.IGNORECASE
        )
        if age_match:
            info["age"] = int(age_match.group(1))

        # Gender
        gender_match = re.search(
            r"(?:sex|gender)[\s:]+([MF]|male|female)",
            text,
            re.IGNORECASE
        )
        if gender_match:
            gender = gender_match.group(1).lower()
            info["gender"] = "male" if gender in ["m", "male"] else "female"

        return info

    def _extract_diagnoses(self, text: str) -> List[Dict[str, Any]]:
        """Extract diagnoses with ICD codes."""
        diagnoses = []

        for pattern in self.DIAGNOSIS_PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                diagnosis_text = match.group(1).strip()

                # Look for ICD codes
                icd_codes = re.findall(self.ICD_PATTERN, diagnosis_text)

                diagnosis = {
                    "description": diagnosis_text,
                    "icd_codes": icd_codes,
                    "is_primary": "primary" in match.group(0).lower()
                }

                diagnoses.append(diagnosis)
                self.entities.append(MedicalEntity(
                    entity_type="DIAGNOSIS",
                    value=diagnosis_text,
                    confidence=0.85
                ))

        return diagnoses

    def _extract_procedures(self, text: str) -> List[Dict[str, Any]]:
        """Extract procedures with CPT codes."""
        procedures = []

        for pattern in self.PROCEDURE_PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                procedure_text = match.group(1).strip()

                # Look for CPT codes
                cpt_codes = re.findall(self.CPT_PATTERN, procedure_text)

                procedure = {
                    "description": procedure_text,
                    "cpt_codes": cpt_codes
                }

                procedures.append(procedure)
                self.entities.append(MedicalEntity(
                    entity_type="PROCEDURE",
                    value=procedure_text,
                    confidence=0.85
                ))

        return procedures

    def _extract_medications(self, text: str) -> List[Dict[str, Any]]:
        """Extract medication information."""
        medications = []

        # Find medication sections
        med_section = re.search(
            r"(?:medications?|discharge medications?)[\s:]+(.+?)(?=\n\n|\n[A-Z]|\Z)",
            text,
            re.IGNORECASE | re.DOTALL
        )

        if med_section:
            med_text = med_section.group(1)

            # Parse individual medications
            med_lines = med_text.split("\n")
            for line in med_lines:
                line = line.strip()
                if line and len(line) > 3:
                    # Try to extract dosage
                    dosage_match = re.search(
                        r"(\d+(?:\.\d+)?)\s*(mg|ml|mcg|g|units?)",
                        line,
                        re.IGNORECASE
                    )

                    medication = {
                        "name": line,
                        "dosage": dosage_match.group(0) if dosage_match else None
                    }

                    medications.append(medication)
                    self.entities.append(MedicalEntity(
                        entity_type="MEDICATION",
                        value=line,
                        confidence=0.8
                    ))

        return medications

    def _extract_vital_signs(self, text: str) -> Dict[str, Any]:
        """Extract vital signs."""
        vitals = {}

        # Blood pressure
        bp_match = re.search(
            r"(?:BP|blood pressure)[\s:]+(\d{2,3})/(\d{2,3})",
            text,
            re.IGNORECASE
        )
        if bp_match:
            vitals["blood_pressure"] = {
                "systolic": int(bp_match.group(1)),
                "diastolic": int(bp_match.group(2))
            }

        # Heart rate
        hr_match = re.search(
            r"(?:HR|heart rate|pulse)[\s:]+(\d{2,3})",
            text,
            re.IGNORECASE
        )
        if hr_match:
            vitals["heart_rate"] = int(hr_match.group(1))

        # Temperature
        temp_match = re.search(
            r"(?:temp|temperature)[\s:]+(\d{2,3}(?:\.\d)?)",
            text,
            re.IGNORECASE
        )
        if temp_match:
            vitals["temperature"] = float(temp_match.group(1))

        # Respiratory rate
        rr_match = re.search(
            r"(?:RR|respiratory rate|resp)[\s:]+(\d{1,2})",
            text,
            re.IGNORECASE
        )
        if rr_match:
            vitals["respiratory_rate"] = int(rr_match.group(1))

        # Oxygen saturation
        o2_match = re.search(
            r"(?:O2|SpO2|oxygen sat)[\s:]+(\d{2,3})%?",
            text,
            re.IGNORECASE
        )
        if o2_match:
            vitals["oxygen_saturation"] = int(o2_match.group(1))

        return vitals

    def _extract_lab_results(self, text: str) -> List[Dict[str, Any]]:
        """Extract laboratory results."""
        lab_results = []

        # Common lab patterns
        lab_patterns = [
            (r"(?:WBC|white blood cell)[\s:]+(\d+(?:\.\d+)?)", "WBC", "K/uL"),
            (r"(?:RBC|red blood cell)[\s:]+(\d+(?:\.\d+)?)", "RBC", "M/uL"),
            (r"(?:Hgb|hemoglobin)[\s:]+(\d+(?:\.\d+)?)", "Hemoglobin", "g/dL"),
            (r"(?:Hct|hematocrit)[\s:]+(\d+(?:\.\d+)?)", "Hematocrit", "%"),
            (r"(?:platelets?|plt)[\s:]+(\d+)", "Platelets", "K/uL"),
            (r"(?:glucose|blood sugar)[\s:]+(\d+)", "Glucose", "mg/dL"),
            (r"(?:creatinine|cr)[\s:]+(\d+(?:\.\d+)?)", "Creatinine", "mg/dL"),
            (r"(?:BUN)[\s:]+(\d+)", "BUN", "mg/dL"),
        ]

        for pattern, name, unit in lab_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                lab_results.append({
                    "test_name": name,
                    "value": float(match.group(1)),
                    "unit": unit
                })

        return lab_results

    def _extract_dates(self, text: str) -> Dict[str, str]:
        """Extract admission and discharge dates."""
        dates = {}

        admission_match = re.search(
            r"(?:admission date|admitted|date of admission)[\s:]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
            text,
            re.IGNORECASE
        )
        if admission_match:
            dates["admission"] = admission_match.group(1)

        discharge_match = re.search(
            r"(?:discharge date|discharged|date of discharge)[\s:]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
            text,
            re.IGNORECASE
        )
        if discharge_match:
            dates["discharge"] = discharge_match.group(1)

        return dates

    def _extract_physician(self, text: str) -> Optional[str]:
        """Extract attending physician name."""
        match = re.search(
            r"(?:attending|physician|doctor|dr\.?)[\s:]+([A-Za-z\s\.]+?)(?:\n|,|MD|DO)",
            text,
            re.IGNORECASE
        )
        if match:
            return match.group(1).strip()
        return None

    def _extract_hospital(self, text: str) -> Optional[str]:
        """Extract hospital name."""
        match = re.search(
            r"([A-Za-z\s]+(?:hospital|medical center|clinic|health))",
            text,
            re.IGNORECASE
        )
        if match:
            return match.group(1).strip()
        return None
