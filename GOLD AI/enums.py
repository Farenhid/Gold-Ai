from enum import Enum


class TransactionType(str, Enum):
    SELL_RAW_GOLD = "Sell Raw Gold"
    BUY_RAW_GOLD = "Buy Raw Gold"
    RECEIVE_MONEY = "Receive Money"
    SEND_MONEY = "Send Money"
    RECEIVE_RAW_GOLD = "Receive Raw Gold"
    GIVE_RAW_GOLD = "Give Raw Gold"
    RECEIVE_JEWELRY = "Receive Jewelry"
    GIVE_JEWELRY = "Give Jewelry"
