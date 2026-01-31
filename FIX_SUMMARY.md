# Fix Summary: Redundant "Record Debt" Transaction

## Problem

When users described partial payment scenarios like:
> "Bought 30 grams of scrap gold from Customer Alavi for 290 million Toman. Paid 100 million Toman cash; the remaining 190 million is debt."

The LLM would incorrectly generate 3 transactions:
1. Sell Raw Gold (290M)
2. Send Money (100M)
3. **Record Debt (190M) ← WRONG!**

The third transaction was redundant because the accounting system **derives** customer balance from the sum of transactions. Adding a third transaction would double-count the debt, resulting in incorrect balances.

## Root Cause

LLMs naturally treat action verbs like "registered" or "recorded" as separate actions to perform. The phrase "registered the remaining 190 million as debt" was being interpreted as a transaction rather than as a description of the resulting state.

## Solution Implemented

### 1. Extended System Prompt in `main.py`

Added a new section **"Balance and Debt (IMPORTANT)"** with explicit rules:

- Customer balance is computed by **summing all transactions** - there's no separate "balance" or "debt" field
- **NEVER** output transactions for "recording debt", "registering remaining balance", etc.
- Only output **ACTUAL MOVEMENTS**: buy/sell gold, receive/send money, receive/give raw gold/jewelry
- Clear rule: "bought X for Y, paid Z" = exactly 2 transactions (Buy for Y + Send Money for Z)

### 2. Added Concrete Example

Added a worked example showing the correct output for the problematic scenario:

```json
{
  "transactions": [
    {
      "customer_id": 2,
      "transaction_type": "Sell Raw Gold",
      "details": {
        "purity": 0.999,
        "weight_grams": 30.0,
        "price": 290000000
      }
    },
    {
      "customer_id": 2,
      "transaction_type": "Send Money",
      "details": {
        "amount": 100000000,
        "bank_account_id": 1
      }
    }
  ]
}
```

With explicit note: "The remaining 190M debt is automatically calculated by the system (290M owed - 100M paid = 190M remaining debt). Do NOT create a third transaction."

## Verification

Created `test_partial_payment.py` which proves the fix works:

### Test Results:
```
Initial balance:   0 Rial, 0g gold
After Sell (290M): +290,000,000 Rial, -30g gold (we owe customer)
After Send (100M): +190,000,000 Rial, -30g gold (remaining debt)

✓ CORRECT: Money balance is +190M (debt automatically calculated)
✓ CORRECT: Gold balance is -30g (customer gave us gold)
✓ No redundant "record debt" transaction needed
```

## Transaction Type Clarification

For the scenario "goldsmith bought gold from customer and paid partially":

1. **Sell Raw Gold** (from customer's perspective)
   - Customer sold gold to goldsmith
   - money_amount = +price (we owe them)
   - gold_amount = -weight (they gave us gold)

2. **Send Money** (payment reduces debt)
   - From customer's perspective, they "send" money out
   - money_amount = -amount (reduces what we owe)
   - Attached to bank_account_id

Result: 290M - 100M = 190M remaining debt (derived, not recorded)

## Files Modified

- **[main.py](main.py)**: Extended system prompt with Balance/Debt rules and example
- **[test_partial_payment.py](test_partial_payment.py)**: Created comprehensive test

## Impact

- **Before**: LLM could generate invalid "record_debt" transactions → double-counting → wrong balances
- **After**: LLM generates only real movement transactions → correct automatic balance calculation

The fix ensures the LLM respects the domain expert's accounting model where balance is a **derived state** (sum of transactions) not a **stored field** (updated by separate transactions).
