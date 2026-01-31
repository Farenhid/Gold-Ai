from decimal import Decimal
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException

from database import get_db
from models import Transaction, Customer, BankAccount, JewelryItem
from schemas import (
    TransactionCreate,
    TransactionResponse,
    SellRawGoldSchema,
    BuyRawGoldSchema,
    ReceiveMoneySchema,
    SendMoneySchema,
    ReceiveRawGoldSchema,
    GiveRawGoldSchema,
    ReceiveJewelrySchema,
    GiveJewelrySchema,
)
from enums import TransactionType

router = APIRouter()


def _d(v: float) -> Decimal:
    return Decimal(str(v))


@router.post("", response_model=TransactionResponse, status_code=201)
def create_transaction(
    payload: TransactionCreate,
    db: Session = Depends(get_db),
):
    customer = db.query(Customer).filter(Customer.customer_id == payload.customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    details = payload.details
    tx_type = payload.transaction_type

    money_amount = Decimal("0")
    gold_amount_grams = Decimal("0")
    bank_account_id = None
    item_id = None
    price = None
    weight_grams = None
    purity = None

    match tx_type:
        case TransactionType.SELL_RAW_GOLD:
            d = details
            if not isinstance(d, SellRawGoldSchema):
                raise HTTPException(status_code=422, detail="Invalid details for Sell Raw Gold")
            money_amount = _d(d.price)
            gold_amount_grams = -_d(d.weight_grams)
            weight_grams = _d(d.weight_grams)
            purity = _d(d.purity)
            price = _d(d.price)

        case TransactionType.BUY_RAW_GOLD:
            d = details
            if not isinstance(d, BuyRawGoldSchema):
                raise HTTPException(status_code=422, detail="Invalid details for Buy Raw Gold")
            money_amount = -_d(d.price)
            gold_amount_grams = _d(d.weight_grams)
            weight_grams = _d(d.weight_grams)
            purity = _d(d.purity)
            price = _d(d.price)

        case TransactionType.RECEIVE_MONEY:
            d = details
            if not isinstance(d, ReceiveMoneySchema):
                raise HTTPException(status_code=422, detail="Invalid details for Receive Money")
            bank = db.query(BankAccount).filter(BankAccount.account_id == d.bank_account_id).first()
            if not bank:
                raise HTTPException(status_code=404, detail="Bank account not found")
            money_amount = _d(d.amount)
            bank_account_id = d.bank_account_id

        case TransactionType.SEND_MONEY:
            d = details
            if not isinstance(d, SendMoneySchema):
                raise HTTPException(status_code=422, detail="Invalid details for Send Money")
            bank = db.query(BankAccount).filter(BankAccount.account_id == d.bank_account_id).first()
            if not bank:
                raise HTTPException(status_code=404, detail="Bank account not found")
            money_amount = -_d(d.amount)
            bank_account_id = d.bank_account_id

        case TransactionType.RECEIVE_RAW_GOLD:
            d = details
            if not isinstance(d, ReceiveRawGoldSchema):
                raise HTTPException(status_code=422, detail="Invalid details for Receive Raw Gold")
            gold_amount_grams = _d(d.weight_grams)
            weight_grams = _d(d.weight_grams)
            purity = _d(d.purity)

        case TransactionType.GIVE_RAW_GOLD:
            d = details
            if not isinstance(d, GiveRawGoldSchema):
                raise HTTPException(status_code=422, detail="Invalid details for Give Raw Gold")
            gold_amount_grams = -_d(d.weight_grams)
            weight_grams = _d(d.weight_grams)
            purity = _d(d.purity)

        case TransactionType.RECEIVE_JEWELRY:
            d = details
            if not isinstance(d, ReceiveJewelrySchema):
                raise HTTPException(status_code=422, detail="Invalid details for Receive Jewelry")
            jewelry = db.query(JewelryItem).filter(JewelryItem.jewelry_code == d.jewelry_code).first()
            if not jewelry:
                raise HTTPException(status_code=404, detail=f"Jewelry with code '{d.jewelry_code}' not found")
            pure_gold = float(jewelry.weight_grams) * float(jewelry.purity)
            gold_amount_grams = _d(pure_gold)
            item_id = jewelry.jewelry_id
            jewelry.status = "In Stock (Consignment)"

        case TransactionType.GIVE_JEWELRY:
            d = details
            if not isinstance(d, GiveJewelrySchema):
                raise HTTPException(status_code=422, detail="Invalid details for Give Jewelry")
            jewelry = db.query(JewelryItem).filter(JewelryItem.jewelry_code == d.jewelry_code).first()
            if not jewelry:
                raise HTTPException(status_code=404, detail=f"Jewelry with code '{d.jewelry_code}' not found")
            pure_gold = float(jewelry.weight_grams) * float(jewelry.purity)
            gold_amount_grams = -_d(pure_gold)
            item_id = jewelry.jewelry_id

    tx = Transaction(
        customer_id=payload.customer_id,
        transaction_type=tx_type.value,
        item_id=item_id,
        bank_account_id=bank_account_id,
        price=price,
        weight_grams=weight_grams,
        purity=purity,
        money_amount=money_amount,
        gold_amount_grams=gold_amount_grams,
        notes=payload.notes,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return TransactionResponse.model_validate(tx)
