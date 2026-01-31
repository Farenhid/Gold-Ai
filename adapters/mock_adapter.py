"""
Mock Implementation of Accounting Adapter

Provides a mock accounting system for development and testing purposes.
This adapter simulates an accounting system with in-memory data.
"""

from .base import AccountingAdapter
from typing import List, Dict, Literal
import uuid


class MockAccountingAdapter(AccountingAdapter):
    """
    Mock adapter that simulates an accounting system with fake data.
    
    This is useful for development and testing without connecting
    to a real accounting system.
    """
    
    def __init__(self):
        """Initialize the mock adapter with sample accounts and data."""
        self._accounts = {
            "c1": {
                "id": "c1",
                "name": "Collaborator Akbari",
                "type": "collaborator",
                "balance": {
                    "rial": 0,
                    "gold_gr": -5,  # Owes 5 grams of gold
                    "usd": 0
                }
            },
            "c2": {
                "id": "c2",
                "name": "Collaborator Saeedi",
                "type": "collaborator",
                "balance": {
                    "rial": 80_000_000,  # Has 80 million Toman
                    "gold_gr": 8,
                    "usd": 0
                }
            },
            "u1": {
                "id": "u1",
                "name": "Customer Rezaei",
                "type": "customer",
                "balance": {
                    "rial": 0,
                    "gold_gr": 0,
                    "usd": 0
                }
            },
            "u2": {
                "id": "u2",
                "name": "Customer Mohammadi",
                "type": "customer",
                "balance": {
                    "rial": -5_000_000,  # Owes 5 million Toman
                    "gold_gr": 2,
                    "usd": 0
                }
            }
        }
        self._gold_price = 10_000_000  # 10 million Toman per gram
        self._transaction_log = []

    def get_accounts(self, account_type: Literal['customer', 'collaborator', 'all']) -> List[Dict]:
        """
        Returns the list of accounts filtered by type.
        
        Args:
            account_type: Filter by 'customer', 'collaborator', or 'all'
        
        Returns:
            List of account dictionaries
        """
        if account_type == 'all':
            return list(self._accounts.values())
        return [acc for acc in self._accounts.values() if acc['type'] == account_type]

    def get_account_balance(self, account_id: str) -> Dict:
        """
        Returns the balance for a specific account.
        
        Args:
            account_id: The ID of the account
        
        Returns:
            Balance dictionary or empty dict if not found
        """
        account = self._accounts.get(account_id)
        if account:
            return account.get("balance", {})
        return {}

    def get_live_gold_price(self) -> float:
        """
        Returns the current gold price per gram.
        
        Returns:
            Price per gram in Rial
        """
        return self._gold_price

    def execute_transaction(self, transaction_details: Dict) -> Dict:
        """
        Executes a transaction and logs it.
        
        In a real implementation, this would update the accounting system.
        For the mock, we just log the transaction and return success.
        
        Args:
            transaction_details: Transaction information
        
        Returns:
            Transaction result with status and ID
        """
        # Generate a unique transaction ID
        transaction_id = str(uuid.uuid4())
        
        # Log the transaction
        transaction_record = {
            "transaction_id": transaction_id,
            **transaction_details
        }
        self._transaction_log.append(transaction_record)
        
        # In a real implementation, this would update account balances
        # For now, we just simulate the transaction
        print(f"[MOCK ADAPTER] Transaction executed: {transaction_details}")
        
        return {
            "status": "success",
            "transaction_id": transaction_id,
            "message": f"Transaction executed successfully"
        }
    
    def get_transaction_log(self) -> List[Dict]:
        """
        Returns the log of all executed transactions.
        
        This is a helper method specific to the mock adapter
        for debugging and testing purposes.
        
        Returns:
            List of all transactions
        """
        return self._transaction_log
    
    def update_gold_price(self, new_price: float):
        """
        Updates the gold price.
        
        This is a helper method specific to the mock adapter
        for testing purposes.
        
        Args:
            new_price: New price per gram in Rial
        """
        self._gold_price = new_price
        print(f"[MOCK ADAPTER] Gold price updated to: {new_price} Rial/gram")
