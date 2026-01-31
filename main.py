"""
FastAPI Application - Smart Gold Accounting Middleware

This middleware translates conversational transaction descriptions
into structured API calls using OpenAI's language models.
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
import os
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

from adapters.sqlalchemy_adapter import SqlAlchemyAdapter

# Load .env from project root (same folder as this file) so the key is found
_env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=_env_path)

# Initialize FastAPI app
app = FastAPI(
    title="Gold Accounting Middleware",
    description="Smart middleware for translating conversational transactions into accounting API calls",
    version="1.0.0"
)

# Initialize the accounting adapter (using domain expert's logic)
adapter = SqlAlchemyAdapter()

# Initialize OpenAI client
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    print("WARNING: OPENAI_API_KEY not found in environment. NLP features will not work.")
    openai_client = None
else:
    openai_client = OpenAI(api_key=openai_api_key)

openai_model = os.getenv("OPENAI_MODEL", "gpt-5.2")  # Using most powerful model for best reasoning


# Pydantic models for request/response
class EventInput(BaseModel):
    """Input model for processing an event"""
    text: str = Field(..., description="Natural language description of the transaction")


class SuggestionInput(BaseModel):
    """Input model for getting a suggestion"""
    scenario: str = Field(..., description="Description of the scenario")


class TransactionPlan(BaseModel):
    """Model for a transaction plan"""
    action: str = Field(..., description="Human-readable action description")
    details: Dict = Field(..., description="Detailed transaction information")


class ExecutePlanInput(BaseModel):
    """Input model for executing a plan"""
    plan: List[Dict] = Field(..., description="List of transactions to execute")


class ClarificationInput(BaseModel):
    """Input model for clarifying a transaction description"""
    text: str = Field(..., description="Natural language description of the transaction")


# NLP Core Functions
def clarify_transaction_with_llm(text: str) -> Dict:
    """
    Use OpenAI to generate probable interpretations of a transaction description.
    
    Args:
        text: Natural language transaction description
    
    Returns:
        Dict containing list of interpretations with probability scores
    """
    if not openai_client:
        raise HTTPException(
            status_code=500,
            detail="OpenAI API key not configured. Please set OPENAI_API_KEY in .env file."
        )
    
    # Get current accounts and gold price for context
    collaborators = adapter.get_accounts(account_type='collaborator')
    customers = adapter.get_accounts(account_type='customer')
    gold_price = adapter.get_live_gold_price()
    
    # Build context for the LLM
    customer_list = []
    for customer in customers + collaborators:
        customer_list.append({
            "name": customer['name'],
            "type": customer['type'],
            "balance": customer['balance']
        })
    
    bank_accounts = []
    if hasattr(adapter, "get_bank_accounts"):
        bank_accounts = adapter.get_bank_accounts()
        
    context = {
        "customers": customer_list,
        "bank_accounts": bank_accounts,
        "gold_price": gold_price
    }
    
    system_prompt = """You are an expert gold accounting assistant. The user provided a transaction description that might be ambiguous. 
Based on the provided context (customers, bank accounts, gold price), generate up to 3 most likely interpretations of what the user meant. 
Each interpretation should be a clear, detailed sentence explaining exactly what happens (e.g., 'Customer A sells 10g gold to the shop for X amount'). 
Order them by probability (highest to lowest).

Context:
- Customers/Collaborators: {customers}
- Bank Accounts: {bank_accounts}
- Gold Price: {gold_price} Rial/gram

Return JSON in this exact format: 
{{
  "interpretations": [
    {{"text": "detailed explanation 1", "probability": 0.9}},
    {{"text": "detailed explanation 2", "probability": 0.7}}
  ]
}}"""

    user_prompt = f"""Transaction Description: {text}

Generate clarification options."""

    try:
        response = openai_client.chat.completions.create(
            model=openai_model,
            messages=[
                {"role": "system", "content": system_prompt.format(
                    customers=context["customers"],
                    bank_accounts=context["bank_accounts"],
                    gold_price=context["gold_price"]
                )},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.4
        )
        
        # Parse the response
        import json
        result_text = response.choices[0].message.content
        result = json.loads(result_text)
        
        return result
            
    except Exception as e:
        print(f"Error clarifying transaction with LLM: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clarify transaction: {str(e)}"
        )


def analyze_transaction_with_llm(text: str) -> List[Dict]:
    """
    Use OpenAI to analyze a transaction description and extract structured data.
    
    Args:
        text: Natural language transaction description
    
    Returns:
        List of structured transaction dictionaries
    """
    if not openai_client:
        raise HTTPException(
            status_code=500,
            detail="OpenAI API key not configured. Please set OPENAI_API_KEY in .env file."
        )
    
    # Get current accounts and gold price for context
    collaborators = adapter.get_accounts(account_type='collaborator')
    customers = adapter.get_accounts(account_type='customer')
    gold_price = adapter.get_live_gold_price()
    
    # Build context for the LLM with customer_id mapping
    customer_list = []
    for customer in customers + collaborators:
        customer_list.append({
            "customer_id": int(customer['id']),
            "name": customer['name'],
            "type": customer['type'],
            "balance": customer['balance']
        })
    
    bank_accounts = []
    if hasattr(adapter, "get_bank_accounts"):
        bank_accounts = adapter.get_bank_accounts()
    context = {
        "customers": customer_list,
        "bank_accounts": bank_accounts,
        "gold_price_per_gram_rial": gold_price
    }
    
    # Create the prompt for OpenAI (aligned with prompts/jewelry_deal_scenarios.json)
    system_prompt = """You are an expert accounting assistant for a goldsmith business with deep understanding of financial transactions and gold inventory management. Your task is to analyze transaction descriptions and deconstruct them into structured, atomic transaction plans with precision. Context (balances, accounts) is provided by the system from the database; user_input is what the person says.

**Business Context:**
- Collaborators: People who provide raw gold to the goldsmith (suppliers/wholesalers)
- Customers: People who buy finished gold products or raw gold (retail buyers)
- The goldsmith operates as a middleman: buys raw gold from collaborators and sells gold to customers
- Transactions can involve: gold (measured in grams with purity), money (USD, Rial, Toman), jewelry items
- Complex transactions often involve multiple steps that must be properly sequenced

**Transaction Types Reference (MUST use these exact values):**
- "Sell Raw Gold"
- "Buy Raw Gold"
- "Receive Money"
- "Send Money"
- "Receive Raw Gold"
- "Give Raw Gold"
- "Receive Jewelry"
- "Give Jewelry"

**Transaction Structure:**
Each transaction must have:
- customer_id: Integer ID from context (resolve person/account names to IDs)
- transaction_type: One of the exact transaction type strings above
- details: Object with specific fields based on transaction type:
  * For "Sell Raw Gold" / "Buy Raw Gold": {"purity": number (e.g. 18 for 18k or 0.750), "weight_grams": float, "price": float}
  * For "Receive Money" / "Send Money": {"amount": float, "bank_account_id": int}
  * For "Receive Raw Gold" / "Give Raw Gold": {"weight_grams": float, "purity": number}
  * For "Receive Jewelry" / "Give Jewelry": {"jewelry_code": string}
- notes: Optional string for additional information

**Critical Instructions:**
1. Resolve person names and account names to customer_id and bank_account_id from the provided context (case-insensitive matching).
2. Extract exact amounts (e.g. "2000$" → 2000, "45 million Toman" → 45000000).
3. Use default purity (e.g. 18 for 18k) if not stated.
4. Break complex transactions into sequential atomic steps. Map logical steps to API transactions (e.g. "sell item" + "give item" = one "Give Jewelry" transaction).
5. Return ONLY valid JSON in this exact format: {"transactions": [...]}
6. Do not add explanations outside the JSON structure.

**Balance and Debt (STRICT RULES):**
The system computes each customer's money and gold balance automatically. There is NO separate "balance" or "debt" transaction.

CRITICAL LAWS:
1. NEVER output a transaction that only "records debt", "registers remaining balance", or "records balance due".
2. DO NOT add a separate transaction for "remaining debt" or "debt settlement" as a standalone record; that causes double-counting.
3. Every transaction MUST be one of the 8 types above. "Record Debt" is NOT valid.

**Complex Scenario Patterns (use system-provided context to validate):**

1) Settling gold debt: part in gold, part in cash
- When user says "gave X grams" and "paid $Y for Z grams from <account>", output 3 transactions in order: (1) Give Raw Gold X g to the person, (2) Buy Raw Gold Z g price Y (we settle Z g in cash; we did not receive physical gold), (3) Send Money Y from the named bank account.
- Validate with context: X + Z = amount we owed. Resolve person and account to IDs from context.

2) Jewelry sale to end user; end user pays collaborator; we settle gold debt
- When user says "sold jewelry item no X to end user for $Y and he paid it to [collaborator] for Z grams of gold", output 4 transactions in order: (1) Give Jewelry (item X to end user) — sale and give item are one transaction; (2) Receive Money (amount Y from end user); (3) Buy Raw Gold (Z g from collaborator, price Y); (4) Send Money (amount Y to collaborator).
- Resolve: end user → customer_id, collaborator → customer_id, jewelry "item no X" → jewelry_code from context, bank accounts from context. Remaining debt to collaborator = N − Z grams.

3) Third party gave gold on our behalf (triangular settlement)
- When user says "[person A] gave [person B] X grams on our behalf", output 2 transactions in order: (1) Receive Raw Gold X g from person A (we receive from A; settles A's debt to us), (2) Give Raw Gold X g to person B (we give to B; settles part of our debt to B).
- Resolve person names to customer_id. Use default purity (e.g. 18) if not stated.

**Example: Settling gold debt (part gold, part cash)**
Input: "I gave Mr. Zamani 8 grams of gold and paid 2000$ for 4 grams from haspa account" (context: we owe Mr. Zamani 12g gold.)
Output: 3 transactions — Give Raw Gold 8g, Buy Raw Gold 4g price 2000, Send Money 2000 from haspa account. Order: give gold, buy gold (settlement), send money. Mr. Zamani's remaining gold balance becomes zero (12 − 8 − 4).

**Example: Partial payment (money only, STRICTLY 2 STEPS):**
Input: "Bought 30 grams of scrap gold from Customer Alavi for 290 million Toman. Paid 100 million Toman cash; the remaining 190 million is debt."
Output: (1) Sell Raw Gold 30g for 290M, (2) Send Money 100M. Do NOT create a third transaction for "remaining debt" — the system calculates it automatically."""

    user_prompt = f"""Current Business Context:
Available Customers (resolve person names to customer_id):
{context['customers']}

Bank Accounts (resolve account names like "haspa" to bank_account_id):
{context['bank_accounts']}

Current Gold Price: {context['gold_price_per_gram_rial']:,.0f} Rial per gram

Transaction Description:
{text}

Analyze this transaction and return a structured JSON array of atomic transactions following the exact format specified in the system prompt."""

    try:
        response = openai_client.chat.completions.create(
            model=openai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.1
        )
        
        # Parse the response
        import json
        result_text = response.choices[0].message.content
        result = json.loads(result_text)
        
        # The response might be wrapped in a key like "transactions"
        if isinstance(result, dict) and "transactions" in result:
            return result["transactions"]
        elif isinstance(result, dict) and "plan" in result:
            return result["plan"]
        elif isinstance(result, list):
            return result
        else:
            # If it's a dict with transaction data, wrap it in a list
            return [result]
            
    except Exception as e:
        print(f"Error analyzing transaction with LLM: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze transaction: {str(e)}"
        )


def generate_suggestion_with_llm(scenario: str, collaborators: List[Dict]) -> str:
    """
    Use OpenAI to generate a smart suggestion based on the scenario.
    
    Args:
        scenario: Description of the situation
        collaborators: List of collaborator accounts with balances
    
    Returns:
        Suggestion text
    """
    if not openai_client:
        raise HTTPException(
            status_code=500,
            detail="OpenAI API key not configured. Please set OPENAI_API_KEY in .env file."
        )
    
    system_prompt = """You are an expert financial advisor for a goldsmith business. Your task is to provide smart suggestions for managing relationships with collaborators (gold suppliers).

**Key Principles:**
- If the goldsmith owes gold to a collaborator (negative gold_gr balance), prioritize paying them
- If the goldsmith owes money to a collaborator (negative rial balance), prioritize settling that debt
- The goldsmith should maintain good relationships by settling debts promptly
- Suggest the most indebted collaborator for incoming payments

Provide a clear, concise suggestion in 1-2 sentences."""

    user_prompt = f"""Scenario: {scenario}

Current Collaborators and Their Balances:
{collaborators}

Based on the debts and balances, which collaborator should receive priority for this transaction? Provide a brief suggestion."""

    try:
        response = openai_client.chat.completions.create(
            model=openai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2
        )
        
        return response.choices[0].message.content
            
    except Exception as e:
        print(f"Error generating suggestion with LLM: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate suggestion: {str(e)}"
        )


# API Endpoints
@app.get("/")
async def read_root():
    """Serve the frontend HTML page from project root so it loads regardless of cwd."""
    _index_path = Path(__file__).resolve().parent / "index.html"
    return FileResponse(_index_path)


@app.post("/clarify-event")
async def clarify_event(input_data: ClarificationInput):
    """
    Clarify ambiguous transaction descriptions.
    
    Returns up to 3 interpretations of the user's input.
    """
    try:
        result = clarify_transaction_with_llm(input_data.text)
        return result
    except Exception as e:
        print(f"Error in clarify_event: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/process-event")
async def process_event(event_input: EventInput):
    """
    Process a natural language transaction description.
    
    This endpoint:
    1. Analyzes the text using OpenAI
    2. Extracts structured transaction data
    3. Returns a plan for user approval
    """
    try:
        # Analyze the transaction with LLM
        transactions = analyze_transaction_with_llm(event_input.text)
        
        # Format the plan for display
        plan = []
        for i, tx in enumerate(transactions, 1):
            # Extract display fields based on the new LLM output structure
            action_name = tx.get("transaction_type", tx.get("action", "Unknown Action"))
            description = tx.get("notes", tx.get("description", ""))
            
            plan.append({
                "step": i,
                "action": action_name,
                "description": description,
                "details": tx
            })
        
        return {
            "status": "plan_generated",
            "plan": plan,
            "message": f"Generated {len(plan)} transaction(s) from your description"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in process_event: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process event: {str(e)}"
        )


@app.post("/get-suggestion")
async def get_suggestion(suggestion_input: SuggestionInput):
    """
    Get a smart suggestion for handling a transaction.
    
    This endpoint:
    1. Analyzes current collaborator balances
    2. Identifies debtors and creditors
    3. Provides an optimal recommendation using AI
    """
    try:
        # Get all collaborator accounts
        collaborators = adapter.get_accounts(account_type='collaborator')
        
        # Simple fallback logic if OpenAI is not available
        if not openai_client:
            # Find collaborators with negative balances (debts)
            debtors = []
            for acc in collaborators:
                balance = acc['balance']
                total_debt = 0
                
                if balance['gold_gr'] < 0:
                    gold_price = adapter.get_live_gold_price()
                    total_debt += abs(balance['gold_gr']) * gold_price
                
                if balance['rial'] < 0:
                    total_debt += abs(balance['rial'])
                
                if total_debt > 0:
                    debtors.append({
                        "account": acc,
                        "total_debt_rial": total_debt
                    })
            
            if debtors:
                # Sort by total debt and get the highest
                best_option = max(debtors, key=lambda x: x['total_debt_rial'])
                account = best_option['account']
                
                suggestion = f"Suggestion: Prioritize '{account['name']}' for this transaction. "
                
                if account['balance']['gold_gr'] < 0:
                    suggestion += f"You owe them {abs(account['balance']['gold_gr'])} grams of gold. "
                
                if account['balance']['rial'] < 0:
                    suggestion += f"You owe them {abs(account['balance']['rial']):,.0f} Rial. "
                
                return {
                    "status": "suggestion_ready",
                    "suggestion": suggestion,
                    "recommended_account": account
                }
            else:
                return {
                    "status": "no_suggestion",
                    "suggestion": "No significant debts found. You can choose any collaborator for this transaction."
                }
        
        # Use OpenAI for smarter suggestions
        suggestion = generate_suggestion_with_llm(suggestion_input.scenario, collaborators)
        
        return {
            "status": "suggestion_ready",
            "suggestion": suggestion,
            "collaborators": collaborators
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_suggestion: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate suggestion: {str(e)}"
        )


@app.post("/execute-plan")
async def execute_plan(execute_input: ExecutePlanInput):
    """
    Execute an approved transaction plan.
    
    This endpoint:
    1. Receives the approved plan from the frontend
    2. Executes each transaction via the adapter
    3. Returns the results
    """
    try:
        results = []
        errors = []
        
        for transaction in execute_input.plan:
            # Extract the details from the transaction
            # The transaction might be wrapped in a "details" key or be the transaction itself
            if "details" in transaction and isinstance(transaction["details"], dict):
                tx_data = transaction["details"]
            else:
                tx_data = transaction
            
            # Execute via adapter
            result = adapter.execute_transaction(tx_data)
            
            if result.get("status") == "error":
                errors.append({
                    "transaction": tx_data,
                    "error": result.get("message")
                })
            else:
                results.append({
                    "transaction": tx_data,
                    "result": result
                })
        
        if errors:
            return {
                "status": "partial_success" if results else "error",
                "message": f"Executed {len(results)} transaction(s) successfully, {len(errors)} failed",
                "results": results,
                "errors": errors
            }
        
        return {
            "status": "success",
            "message": f"Successfully executed {len(results)} transaction(s)",
            "results": results
        }
        
    except Exception as e:
        print(f"Error in execute_plan: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to execute plan: {str(e)}"
        )


@app.get("/accounts")
async def get_accounts(account_type: str = "all"):
    """
    Get all accounts or filter by type.
    
    Query parameters:
        account_type: 'customer', 'collaborator', or 'all' (default)
    """
    try:
        if account_type not in ['customer', 'collaborator', 'all']:
            raise HTTPException(status_code=400, detail="Invalid account_type")
        
        accounts = adapter.get_accounts(account_type=account_type)
        return {
            "status": "success",
            "accounts": accounts
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/gold-price")
async def get_gold_price():
    """Get the current live gold price per gram"""
    try:
        price = adapter.get_live_gold_price()
        return {
            "status": "success",
            "price_per_gram_rial": price,
            "formatted": f"{price:,.0f} Rial/gram"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
