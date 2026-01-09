"""
LLM-driven result formatting service for dynamic result display based on query type.
This service uses LLM to generate appropriate result displays for different analysis types.
"""
import json
import logging
import os
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class ResultFormatter:
    """Service to format computation results using LLM for dynamic display."""
    
    def __init__(self):
        # Provider selection (default: groq - FREE tier)
        self.llm_provider: str = os.getenv("LLM_PROVIDER", "groq").lower()
        
        # Groq configuration (FREE tier: 14,400 requests/day - RECOMMENDED)
        self.groq_api_key: Optional[str] = os.getenv("GROQ_API_KEY")
        self.groq_model: str = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
        
        # OpenAI configuration (paid)
        self.openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
        self.openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        
        self.timeout_seconds: int = int(os.getenv("LLM_TIMEOUT_SECONDS", "15"))
    
    def format_result(
        self,
        result_data: Dict[str, Any],
        spec: Optional[Dict[str, Any]] = None,
        research_question: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Format computation results for display based on the query type and result structure.
        
        Args:
            result_data: The raw computation result
            spec: The computation spec (if available)
            research_question: The research question from the prompt
        
        Returns:
            Formatted result with display instructions
        """
        try:
            # If LLM is available, use it for intelligent formatting
            if self.groq_api_key:
                return self._format_with_llm(result_data, spec, research_question)
            else:
                # Fallback to rule-based formatting
                return self._format_with_rules(result_data, spec, research_question)
        except Exception as e:
            logger.warning(f"LLM formatting failed, using rule-based: {e}")
            return self._format_with_rules(result_data, spec, research_question)
    
    def _format_with_llm(
        self,
        result_data: Dict[str, Any],
        spec: Optional[Dict[str, Any]],
        research_question: Optional[str]
    ) -> Dict[str, Any]:
        """Format results using LLM."""
        system_prompt = self._get_formatting_prompt()
        
        # Extract medical context from spec
        medical_context = self._extract_medical_context(spec, result_data)
        
        user_prompt = f"""Given the following computation result and research question, generate a comprehensive formatted display structure with domain-specific recommendations.

Research Question: {research_question or 'Not specified'}

Medical Context:
{json.dumps(medical_context, indent=2)}

Computation Spec:
{json.dumps(spec, indent=2) if spec else 'Not available'}

Raw Result Data:
{json.dumps(result_data, indent=2, default=str)}

Generate a JSON response with the following structure:
{{
  "display_type": "table" | "cards" | "list" | "chart" | "mixed",
  "title": "Main result title",
  "summary": "Brief, comprehensive summary of findings in 2-3 sentences",
  "sections": [
    {{
      "title": "Section title",
      "type": "statistics" | "patient_list" | "threshold_analysis" | "cohort_demographics" | "survival_curves" | "correlation_matrix" | "risk_assessment",
      "content": {{...}},  // For patient_list: {{"headers": ["col1", "col2"], "rows": [["val1", "val2"]]}}
      "data": {{...}}  // Additional structured data
    }}
  ],
  "key_insights": ["insight1", "insight2"],  // 3-5 key findings
  "recommendations": [
    {{
      "priority": "high" | "medium" | "low",
      "category": "clinical" | "monitoring" | "treatment" | "prevention" | "research",
      "text": "Specific, actionable recommendation based on the medical domain and findings"
    }}
  ],  // Domain-specific, actionable recommendations
  "clinical_significance": "Explanation of what these results mean clinically",
  "next_steps": ["step1", "step2"]  // Suggested follow-up actions
}}

IMPORTANT:
- **CRITICAL: Use ONLY the actual patient data provided in the Raw Result Data. DO NOT generate or invent patient names, IDs, or data.**
- If "matching_patients" or "patients_above_threshold" is in the result, use that EXACT data to create the patient list table
- Extract patient data fields directly from the provided data (e.g., patient_id, Age, Gender, Cancer_Type, Stage, etc.)
- DO NOT create fake patient names - use only the fields that exist in the actual data
- For patient_list sections, use the actual column names and values from the matching_patients data
- Analyze the medical domain (diabetes, cancer, cardiovascular, etc.) from variables and context
- Provide SPECIFIC recommendations based on the medical condition and findings
- For threshold analyses, include risk stratification and clinical implications
- For patient lists, explain why these patients need attention
- For date-based queries, highlight temporal patterns and trends
- For age-based queries, consider age-specific risk factors and recommendations
- For condition-based queries, provide condition-specific clinical guidance
- Make recommendations actionable and evidence-based
- Consider the severity and prevalence of findings
- Adapt recommendations to the specific query type (listing, filtering, analysis)"""

        try:
            formatted_result = None
            if self.llm_provider == "groq" and self.groq_api_key:
                formatted_result = self._call_groq(system_prompt, user_prompt, result_data, spec)
            elif self.llm_provider == "openai" and self.openai_api_key:
                formatted_result = self._call_openai(system_prompt, user_prompt, result_data, spec)
            
            # Post-process to ensure actual patient data is used
            if formatted_result:
                formatted_result = self._ensure_actual_patient_data(formatted_result, result_data)
                return formatted_result
        except Exception as e:
            logger.warning(f"LLM call failed: {e}")
        
        # Fallback to rule-based
        return self._format_with_rules(result_data, spec, research_question)
    
    def _ensure_actual_patient_data(
        self,
        formatted_result: Dict[str, Any],
        result_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Ensure formatted result uses actual patient data instead of generated data."""
        # Extract actual patient data from result_data
        actual_patients = None
        
        # Check nested result structure
        nested_result = result_data.get("result", {})
        if not nested_result and isinstance(result_data, dict):
            nested_result = result_data
        
        # Look for matching_patients in operations
        if nested_result.get("operations"):
            for op_id, op_result in nested_result["operations"].items():
                if isinstance(op_result, dict) and op_result.get("matching_patients"):
                    actual_patients = op_result["matching_patients"]
                    break
        
        # Also check top-level
        if not actual_patients and nested_result.get("matching_patients"):
            actual_patients = nested_result["matching_patients"]
        
        # If we have actual patient data, replace any patient_list sections with real data
        if actual_patients and len(actual_patients) > 0:
            # Find patient_list sections in formatted result
            if formatted_result.get("sections"):
                for section in formatted_result["sections"]:
                    if section.get("type") == "patient_list":
                        # Replace with actual patient data
                        first_patient = actual_patients[0]
                        available_columns = [k for k in first_patient.keys() if k not in ["org_id"]]
                        headers = [col.replace("_", " ").title() for col in available_columns]
                        
                        rows = []
                        for p in actual_patients[:100]:
                            row = []
                            for col in available_columns:
                                value = p.get(col)
                                if value is None:
                                    row.append("N/A")
                                elif isinstance(value, (int, float)):
                                    if col.lower() in ["age"]:
                                        row.append(str(int(value)))
                                    else:
                                        row.append(f"{value:.2f}" if isinstance(value, float) else str(value))
                                else:
                                    row.append(str(value))
                            rows.append(row)
                        
                        section["content"] = {
                            "headers": headers,
                            "rows": rows
                        }
                        section["data"] = {"total_count": len(actual_patients)}
        
        return formatted_result
    
    def _call_groq(
        self,
        system_prompt: str,
        user_prompt: str,
        result_data: Dict[str, Any],
        spec: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Call Groq API for formatting."""
        body = {
            "model": self.groq_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }
        
        with httpx.Client(timeout=self.timeout_seconds) as client:
            resp = client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.groq_api_key}"},
                json=body,
            )
            resp.raise_for_status()
            data = resp.json()
        
        message = data.get("choices", [{}])[0].get("message", {})
        content = message.get("content", "{}")
        
        formatted = json.loads(content)
        # Don't include raw_data to avoid circular references
        # The raw data is already available in the result structure
        return formatted
    
    def _call_openai(
        self,
        system_prompt: str,
        user_prompt: str,
        result_data: Dict[str, Any],
        spec: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Call OpenAI API for formatting."""
        body = {
            "model": self.openai_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }
        
        with httpx.Client(timeout=self.timeout_seconds) as client:
            resp = client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.openai_api_key}"},
                json=body,
            )
            resp.raise_for_status()
            data = resp.json()
        
        message = data.get("choices", [{}])[0].get("message", {})
        content = message.get("content", "{}")
        
        formatted = json.loads(content)
        # Don't include raw_data to avoid circular references
        # The raw data is already available in the result structure
        return formatted
    
    def _format_with_rules(
        self,
        result_data: Dict[str, Any],
        spec: Optional[Dict[str, Any]],
        research_question: Optional[str]
    ) -> Dict[str, Any]:
        """Rule-based formatting fallback with domain-aware recommendations."""
        analysis_type = (spec or {}).get("analysis_type") or result_data.get("analysis_type", "basic_statistics")
        operations = result_data.get("operations") or {}
        
        # Extract medical context for recommendations
        medical_context = self._extract_medical_context(spec, result_data)
        
        formatted = {
            "display_type": "mixed",
            "title": self._get_title(analysis_type, research_question),
            "summary": self._get_summary(result_data, analysis_type),
            "sections": [],
            "key_insights": [],
            "recommendations": [],
            "clinical_significance": "",
            "next_steps": []
            # Don't include raw_data to avoid circular references
        }
        
        # Extract nested result if present
        nested_result = result_data.get("result", {})
        if not nested_result and isinstance(result_data, dict):
            nested_result = result_data
        
        # Add sections based on result structure
        if nested_result.get("patients_above_threshold"):
            patients = nested_result["patients_above_threshold"]
            formatted["sections"].append({
                "title": "Patients Matching Criteria",
                "type": "patient_list",
                "content": {
                    "headers": ["Patient ID", "Value", "Risk Level", "Organization"],
                    "rows": [
                        [
                            str(p.get("patient_id", "N/A")),
                            f"{p.get('value', 0):.2f}",
                            p.get("risk_level", "N/A"),
                            str(p.get("org_id", "N/A"))
                        ]
                        for p in patients[:50]  # Limit to 50 for display
                    ]
                },
                "data": {"total_count": len(patients)}
            })
            
            # Add recommendations for threshold analysis
            threshold = nested_result.get("threshold_value")
            if threshold:
                formatted["recommendations"].extend(
                    self._generate_domain_recommendations(medical_context, nested_result)
                )
        
        # Check operations for categorical filters and threshold analysis
        if nested_result.get("operations"):
            for op_id, op_result in nested_result["operations"].items():
                if isinstance(op_result, dict):
                    # Handle categorical_filter operations (e.g., "list breast cancer patients", "list stage 2 and 4 patients")
                    if op_result.get("type") == "categorical_filter":
                        patients = op_result.get("matching_patients", [])
                        filter_criteria = op_result.get("filter_criteria", {})
                        
                        if patients and len(patients) > 0:
                            # Extract all available columns from the first patient
                            first_patient = patients[0]
                            available_columns = [k for k in first_patient.keys() if k not in ["org_id"]]
                            
                            # Create headers from actual patient data columns
                            headers = [col.replace("_", " ").title() for col in available_columns]
                            
                            # Create rows from actual patient data
                            rows = []
                            for p in patients[:100]:  # Limit to 100 for display
                                row = []
                                for col in available_columns:
                                    value = p.get(col)
                                    if value is None:
                                        row.append("N/A")
                                    elif isinstance(value, (int, float)):
                                        # Format numbers appropriately
                                        if col.lower() in ["age"]:
                                            row.append(str(int(value)))
                                        else:
                                            row.append(f"{value:.2f}" if isinstance(value, float) else str(value))
                                    else:
                                        row.append(str(value))
                                rows.append(row)
                            
                            formatted["sections"].append({
                                "title": "Patient List",
                                "type": "patient_list",
                                "content": {
                                    "headers": headers,
                                    "rows": rows
                                },
                                "data": {"total_count": len(patients)}
                            })
                            
                            # Generate insights
                            formatted["key_insights"].append(f"Found {len(patients)} patients matching the specified criteria.")
                            
                            # Generate recommendations
                            formatted["recommendations"].extend(
                                self._generate_domain_recommendations(medical_context, op_result)
                            )
                    
                    elif op_result.get("type") == "mean" and op_result.get("threshold_value"):
                        # Threshold analysis operation
                        formatted["sections"].append({
                            "title": "Threshold Analysis",
                            "type": "threshold_analysis",
                            "data": {
                                "threshold": op_result.get("threshold_value"),
                                "above_count": op_result.get("above_threshold_count", 0),
                                "above_percentage": op_result.get("above_threshold_percentage", 0),
                                "total_count": op_result.get("count", 0)
                            }
                        })
                        
                        if op_result.get("patients_above_threshold"):
                            patients = op_result["patients_above_threshold"]
                            formatted["sections"].append({
                                "title": "Patients Above Threshold",
                                "type": "patient_list",
                                "content": {
                                    "headers": ["Patient ID", "Value", "Risk Level"],
                                    "rows": [
                                        [
                                            str(p.get("patient_id", "N/A")),
                                            f"{p.get('value', 0):.2f}",
                                            p.get("risk_level", "N/A")
                                        ]
                                        for p in patients[:50]
                                    ]
                                },
                                "data": {"total_count": len(patients)}
                            })
                            
                            # Generate recommendations
                            formatted["recommendations"].extend(
                                self._generate_domain_recommendations(medical_context, op_result)
                            )
                    else:
                        formatted["sections"].append({
                            "title": f"Operation: {op_id}",
                            "type": "statistics",
                            "data": op_result
                        })
        
        if nested_result.get("mean") or nested_result.get("average"):
            mean = nested_result.get("mean") or nested_result.get("average")
            formatted["sections"].append({
                "title": "Statistical Summary",
                "type": "statistics",
                "data": {
                    "mean": mean,
                    "count": nested_result.get("count", 0),
                    "sum": nested_result.get("sum"),
                    "variance": nested_result.get("variance")
                }
            })
        
        # Generate key insights
        formatted["key_insights"] = self._generate_key_insights(nested_result, medical_context)
        
        # Generate clinical significance
        formatted["clinical_significance"] = self._generate_clinical_significance(nested_result, medical_context)
        
        # Generate next steps
        formatted["next_steps"] = self._generate_next_steps(nested_result, medical_context)
        
        return formatted
    
    def _generate_domain_recommendations(
        self,
        medical_context: Dict[str, Any],
        result_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate domain-specific recommendations based on medical context and results."""
        recommendations = []
        domain = medical_context.get("medical_domain", "general")
        threshold = result_data.get("threshold_value")
        above_count = result_data.get("above_threshold_count", 0)
        above_percentage = result_data.get("above_threshold_percentage", 0)
        
        if domain == "diabetes" and threshold:
            if above_percentage > 30:
                recommendations.append({
                    "priority": "high",
                    "category": "clinical",
                    "text": f"High prevalence ({above_percentage:.1f}%) of patients above {threshold} mg/dL. Consider population-level intervention strategies and enhanced monitoring protocols."
                })
            elif above_percentage > 10:
                recommendations.append({
                    "priority": "medium",
                    "category": "monitoring",
                    "text": f"Moderate prevalence ({above_percentage:.1f}%) of elevated glucose levels. Implement targeted monitoring and patient education programs."
                })
            
            recommendations.append({
                "priority": "high",
                "category": "treatment",
                "text": "Review medication regimens for patients above threshold. Consider dose adjustments or additional glucose-lowering agents."
            })
            
            recommendations.append({
                "priority": "medium",
                "category": "prevention",
                "text": "Provide lifestyle counseling focusing on diet, exercise, and medication adherence for affected patients."
            })
        
        elif domain == "oncology":
            recommendations.append({
                "priority": "high",
                "category": "clinical",
                "text": "Coordinate with oncology team for appropriate staging, treatment planning, and follow-up care."
            })
            recommendations.append({
                "priority": "medium",
                "category": "monitoring",
                "text": "Schedule regular follow-up appointments to monitor treatment response and disease progression."
            })
        
        elif domain == "cardiology":
            recommendations.append({
                "priority": "high",
                "category": "clinical",
                "text": "Assess cardiovascular risk factors and consider preventive interventions based on findings."
            })
            recommendations.append({
                "priority": "medium",
                "category": "monitoring",
                "text": "Implement regular cardiovascular monitoring and risk factor management."
            })
        
        else:
            # General recommendations
            if threshold and above_count > 0:
                recommendations.append({
                    "priority": "medium",
                    "category": "clinical",
                    "text": f"{above_count} patients exceed the threshold value. Review individual cases for appropriate clinical intervention."
                })
        
        return recommendations
    
    def _generate_key_insights(
        self,
        result_data: Dict[str, Any],
        medical_context: Dict[str, Any]
    ) -> List[str]:
        """Generate key insights from the results."""
        insights = []
        
        if result_data.get("mean") or result_data.get("average"):
            mean = result_data.get("mean") or result_data.get("average")
            count = result_data.get("count", 0)
            insights.append(f"Average value across {count} data points: {mean:.2f}")
        
        if result_data.get("threshold_value"):
            threshold = result_data["threshold_value"]
            above_count = result_data.get("above_threshold_count", 0)
            above_percentage = result_data.get("above_threshold_percentage", 0)
            insights.append(f"{above_percentage:.1f}% of patients ({above_count}) exceed the threshold of {threshold}")
        
        if result_data.get("risk_category"):
            insights.append(f"Overall risk category: {result_data['risk_category']}")
        
        return insights
    
    def _generate_clinical_significance(
        self,
        result_data: Dict[str, Any],
        medical_context: Dict[str, Any]
    ) -> str:
        """Generate explanation of clinical significance."""
        domain = medical_context.get("medical_domain", "general")
        
        if domain == "diabetes" and result_data.get("threshold_value"):
            threshold = result_data["threshold_value"]
            above_percentage = result_data.get("above_threshold_percentage", 0)
            if above_percentage > 20:
                return f"High prevalence of elevated glucose levels ({above_percentage:.1f}%) indicates significant glycemic control challenges in this population. This may increase risk of diabetes-related complications."
            else:
                return f"Moderate prevalence of elevated glucose levels ({above_percentage:.1f}%) suggests need for targeted intervention and monitoring."
        
        return "Results indicate findings that require clinical review and appropriate intervention based on established guidelines."
    
    def _generate_next_steps(
        self,
        result_data: Dict[str, Any],
        medical_context: Dict[str, Any]
    ) -> List[str]:
        """Generate suggested next steps."""
        steps = []
        
        if result_data.get("patients_above_threshold"):
            steps.append("Review individual patient records for those above threshold")
            steps.append("Schedule follow-up appointments or consultations as needed")
        
        if result_data.get("threshold_value"):
            steps.append("Consider adjusting treatment protocols based on findings")
            steps.append("Implement monitoring and tracking for at-risk patients")
        
        steps.append("Share findings with relevant clinical teams")
        steps.append("Document results in patient records")
        
        return steps
    
    def _get_title(self, analysis_type: str, research_question: Optional[str]) -> str:
        """Generate title based on analysis type."""
        if research_question:
            return research_question
        
        type_titles = {
            "mean_difference": "Mean Difference Analysis",
            "regression": "Regression Analysis",
            "correlation": "Correlation Analysis",
            "survival": "Survival Analysis",
            "cohort_analysis": "Cohort Analysis",
            "basic_statistics": "Statistical Analysis"
        }
        return type_titles.get(analysis_type, "Computation Results")
    
    def _get_summary(self, result_data: Dict[str, Any], analysis_type: str) -> str:
        """Generate summary based on result data."""
        if result_data.get("patients_above_threshold"):
            count = len(result_data["patients_above_threshold"])
            return f"Found {count} patients matching the specified criteria."
        
        if result_data.get("mean") or result_data.get("average"):
            mean = result_data.get("mean") or result_data.get("average")
            count = result_data.get("count", 0)
            return f"Average value: {mean:.2f} across {count} data points."
        
        return "Computation completed successfully."
    
    def _get_formatting_prompt(self) -> str:
        """Get system prompt for LLM formatting."""
        return (
            "You are an expert medical data analyst and clinical decision support specialist. "
            "Your task is to format computation results into a clear, clinically meaningful display structure "
            "with domain-specific insights and actionable recommendations.\n\n"
            
            "Your responsibilities:\n"
            "1. Identify the medical domain (diabetes, oncology, cardiology, etc.) from the data\n"
            "2. Interpret results in clinical context\n"
            "3. Provide evidence-based recommendations specific to the medical condition\n"
            "4. Highlight clinically significant findings\n"
            "5. Suggest appropriate follow-up actions\n\n"
            
            "Display Guidelines:\n"
            "- For categorical queries (e.g., 'list patients with stage 2 cancer'), create a patient list table with staging information\n"
            "- For threshold queries (e.g., 'patients above 150 mg/dL'), show threshold analysis with risk stratification\n"
            "- For statistical queries, show summary statistics with clinical interpretation\n"
            "- For cohort analysis, show demographics, outcomes, and comparative insights\n"
            "- For survival analysis, suggest survival curves and prognostic factors\n"
            "- For correlation/regression, explain clinical relationships and implications\n\n"
            
            "Recommendation Guidelines:\n"
            "- HIGH priority: Urgent clinical actions (e.g., immediate treatment, referral)\n"
            "- MEDIUM priority: Important monitoring or intervention (e.g., follow-up testing, lifestyle changes)\n"
            "- LOW priority: Preventive or educational measures\n"
            "- Base recommendations on:\n"
            "  * Medical guidelines for the identified condition\n"
            "  * Severity and prevalence of findings\n"
            "  * Risk stratification results\n"
            "  * Evidence-based best practices\n\n"
            
            "Medical Domain Examples:\n"
            "- Diabetes: Focus on glycemic control, complications, medication adjustments\n"
            "- Cancer: Focus on staging, treatment response, prognosis\n"
            "- Cardiovascular: Focus on risk factors, prevention, monitoring\n"
            "- Infectious Disease: Focus on transmission, treatment, prevention\n"
            "- Mental Health: Focus on severity, treatment options, support\n\n"
            
            "Always:\n"
            "- Use medical terminology appropriately\n"
            "- Provide context for numerical values (normal ranges, clinical significance)\n"
            "- Explain why findings matter clinically\n"
            "- Suggest evidence-based next steps\n"
            "- Consider patient safety and quality of care\n\n"
            
            "Return valid JSON only, no markdown. Ensure all recommendations are specific to the identified medical domain."
        )
    
    def _extract_medical_context(
        self,
        spec: Optional[Dict[str, Any]],
        result_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract medical context from spec and result data to help LLM understand the domain."""
        context = {
            "medical_domain": "general",
            "variables": [],
            "metrics": [],
            "conditions": [],
            "analysis_type": None
        }
        
        # Extract from spec
        if spec:
            context["analysis_type"] = spec.get("analysis_type", "basic_statistics")
            context["research_question"] = spec.get("research_question", "")
            context["prompt_text"] = spec.get("prompt_text", "")
            
            # Extract variables and identify medical domain
            variables = spec.get("variables", [])
            for var in variables:
                var_info = {
                    "id": var.get("id"),
                    "name": var.get("name"),
                    "dtype": var.get("dtype"),
                    "unit": var.get("unit"),
                    "concept_tags": var.get("concept_tags", [])
                }
                context["variables"].append(var_info)
                
                # Identify medical domain from variable names and tags
                var_name_lower = (var.get("name", "") + " " + " ".join(var.get("concept_tags", []))).lower()
                
                if any(term in var_name_lower for term in ["blood_sugar", "glucose", "diabetes", "hba1c", "insulin"]):
                    context["medical_domain"] = "diabetes"
                    context["conditions"].append("diabetes")
                elif any(term in var_name_lower for term in ["cancer", "tumor", "oncology", "stage", "malignancy"]):
                    context["medical_domain"] = "oncology"
                    context["conditions"].append("cancer")
                elif any(term in var_name_lower for term in ["blood_pressure", "cardiac", "heart", "cardiovascular", "cholesterol"]):
                    context["medical_domain"] = "cardiology"
                    context["conditions"].append("cardiovascular_disease")
                elif any(term in var_name_lower for term in ["infection", "bacterial", "viral", "pathogen"]):
                    context["medical_domain"] = "infectious_disease"
                elif any(term in var_name_lower for term in ["mental", "depression", "anxiety", "psychiatric"]):
                    context["medical_domain"] = "mental_health"
                elif any(term in var_name_lower for term in ["respiratory", "lung", "asthma", "copd"]):
                    context["medical_domain"] = "pulmonology"
                
                if var.get("unit"):
                    context["metrics"].append(f"{var.get('name')} ({var.get('unit')})")
        
        # Extract from result data
        if result_data.get("result"):
            nested_result = result_data["result"]
            if isinstance(nested_result, dict):
                if nested_result.get("metric_name"):
                    context["metrics"].append(nested_result["metric_name"])
                if nested_result.get("threshold_value"):
                    context["threshold"] = nested_result["threshold_value"]
                if nested_result.get("risk_category"):
                    context["risk_level"] = nested_result["risk_category"]
        
        # Extract from operations in result
        if result_data.get("result") and isinstance(result_data["result"], dict):
            operations = result_data["result"].get("operations", {})
            for op_id, op_result in operations.items():
                if isinstance(op_result, dict):
                    if op_result.get("threshold_value"):
                        context["threshold"] = op_result["threshold_value"]
                    if op_result.get("patients_above_threshold"):
                        context["patients_count"] = len(op_result["patients_above_threshold"])
        
        return context

