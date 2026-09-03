# service.py
"""Core services for HYDRA Opportunity Intelligence Engine (HOI).
Implements connector registration, opportunity discovery (stub), scoring and proposal generation.
All state is stored in an in‑memory placeholder `_STORE`; replace with persistent DB in production.
"""
from .models import SourceConnector, Opportunity, OpportunityScore, InvestmentProposal
from datetime import datetime, timedelta
import uuid

# Simple in‑memory store
_STORE = {
    "connectors": {},  # connector_id -> SourceConnector
    "opportunities": {},  # opp_id -> Opportunity
    "scores": {},  # opp_id -> OpportunityScore
    "proposals": {},  # opp_id -> InvestmentProposal
    "audit": []
}

def _audit(event: str, details: dict):
    _STORE["audit"].append({"timestamp": datetime.utcnow().isoformat(), "event": event, "details": details})

# Connector management
def register_connector(name: str, description: str, type_: str, config: dict | None = None) -> SourceConnector:
    connector_id = f"conn-{uuid.uuid4().hex[:8]}"
    connector = SourceConnector(
        connector_id=connector_id,
        name=name,
        description=description,
        type=type_,
        config=config or {}
    )
    _STORE["connectors"][connector_id] = connector
    _audit("register_connector", {"connector_id": connector_id, "name": name})
    return connector

def list_connectors() -> list[SourceConnector]:
    return list(_STORE["connectors"].values())

# Opportunity discovery placeholder (real implementation would call external sources)
def discover_opportunity(title: str, description: str, source_connector_id: str, raw_data: dict | None = None) -> Opportunity:
    if source_connector_id not in _STORE["connectors"]:
        raise ValueError("Connector not registered")
    opp_id = f"opp-{uuid.uuid4().hex[:10]}"
    opp = Opportunity(
        opp_id=opp_id,
        title=title,
        description=description,
        source_connector_id=source_connector_id,
        raw_data=raw_data or {}
    )
    _STORE["opportunities"][opp_id] = opp
    _audit("discover_opportunity", {"opp_id": opp_id, "connector_id": source_connector_id})
    return opp

# Scoring – simple weighted sum (weights can be configured later)
def score_opportunity(opp_id: str, **kwargs) -> OpportunityScore:
    if opp_id not in _STORE["opportunities"]:
        raise ValueError("Opportunity not found")
    # Extract scores, ensuring 0‑10 range
    fields = [
        "rentabilidad", "escalabilidad", "automatizacion", "coste_inicial",
        "riesgo", "competencia", "tiempo_ingresos", "replicacion",
        "sinergia", "valor_estrategico"
    ]
    scores = {f: float(kwargs.get(f, 0.0)) for f in fields}
    total = sum(scores.values()) / len(fields)  # average as total_score (0‑10)
    opp_score = OpportunityScore(
        opp_id=opp_id,
        **scores,
        total_score=total,
        evaluated_at=datetime.utcnow()
    )
    _STORE["scores"][opp_id] = opp_score
    _audit("score_opportunity", {"opp_id": opp_id, "total": total})
    return opp_score

# Proposal generation based on score and a simple investment heuristic
def generate_proposal(opp_id: str, investment_multiplier: float = 1.0) -> InvestmentProposal:
    if opp_id not in _STORE["scores"]:
        raise ValueError("Opportunity has not been scored")
    score = _STORE["scores"][opp_id]
    opp = _STORE["opportunities"][opp_id]
    # Simple heuristic: recommended investment = total_score * 10k * multiplier
    recommended = round(score.total_score * 10000 * investment_multiplier, 2)
    # Expected ROI months inversely proportional to score (higher score => quicker ROI)
    roi_months = max(1, int(12 - (score.total_score / 10) * 8))
    proposal = InvestmentProposal(
        opp_id=opp_id,
        title=opp.title,
        total_score=score.total_score,
        recommended_investment=recommended,
        expected_roi_months=roi_months,
        rationale=f"Score {score.total_score:.2f} suggests viable investment with expected ROI in {roi_months} months.",
        generated_at=datetime.utcnow()
    )
    _STORE["proposals"][opp_id] = proposal
    _audit("generate_proposal", {"opp_id": opp_id, "investment": recommended})
    return proposal

def get_proposal(opp_id: str) -> InvestmentProposal | None:
    return _STORE["proposals"].get(opp_id)

def audit_log():
    return _STORE["audit"]
