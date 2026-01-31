"""
SQLAlchemy Implementation of Accounting Adapter

Provides integration with the domain expert's accounting system
using the models and logic from the GOLD AI folder.
"""

import sys
import os
from pathlib import Path
from typing import List, Dict, Literal
from decimal import Decimal

# Add GOLD AI folder to Python path
gold_ai_path = Path(__file__).parent.parent / "GOLD AI"
sys.path.insert(0, str(gold_ai_path))

from database import SessionLocal, engine, Base
from models import Customer, BankAccount, JewelryItem, Transaction
from schemas import TransactionCreate, SellRawGoldSchema, BuyRawGoldSchema, ReceiveMoneySchema, SendMoneySchema, ReceiveRawGoldSchema, GiveRawGoldSchema, ReceiveJewelrySchema, GiveJewelrySchema
from enums import TransactionType
from sqlalchemy import func

from .base import AccountingAdapter


class SqlAlchemyAdapter(AccountingAdapter):
    """
    SQLAlchemy adapter that integrates with the domain expert's accounting system.
    
    This adapter uses the models and business logic defined in the GOLD AI folder
    to provide real database persistence for transactions.
    """
    
    def __init__(self, gold_price_per_gram: float = 10_000_000):
        """
        Initialize the adapter with a default gold price.
        
        Args:
            gold_price_per_gram: Default gold price in Rial per gram
        """
        # Create tables if they don't exist
        Base.metadata.create_all(bind=engine)
        self._gold_price = gold_price_per_gram
    
    def _get_db(self):
        """Get a database session."""
        db = SessionLocal()
        try:
            return db
        except:
            db.close()
            raise
    
    def _calculate_customer_balance(self, db, customer_id: int) -> Dict:
        """Calculate customer balance from transactions."""
        row = (
            db.query(
                func.coalesce(func.sum(Transaction.money_amount), 0).label("money_sum"),
                func.coalesce(func.sum(Transaction.gold_amount_grams), 0).label("gold_sum"),
            )
            .filter(Transaction.customer_id == customer_id)
            .one()
        )
        
        customer = db.query(Customer).filter(Customer.customer_id == customer_id).first()
        if not customer:
            return {"rial": 0, "gold_gr": 0, "usd": 0}
        
        money_balance = float(customer.initial_money_balance) + float(row.money_sum or 0)
        gold_balance = float(customer.initial_gold_balance_grams) + float(row.gold_sum or 0)
        
        return {
            "rial": money_balance,
            "gold_gr": gold_balance,
            "usd": 0  # Not currently tracked
        }

    def get_accounts(self, account_type: Literal['customer', 'collaborator', 'all']) -> List[Dict]:
        """
        Returns the list of accounts filtered by type.
        
        Note: The domain expert's system uses 'Customer' for all accounts.
        We distinguish between customers and collaborators based on naming convention
        or initial balance characteristics.
        
        Args:
            account_type: Filter by 'customer', 'collaborator', or 'all'
        
        Returns:
            List of account dictionaries
        """
        db = self._get_db()
        try:
            customers = db.query(Customer).all()
            accounts = []
            
            for customer in customers:
                balance = self._calculate_customer_balance(db, customer.customer_id)
                
                # Determine type based on name (simple heuristic)
                # In a real system, you'd add a type field to the Customer model
                name_lower = customer.full_name.lower()
                acc_type = 'collaborator' if 'collaborator' in name_lower else 'customer'
                
                if account_type != 'all' and acc_type != account_type:
                    continue
                
                accounts.append({
                    "id": str(customer.customer_id),
                    "name": customer.full_name,
                    "type": acc_type,
                    "balance": balance
                })
            
            return accounts
        finally:
            db.close()

    def get_account_balance(self, account_id: str) -> Dict:
        """
        Returns the balance for a specific account.
        
        Args:
            account_id: The ID of the account (customer_id)
        
        Returns:
            Balance dictionary
        """
        db = self._get_db()
        try:
            customer_id = int(account_id)
            return self._calculate_customer_balance(db, customer_id)
        finally:
            db.close()

    def get_live_gold_price(self) -> float:
        """
        Returns the current gold price per gram.
        
        Returns:
            Price per gram in Rial
        """
        return self._gold_price
    
    def update_gold_price(self, new_price: float):
        """Update the gold price."""
        self._gold_price = new_price

    def execute_transaction(self, transaction_details: Dict) -> Dict:
        """
        Executes a transaction using the domain expert's logic.
        
        Args:
            transaction_details: Transaction information with structure:
            {
                "customer_id": int,
                "transaction_type": str (TransactionType value),
                "details": dict (specific schema based on transaction_type),
                "notes": str (optional)
            }
        
        Returns:
            Transaction result with status and ID
        """
        db = self._get_db()
        try:
            # Extract transaction data
            customer_id = transaction_details.get("customer_id")
            tx_type_str = transaction_details.get("transaction_type")
            details = transaction_details.get("details", {})
            notes = transaction_details.get("notes")
            
            # Validate customer exists
            customer = db.query(Customer).filter(Customer.customer_id == customer_id).first()
            if not customer:
                return {
                    "status": "error",
                    "message": f"Customer with ID {customer_id} not found"
                }
            
            # Parse transaction type
            try:
                tx_type = TransactionType(tx_type_str)
            except ValueError:
                return {
                    "status": "error",
                    "message": f"Invalid transaction type: {tx_type_str}"
                }
            
            # Helper function to convert to Decimal
            def _d(v) -> Decimal:
                return Decimal(str(v))
            
            # Initialize transaction fields
            money_amount = Decimal("0")
            gold_amount_grams = Decimal("0")
            bank_account_id = None
            item_id = None
            price = None
            weight_grams = None
            purity = None
            
            # Process based on transaction type (logic from GOLD AI/routers/transactions.py)
            if tx_type == TransactionType.SELL_RAW_GOLD:
                money_amount = _d(details.get("price", 0))
                gold_amount_grams = -_d(details.get("weight_grams", 0))
                weight_grams = _d(details.get("weight_grams", 0))
                purity = _d(details.get("purity", 0))
                price = _d(details.get("price", 0))
            
            elif tx_type == TransactionType.BUY_RAW_GOLD:
                money_amount = -_d(details.get("price", 0))
                gold_amount_grams = _d(details.get("weight_grams", 0))
                weight_grams = _d(details.get("weight_grams", 0))
                purity = _d(details.get("purity", 0))
                price = _d(details.get("price", 0))
            
            elif tx_type == TransactionType.RECEIVE_MONEY:
                bank_acc_id = details.get("bank_account_id")
                bank = db.query(BankAccount).filter(BankAccount.account_id == bank_acc_id).first()
                if not bank:
                    return {
                        "status": "error",
                        "message": f"Bank account with ID {bank_acc_id} not found"
                    }
                money_amount = _d(details.get("amount", 0))
                bank_account_id = bank_acc_id
            
            elif tx_type == TransactionType.SEND_MONEY:
                bank_acc_id = details.get("bank_account_id")
                bank = db.query(BankAccount).filter(BankAccount.account_id == bank_acc_id).first()
                if not bank:
                    return {
                        "status": "error",
                        "message": f"Bank account with ID {bank_acc_id} not found"
                    }
                money_amount = -_d(details.get("amount", 0))
                bank_account_id = bank_acc_id
            
            elif tx_type == TransactionType.RECEIVE_RAW_GOLD:
                gold_amount_grams = _d(details.get("weight_grams", 0))
                weight_grams = _d(details.get("weight_grams", 0))
                purity = _d(details.get("purity", 0))
            
            elif tx_type == TransactionType.GIVE_RAW_GOLD:
                gold_amount_grams = -_d(details.get("weight_grams", 0))
                weight_grams = _d(details.get("weight_grams", 0))
                purity = _d(details.get("purity", 0))
            
            elif tx_type == TransactionType.RECEIVE_JEWELRY:
                jewelry_code = details.get("jewelry_code")
                jewelry = db.query(JewelryItem).filter(JewelryItem.jewelry_code == jewelry_code).first()
                if not jewelry:
                    return {
                        "status": "error",
                        "message": f"Jewelry with code '{jewelry_code}' not found"
                    }
                pure_gold = float(jewelry.weight_grams) * float(jewelry.purity)
                gold_amount_grams = _d(pure_gold)
                item_id = jewelry.jewelry_id
                jewelry.status = "In Stock (Consignment)"
            
            elif tx_type == TransactionType.GIVE_JEWELRY:
                jewelry_code = details.get("jewelry_code")
                jewelry = db.query(JewelryItem).filter(JewelryItem.jewelry_code == jewelry_code).first()
                if not jewelry:
                    return {
                        "status": "error",
                        "message": f"Jewelry with code '{jewelry_code}' not found"
                    }
                pure_gold = float(jewelry.weight_grams) * float(jewelry.purity)
                gold_amount_grams = -_d(pure_gold)
                item_id = jewelry.jewelry_id
            
            # Create and save transaction
            tx = Transaction(
                customer_id=customer_id,
                transaction_type=tx_type.value,
                item_id=item_id,
                bank_account_id=bank_account_id,
                price=price,
                weight_grams=weight_grams,
                purity=purity,
                money_amount=money_amount,
                gold_amount_grams=gold_amount_grams,
                notes=notes,
            )
            
            db.add(tx)
            db.commit()
            db.refresh(tx)
            
            return {
                "status": "success",
                "transaction_id": str(tx.transaction_id),
                "message": f"Transaction executed successfully"
            }
            
        except Exception as e:
            db.rollback()
            return {
                "status": "error",
                "message": f"Failed to execute transaction: {str(e)}"
            }
        finally:
            db.close()
