#!/usr/bin/env python3
"""
Fixed final execution test
"""
import sys
sys.path.insert(0, '/home/genesis/opt/genesis/HYDRA/src')

from src import Business
from src.hydra.controller.treasury import TreasuryController
from datetime import datetime

def main():
    print("=" * 70)
    print("HYDRA MVP FINAL EXECUTION TEST")
    print("=" * 70)
    print(f"Testing the complete MVP implementation (Días 15-30)")
    print()
    
    # Initialize controllers
    treasury = TreasuryController()
    
    # Test 1: Create HYDRAs
    print("1. === CREANDO HYDRAS FUNDADORAS ===")
    businesses = {}
    for hydra_type in ['financial', 'design', 'trading']:
        business = Business(hydra_type)
        businesses[hydra_type] = business
        print(f"   ✓ {hydra_type.upper()}: {business.business_id}")
        print(f"     Product: {business.product_name}")
        print(f"     Price: ${business.pricing}/mes")
    
    print()
    
    # Test 2: Setup LinkedIn Ads campaigns
    print("2. === CONFIGURANDO CAMPANAS DE LINKEDIN ADS ===")
    
    from src.marketing import MarketingAgent
    from src.sales import SalesAgent
    
    for hydra_type, business in businesses.items():
        marketing = MarketingAgent(hydra_type, 500.0)
        campaign = marketing.run_campaign('LinkedIn', 300.0)
        if campaign:
            print(f"   ✓ {hydra_type.upper()} LinkedIn Ads: {campaign['leads_generated']} leads")
        
        sales_agent = SalesAgent(hydra_type, business.pricing, business.business_id)
        leads = sales_agent.generate_leads(30, "LinkedIn Ads")
        business.leads = leads
        print(f"   ✓ {hydra_type.upper()} leads: {len(leads)}")
    
    print()
    
    # Test 3: Execute sales funnel
    print("3. === EJECUTANDO FUNNEL DE VENTAS ===")
    
    total_customers_converted = 0
    total_revenue = 0
    total_costs = 0
    
    for hydra_type, business in businesses.items():
        sales_agent = SalesAgent(business.business_type, business.pricing, business.business_id)
        
        # Convert qualified leads
        qualified_leads = [l for l in business.leads if l['email'].count('@') == 1 and '.' in l['email'].split('@')[1]]
        customers_converted = min(2, len(qualified_leads))
        
        for i in range(customers_converted):
            lead = qualified_leads[i]
            customer = sales_agent.convert_lead(lead['id'])
            
            if customer:
                print(f"   ✓ {hydra_type.upper()} Customer: {customer['email']} -> ${customer['price']}/mes")
        
        # Generate sales
        marketing_cost = 300.0
        revenue = business.generate_sales(customers_converted)
        
        total_customers_converted += customers_converted
        total_revenue += revenue
        total_costs += marketing_cost
        
        print(f"   ✓ {hydra_type.upper()}: {customers_converted} customers, ${revenue} revenue, ${business.calculate_monthly_metrics()['net_profit']} profit")
    
    print()
    
    # Test 4: Register transactions in Treasury
    print("4. === REGISTRANDO TRANSACCIONES EN TRESORERÍA ===")
    
    for hydra_type, business in businesses.items():
        metrics = business.calculate_monthly_metrics()
        treasury.record_transaction(hydra_type, metrics['monthly_revenue'])
        
        is_valid = treasury.validate_profit(hydra_type, metrics['net_profit'])
        print(f"   ✓ {hydra_type.upper()}: ${metrics['monthly_revenue']} revenue, profit validation: {'VALID' if is_valid else 'INVALID'}")
    
    print()
    
    # Test 5: System summary
    print("5. === RESUMEN DEL SISTEMA ===")
    
    total_profit = sum(b.calculate_monthly_metrics()['net_profit'] for b in businesses.values())
    profitable_count = sum(1 for b in businesses.values() if b.calculate_monthly_metrics()['can_reproduce'])
    
    print(f"   🎯 KPIs Generales:")
    print(f"     - Total customers converted: {total_customers_converted}")
    print(f"     - Total revenue: ${total_revenue}")
    print(f"     - Total costs: ${total_costs}")
    print(f"     - Total profit: ${total_profit}")
    print(f"     - HYDRAs rentables: {profitable_count}/{len(businesses)}")
    
    # Check for reproduction
    if total_profit >= 50:
        print(f"\n🎉 ÉXITO: $50+ profit achieved!")
        print(f"✅ Sistema listo para escalamiento")
    else:
        print(f"\n⚠️  OBJETIVO DE $50 NO ALCANZADO")
        print(f"   Profit actual: ${total_profit} (objetivo: $50)")
    
    print()
    print("=" * 70)
    print("MVP EXECUTION COMPLETED")
    print("=" * 70)

if __name__ == "__main__":
    main()
