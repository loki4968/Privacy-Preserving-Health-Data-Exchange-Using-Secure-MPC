"""
Column Mapping Service for automatic variable-to-column matching.

This service uses semantic similarity, unit matching, and data type compatibility
to automatically map computation spec variables to dataset columns.
"""

import logging
import re
from typing import Dict, List, Optional, Tuple, Any
from difflib import SequenceMatcher
import json

logger = logging.getLogger(__name__)


class ColumnMappingService:
    """Service for automatically mapping computation variables to dataset columns."""
    
    def __init__(self):
        # Common unit conversions and synonyms
        self.unit_synonyms = {
            'mg/dl': ['mg/dL', 'mg_dl', 'mg per dl', 'milligrams per deciliter'],
            'mmol/l': ['mmol/L', 'mmol_l', 'mmol per l', 'millimoles per liter'],
            'mmhg': ['mmHg', 'mm_hg', 'mm hg', 'millimeters of mercury'],
            'bpm': ['beats per minute', 'heart rate', 'pulse'],
            'kg/m2': ['kg/m^2', 'kg per m2', 'bmi'],
            'years': ['age', 'yr', 'yrs'],
            'celsius': ['°C', 'C', 'celsius', 'centigrade'],
            'fahrenheit': ['°F', 'F', 'fahrenheit'],
        }
        
        # Common health metric patterns
        self.metric_patterns = {
            'blood_glucose': [
                r'glucose', r'blood.?sugar', r'blood.?glucose', r'glucose.?level',
                r'fasting.?glucose', r'glucose.?mg', r'sugar.?level'
            ],
            'blood_pressure': [
                r'blood.?pressure', r'bp', r'systolic', r'diastolic', r'pressure'
            ],
            'heart_rate': [
                r'heart.?rate', r'pulse', r'hr', r'bpm', r'heartbeat'
            ],
            'temperature': [
                r'temperature', r'temp', r'body.?temp', r'fever'
            ],
            'bmi': [
                r'bmi', r'body.?mass.?index', r'body.?mass'
            ],
            'age': [
                r'age', r'years.?old', r'yr', r'yrs'
            ],
            'weight': [
                r'weight', r'wt', r'body.?weight', r'kg', r'pounds', r'lbs'
            ],
            'height': [
                r'height', r'ht', r'body.?height', r'cm', r'inches', r'in'
            ],
        }
    
    def find_best_matches(
        self,
        variable: Dict[str, Any],
        dataset_columns: List[Dict[str, Any]],
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Find the best matching columns for a given variable.
        
        Args:
            variable: ComputationSpecVariable dict with id, name, concept_tags, unit, dtype
            dataset_columns: List of column descriptors with name, data_type, unit, semantic_tags
            top_k: Number of top matches to return
            
        Returns:
            List of matches with scores, sorted by confidence (highest first)
        """
        variable_name = variable.get('name', '').lower()
        variable_id = variable.get('id', '').lower()
        variable_tags = variable.get('concept_tags', []) or []
        variable_unit = variable.get('unit', '').lower() if variable.get('unit') else None
        variable_dtype = variable.get('dtype', 'float')
        
        matches = []
        
        for col in dataset_columns:
            col_name = col.get('column_name', '').lower()
            col_tags = col.get('semantic_tags', []) or []
            col_unit = col.get('unit', '').lower() if col.get('unit') else None
            col_dtype = col.get('data_type', 'float')
            
            # Calculate similarity scores
            name_similarity = self._name_similarity(variable_name, variable_id, col_name)
            tag_similarity = self._tag_similarity(variable_tags, col_tags)
            unit_compatibility = self._unit_compatibility(variable_unit, col_unit)
            type_compatibility = self._type_compatibility(variable_dtype, col_dtype)
            pattern_match = self._pattern_match(variable_name, variable_id, variable_tags, col_name, col_tags)
            
            # Weighted composite score
            composite_score = (
                name_similarity * 0.35 +
                tag_similarity * 0.30 +
                pattern_match * 0.20 +
                unit_compatibility * 0.10 +
                type_compatibility * 0.05
            )
            
            matches.append({
                'column_name': col.get('column_name'),
                'column_index': col.get('column_index'),
                'confidence_score': composite_score,
                'name_similarity': name_similarity,
                'tag_similarity': tag_similarity,
                'unit_compatibility': unit_compatibility,
                'type_compatibility': type_compatibility,
                'pattern_match': pattern_match,
                'reasoning': self._generate_reasoning(
                    variable_name, col_name, composite_score,
                    name_similarity, tag_similarity, unit_compatibility
                )
            })
        
        # Sort by confidence and return top_k
        matches.sort(key=lambda x: x['confidence_score'], reverse=True)
        return matches[:top_k]
    
    def _name_similarity(self, var_name: str, var_id: str, col_name: str) -> float:
        """Calculate string similarity between variable name/id and column name."""
        # Try both variable name and id
        sim1 = SequenceMatcher(None, var_name, col_name).ratio()
        sim2 = SequenceMatcher(None, var_id, col_name).ratio()
        
        # Check for substring matches (boost score)
        if var_name in col_name or col_name in var_name:
            sim1 = max(sim1, 0.8)
        if var_id in col_name or col_name in var_id:
            sim2 = max(sim2, 0.8)
        
        return max(sim1, sim2)
    
    def _tag_similarity(self, var_tags: List[str], col_tags: List[str]) -> float:
        """Calculate similarity based on semantic tags."""
        if not var_tags or not col_tags:
            return 0.0
        
        var_tags_lower = [t.lower() for t in var_tags]
        col_tags_lower = [t.lower() for t in col_tags]
        
        # Count matches
        matches = sum(1 for tag in var_tags_lower if tag in col_tags_lower)
        if matches == 0:
            return 0.0
        
        # Jaccard similarity
        union = len(set(var_tags_lower + col_tags_lower))
        return matches / union if union > 0 else 0.0
    
    def _unit_compatibility(self, var_unit: Optional[str], col_unit: Optional[str]) -> float:
        """Check if units are compatible (exact match or known conversions)."""
        if not var_unit and not col_unit:
            return 0.5  # Both missing, neutral
        if not var_unit or not col_unit:
            return 0.2  # One missing, low compatibility
        
        var_unit_lower = var_unit.lower().strip()
        col_unit_lower = col_unit.lower().strip()
        
        # Exact match
        if var_unit_lower == col_unit_lower:
            return 1.0
        
        # Check synonyms
        for canonical, synonyms in self.unit_synonyms.items():
            if var_unit_lower in synonyms and col_unit_lower in synonyms:
                return 0.9  # Same unit family
        
        # Check if one contains the other
        if var_unit_lower in col_unit_lower or col_unit_lower in var_unit_lower:
            return 0.6
        
        # Known incompatible units (e.g., mg/dL vs mmHg)
        incompatible_pairs = [
            ('mg/dl', 'mmhg'), ('mg/dl', 'bpm'), ('mmhg', 'bpm'),
            ('celsius', 'fahrenheit')  # Would need conversion
        ]
        for u1, u2 in incompatible_pairs:
            if (var_unit_lower in u1 and col_unit_lower in u2) or \
               (var_unit_lower in u2 and col_unit_lower in u1):
                return 0.0
        
        return 0.3  # Unknown units, low compatibility
    
    def _type_compatibility(self, var_dtype: str, col_dtype: str) -> float:
        """Check if data types are compatible."""
        type_map = {
            'float': ['float', 'numeric', 'decimal', 'real'],
            'int': ['int', 'integer', 'numeric'],
            'string': ['string', 'text', 'varchar', 'char'],
        }
        
        var_types = type_map.get(var_dtype.lower(), [var_dtype.lower()])
        col_types = type_map.get(col_dtype.lower(), [col_dtype.lower()])
        
        if any(vt in col_types for vt in var_types):
            return 1.0
        if var_dtype.lower() == 'float' and col_dtype.lower() == 'int':
            return 0.8  # Int can be used as float
        return 0.0
    
    def _pattern_match(
        self,
        var_name: str,
        var_id: str,
        var_tags: List[str],
        col_name: str,
        col_tags: List[str]
    ) -> float:
        """Use regex patterns to match health metrics."""
        all_var_text = ' '.join([var_name, var_id] + var_tags).lower()
        all_col_text = ' '.join([col_name] + col_tags).lower()
        
        best_match = 0.0
        for metric_type, patterns in self.metric_patterns.items():
            var_matches = sum(1 for p in patterns if re.search(p, all_var_text, re.IGNORECASE))
            col_matches = sum(1 for p in patterns if re.search(p, all_col_text, re.IGNORECASE))
            
            if var_matches > 0 and col_matches > 0:
                # Both match the same metric type
                best_match = max(best_match, 0.9)
            elif var_matches > 0 or col_matches > 0:
                # One matches
                best_match = max(best_match, 0.4)
        
        return best_match
    
    def _generate_reasoning(
        self,
        var_name: str,
        col_name: str,
        score: float,
        name_sim: float,
        tag_sim: float,
        unit_comp: float
    ) -> str:
        """Generate human-readable reasoning for the match."""
        reasons = []
        
        if name_sim > 0.7:
            reasons.append(f"Strong name similarity ({name_sim:.2f})")
        elif name_sim > 0.4:
            reasons.append(f"Moderate name similarity ({name_sim:.2f})")
        
        if tag_sim > 0.5:
            reasons.append(f"Semantic tag overlap ({tag_sim:.2f})")
        
        if unit_comp > 0.8:
            reasons.append("Unit match")
        elif unit_comp > 0.5:
            reasons.append("Compatible units")
        elif unit_comp < 0.3:
            reasons.append("Unit mismatch")
        
        if not reasons:
            reasons.append("Low confidence match")
        
        return "; ".join(reasons) if reasons else "No strong indicators"
    
    def auto_map_variables_to_dataset(
        self,
        variables: List[Dict[str, Any]],
        dataset_columns: List[Dict[str, Any]],
        min_confidence: float = 0.3
    ) -> Dict[str, Dict[str, Any]]:
        """
        Automatically map all variables to dataset columns.
        
        Returns:
            Dict mapping variable_id -> best match info
        """
        mappings = {}
        
        for var in variables:
            var_id = var.get('id') or var.get('name', 'unknown')
            matches = self.find_best_matches(var, dataset_columns, top_k=1)
            
            if matches and matches[0]['confidence_score'] >= min_confidence:
                mappings[var_id] = {
                    'variable': var,
                    'best_match': matches[0],
                    'all_matches': matches
                }
            else:
                # No good match found
                mappings[var_id] = {
                    'variable': var,
                    'best_match': None,
                    'all_matches': matches if matches else []
                }
        
        return mappings

