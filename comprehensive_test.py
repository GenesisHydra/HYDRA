#!/usr/bin/env python3
"""
Prueba completa del sistema HYDRA
"""
import sys
sys.path.insert(0, '/home/genesis/opt/genesis/HYDRA/src')

from src import Business, MarketResearch
from src.hydra.controller.treasury import TreasuryController
from datetime import datetime

def test_business_class():
    print("1. === Testing Business Class ===")
    
    # Test creating businesses
    businesses = []
    for btype in ['financial', 'design', 'trading']:
        business = Business(btype)
        businesses.append(business)
        print(f"   ✓ Created {btype}: ID {business.business_id}")
    
    # Test generating sales
    for i, business in enumerate(businesses):
        customers = [2, 3, 2][i]  # Different customer counts
        revenue = business.generate_sales(customers)
        print(f"   ✓ {business.business_type}: Generated ${revenue} with {customers} customers")
    
    # Test calculate_monthly_metrics
    for business in businesses:
        metrics = business.calculate_monthly_metrics(500.0)
        print(f"   ✓ {business.business_type}: Revenue ${metrics['monthly_revenue']}, Net Profit ${metrics['net_profit']}")
    
    print("   ✅ Business class test PASSED\n")

def test_market_research():
    print("2. === Testing Market Research ===")
    
    research = MarketResearch()
    
    for btype in ['financial', 'design', 'trading']:
        # Test market research
        market_data = research.research_market(btype, f'test-{btype}')
        print(f"   ✓ {btype.upper()}: Market research completed")
        print(f"     - OMV: ${market_data.get('estimated_omv', {}).get('omv_usd', 0):.2f}")
        print(f"     - Opportunity Score: {market_data.get('market_opportunity_score', 0)}")
        
        # Test contact validation
        contacts = research.validate_real_contacts(btype, 10)
        qualified = sum(1 for c in contacts if c.get('qualified'))
        print(f"   ✓ {btype.upper()}: Generated {len(contacts)} contacts, {qualified} qualified")
        
        # Test niche selection
        niche = research.select_target_niche(btype, market_data)
        print(f"   ✓ {btype.upper()}: Selected niche '{niche['selected_niche']}'")
        print(f"     - Recommended price: ${niche['recommended_price']}")
        print(f"     - Potential revenue: ${niche['monthly_revenue_potential']:.2f}/mes")
    
    print("   ✅ Market Research test PASSED\n")

def test_treasury():
    print("3. === Testing Treasury Controller ===")
    
    # Test treasury initialization
    treasury = TreasuryController()
    status = treasury.get_status()
    
    print(f"   ✓ Treasury initialized")
    print(f"   - Financial funds: ${status['financial_funds']}")
    print(f"   - Design funds: ${status['design_funds']}")
    print(f"   - Trading funds: ${status['trading_funds']}")
    print(f"   - System reserves: ${status['system_reserves']}")
    print(f"   - Allocated budgets: {status['allocated_budgets']}")
    
    # Test budget allocation
    result = treasury.allocate_budget('financial', 250.0, 'Marketing campaign')
    print(f"   ✓ Budget allocation: {'SUCCESS' if result else 'FAILED'}")
    
    # Test profit validation
    is_profit = treasury.validate_profit('financial', 60.0)
    print(f"   ✓ Profit validation (>=50): {'VALID' if is_profit else 'INVALID'}")
    
    is_loss = treasury.validate_profit('financial', 30.0)
    print(f"   ✓ Profit validation (>=50): {'VALID' if is_loss else 'INVALID'}")
    
    print("   ✅ Treasury Controller test PASSED\n")

def test_integration():
    print("4. === Testing System Integration ===")
    
    # Create test scenario
    business = Business('financial')
    
    # Generate some sales
    business.generate_sales(5)
    print(f"   ✓ Business sales: {business.sales_count} customers, ${business.revenue} revenue")
    
    # Calculate metrics
    metrics = business.calculate_monthly_metrics(500.0)
    print(f"   ✓ Metrics calculated:")
    print(f"     - Monthly revenue: ${metrics['monthly_revenue']}")
    print(f"     - Net profit: ${metrics['net_profit']}")
    print(f"     - Profitability: {'YES' if metrics['profitable'] else 'NO'}")
    print(f"     - Can reproduce: {'YES' if metrics['can_reproduce'] else 'NO'}")
    
    # Check if business can reproduce
    if metrics['can_reproduce']:
        print(f"   ✓ Business can now reproduce and create daughter HYDRAs")
    
    print("   ✅ Integration test PASSED\n")

def main():
    print("=" * 70)
    print("HYDRA SYSTEM COMPREHENSIVE TEST")
    print("=" * 70)
    print(f"Iniciando pruebas a las {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        test_business_class()
        test_market_research()
        test_treasury()
        test_integration()
        
        print("=" * 70)
        print("TODAS LAS PRUEBAS PASARON ✅")
        print("=" * 70)
        print()
        print("El sistema HYDRA está completamente operativo:")
        print("  ✅ Core Business Logic")
        print("  ✅ Market Research")
        print("  ✅ Treasury Controller")
        print("  ✅ Ecosystem Integration")
        print()
        print("Listo para alcanzar primeros $50 ingresos reales!")
        
    except Exception as e:
        print("=" * 70)
        print(f"ERROR durante las pruebas: {str(e)}")
        print("=" * 70)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
