from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Union
from pydantic import BaseModel, ConfigDict, model_validator

from enums import TransactionType


# ----- Bank Accounts -----
class BankAccountCreate(BaseModel):
    account_name: str


class BankAccountResponse(BaseModel):
    account_id: int
    account_name: str
    balance: Optional[Decimal] = None

    model_config = ConfigDict(from_attributes=True)


# ----- Customers -----
class CustomerCreate(BaseModel):
    full_name: str
    phone_number: Optional[str] = None
    initial_money_balance: Decimal = Decimal("0")
    initial_gold_balance_grams: Decimal = Decimal("0")


class CustomerResponse(BaseModel):
    customer_id: int
    full_name: str
    phone_number: Optional[str] = None
    initial_money_balance: Decimal
    initial_gold_balance_grams: Decimal
    money_balance: Optional[Decimal] = None
    gold_balance_grams: Optional[Decimal] = None

    model_config = ConfigDict(from_attributes=True)


# ----- Standard Items -----
class StandardItemCreate(BaseModel):
    name: str
    weight_grams: Decimal
    purity: Decimal


class StandardItemResponse(BaseModel):
    item_id: int
    name: str
    weight_grams: Decimal
    purity: Decimal

    model_config = ConfigDict(from_attributes=True)


# ----- Jewelry Items -----
class JewelryItemCreate(BaseModel):
    jewelry_code: str
    name: str
    weight_grams: Decimal
    purity: Decimal
    premium: Decimal
    status: str = "In Stock"


class JewelryItemResponse(BaseModel):
    jewelry_id: int
    jewelry_code: str
    name: str
    weight_grams: Decimal
    purity: Decimal
    premium: Decimal
    status: str

    model_config = ConfigDict(from_attributes=True)


# ----- Transaction type detail schemas -----
class SellRawGoldSchema(BaseModel):
    purity: float
    weight_grams: float
    price: float


class BuyRawGoldSchema(BaseModel):
    purity: float
    weight_grams: float
    price: float


class ReceiveMoneySchema(BaseModel):
    amount: float
    bank_account_id: int


class SendMoneySchema(BaseModel):
    amount: float
    bank_account_id: int


class ReceiveRawGoldSchema(BaseModel):
    weight_grams: float
    purity: float


class GiveRawGoldSchema(BaseModel):
    weight_grams: float
    purity: float


class ReceiveJewelrySchema(BaseModel):
    jewelry_code: str


class GiveJewelrySchema(BaseModel):
    jewelry_code: str


# ----- Transactions -----
_DETAIL_SCHEMAS = {
    TransactionType.SELL_RAW_GOLD: SellRawGoldSchema,
    TransactionType.BUY_RAW_GOLD: BuyRawGoldSchema,
    TransactionType.RECEIVE_MONEY: ReceiveMoneySchema,
    TransactionType.SEND_MONEY: SendMoneySchema,
    TransactionType.RECEIVE_RAW_GOLD: ReceiveRawGoldSchema,
    TransactionType.GIVE_RAW_GOLD: GiveRawGoldSchema,
    TransactionType.RECEIVE_JEWELRY: ReceiveJewelrySchema,
    TransactionType.GIVE_JEWELRY: GiveJewelrySchema,
}


class TransactionCreate(BaseModel):
    customer_id: int
    transaction_type: TransactionType
    details: Union[
        SellRawGoldSchema,
        BuyRawGoldSchema,
        ReceiveMoneySchema,
        SendMoneySchema,
        ReceiveRawGoldSchema,
        GiveRawGoldSchema,
        ReceiveJewelrySchema,
        GiveJewelrySchema,
    ]
    notes: str | None = None

    @model_validator(mode="after")
    def details_match_transaction_type(self) -> "TransactionCreate":
        schema_cls = _DETAIL_SCHEMAS.get(self.transaction_type)
        if schema_cls is None:
            return self
        data = self.details.model_dump() if hasattr(self.details, "model_dump") else self.details
        if isinstance(data, dict):
            self.details = schema_cls.model_validate(data)
        return self


class RawGoldBalanceByPurityItem(BaseModel):
    purity: Decimal
    net_gold_grams: Decimal


class JewelryBalanceItem(BaseModel):
    jewelry_code: str
    status: str


class TransactionResponse(BaseModel):
    transaction_id: int
    customer_id: int
    transaction_date: datetime
    transaction_type: str
    item_type: Optional[str] = None
    item_id: Optional[int] = None
    bank_account_id: Optional[int] = None
    price: Optional[Decimal] = None
    weight_grams: Optional[Decimal] = None
    purity: Optional[Decimal] = None
    money_amount: Optional[Decimal] = None
    gold_amount_grams: Optional[Decimal] = None
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
