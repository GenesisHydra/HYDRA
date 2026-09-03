#!/usr/bin/env python3
import sys
sys.path.insert(0, 'src')

from business import Business
from database import SessionLocal

def print_business_status(biz, label):
    status = biz.get_status()
    print(f"{label}:")
    print(f"  Business ID: {status['business_id']}")
    print(f"  Capital: {status['capital']}")
    print(f"  Profit: {status['profit']}")
    print(f"  Monthly Customers: {status['monthly_customers']}")
    print(f"  Active Subscriptions: {status['active_subscriptions']}")
    print(f"  Sales Count: {status['sales_count']}")
    print(f"  Revenue This Month: {status['revenue_this_month']}")
    print(f"  Profitable: {status['profitable']}")
    print()

def test_business():
    # Create a new business session
    session = SessionLocal()
    
    # Create a new business
    biz = Business("financial", 1000.0, session=session)
    print_business_status(biz, "After business creation")
    
    # Generate a lead
    lead = biz.generate_lead("LinkedIn", "test@example.com")
    print(f"Generated lead: {lead['id']} - {lead['email']}")
    print(f"Leads in memory: {len(biz.leads)}")
    print_business_status(biz, "After lead generation")
    
    # Convert the lead
    customer = biz.convert_lead(lead["id"])
    if customer:
        print(f"Converted lead to customer: {customer['id']} - {customer['email']}")
    else:
        print("Failed to convert lead")
    print(f"Leads in memory: {len(biz.leads)}")
    print_business_status(biz, "After lead conversion")
    
    # Generate sales
    revenue = biz.generate_sales(1)
    print(f"Generated sales: {revenue}")
    print_business_status(biz, "After generate_sales(1)")
    
    # Calculate metrics
    metrics = biz.calculate_monthly_metrics(50.0)
    print(f"Monthly revenue: {metrics['monthly_revenue']}")
    print(f"Net profit: {metrics['net_profit']}")
    print_business_status(biz, "After calculate_monthly_metrics")
    
    # Run a business cycle
    print("Running business cycle with marketing_budget=200.0")
    cycle_metrics = biz.run_business_cycle(200.0)
    print(f"Cycle revenue: {cycle_metrics['monthly_revenue']}")
    print(f"Cycle profit: {cycle_metrics['net_profit']}")
    print_business_status(biz, "After run_business_cycle")
    
    # Get final status
    status = biz.get_status()
    print("Final business status:")
    print(f"  {status}")
    
    session.close()

if __name__ == "__main__":
    test_business()
