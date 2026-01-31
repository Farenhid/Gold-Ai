"""
Abstract Base Class for Accounting System Adapters

Defines the interface that all accounting system adapters must implement.
This allows the middleware to work with different accounting systems
without changing the core business logic.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Literal


class AccountingAdapter(ABC):
    """
    Abstract base class for accounting system adapters.
    
    All methods in this class must be implemented by concrete adapters
    to provide integration with specific accounting systems.
    """
    
    @abstractmethod
    def get_accounts(self, account_type: Literal['customer', 'collaborator', 'all']) -> List[Dict]:
        """
        Returns the list of accounts filtered by type.
        
        Args:
            account_type: Type of accounts to retrieve
                - 'customer': Only customer accounts
                - 'collaborator': Only collaborator accounts
                - 'all': All accounts
        
        Returns:
            List of account dictionaries with structure:
            {
                "id": str,
                "name": str,
                "type": "customer" | "collaborator",
                "balance": {
                    "rial": float,
                    "gold_gr": float,
                    "usd": float
                }
            }
        """
        pass

    @abstractmethod
    def get_account_balance(self, account_id: str) -> Dict:
        """
        Returns the account balance of a specific person.
        
        Args:
            account_id: Unique identifier of the account
        
        Returns:
            Dictionary with balance in different currencies:
            {
                "rial": float,
                "gold_gr": float,  # grams of gold
                "usd": float
            }
        """
        pass

    @abstractmethod
    def get_live_gold_price(self) -> float:
        """
        Returns the current live price per gram of raw gold.
        
        Returns:
            Price per gram in Rial
        """
        pass

    @abstractmethod
    def execute_transaction(self, transaction_details: Dict) -> Dict:
        """
        Executes a single transaction in the accounting system.
        
        Args:
            transaction_details: Dictionary containing transaction information:
            {
                "action": str,  # Type of transaction
                "from_account": str (optional),
                "to_account": str (optional),
                "amount": float,
                "currency": "gold_gr" | "rial" | "usd",
                "description": str
            }
        
        Returns:
            Dictionary with transaction result:
            {
                "status": "success" | "error",
                "transaction_id": str (optional),
                "message": str (optional)
            }
        """
        pass
