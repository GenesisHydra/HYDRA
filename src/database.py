

from sqlalchemy import Column, Integer, String, DateTime, Float, create_engine, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()
engine = create_engine("sqlite:///hydra.db", echo=False)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


engine = create_engine("sqlite:///hydra.db", echo=False)



class TreasuryStateModel(Base):
    """SQLAlchemy model for treasury state per business type."""
    __tablename__ = "treasury_state"

    id = Column(Integer, primary_key=True, index=True)
    business_type = Column(String, unique=True, index=True, nullable=False)  # financial, design, trading
    capital = Column(Float, default=0.0)
    budget = Column(Float, default=0.0)
    expenses = Column(Float, default=0.0)
    revenue = Column(Float, default=0.0)
    profit = Column(Float, default=0.0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TreasuryHistoryModel(Base):
    """SQLAlchemy model for treasury history/audit trail."""
    __tablename__ = "treasury_history"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    type = Column(String)  # profit_validation, budget_allocation, transfer, auto_balance, transaction
    hydra_id = Column(String, nullable=True)  # business type or specific ID
    amount = Column(Float, nullable=True)
    reason = Column(String, nullable=True)
    action = Column(String)  # approved, rejected, completed, etc.
    message = Column(String, nullable=True)
    business_type = Column(String, nullable=True)
    revenue = Column(Float, nullable=True)
    expenses = Column(Float, nullable=True)
    profit = Column(Float, nullable=True)


def create_tables():
    """Create all tables in the database."""
    Base.metadata.create_all(bind=engine)


class AuditModel(Base):
    __tablename__ = "audits"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    type = Column(String)  # transaction_validation, hydra_validity, ecosystem_audit
    data = Column(JSON)  # Store audit data as JSON
    auditor = Column(String, default="system")


class CampaignModel(Base):
    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(String, unique=True, index=True, nullable=False)
    business_id = Column(Integer, nullable=False)
    platform = Column(String, nullable=False)
    budget = Column(Float, default=0.0)
    leads_generated = Column(Integer, default=0)
    cost_per_lead = Column(Float, default=0.0)
    status = Column(String, default="active")
    start_date = Column(DateTime, default=datetime.utcnow)


class BusinessModel(Base):
    __tablename__ = "businesses"

    business_id = Column(String, primary_key=True, index=True)
    business_type = Column(String, nullable=False)
    capital = Column(Float, default=0.0)
    revenue = Column(Float, default=0.0)
    expenses = Column(Float, default=0.0)
    profit = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    product_name = Column(String)
    pricing = Column(Float)
    target_customers = Column(String)
    features = Column(JSON)
    customer_base_size = Column(Integer)
    conversion_rate = Column(Float)
    monthly_customers = Column(Integer)
    active_subscriptions = Column(Integer)
    sales_count = Column(Integer)
    customer_satisfaction_score = Column(Float)


class LeadModel(Base):
    __tablename__ = "leads"

    lead_id = Column(String, primary_key=True, index=True)
    business_id = Column(Integer, nullable=False)
    email = Column(String, nullable=False)
    source = Column(String)
    timestamp = Column(DateTime)
    qualified = Column(Integer, default=0)
    score = Column(Integer, default=0)
    value = Column(Float)
    customer_id = Column(String, nullable=True)


class CustomerModel(Base):
    __tablename__ = "customers"

    customer_id = Column(String, primary_key=True, index=True)
    business_id = Column(Integer, nullable=False)
    email = Column(String, nullable=False)
    plan = Column(String)
    price = Column(Float)
    start_date = Column(DateTime)
    status = Column(String)
    stripe_customer_id = Column(String, nullable=True)
    start_date = Column(DateTime, default=datetime.utcnow)




class AccountingReportModel(Base):
    __tablename__ = "accounting_reports"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    period_year = Column(Integer, nullable=False)
    period_month = Column(Integer, nullable=False)
    period_month_name = Column(String, nullable=False)
    period_quarter = Column(Integer, nullable=False)
    total_revenue = Column(Float, default=0.0)
    total_expenses = Column(Float, default=0.0)
    total_profit = Column(Float, default=0.0)
    total_customers = Column(Integer, default=0)
    profit_margin = Column(Float, default=0.0)
    average_revenue_per_customer = Column(Float, default=0.0)
    report_data = Column(JSON)  # Guardar el reporte completo como JSON


class TransactionModel(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(String, unique=True, index=True, nullable=False)
    business_id = Column(Integer, nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String, default="eur")
    status = Column(String, default="pending")  # pending, succeeded, failed
    description = Column(String, nullable=True)
    receipt_email = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
