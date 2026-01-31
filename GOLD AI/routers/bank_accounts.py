from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import APIRouter, Depends, HTTPException

from database import get_db
from models import BankAccount, Transaction
from schemas import BankAccountCreate, BankAccountResponse

router = APIRouter()


def _balance_for_account(db: Session, account_id: int) -> Decimal:
    result = (
        db.query(func.coalesce(func.sum(Transaction.money_amount), 0))
        .filter(Transaction.bank_account_id == account_id)
        .scalar()
    )
    return Decimal(str(result)) if result is not None else Decimal("0")


@router.post("", response_model=BankAccountResponse)
def create_bank_account(
    payload: BankAccountCreate,
    db: Session = Depends(get_db),
):
    account = BankAccount(account_name=payload.account_name)
    db.add(account)
    db.commit()
    db.refresh(account)
    balance = _balance_for_account(db, account.account_id)
    return BankAccountResponse(
        account_id=account.account_id,
        account_name=account.account_name,
        balance=balance,
    )


@router.get("", response_model=list[BankAccountResponse])
def list_bank_accounts(db: Session = Depends(get_db)):
    accounts = db.query(BankAccount).all()
    return [
        BankAccountResponse(
            account_id=a.account_id,
            account_name=a.account_name,
            balance=_balance_for_account(db, a.account_id),
        )
        for a in accounts
    ]
