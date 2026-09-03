"""
Database module for HYDRA - SQLAlchemy models and session management.
"""

import os
from datetime import datetime
from typing import Optional, List

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session

# Database URL - SQLite for simplicity, can be changed to PostgreSQL later
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/hydra.db")

# Ensure data directory exists
os.makedirs(os.path.dirname(DATABASE_URL.replace("sqlite:///", "")), exist_ok=True)

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class BusinessModel(Base):
    """SQLAlchemy model for a HYDRA business."""
    __tablename__ = "businesses"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(String, unique=True, index=True, nullable=False)
    business_type = Column(String, nullable=False)  # financial, design, trading
    capital = Column(Float, default=0.0)
    revenue = Column(Float, default=0.0)
    expenses = Column(Float, default=0.0)
    profit = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Product details
    product_name = Column(String)
    pricing = Column(Float)
    target_customers = Column(String)
    features = Column(JSON)  # Store list of features
    customer_base_size = Column(Integer)
    conversion_rate = Column(Float)
    
    # Operational metrics
    monthly_customers = Column(Integer, default=0)
    active_subscriptions = Column(Integer, default=0)
    sales_count = Column(Integer, default=0)
    customer_satisfaction_score = Column(Integer, default=0)
    
    # Relationships
    leads = relationship("LeadModel", back_populates="business", cascade="all, delete-orphan")
    customers = relationship("CustomerModel", back_populates="business", cascade="all, delete-orphan")
    campaigns = relationship("CampaignModel", back_populates="business", cascade="all, delete-orphan")


class LeadModel(Base):
    """SQLAlchemy model for a lead."""
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(String, unique=True, index=True, nullable=False)
    business_id = Column(Integer, ForeignKey("businesses.id"))
    email = Column(String, nullable=False)
    source = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    qualified = Column(Boolean, default=False)
    score = Column(Integer, default=0)
    value = Column(Float, default=0.0)
    customer_id = Column(String, nullable=True)  # Reference to customer if converted
    
    # Relationship
    business = relationship("BusinessModel", back_populates="leads")


class CustomerModel(Base):
    """SQLAlchemy model for a customer (subscription)."""
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(String, unique=True, index=True, nullable=False)
    business_id = Column(Integer, ForeignKey("businesses.id"))
    email = Column(String, nullable=False)
    plan = Column(String, default="monthly")
    price = Column(Float)
    start_date = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="active")  # active, cancelled, paused
    
    # Relationship
    business = relationship("BusinessModel", back_populates="customers")


class TransactionModel(Base):
    """SQLAlchemy model for financial transactions."""
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    business_type = Column(String)  # financial, design, trading
    revenue = Column(Float, default=0.0)
    expenses = Column(Float, default=0.0)
    profit = Column(Float, default=0.0)
    timestamp = Column(DateTime, default=datetime.utcnow)
    description = Column(String, nullable=True)


class AccountingReportModel(Base):
    """SQLAlchemy model for storing accounting reports."""
    __tablename__ = "accounting_reports"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    period_year = Column(Integer)
    period_month = Column(Integer)
    period_month_name = Column(String)
    period_quarter = Column(Integer)
    
    # Summary metrics
    total_revenue = Column(Float)
    total_expenses = Column(Float)
    total_profit = Column(Float)
    total_customers = Column(Integer)
    profit_margin = Column(Float)
    average_revenue_per_customer = Column(Float)
    
    # Store full report as JSON for flexibility
    report_data = Column(JSON)


class CampaignModel(Base):
    """SQLAlchemy model for a marketing campaign."""
    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(String, unique=True, index=True, nullable=False)
    business_id = Column(Integer, ForeignKey("businesses.id"))
    platform = Column(String)
    budget = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="active")  # active, paused, completed
    
    # Relationship
    business = relationship("BusinessModel", back_populates="campaigns")


class AuditModel(Base):
    __tablename__ = "audits"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    type = Column(String)  # transaction_validation, hydra_validity, ecosystem_audit
    data = Column(JSON)  # Store audit data as JSON
    auditor = Column(String, default="system")

class TreasuryStateModel(Base):
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


def get_db() -> Session:
    """Get a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Initialize database on import
create_tables()
