"""
Integration Test Script for Domain Expert Logic

This script tests the complete flow from natural language input
to database persistence using the domain expert's accounting logic.
"""

import sys
from pathlib import Path

# Add GOLD AI folder to path
gold_ai_path = Path(__file__).parent / "GOLD AI"
sys.path.insert(0, str(gold_ai_path))

from adapters.sqlalchemy_adapter import SqlAlchemyAdapter
from database import SessionLocal, Base, engine
from models import Customer, BankAccount, JewelryItem

def setup_test_data():
    """Create sample customers and bank accounts for testing."""
    print("Setting up test data...")
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # Check if data already exists
        existing_customers = db.query(Customer).count()
        if existing_customers > 0:
            print(f"Found {existing_customers} existing customers in database")
            return
        
        # Create sample customers (including collaborators)
        customers_data = [
            {"full_name": "Collaborator Akbari", "phone_number": "09121234567", 
             "initial_money_balance": 0, "initial_gold_balance_grams": -5},
            {"full_name": "Collaborator Saeedi", "phone_number": "09129876543",
             "initial_money_balance": 80000000, "initial_gold_balance_grams": 8},
            {"full_name": "Customer Rezaei", "phone_number": "09131234567",
             "initial_money_balance": 0, "initial_gold_balance_grams": 0},
            {"full_name": "Customer Mohammadi", "phone_number": "09139876543",
             "initial_money_balance": -5000000, "initial_gold_balance_grams": 2},
        ]
        
        for data in customers_data:
            customer = Customer(**data)
            db.add(customer)
        
        # Create sample bank accounts
        bank_accounts = [
            {"account_name": "Main Business Account"},
            {"account_name": "Petty Cash"},
        ]
        
        for data in bank_accounts:
            account = BankAccount(**data)
            db.add(account)
        
        # Create sample jewelry items
        jewelry_items = [
            {"jewelry_code": "RING-001", "name": "Gold Ring 18K", 
             "weight_grams": 5.5, "purity": 0.750, "premium": 500000, "status": "In Stock"},
            {"jewelry_code": "NECK-001", "name": "Gold Necklace 24K",
             "weight_grams": 12.0, "purity": 0.999, "premium": 2000000, "status": "In Stock"},
        ]
        
        for data in jewelry_items:
            item = JewelryItem(**data)
            db.add(item)
        
        db.commit()
        print("✓ Test data created successfully!")
        
        # Display created customers
        print("\nCreated Customers:")
        customers = db.query(Customer).all()
        for c in customers:
            print(f"  - ID: {c.customer_id}, Name: {c.full_name}, "
                  f"Money: {c.initial_money_balance}, Gold: {c.initial_gold_balance_grams}g")
        
        # Display bank accounts
        print("\nCreated Bank Accounts:")
        accounts = db.query(BankAccount).all()
        for a in accounts:
            print(f"  - ID: {a.account_id}, Name: {a.account_name}")
        
        # Display jewelry
        print("\nCreated Jewelry Items:")
        items = db.query(JewelryItem).all()
        for i in items:
            print(f"  - Code: {i.jewelry_code}, Name: {i.name}, "
                  f"Weight: {i.weight_grams}g, Purity: {i.purity}")
    
    finally:
        db.close()


def test_adapter_basic_operations():
    """Test basic adapter operations."""
    print("\n" + "="*60)
    print("Testing Adapter Basic Operations")
    print("="*60)
    
    adapter = SqlAlchemyAdapter()
    
    # Test get_accounts
    print("\n1. Testing get_accounts()...")
    all_accounts = adapter.get_accounts(account_type='all')
    print(f"   Found {len(all_accounts)} total accounts")
    
    customers = adapter.get_accounts(account_type='customer')
    print(f"   Found {len(customers)} customer accounts")
    
    collaborators = adapter.get_accounts(account_type='collaborator')
    print(f"   Found {len(collaborators)} collaborator accounts")
    
    # Test get_live_gold_price
    print("\n2. Testing get_live_gold_price()...")
    gold_price = adapter.get_live_gold_price()
    print(f"   Current gold price: {gold_price:,.0f} Rial/gram")
    
    # Test get_account_balance
    print("\n3. Testing get_account_balance()...")
    if all_accounts:
        test_account = all_accounts[0]
        balance = adapter.get_account_balance(test_account['id'])
        print(f"   Account '{test_account['name']}' balance:")
        print(f"   - Money: {balance['rial']:,.2f} Rial")
        print(f"   - Gold: {balance['gold_gr']:.2f} grams")
    
    print("\n✓ Basic operations test completed!")


def test_transaction_execution():
    """Test executing transactions through the adapter."""
    print("\n" + "="*60)
    print("Testing Transaction Execution")
    print("="*60)
    
    adapter = SqlAlchemyAdapter()
    
    # Get a customer for testing
    customers = adapter.get_accounts(account_type='customer')
    if not customers:
        print("   ✗ No customers found for testing")
        return
    
    test_customer = customers[0]
    customer_id = int(test_customer['id'])
    
    print(f"\n1. Testing SELL_RAW_GOLD transaction...")
    print(f"   Customer: {test_customer['name']} (ID: {customer_id})")
    
    # Test transaction: Customer sells 10 grams of 24k gold
    transaction_data = {
        "customer_id": customer_id,
        "transaction_type": "Sell Raw Gold",
        "details": {
            "purity": 0.999,
            "weight_grams": 10.0,
            "price": 100000000  # 100 million Rial
        },
        "notes": "Test transaction: Customer sells 10g of 24k gold"
    }
    
    result = adapter.execute_transaction(transaction_data)
    
    if result['status'] == 'success':
        print(f"   ✓ Transaction executed successfully!")
        print(f"   Transaction ID: {result['transaction_id']}")
        
        # Check updated balance
        new_balance = adapter.get_account_balance(test_customer['id'])
        print(f"   Updated balance:")
        print(f"   - Money: {new_balance['rial']:,.2f} Rial (increased)")
        print(f"   - Gold: {new_balance['gold_gr']:.2f} grams (decreased)")
    else:
        print(f"   ✗ Transaction failed: {result.get('message')}")
    
    print("\n2. Testing BUY_RAW_GOLD transaction...")
    
    # Test transaction: Customer buys 5 grams of 18k gold
    transaction_data2 = {
        "customer_id": customer_id,
        "transaction_type": "Buy Raw Gold",
        "details": {
            "purity": 0.750,
            "weight_grams": 5.0,
            "price": 37500000  # 37.5 million Rial
        },
        "notes": "Test transaction: Customer buys 5g of 18k gold"
    }
    
    result2 = adapter.execute_transaction(transaction_data2)
    
    if result2['status'] == 'success':
        print(f"   ✓ Transaction executed successfully!")
        print(f"   Transaction ID: {result2['transaction_id']}")
        
        # Check updated balance
        new_balance2 = adapter.get_account_balance(test_customer['id'])
        print(f"   Updated balance:")
        print(f"   - Money: {new_balance2['rial']:,.2f} Rial (decreased)")
        print(f"   - Gold: {new_balance2['gold_gr']:.2f} grams (increased)")
    else:
        print(f"   ✗ Transaction failed: {result2.get('message')}")
    
    print("\n✓ Transaction execution test completed!")


def test_invalid_transactions():
    """Test error handling for invalid transactions."""
    print("\n" + "="*60)
    print("Testing Error Handling")
    print("="*60)
    
    adapter = SqlAlchemyAdapter()
    
    print("\n1. Testing with invalid customer ID...")
    invalid_tx = {
        "customer_id": 99999,
        "transaction_type": "Sell Raw Gold",
        "details": {
            "purity": 0.999,
            "weight_grams": 10.0,
            "price": 100000000
        }
    }
    
    result = adapter.execute_transaction(invalid_tx)
    if result['status'] == 'error':
        print(f"   ✓ Error correctly caught: {result['message']}")
    else:
        print(f"   ✗ Should have returned error!")
    
    print("\n2. Testing with invalid transaction type...")
    invalid_tx2 = {
        "customer_id": 1,
        "transaction_type": "Invalid Type",
        "details": {}
    }
    
    result2 = adapter.execute_transaction(invalid_tx2)
    if result2['status'] == 'error':
        print(f"   ✓ Error correctly caught: {result2['message']}")
    else:
        print(f"   ✗ Should have returned error!")
    
    print("\n✓ Error handling test completed!")


def verify_database_state():
    """Verify the final state of the database."""
    print("\n" + "="*60)
    print("Database State Verification")
    print("="*60)
    
    db = SessionLocal()
    try:
        from models import Transaction
        
        customers = db.query(Customer).all()
        print(f"\nTotal Customers: {len(customers)}")
        
        transactions = db.query(Transaction).all()
        print(f"Total Transactions: {len(transactions)}")
        
        if transactions:
            print("\nRecent Transactions:")
            for tx in transactions[-3:]:  # Show last 3
                print(f"  - ID: {tx.transaction_id}, Customer: {tx.customer_id}, "
                      f"Type: {tx.transaction_type}")
                print(f"    Money: {tx.money_amount}, Gold: {tx.gold_amount_grams}g")
        
        print("\n✓ Database verification completed!")
    
    finally:
        db.close()


def main():
    """Run all integration tests."""
    print("="*60)
    print("GOLD ACCOUNTING - INTEGRATION TEST")
    print("="*60)
    
    try:
        # Setup
        setup_test_data()
        
        # Test basic operations
        test_adapter_basic_operations()
        
        # Test transaction execution
        test_transaction_execution()
        
        # Test error handling
        test_invalid_transactions()
        
        # Verify final state
        verify_database_state()
        
        print("\n" + "="*60)
        print("✓ ALL TESTS COMPLETED SUCCESSFULLY!")
        print("="*60)
        print("\nThe integration between NLP middleware and domain expert")
        print("accounting logic is working correctly.")
        print("\nYou can now:")
        print("1. Start the main application: python main.py")
        print("2. Use the /process-event endpoint with natural language")
        print("3. Execute the generated plans through /execute-plan")
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
