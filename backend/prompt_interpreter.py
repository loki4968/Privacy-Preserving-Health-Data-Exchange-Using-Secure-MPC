import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class PromptInterpreter:
    """Service to convert natural-language prompts into structured computation specs.

    Supports multiple LLM providers:
    - Groq (FREE tier, fast inference, recommended - requires API key)
    - OpenAI (paid, requires API key)
    - Hugging Face (FREE tier, requires API key)
    - Ollama (FREE, local, no API key needed)
    - Enhanced heuristics (FREE, no dependencies - fallback)
    
    Falls back through providers in order until one succeeds.
    """

    def __init__(self) -> None:
        # Provider selection (default: groq - FREE tier)
        self.llm_provider: str = os.getenv("LLM_PROVIDER", "groq").lower()
        
        # Groq configuration (FREE tier: 14,400 requests/day - RECOMMENDED)
        self.groq_api_key: Optional[str] = os.getenv("GROQ_API_KEY")
        self.groq_model: str = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
        
        # OpenAI configuration (paid)
        self.openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
        self.openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        
        # Hugging Face configuration (FREE tier: 1,000 requests/month)
        self.hf_api_key: Optional[str] = os.getenv("HUGGINGFACE_API_KEY")
        self.hf_model: str = os.getenv("HF_MODEL", "mistralai/Mistral-7B-Instruct-v0.2")
        
        # Ollama configuration (FREE, local)
        self.ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3.2")
        
        self.timeout_seconds: int = int(os.getenv("LLM_TIMEOUT_SECONDS", "15"))

    # --------------------------------------------------------------------- #
    # Public API
    # --------------------------------------------------------------------- #
    def interpret_prompt(self, prompt_text: str) -> Dict[str, Any]:
        """Convert a free-text research prompt into a computation spec dict.

        The returned dict is compatible with the ComputationSpec Pydantic model
        defined in `backend/routers/secure_computations.py`.
        """
        prompt_text = (prompt_text or "").strip()
        if not prompt_text:
            return {
                "prompt_text": None,
                "analysis_type": None,
                "variables": [],
                "operations": [],
            }

        # Try LLM-based interpretation based on provider preference
        # Groq is checked first as it's the recommended FREE option
        if self.llm_provider == "groq" and self.groq_api_key:
            try:
                spec = self._interpret_with_groq(prompt_text)
                if spec:
                    return spec
            except Exception as e:
                logger.warning(f"Groq interpretation failed: {e}, trying fallback")
        
        if self.llm_provider == "openai" and self.openai_api_key:
            try:
                spec = self._interpret_with_openai(prompt_text)
                if spec:
                    return spec
            except Exception as e:
                logger.warning(f"OpenAI interpretation failed: {e}, trying fallback")
        
        if self.llm_provider == "huggingface" and self.hf_api_key:
            try:
                spec = self._interpret_with_huggingface(prompt_text)
                if spec:
                    return spec
            except Exception as e:
                logger.warning(f"Hugging Face interpretation failed: {e}, trying fallback")
        
        if self.llm_provider == "ollama":
            try:
                spec = self._interpret_with_ollama(prompt_text)
                if spec:
                    return spec
            except Exception as e:
                logger.warning(f"Ollama interpretation failed: {e}, trying fallback")
        
        # Auto-try free providers if primary provider not configured
        # Try Groq (free tier) if not already tried
        if self.llm_provider != "groq" and self.groq_api_key:
            try:
                spec = self._interpret_with_groq(prompt_text)
                if spec:
                    return spec
            except httpx.HTTPStatusError as e:
                if e.response and e.response.status_code == 429:
                    logger.debug(f"Groq rate limit exceeded. Skipping Groq fallback.")
                else:
                    logger.debug(f"Groq auto-try failed: {e}")
            except Exception as e:
                logger.debug(f"Groq auto-try failed: {e}")
        
        # Try Ollama (local, free) if not already tried
        if self.llm_provider != "ollama":
            try:
                spec = self._interpret_with_ollama(prompt_text)
                if spec:
                    return spec
            except Exception as e:
                logger.debug(f"Ollama auto-try failed: {e}")

        # Fallback to enhanced heuristic interpretation (always works, no cost)
        return self._interpret_with_heuristics(prompt_text)

    # --------------------------------------------------------------------- #
    # LLM-backed implementation
    # --------------------------------------------------------------------- #
    def _interpret_with_openai(self, prompt_text: str) -> Dict[str, Any]:
        """Call OpenAI's chat completions API to get a structured spec."""
        if not self.openai_api_key:
            raise ValueError("OpenAI API key not configured")
        
        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json",
        }

        system_prompt = self._get_system_prompt()

        body = {
            "model": self.openai_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt_text},
            ],
            "response_format": {"type": "json_object"},
        }

        with httpx.Client(timeout=self.timeout_seconds) as client:
            resp = client.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=body,
            )
            resp.raise_for_status()
            data = resp.json()

        return self._parse_llm_response(data, prompt_text)

    # --------------------------------------------------------------------- #
    # Heuristic (no-LLM) implementation
    # --------------------------------------------------------------------- #
    def _interpret_with_heuristics(self, prompt_text: str) -> Dict[str, Any]:
        """Enhanced rules-based interpretation (FREE, no API needed)."""
        text = prompt_text.lower()
        
        # Extract research question (first sentence or key phrase)
        research_question = None
        sentences = prompt_text.split('.')
        if sentences:
            research_question = sentences[0].strip()
            if len(research_question) > 200:
                research_question = research_question[:200] + "..."
        
        variables: List[Dict[str, Any]] = []
        population_criteria: Dict[str, Any] = {}
        analysis_type: Optional[str] = None
        operations: List[Dict[str, Any]] = []
        
        # Enhanced variable detection with more patterns
        variable_patterns = {
            "blood_glucose": {
                "keywords": ["glucose", "blood sugar", "blood sugar level", "fasting glucose", "glucose level"],
                "role": "outcome",
                "dtype": "float",
                "unit": "mg/dL",
                "tags": ["blood_glucose", "glucose", "mg/dL", "fasting"]
            },
            "diabetes_status": {
                "keywords": ["diabetic", "diabetes", "diabetes status", "type 2 diabetes", "type 1 diabetes"],
                "role": "exposure",
                "dtype": "string",
                "unit": None,
                "tags": ["diabetes", "diagnosis", "condition"]
            },
            "bmi": {
                "keywords": ["bmi", "body mass index", "body mass"],
                "role": "covariate",
                "dtype": "float",
                "unit": "kg/m^2",
                "tags": ["bmi", "body_mass_index"]
            },
            "age": {
                "keywords": ["age", "years old", "aged"],
                "role": "covariate",
                "dtype": "int",
                "unit": "years",
                "tags": ["age", "years"]
            },
            "cholesterol": {
                "keywords": ["cholesterol", "ldl", "hdl", "triglycerides"],
                "role": "outcome",
                "dtype": "float",
                "unit": "mg/dL",
                "tags": ["cholesterol", "lipid"]
            },
            "blood_pressure": {
                "keywords": ["blood pressure", "systolic", "diastolic", "bp"],
                "role": "outcome",
                "dtype": "float",
                "unit": "mmHg",
                "tags": ["blood_pressure", "bp", "systolic", "diastolic"]
            },
            "heart_rate": {
                "keywords": ["heart rate", "pulse", "hr", "bpm"],
                "role": "outcome",
                "dtype": "int",
                "unit": "bpm",
                "tags": ["heart_rate", "pulse", "hr"]
            },
        }
        
        for var_id, pattern in variable_patterns.items():
            if any(kw in text for kw in pattern["keywords"]):
                variables.append({
                    "id": var_id,
                    "name": pattern["keywords"][0].title(),
                    "role": pattern["role"],
                    "dtype": pattern["dtype"],
                    "unit": pattern["unit"],
                    "concept_tags": pattern["tags"]
                })
        
        # Extract population criteria
        import re
        age_match = re.search(r'age[:\s]+(\d+)[-\s]+(\d+)', text)
        if age_match:
            population_criteria["age_min"] = int(age_match.group(1))
            population_criteria["age_max"] = int(age_match.group(2))
        elif "age" in text:
            age_single = re.search(r'age[:\s]+(\d+)', text)
            if age_single:
                population_criteria["age_min"] = int(age_single.group(1))
        
        if "last" in text and ("month" in text or "6 months" in text):
            population_criteria["time_window"] = "last_6_months"
        elif "last" in text and "year" in text:
            population_criteria["time_window"] = "last_year"
        
        # Fallback: generic numeric variable if we didn't detect anything
        if not variables:
            variables.append({
                "id": "value",
                "name": "Value",
                "role": None,
                "dtype": "float",
                "unit": None,
                "concept_tags": None,
            })
        
        # Enhanced analysis type detection with priority order (most specific first)
        # Check for specific domain keywords FIRST to avoid false matches
        
        # Epidemiological/Public Health (check before cohort - more specific)
        # Check for simple keywords that common users would use
        if any(term in text for term in ["outbreak", "epidemic", "epidemiological", "disease spread", "disease pattern", 
                                         "disease trend", "across regions", "across areas", "public health", 
                                         "disease spreading", "how is disease", "disease in different", "disease by region"]):
            analysis_type = "epidemiological"
            op_type = "epidemiological"
        # Drug Safety/Pharmacovigilance (specific domain)
        elif any(term in text for term in ["drug safety", "adverse reaction", "adverse event", "side effect", "pharmacovigilance", "drug reaction"]):
            analysis_type = "drug_safety"
            op_type = "drug_safety"
        # Genomics (specific domain)
        elif any(term in text for term in ["gwas", "genome-wide", "genetic association", "genetic variant", "snp"]):
            analysis_type = "secure_gwas"
            op_type = "secure_gwas"
        # Pharmacogenomics (specific domain)
        elif any(term in text for term in ["pharmacogenomic", "drug-gene", "gene variant", "genetic drug"]):
            analysis_type = "pharmacogenomics"
            op_type = "pharmacogenomics"
        # Machine Learning (check before basic stats - more specific)
        elif any(term in text for term in ["machine learning", "ml model", "train model", "train a model", "build model", "federated learning", "ai model"]):
            if "random forest" in text or "ensemble" in text:
                analysis_type = "federated_random_forest"
                op_type = "federated_random_forest"
            elif "logistic" in text or "classification" in text:
                analysis_type = "federated_logistic"
                op_type = "federated_logistic"
            else:
                analysis_type = "federated_logistic"  # Default ML type
                op_type = "federated_logistic"
        # Anomaly Detection (specific ML type - check BEFORE categorical filter)
        # Check for anomaly keywords first, even if "find" or "patients" is present
        elif any(term in text for term in ["anomaly", "outlier", "abnormal", "unusual", "detect abnormal", 
                                         "find abnormal", "find outliers", "abnormal patients", "abnormal vital", 
                                         "abnormal health", "detect unusual", "find unusual", "find abnormal patients"]):
            analysis_type = "anomaly_detection"
            op_type = "anomaly_detection"
        # Advanced Statistics
        elif "regression" in text or ("predict" in text and ("model" in text or "using" in text)):
            analysis_type = "regression"
            op_type = "secure_regression"
        elif any(term in text for term in ["survival", "time-to-event", "time to", "kaplan", "survival rate"]):
            analysis_type = "survival"
            op_type = "secure_survival"
        elif any(term in text for term in ["correlation", "correlate", "relationship between", "how are", "related to"]):
            analysis_type = "correlation"
            op_type = "secure_correlation"
        # Cohort Analysis (check after epidemiological - less specific)
        elif any(term in text for term in ["cohort", "compare groups", "group comparison", "compare patients"]):
            analysis_type = "cohort_analysis"
            op_type = "cohort_analysis"
        # Genomics
        elif "gwas" in text or "genome-wide" in text or "genetic association" in text:
            analysis_type = "secure_gwas"
            op_type = "secure_gwas"
        elif "pharmacogenomic" in text or "drug-gene" in text or "gene variant" in text:
            analysis_type = "pharmacogenomics"
            op_type = "pharmacogenomics"
        # Basic Statistics (simple keywords)
        elif "variance" in text or "variability" in text or "spread" in text:
            analysis_type = "variance"
            op_type = "secure_variance"
        elif "sum" in text or ("total" in text and "number" in text):
            analysis_type = "sum"
            op_type = "secure_sum"
        elif any(term in text for term in ["average", "mean", "calculate average", "what is the average"]):
            analysis_type = "average"
            op_type = "secure_average"
        elif "compare" in text or "difference" in text:
            analysis_type = "mean_difference"
            op_type = "secure_mean"
        # Categorical Filter (check last - least specific, but common)
        # BUT: Skip if anomaly keywords are present (already handled above)
        elif any(term in text for term in ["list", "find", "show", "identify"]) and any(term in text for term in ["patients", "people", "cases"]):
            # Only use categorical_filter if it's clearly a filtering query AND not an anomaly detection query
            if not any(term in text for term in ["abnormal", "anomaly", "outlier", "unusual"]):
                if any(term in text for term in ["with", "having", "who are", "where", "greater than", "less than", "equal to", "higher than", "lower than", "stage", "type", "above", "below"]):
                    analysis_type = "categorical_filter"
                    op_type = "categorical_filter"
                else:
                    analysis_type = "basic_statistics"
                    op_type = "secure_average"
            else:
                # Anomaly keywords present - should have been caught above, but fallback
                analysis_type = "anomaly_detection"
                op_type = "anomaly_detection"
        else:
            analysis_type = "basic_statistics"
            op_type = "secure_average"
        
        # Generic filter extraction - extract ANY filters mentioned in the prompt
        categorical_filters = {}
        import re
        
        # Extract date filters
        date_patterns = [
            (r'treated\s+on\s+(\d{4}-\d{2}-\d{2})', 'treatment_date', '='),
            (r'on\s+(\d{4}-\d{2}-\d{2})', 'date', '='),
            (r'before\s+(\d{4}-\d{2}-\d{2})', 'date', '<'),
            (r'after\s+(\d{4}-\d{2}-\d{2})', 'date', '>'),
            (r'on\s+or\s+before\s+(\d{4}-\d{2}-\d{2})', 'date', '<='),
            (r'on\s+or\s+after\s+(\d{4}-\d{2}-\d{2})', 'date', '>='),
        ]
        for pattern, col_name, op in date_patterns:
            match = re.search(pattern, text.lower())
            if match:
                date_val = match.group(1)
                if op == '=':
                    categorical_filters[col_name] = date_val
                else:
                    categorical_filters[col_name] = {"operator": op, "value": date_val}
                break
        
        # Extract age filters
        age_under = re.search(r'under\s+age\s+(\d+)', text.lower())
        if age_under:
            categorical_filters["age"] = {"operator": "<", "value": int(age_under.group(1))}
        age_over = re.search(r'over\s+age\s+(\d+)', text.lower())
        if age_over:
            categorical_filters["age"] = {"operator": ">", "value": int(age_over.group(1))}
        age_range = re.search(r'age\s+(\d+)[-\s]+(\d+)', text.lower())
        if age_range:
            categorical_filters["age"] = {"min": int(age_range.group(1)), "max": int(age_range.group(2))}
        
        # Extract condition/diagnosis filters (generic)
        condition_patterns = [
            (r'heart\s+attack', 'condition', 'heart attack'),
            (r'corona', 'admission_reason', 'corona'),
            (r'covid', 'admission_reason', 'covid'),
            (r'suffered\s+due\s+to\s+([^,\s]+)', 'condition', None),  # Will extract from group
            (r'admitted\s+due\s+to\s+([^,\s]+)', 'admission_reason', None),
            (r'diagnosed\s+with\s+([^,\s]+)', 'diagnosis', None),
        ]
        for pattern, col_name, fixed_value in condition_patterns:
            match = re.search(pattern, text.lower())
            if match:
                value = fixed_value if fixed_value else match.group(1) if len(match.groups()) > 0 else fixed_value
                if value:
                    categorical_filters[col_name] = value
                    break
        
        # Extract cancer stage (if mentioned)
        if "stage" in text.lower():
            stage_match = re.search(r'(?:stage|staging)\s*(\d+|i{1,4}|first|second|third|fourth)', text.lower())
            if stage_match:
                stage_val = stage_match.group(1)
                stage_map = {
                    "1": "I", "first": "I",
                    "2": "II", "second": "II", "ii": "II",
                    "3": "III", "third": "III", "iii": "III",
                    "4": "IV", "fourth": "IV", "iv": "IV"
                }
                categorical_filters["cancer_stage"] = stage_map.get(stage_val.lower(), stage_val.upper())
        
        # Extract cancer type (if mentioned)
        cancer_types = ["breast", "lung", "colon", "prostate", "leukemia", "ovarian", "pancreatic", "liver", "kidney", "thyroid"]
        for cancer_type in cancer_types:
            if cancer_type in text.lower():
                categorical_filters["cancer_type"] = cancer_type.capitalize()
                break
        
        # Generic condition detection
        if "cancer" in text.lower():
            categorical_filters["condition_type"] = "cancer"
        if "diabetes" in text.lower() or "diabetic" in text.lower():
            categorical_filters["condition"] = "diabetes"
        
        # Create operation
        primary_var_id = variables[0]["id"] if variables else "value"
        operation = {
            "id": "main_operation",
            "type": op_type,
            "input": primary_var_id,
            "x": None,
            "y": None,
            "options": None,
        }
        
        # Add grouping if comparison detected
        if analysis_type == "mean_difference" and len(variables) > 1:
            # Find exposure variable (diabetes_status, etc.)
            exposure_var = next((v for v in variables if v.get("role") == "exposure"), None)
            if exposure_var:
                operation["options"] = {"group_by": exposure_var["id"]}
        
        # Add categorical filters to operation options
        if categorical_filters:
            if not operation.get("options"):
                operation["options"] = {}
            operation["options"]["filters"] = categorical_filters
        
        # Add categorical filters to population criteria as well
        if categorical_filters and population_criteria:
            population_criteria.update(categorical_filters)
        elif categorical_filters:
            population_criteria = categorical_filters
        
        operations.append(operation)
        
        return {
            "prompt_text": prompt_text,
            "research_question": research_question,
            "analysis_type": analysis_type,
            "population_criteria": population_criteria if population_criteria else None,
            "variables": variables,
            "operations": operations,
        }
    
    # --------------------------------------------------------------------- #
    # Groq API (FREE tier: 14,400 requests/day)
    # --------------------------------------------------------------------- #
    def _interpret_with_groq(self, prompt_text: str) -> Dict[str, Any]:
        """Call Groq API (FREE tier) for prompt interpretation with retry logic and rate limiting."""
        if not self.groq_api_key:
            raise ValueError("Groq API key not configured")
        
        headers = {
            "Authorization": f"Bearer {self.groq_api_key}",
            "Content-Type": "application/json",
        }
        
        system_prompt = self._get_system_prompt()
        
        body = {
            "model": self.groq_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt_text},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,  # Lower temperature for more consistent JSON
        }
        
        # Retry logic with exponential backoff for rate limiting
        max_retries = 3
        base_delay = 2  # Start with 2 seconds
        
        for attempt in range(max_retries):
            try:
                with httpx.Client(timeout=self.timeout_seconds) as client:
                    resp = client.post(
                        "https://api.groq.com/openai/v1/chat/completions",
                        headers=headers,
                        json=body,
                    )
                    
                    # Handle rate limiting (429)
                    if resp.status_code == 429:
                        if attempt < max_retries - 1:
                            # Calculate exponential backoff: 2s, 4s, 8s
                            delay = base_delay * (2 ** attempt)
                            logger.warning(f"Groq rate limit hit (429). Retrying in {delay} seconds (attempt {attempt + 1}/{max_retries})...")
                            time.sleep(delay)
                            continue
                        else:
                            # Last attempt failed - raise error to trigger fallback
                            logger.error("Groq rate limit exceeded after all retries. Falling back to heuristics.")
                            raise httpx.HTTPStatusError(
                                "Rate limit exceeded",
                                request=resp.request,
                                response=resp
                            )
                    
                    # Handle other errors
                    resp.raise_for_status()
                    data = resp.json()
                    return self._parse_llm_response(data, prompt_text)
                    
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429 and attempt < max_retries - 1:
                    # Already handled above, but catch here too
                    continue
                # For other HTTP errors, raise immediately
                raise
            except Exception as e:
                # For other errors (network, timeout, etc.), raise immediately
                logger.warning(f"Groq API error: {e}")
                raise
        
        # If we get here, all retries failed
        raise httpx.HTTPStatusError(
            "Rate limit exceeded after retries",
            request=None,
            response=None
        )
    
    # --------------------------------------------------------------------- #
    # Hugging Face Inference API (FREE tier: 1,000 requests/month)
    # --------------------------------------------------------------------- #
    def _interpret_with_huggingface(self, prompt_text: str) -> Dict[str, Any]:
        """Call Hugging Face Inference API (FREE tier) for prompt interpretation."""
        if not self.hf_api_key:
            raise ValueError("Hugging Face API key not configured")
        
        headers = {
            "Authorization": f"Bearer {self.hf_api_key}",
            "Content-Type": "application/json",
        }
        
        system_prompt = self._get_system_prompt()
        full_prompt = f"{system_prompt}\n\nUser: {prompt_text}\n\nAssistant:"
        
        body = {
            "inputs": full_prompt,
            "parameters": {
                "temperature": 0.1,
                "max_new_tokens": 1000,
                "return_full_text": False,
            },
        }
        
        with httpx.Client(timeout=self.timeout_seconds * 2) as client:  # HF can be slower
            resp = client.post(
                f"https://api-inference.huggingface.co/models/{self.hf_model}",
                headers=headers,
                json=body,
            )
            resp.raise_for_status()
            data = resp.json()
        
        # HF returns different format - extract text from response
        if isinstance(data, list) and len(data) > 0:
            content = data[0].get("generated_text", "")
        elif isinstance(data, dict):
            content = data.get("generated_text", "")
        else:
            content = str(data)
        
        # Try to extract JSON from response
        try:
            # Look for JSON object in the response
            import re
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', content, re.DOTALL)
            if json_match:
                spec = json.loads(json_match.group())
                return self._normalize_spec(spec, prompt_text)
        except Exception as e:
            logger.warning(f"Failed to parse HF response as JSON: {e}")
        
        raise RuntimeError("Failed to extract valid JSON from Hugging Face response")
    
    # --------------------------------------------------------------------- #
    # Ollama (FREE, local, no API key needed)
    # --------------------------------------------------------------------- #
    def _interpret_with_ollama(self, prompt_text: str) -> Dict[str, Any]:
        """Call local Ollama API (FREE, no API key needed)."""
        system_prompt = self._get_system_prompt()
        
        body = {
            "model": self.ollama_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt_text},
            ],
            "format": "json",
            "options": {
                "temperature": 0.1,
            },
        }
        
        try:
            with httpx.Client(timeout=self.timeout_seconds * 2) as client:  # Local can be slower
                resp = client.post(
                    f"{self.ollama_base_url}/api/chat",
                    json=body,
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.ConnectError:
            raise RuntimeError(
                f"Ollama not running at {self.ollama_base_url}. "
                "Install from https://ollama.ai and run: ollama pull llama3.2"
            )
        
        message = data.get("message", {})
        content = message.get("content", "")
        
        try:
            spec = json.loads(content)
            return self._normalize_spec(spec, prompt_text)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Failed to decode JSON from Ollama: {exc}")
    
    # --------------------------------------------------------------------- #
    # Helper methods
    # --------------------------------------------------------------------- #
    def _get_system_prompt(self) -> str:
        """Get the system prompt for LLM interpretation."""
        return (
            "You are a medical research computation planner for a privacy-preserving "
            "multi-party analytics system. Given a natural language description of a "
            "study or survey, you must respond with STRICT JSON containing a generic "
            "computation specification.\n\n"
            "JSON schema (no extra fields):\n"
            "{\n"
            '  "prompt_text": string,              // original prompt\n'
            '  "research_question": string|null,  // formal research question extracted from prompt\n'
            '  "analysis_type": string|null,       // e.g. "mean_difference", "regression", "survival", "correlation", "basic_statistics", "cohort_analysis"\n'
            '  "population_criteria": object|null, // e.g. {"age_min": 18, "age_max": 65, "diagnosis": "diabetes", "time_window": "last_6_months"}\n'
            '  "variables": [\n'
            "    {\n"
            '      "id": string|null,              // machine id like "fasting_glucose"; use snake_case\n'
            '      "name": string,                 // human name like "Fasting blood glucose"\n'
            '      "role": string|null,            // one of "exposure", "outcome", "covariate", "stratifier", or null\n'
            '      "dtype": string,                // "float", "int", or "string"\n'
            '      "unit": string|null,            // e.g. "mg/dL", "kg/m^2", "years"\n'
            '      "concept_tags": [string] | null // semantic tags like ["blood_glucose", "fasting", "mg/dL"] for automatic column mapping\n'
            "    }\n"
            "  ],\n"
            '  "operations": [\n'
            "    {\n"
            '      "id": string,                   // operation id like "main_operation"\n'
            '      "type": string,                 // e.g. "secure_mean", "secure_correlation", "cohort_analysis", "secure_regression", "secure_survival", "categorical_filter"\n'
            '      "input": string|null,           // variable id for single-input ops\n'
            '      "x": string|null,               // x variable id for pairwise ops\n'
            '      "y": string|null,               // y variable id for pairwise ops\n'
            '      "options": object|null          // additional options:\n'
            '        // For categorical_filter or cohort_analysis:\n'
            '        //   "filters": {\n'
            '        //     "age": {"operator": "<", "value": 32}  // or {"min": 18, "max": 65}\n'
            '        //     "treatment_date": "2023-01-01"  // or {"operator": "<=", "value": "2023-12-31"}\n'
            '        //     "condition": "heart attack"  // or "diagnosis": "corona"\n'
            '        //     "admission_reason": "corona"\n'
            '        //     "cancer_type": "Breast"\n'
            '        //     "cancer_stage": "II"\n'
            '        //     // ANY column name from the data can be used as a filter\n'
            '        //   }\n'
            "    }\n"
            "  ],\n"
            '  "output_preferences": object|null    // e.g. {"include_plots": true, "confidence_intervals": true}\n'
            "}\n\n"
            "Rules:\n"
            "- ALWAYS respond with valid JSON only, no markdown.\n"
            "- Extract ALL variables mentioned in the prompt (exposures, outcomes, covariates).\n"
            "- Include rich concept_tags for each variable to enable automatic column mapping (e.g., for 'blood glucose' include ['blood_glucose', 'glucose', 'mg/dL', 'fasting']).\n"
            "- Extract ALL filter criteria from the prompt and add them to operation.options.filters:\n"
            "  * Date filters: 'treated on 2023-01-01' → {\"treatment_date\": \"2023-01-01\"} or {\"treatment_date\": {\"operator\": \"on\", \"value\": \"2023-01-01\"}}\n"
            "  * Date range: 'on or before 2023-12-31' → {\"treatment_date\": {\"operator\": \"<=\", \"value\": \"2023-12-31\"}}\n"
            "  * Age filters: 'under age 32' → {\"age\": {\"operator\": \"<\", \"value\": 32}} or 'age 18-65' → {\"age\": {\"min\": 18, \"max\": 65}}\n"
            "  * Condition filters: 'heart attack' → {\"condition\": \"heart attack\"} or {\"diagnosis\": \"heart attack\"}\n"
            "  * Admission filters: 'admitted due to corona' → {\"admission_reason\": \"corona\"} or {\"admission_diagnosis\": \"corona\"}\n"
            "  * Stage filters: 'stage 2 cancer' → {\"cancer_stage\": \"II\"}\n"
            "  * Any categorical filter: Extract the column name and value from context\n"
            "- For 'list' or 'find' queries with specific criteria (e.g., 'find patients with diabetes'), set analysis_type='categorical_filter' and include filters in operation.options.filters.\n"
            "- For 'find abnormal', 'detect anomalies', 'find outliers', or 'abnormal patients' queries, set analysis_type='anomaly_detection' and operation.type='anomaly_detection'.\n"
            "- Infer population_criteria from phrases like 'diabetic patients', 'age 18-65', 'last 6 months'.\n"
            "- Set analysis_type based on the research question:\n"
            "  * anomaly_detection for 'abnormal', 'anomaly', 'outlier', 'unusual' queries\n"
            "  * mean_difference for comparisons\n"
            "  * regression for associations/predictions\n"
            "  * survival for time-to-event\n"
            "  * categorical_filter for listing/finding with specific criteria\n"
            "- Include at least one operation that matches the analysis_type.\n"
            "- For comparison studies, set role='exposure' for the grouping variable and role='outcome' for the measured variable.\n"
            "- Be flexible: Extract filters for ANY condition, date, age, or criteria mentioned in the prompt.\n"
        )
    
    def _parse_llm_response(self, data: Dict[str, Any], prompt_text: str) -> Dict[str, Any]:
        """Parse LLM response and normalize spec."""
        choices = data.get("choices") or []
        if not choices:
            raise RuntimeError("No choices returned from LLM")
        
        message = choices[0].get("message") or {}
        content = message.get("content") or ""
        
        try:
            spec = json.loads(content)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Failed to decode JSON from LLM: {exc}") from exc
        
        return self._normalize_spec(spec, prompt_text)
    
    def _normalize_spec(self, spec: Dict[str, Any], prompt_text: str) -> Dict[str, Any]:
        """Normalize spec to ensure all required fields exist."""
        spec.setdefault("prompt_text", prompt_text)
        spec.setdefault("research_question", None)
        spec.setdefault("analysis_type", None)
        spec.setdefault("population_criteria", None)
        spec.setdefault("variables", [])
        spec.setdefault("operations", [])
        spec.setdefault("output_preferences", None)
        return spec


