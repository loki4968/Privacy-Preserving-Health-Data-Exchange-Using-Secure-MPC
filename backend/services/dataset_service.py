"""
Dataset Service for managing dataset descriptors and schema inference.
"""

import csv
import logging
import os
from typing import Dict, List, Optional, Any
import pandas as pd
from sqlalchemy.orm import Session

from models import DatasetDescriptor, Organization
from utils import infer_data_category, get_metric_type

logger = logging.getLogger(__name__)


class DatasetService:
    """Service for managing dataset descriptors and inferring schemas."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def infer_schema_from_csv(
        self,
        file_path: str,
        has_header: bool = True,
        delimiter: str = ',',
        sample_rows: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Infer column schema from a CSV file.
        
        Returns:
            List of column descriptors with name, data_type, unit, semantic_tags
        """
        try:
            # Read CSV with pandas for better handling
            df = pd.read_csv(
                file_path,
                nrows=sample_rows,
                header=0 if has_header else None,
                sep=delimiter,
                low_memory=False
            )
            
            columns = []
            for idx, col_name in enumerate(df.columns):
                col_data = df[col_name].dropna()
                
                # Infer data type
                data_type = self._infer_data_type(col_data)
                
                # Infer unit from column name
                unit = self._infer_unit(col_name)
                
                # Generate semantic tags
                semantic_tags = self._generate_semantic_tags(col_name, col_data, data_type)
                
                columns.append({
                    'column_name': str(col_name),
                    'column_index': idx,
                    'data_type': data_type,
                    'unit': unit,
                    'semantic_tags': semantic_tags,
                    'example_values': col_data.head(3).tolist() if len(col_data) > 0 else [],
                    'null_count': len(df) - len(col_data),
                    'unique_count': col_data.nunique() if len(col_data) > 0 else 0
                })
            
            return columns
        
        except Exception as e:
            logger.error(f"Error inferring schema from CSV: {e}")
            # Fallback: basic schema from headers
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    reader = csv.reader(f, delimiter=delimiter)
                    if has_header:
                        headers = next(reader)
                    else:
                        # Read first row as sample
                        first_row = next(reader)
                        headers = [f"Column_{i}" for i in range(len(first_row))]
                
                return [
                    {
                        'column_name': h,
                        'column_index': idx,
                        'data_type': 'string',  # Default
                        'unit': None,
                        'semantic_tags': [],
                        'example_values': [],
                        'null_count': 0,
                        'unique_count': 0
                    }
                    for idx, h in enumerate(headers)
                ]
            except Exception as e2:
                logger.error(f"Fallback schema inference also failed: {e2}")
                return []
    
    def _infer_data_type(self, series: pd.Series) -> str:
        """Infer data type from pandas Series."""
        if len(series) == 0:
            return 'string'
        
        # Try numeric first
        try:
            pd.to_numeric(series, errors='raise')
            # Check if it's integer-like
            if series.dtype == 'int64' or (series % 1 == 0).all():
                return 'int'
            return 'float'
        except (ValueError, TypeError):
            pass
        
        # Try datetime
        try:
            pd.to_datetime(series, errors='raise')
            return 'datetime'
        except (ValueError, TypeError):
            pass
        
        # Default to string
        return 'string'
    
    def _infer_unit(self, column_name: str) -> Optional[str]:
        """Infer unit from column name."""
        name_lower = column_name.lower()
        
        # Common unit patterns
        unit_patterns = {
            'mg/dl': r'mg/dl|mg\.dl|mg per dl',
            'mmol/l': r'mmol/l|mmol\.l',
            'mmhg': r'mmhg|mm\.hg|mm hg',
            'bpm': r'bpm|beats per minute',
            'kg/m2': r'kg/m2|kg\.m2|bmi',
            'years': r'years|yr|yrs|age',
            'kg': r'\bkg\b|kilograms',
            'lbs': r'\blbs\b|pounds',
            'cm': r'\bcm\b|centimeters',
            'inches': r'inches|in\b',
            'celsius': r'celsius|°c|c\b',
            'fahrenheit': r'fahrenheit|°f|f\b',
        }
        
        for unit, pattern in unit_patterns.items():
            import re
            if re.search(pattern, name_lower, re.IGNORECASE):
                return unit
        
        return None
    
    def _generate_semantic_tags(
        self,
        column_name: str,
        series: pd.Series,
        data_type: str
    ) -> List[str]:
        """Generate semantic tags for a column."""
        tags = []
        name_lower = column_name.lower()
        
        # Use existing utility functions
        metric_type = get_metric_type(column_name)
        if metric_type != "unknown":
            tags.append(metric_type.replace(' ', '_'))
        
        # Add common health metric tags
        health_keywords = {
            'glucose': ['glucose', 'blood_sugar', 'sugar'],
            'blood_pressure': ['blood_pressure', 'bp', 'systolic', 'diastolic'],
            'heart_rate': ['heart_rate', 'pulse', 'hr'],
            'temperature': ['temperature', 'temp', 'fever'],
            'bmi': ['bmi', 'body_mass_index'],
            'age': ['age', 'years'],
            'weight': ['weight', 'body_weight'],
            'height': ['height', 'body_height'],
            'cholesterol': ['cholesterol', 'ldl', 'hdl', 'triglycerides'],
        }
        
        for tag, keywords in health_keywords.items():
            if any(kw in name_lower for kw in keywords):
                tags.append(tag)
                break
        
        # Add data type tag
        if data_type in ['float', 'int']:
            tags.append('numeric')
        
        # Add unit-based tags if unit was inferred
        unit = self._infer_unit(column_name)
        if unit:
            tags.append(f"unit_{unit}")
        
        return list(set(tags))  # Remove duplicates
    
    def create_dataset_descriptor(
        self,
        org_id: int,
        name: str,
        file_path: str,
        description: Optional[str] = None,
        schema: Optional[List[Dict[str, Any]]] = None
    ) -> DatasetDescriptor:
        """Create a new dataset descriptor."""
        # If schema not provided, infer it
        if schema is None:
            schema = self.infer_schema_from_csv(file_path)
        
        dataset = DatasetDescriptor(
            org_id=org_id,
            name=name,
            description=description,
            file_path=file_path,
            schema=schema
        )
        
        self.db.add(dataset)
        self.db.commit()
        self.db.refresh(dataset)
        
        return dataset
    
    def get_dataset_descriptors(
        self,
        org_id: Optional[int] = None,
        active_only: bool = True
    ) -> List[DatasetDescriptor]:
        """Get dataset descriptors, optionally filtered by org."""
        query = self.db.query(DatasetDescriptor)
        
        if org_id:
            query = query.filter(DatasetDescriptor.org_id == org_id)
        
        if active_only:
            query = query.filter(DatasetDescriptor.is_active == True)
        
        return query.all()
    
    def get_dataset_by_id(self, dataset_id: int, org_id: Optional[int] = None) -> Optional[DatasetDescriptor]:
        """Get a dataset descriptor by ID, optionally checking org ownership."""
        query = self.db.query(DatasetDescriptor).filter(DatasetDescriptor.id == dataset_id)
        
        if org_id:
            query = query.filter(DatasetDescriptor.org_id == org_id)
        
        return query.first()

