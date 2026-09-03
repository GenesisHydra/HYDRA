# models.py
"""Data models for HYDRA Opportunity Intelligence Engine (HOI).
Defines structures for opportunity representation, source connectors and scoring.
"""
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class SourceConnector(BaseModel):
    connector_id: str = Field(..., description="Unique ID for the source connector")
    name: str
    description: str
    type: str = Field(..., description="e.g., web, api, rss, database")
    config: dict = Field(default_factory=dict)
    enabled: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Opportunity(BaseModel):
    opp_id: str = Field(..., description="Unique identifier for the opportunity")
    title: str
    description: str
    source_connector_id: str
    raw_data: dict = Field(default_factory=dict)
    discovered_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict = Field(default_factory=dict)

class OpportunityScore(BaseModel):
    opp_id: str
    rentabilidad: float = Field(0.0, ge=0, le=10)
    escalabilidad: float = Field(0.0, ge=0, le=10)
    automatizacion: float = Field(0.0, ge=0, le=10)
    coste_inicial: float = Field(0.0, ge=0, le=10)
    riesgo: float = Field(0.0, ge=0, le=10)
    competencia: float = Field(0.0, ge=0, le=10)
    tiempo_ingresos: float = Field(0.0, ge=0, le=10)
    replicacion: float = Field(0.0, ge=0, le=10)
    sinergia: float = Field(0.0, ge=0, le=10)
    valor_estrategico: float = Field(0.0, ge=0, le=10)
    total_score: float = Field(0.0)
    evaluated_at: datetime = Field(default_factory=datetime.utcnow)

class InvestmentProposal(BaseModel):
    opp_id: str
    title: str
    total_score: float
    recommended_investment: float
    expected_roi_months: int
    rationale: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)
