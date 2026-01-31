from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import APIRouter, Depends, HTTPException

from database import get_db
from models import Customer, Transaction, JewelryItem
from schemas import (
    CustomerCreate,
    CustomerResponse,
    TransactionResponse,
    RawGoldBalanceByPurityItem,
    JewelryBalanceItem,
)
from enums import TransactionType

router = APIRouter()


def _customer_balances(db: Session, customer_id: int):
    row = (
        db.query(
            func.coalesce(func.sum(Transaction.money_amount), 0).label("money_sum"),
            func.coalesce(func.sum(Transaction.gold_amount_grams), 0).label("gold_sum"),
        )
        .filter(Transaction.customer_id == customer_id)
        .one()
    )
    return Decimal(str(row.money_sum)), Decimal(str(row.gold_sum))


def _customer_response(c: Customer, db: Session) -> CustomerResponse:
    money_sum, gold_sum = _customer_balances(db, c.customer_id)
    return CustomerResponse(
        customer_id=c.customer_id,
        full_name=c.full_name,
        phone_number=c.phone_number,
        initial_money_balance=c.initial_money_balance,
        initial_gold_balance_grams=c.initial_gold_balance_grams,
        money_balance=c.initial_money_balance + money_sum,
        gold_balance_grams=c.initial_gold_balance_grams + gold_sum,
    )


@router.post("", response_model=CustomerResponse)
def create_customer(
    payload: CustomerCreate,
    db: Session = Depends(get_db),
):
    customer = Customer(
        full_name=payload.full_name,
        phone_number=payload.phone_number,
        initial_money_balance=payload.initial_money_balance,
        initial_gold_balance_grams=payload.initial_gold_balance_grams,
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return _customer_response(customer, db)


@router.get("", response_model=list[CustomerResponse])
def list_customers(db: Session = Depends(get_db)):
    customers = db.query(Customer).all()
    return [_customer_response(c, db) for c in customers]


@router.get("/{customer_id}", response_model=CustomerResponse)
def get_customer(
    customer_id: int,
    db: Session = Depends(get_db),
):
    customer = db.query(Customer).filter(Customer.customer_id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return _customer_response(customer, db)


@router.get("/{customer_id}/transactions", response_model=list[TransactionResponse])
def get_customer_transactions(
    customer_id: int,
    db: Session = Depends(get_db),
):
    customer = db.query(Customer).filter(Customer.customer_id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    transactions = (
        db.query(Transaction)
        .filter(Transaction.customer_id == customer_id)
        .order_by(Transaction.transaction_date.asc())
        .all()
    )
    return [TransactionResponse.model_validate(t) for t in transactions]


RAW_GOLD_TYPES = {
    TransactionType.SELL_RAW_GOLD.value,
    TransactionType.BUY_RAW_GOLD.value,
    TransactionType.RECEIVE_RAW_GOLD.value,
    TransactionType.GIVE_RAW_GOLD.value,
}


@router.get(
    "/{customer_id}/balance/raw-gold-by-purity",
    response_model=list[RawGoldBalanceByPurityItem],
)
def get_customer_balance_raw_gold_by_purity(
    customer_id: int,
    db: Session = Depends(get_db),
):
    customer = db.query(Customer).filter(Customer.customer_id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    rows = (
        db.query(Transaction.purity, func.sum(Transaction.gold_amount_grams).label("net_gold_grams"))
        .filter(
            Transaction.customer_id == customer_id,
            Transaction.transaction_type.in_(RAW_GOLD_TYPES),
            Transaction.purity.isnot(None),
        )
        .group_by(Transaction.purity)
        .all()
    )
    return [
        RawGoldBalanceByPurityItem(purity=Decimal(str(r.purity)), net_gold_grams=Decimal(str(r.net_gold_grams or 0)))
        for r in rows
    ]


JEWELRY_TYPES = {
    TransactionType.RECEIVE_JEWELRY.value,
    TransactionType.GIVE_JEWELRY.value,
}


@router.get(
    "/{customer_id}/balance/jewelry",
    response_model=list[JewelryBalanceItem],
)
def get_customer_balance_jewelry(
    customer_id: int,
    db: Session = Depends(get_db),
):
    customer = db.query(Customer).filter(Customer.customer_id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    rows = (
        db.query(Transaction.item_id, func.sum(Transaction.gold_amount_grams).label("net_gold"))
        .filter(
            Transaction.customer_id == customer_id,
            Transaction.transaction_type.in_(JEWELRY_TYPES),
            Transaction.item_id.isnot(None),
        )
        .group_by(Transaction.item_id)
        .all()
    )
    result = []
    for r in rows:
        jewelry = db.query(JewelryItem).filter(JewelryItem.jewelry_id == r.item_id).first()
        code = jewelry.jewelry_code if jewelry else str(r.item_id)
        net = Decimal(str(r.net_gold or 0))
        status = "Held by us" if net > 0 else ("With customer" if net < 0 else "Settled")
        result.append(JewelryBalanceItem(jewelry_code=code, status=status))
    return result
