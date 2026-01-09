"""
Intelligent Column Matcher - Generic, robust column name matching system with learning capabilities.

This service provides intelligent matching between filter keys (from prompts) 
and actual CSV column names, handling abbreviations, variations, and synonyms automatically.
It learns from successful matches and improves over time using a knowledge base.
"""

import logging
import re
from typing import Dict, List, Optional, Tuple, Any
from difflib import SequenceMatcher
import unicodedata
from sqlalchemy.orm import Session
from collections import defaultdict

logger = logging.getLogger(__name__)


class IntelligentColumnMatcher:
    """
    Generic column matcher that can match any filter key to any column name
    using multiple intelligent strategies. Learns from successful matches and improves over time.
    """
    
    def __init__(self, db_session: Optional[Session] = None):
        """
        Initialize the matcher with optional database session for learning.
        
        Args:
            db_session: SQLAlchemy session to access historical mappings for learning
        """
        self.db = db_session
        # In-memory cache of learned mappings (variable_id -> column_name -> confidence)
        self.learned_mappings: Dict[str, Dict[str, float]] = defaultdict(dict)
        # Load learned mappings if database is available
        if self.db:
            self._load_learned_mappings()
        # Common medical/health abbreviations and synonyms
        self.synonym_groups = {
            'blood_sugar': ['glucose', 'blood glucose', 'blood sugar', 'sugar', 'gluc', 'bs', 'bg'],
            'blood_pressure': ['bp', 'pressure', 'blood pressure', 'systolic', 'diastolic'],
            'heart_rate': ['hr', 'pulse', 'heart rate', 'bpm', 'heartbeat'],
            'age': ['age', 'years', 'yr', 'yrs', 'years old'],
            'weight': ['weight', 'wt', 'body weight', 'mass'],
            'height': ['height', 'ht', 'body height', 'length'],
            'temperature': ['temp', 'temperature', 'body temp', 'fever'],
            'cholesterol': ['chol', 'cholesterol', 'ldl', 'hdl', 'total cholesterol'],
            'cancer_type': ['cancer type', 'type', 'cancer', 'tumor type'],
            'cancer_stage': ['stage', 'cancer stage', 'tumor stage', 'staging'],
            'diagnosis': ['diagnosis', 'condition', 'disease', 'disorder'],
            'treatment_date': ['treatment date', 'treatment', 'date', 'tx date'],
            'diagnosis_date': ['diagnosis date', 'dx date', 'diagnosed', 'date diagnosed'],
        }
        
        # Common abbreviation patterns
        self.abbreviation_patterns = [
            (r'blood\s*sugar', ['bs', 'bg', 'blood_sug', 'bloodsug', 'blood_sugar']),
            (r'blood\s*glucose', ['bg', 'gluc', 'glucose', 'blood_gluc']),
            (r'blood\s*pressure', ['bp', 'blood_press', 'bloodpress']),
            (r'heart\s*rate', ['hr', 'heartrate', 'heart_rate']),
            (r'patient\s*id', ['pid', 'patientid', 'patient_id', 'id']),
            (r'cancer\s*type', ['cancertype', 'cancer_type', 'type']),
            (r'cancer\s*stage', ['cancerstage', 'cancer_stage', 'stage']),
        ]
    
    def _load_learned_mappings(self):
        """Load confirmed mappings from database to learn from past successes."""
        if not self.db:
            return
        
        try:
            from models import VariableColumnMapping
            
            # Get all confirmed mappings (these are successful matches we've learned from)
            confirmed_mappings = self.db.query(VariableColumnMapping).filter(
                VariableColumnMapping.confirmed == True
            ).all()
            
            for mapping in confirmed_mappings:
                var_id = mapping.variable_id.lower()
                col_name = mapping.column_name
                confidence = mapping.confidence_score or 0.8
                
                # Store in learned mappings with confidence score
                if var_id not in self.learned_mappings:
                    self.learned_mappings[var_id] = {}
                
                # If we've seen this mapping before, increase confidence
                if col_name in self.learned_mappings[var_id]:
                    self.learned_mappings[var_id][col_name] = min(
                        self.learned_mappings[var_id][col_name] + 0.1, 1.0
                    )
                else:
                    self.learned_mappings[var_id][col_name] = confidence
            
            logger.info(f"Loaded {len(confirmed_mappings)} learned mappings from database")
        except Exception as e:
            logger.warning(f"Could not load learned mappings: {e}")
    
    def _check_learned_mappings(self, filter_key: str, available_columns: List[str]) -> Optional[Tuple[str, float]]:
        """
        Check if we've learned a successful mapping for this filter key.
        
        Returns:
            Tuple of (matched_column, confidence) if found, None otherwise
        """
        filter_key_lower = filter_key.lower()
        
        # Check exact match in learned mappings
        if filter_key_lower in self.learned_mappings:
            for col in available_columns:
                if col in self.learned_mappings[filter_key_lower]:
                    confidence = self.learned_mappings[filter_key_lower][col]
                    logger.info(f"Using learned mapping: '{filter_key}' -> '{col}' (confidence: {confidence:.2f})")
                    return (col, confidence)
        
        # Check normalized matches
        filter_normalized = self.normalize_text(filter_key)
        for var_id, col_mappings in self.learned_mappings.items():
            var_normalized = self.normalize_text(var_id)
            if var_normalized == filter_normalized:
                for col in available_columns:
                    if col in col_mappings:
                        confidence = col_mappings[col]
                        logger.info(f"Using learned mapping (normalized): '{filter_key}' -> '{col}' (confidence: {confidence:.2f})")
                        return (col, confidence)
        
        return None
    
    def learn_mapping(self, filter_key: str, matched_column: str, confidence: float, confirmed: bool = False):
        """
        Learn from a successful mapping to improve future matches.
        
        Args:
            filter_key: The filter key that was matched
            matched_column: The column name that was matched
            confidence: Confidence score of the match (0.0-1.0)
            confirmed: Whether this mapping was confirmed by the user
        """
        filter_key_lower = filter_key.lower()
        
        if filter_key_lower not in self.learned_mappings:
            self.learned_mappings[filter_key_lower] = {}
        
        # Boost confidence if confirmed by user
        if confirmed:
            confidence = min(confidence + 0.2, 1.0)
        
        # If we've seen this mapping before, increase confidence
        if matched_column in self.learned_mappings[filter_key_lower]:
            current_conf = self.learned_mappings[filter_key_lower][matched_column]
            # Average with slight boost for repeated successful matches
            self.learned_mappings[filter_key_lower][matched_column] = min(
                (current_conf + confidence) / 2 + 0.05, 1.0
            )
        else:
            self.learned_mappings[filter_key_lower][matched_column] = confidence
        
        logger.info(f"Learned mapping: '{filter_key}' -> '{matched_column}' (confidence: {self.learned_mappings[filter_key_lower][matched_column]:.2f})")
        
        # Optionally save to database if available
        if self.db and confirmed:
            try:
                from models import VariableColumnMapping
                # Note: This would need computation_id and org_id in real usage
                # For now, we just update the in-memory cache
                pass
            except Exception as e:
                logger.warning(f"Could not save learned mapping to database: {e}")
    
    def normalize_text(self, text: str) -> str:
        """
        Normalize text for comparison:
        - Convert to lowercase
        - Remove special characters (keep alphanumeric and spaces)
        - Remove extra whitespace
        - Handle unicode normalization
        """
        if not text:
            return ""
        
        # Convert to lowercase
        text = text.lower()
        
        # Unicode normalization
        text = unicodedata.normalize('NFKD', text)
        
        # Replace common separators with spaces
        text = re.sub(r'[_\-\.,;:]+', ' ', text)
        
        # Remove special characters, keep alphanumeric and spaces
        text = re.sub(r'[^a-z0-9\s]', '', text)
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        return text.strip()
    
    def tokenize(self, text: str) -> List[str]:
        """Tokenize text into words."""
        normalized = self.normalize_text(text)
        return normalized.split() if normalized else []
    
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts using multiple methods."""
        # Normalize both texts
        norm1 = self.normalize_text(text1)
        norm2 = self.normalize_text(text2)
        
        if not norm1 or not norm2:
            return 0.0
        
        # Exact match after normalization
        if norm1 == norm2:
            return 1.0
        
        # SequenceMatcher similarity
        seq_sim = SequenceMatcher(None, norm1, norm2).ratio()
        
        # Token-based similarity (Jaccard)
        tokens1 = set(self.tokenize(norm1))
        tokens2 = set(self.tokenize(norm2))
        if tokens1 or tokens2:
            intersection = len(tokens1 & tokens2)
            union = len(tokens1 | tokens2)
            token_sim = intersection / union if union > 0 else 0.0
        else:
            token_sim = 0.0
        
        # Substring match (one contains the other)
        contains_match = 0.0
        if norm1 in norm2 or norm2 in norm1:
            contains_match = 0.8
        elif len(norm1) > 3 and len(norm2) > 3:
            # Check if significant portion matches
            if len(norm1) < len(norm2):
                if norm1 in norm2:
                    contains_match = len(norm1) / len(norm2) * 0.8
            else:
                if norm2 in norm1:
                    contains_match = len(norm2) / len(norm1) * 0.8
        
        # Combined score (weighted)
        combined = max(seq_sim, token_sim * 0.7 + contains_match * 0.3)
        
        return combined
    
    def check_synonym_match(self, key: str, column: str) -> float:
        """Check if key and column match through synonym groups."""
        key_norm = self.normalize_text(key)
        col_norm = self.normalize_text(column)
        
        # Check each synonym group
        for group_name, synonyms in self.synonym_groups.items():
            key_in_group = any(syn in key_norm for syn in synonyms)
            col_in_group = any(syn in col_norm for syn in synonyms)
            
            if key_in_group and col_in_group:
                # Both are in the same synonym group
                return 0.95
        
        return 0.0
    
    def check_abbreviation_match(self, key: str, column: str) -> float:
        """Check if one is an abbreviation of the other."""
        key_norm = self.normalize_text(key)
        col_norm = self.normalize_text(column)
        
        # Check abbreviation patterns
        for pattern, abbrevs in self.abbreviation_patterns:
            key_matches = bool(re.search(pattern, key_norm, re.IGNORECASE))
            col_matches = any(abbrev in col_norm for abbrev in abbrevs)
            
            if key_matches and col_matches:
                return 0.9
            
            # Reverse check
            col_matches_pattern = bool(re.search(pattern, col_norm, re.IGNORECASE))
            key_matches_abbrev = any(abbrev in key_norm for abbrev in abbrevs)
            
            if col_matches_pattern and key_matches_abbrev:
                return 0.9
        
        # Check if one is a clear abbreviation of the other
        # (e.g., "Blood_Sug" is abbreviation of "blood_sugar")
        key_tokens = self.tokenize(key_norm)
        col_tokens = self.tokenize(col_norm)
        
        if len(key_tokens) == 1 and len(col_tokens) > 1:
            # Key might be abbreviation
            if key_tokens[0] in ''.join(col_tokens) or any(key_tokens[0] in t for t in col_tokens):
                return 0.85
        elif len(col_tokens) == 1 and len(key_tokens) > 1:
            # Column might be abbreviation
            if col_tokens[0] in ''.join(key_tokens) or any(col_tokens[0] in t for t in key_tokens):
                return 0.85
        
        return 0.0
    
    def check_partial_match(self, key: str, column: str) -> float:
        """Check for partial/substring matches with semantic meaning."""
        key_norm = self.normalize_text(key)
        col_norm = self.normalize_text(column)
        
        # Extract meaningful words (ignore common words)
        stop_words = {'the', 'a', 'an', 'and', 'or', 'of', 'in', 'on', 'at', 'to', 'for'}
        key_words = [w for w in self.tokenize(key_norm) if w not in stop_words and len(w) > 2]
        col_words = [w for w in self.tokenize(col_norm) if w not in stop_words and len(w) > 2]
        
        if not key_words or not col_words:
            return 0.0
        
        # Check if significant words overlap
        key_set = set(key_words)
        col_set = set(col_words)
        
        if key_set & col_set:  # Intersection
            overlap_ratio = len(key_set & col_set) / len(key_set | col_set)
            return min(overlap_ratio * 1.2, 0.9)  # Cap at 0.9
        
        # Check if words are similar
        max_word_sim = 0.0
        for kw in key_words:
            for cw in col_words:
                sim = SequenceMatcher(None, kw, cw).ratio()
                if sim > 0.7:  # Words are similar
                    max_word_sim = max(max_word_sim, sim * 0.8)
        
        return max_word_sim
    
    def find_best_match(
        self,
        filter_key: str,
        available_columns: List[str],
        min_confidence: float = 0.5
    ) -> Optional[Tuple[str, float, str]]:
        """
        Find the best matching column for a filter key.
        Uses learned mappings first, then falls back to intelligent matching.
        
        Returns:
            Tuple of (matched_column_name, confidence_score, match_reason) or None
        """
        if not filter_key or not available_columns:
            return None
        
        # First, check if we've learned a successful mapping for this key
        learned_match = self._check_learned_mappings(filter_key, available_columns)
        if learned_match:
            matched_col, learned_confidence = learned_match
            # Boost learned mappings above min_confidence threshold
            if learned_confidence >= min_confidence:
                return (matched_col, learned_confidence, "learned from past successful matches")
        
        # If no learned mapping, use intelligent matching
        best_match = None
        best_score = 0.0
        best_reason = ""
        
        for col in available_columns:
            if not col:
                continue
            
            # Calculate multiple similarity scores
            base_sim = self.calculate_similarity(filter_key, col)
            synonym_sim = self.check_synonym_match(filter_key, col)
            abbrev_sim = self.check_abbreviation_match(filter_key, col)
            partial_sim = self.check_partial_match(filter_key, col)
            
            # Combined score (take the maximum, as different methods catch different cases)
            combined_score = max(base_sim, synonym_sim, abbrev_sim, partial_sim)
            
            # Boost score if multiple methods agree
            method_count = sum([
                base_sim > 0.6,
                synonym_sim > 0.5,
                abbrev_sim > 0.5,
                partial_sim > 0.5
            ])
            if method_count >= 2:
                combined_score = min(combined_score * 1.1, 1.0)
            
            # Determine reason
            if combined_score > best_score:
                best_score = combined_score
                best_match = col
                
                if synonym_sim > 0.8:
                    best_reason = "synonym match"
                elif abbrev_sim > 0.8:
                    best_reason = "abbreviation match"
                elif base_sim > 0.7:
                    best_reason = "high similarity"
                elif partial_sim > 0.6:
                    best_reason = "partial/word match"
                else:
                    best_reason = f"similarity: {combined_score:.2f}"
        
        if best_match and best_score >= min_confidence:
            logger.info(f"Matched filter key '{filter_key}' to column '{best_match}' "
                       f"(confidence: {best_score:.2f}, reason: {best_reason})")
            
            # Learn from this successful match
            self.learn_mapping(filter_key, best_match, best_score, confirmed=False)
            
            return (best_match, best_score, best_reason)
        
        logger.warning(f"No match found for filter key '{filter_key}' in columns: {available_columns}")
        return None
    
    def match_all_filters(
        self,
        filters: Dict[str, Any],
        available_columns: List[str]
    ) -> Dict[str, Optional[str]]:
        """
        Match all filter keys to available columns.
        
        Returns:
            Dict mapping filter_key -> matched_column_name (or None if no match)
        """
        matches = {}
        
        for filter_key in filters.keys():
            match_result = self.find_best_match(filter_key, available_columns, min_confidence=0.4)
            if match_result:
                matches[filter_key] = match_result[0]  # Return column name
            else:
                matches[filter_key] = None
        
        return matches

