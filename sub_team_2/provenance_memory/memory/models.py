
from pathlib import Path
import json
from typing import List, Union
from pydantic import BaseModel, Field, field_validator

DEFAULT_RUNBOOKS_PATH = Path(__file__).resolve().parent.parent / 'data' / 'runbooks.json'

class HistoricalRunbook(BaseModel):
    runbook_id: str = Field(..., description='Unique runbook identifier')
    title: str = Field(..., description='Title of historical runbook')
    error_signature: str = Field(..., description='Error signature associated with historical incident')
    historical_fix: str = Field(..., description='Actionable resolution steps applied')
    provenance_confidence: float = Field(..., ge=0.0, le=1.0, description='Confidence score between 0.0 and 1.0')
    prior_success_count: int = Field(..., ge=0, description='Historical prior success counter')

    @field_validator('runbook_id', 'title', 'error_signature', 'historical_fix')
    @classmethod
    def validate_non_empty_str(cls, value: str, info) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f'Field {info.field_name} must be a non-empty string.')
        return value.strip()

class RunbookMatch(BaseModel):
    runbook_id: str = Field(..., description='Unique runbook identifier')
    historical_fix: str = Field(..., description='Actionable resolution steps')
    provenance_confidence: float = Field(..., ge=0.0, le=1.0, description='Confidence score between 0.0 and 1.0')
    prior_success_count: int = Field(..., ge=0, description='Historical prior success counter')

    @field_validator('runbook_id', 'historical_fix')
    @classmethod
    def validate_non_empty_str(cls, value: str, info) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f'Field {info.field_name} must be a non-empty string.')
        return value.strip()

class RetrievedRunbookMatch(BaseModel):
    runbook_id: str = Field(..., description='Unique runbook identifier')
    historical_fix: str = Field(..., description='Actionable resolution steps')
    provenance_confidence: float = Field(..., ge=0.0, le=1.0, description='Confidence score between 0.0 and 1.0')
    prior_success_count: int = Field(..., ge=0, description='Historical prior success counter')
    similarity_score: float = Field(..., ge=-1.0, le=1.0, description='Cosine similarity score between -1.0 and 1.0')

    @field_validator('runbook_id', 'historical_fix')
    @classmethod
    def validate_non_empty_str(cls, value: str, info) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f'Field {info.field_name} must be a non-empty string.')
        return value.strip()

def load_mock_runbooks(json_path: Union[str, Path] = DEFAULT_RUNBOOKS_PATH) -> List[HistoricalRunbook]:
    path = Path(json_path)
    if not path.exists():
        raise FileNotFoundError(f'Runbooks dataset not found at: {path}')

    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    raw_runbooks = data.get('runbooks', [])
    return [HistoricalRunbook(**item) for item in raw_runbooks]
