from datetime import datetime
from decimal import Decimal
from sqlalchemy import (
    Column, Integer, String, Numeric, DateTime, Text, ForeignKey,
)
from sqlalchemy.orm import relationship

from database import Base


class BankAccount(Base):
    __tablename__ = "bank_accounts"

    account_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    account_name = Column(String(255), nullable=False)

    transactions = relationship("Transaction", back_populates="bank_account")


class Customer(Base):
    __tablename__ = "customers"

    customer_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    full_name = Column(String(255), nullable=False)
    phone_number = Column(String(50), nullable=True)
    initial_money_balance = Column(Numeric(20, 4), default=Decimal("0"), nullable=False)
    initial_gold_balance_grams = Column(Numeric(20, 4), default=Decimal("0"), nullable=False)

    transactions = relationship("Transaction", back_populates="customer")


class StandardItem(Base):
    __tablename__ = "standard_items"

    item_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    weight_grams = Column(Numeric(20, 4), nullable=False)
    purity = Column(Numeric(10, 4), nullable=False)


class JewelryItem(Base):
    __tablename__ = "jewelry_items"

    jewelry_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    jewelry_code = Column(String(100), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    weight_grams = Column(Numeric(20, 4), nullable=False)
    purity = Column(Numeric(10, 4), nullable=False)
    premium = Column(Numeric(20, 4), nullable=False)
    status = Column(String(50), default="In Stock", nullable=False)


class Transaction(Base):
    __tablename__ = "transactions"

    transaction_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey("customers.customer_id"), nullable=False)
    transaction_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    transaction_type = Column(String(100), nullable=False)
    item_type = Column(String(50), nullable=True)
    item_id = Column(Integer, nullable=True)
    bank_account_id = Column(Integer, ForeignKey("bank_accounts.account_id"), nullable=True)
    price = Column(Numeric(20, 4), nullable=True)
    weight_grams = Column(Numeric(20, 4), nullable=True)
    purity = Column(Numeric(10, 4), nullable=True)
    money_amount = Column(Numeric(20, 4), nullable=True)
    gold_amount_grams = Column(Numeric(20, 4), nullable=True)
    notes = Column(Text, nullable=True)

    customer = relationship("Customer", back_populates="transactions")
    bank_account = relationship("BankAccount", back_populates="transactions")
