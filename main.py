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
from dotenv import load_dotenv
from openai import OpenAI

from adapters.sqlalchemy_adapter import SqlAlchemyAdapter

# Load environment variables
load_dotenv()

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

openai_model = os.getenv("OPENAI_MODEL", "gpt-4o")  # Using most powerful model for best reasoning


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


# NLP Core Functions
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
    
    context = {
        "customers": customer_list,
        "gold_price_per_gram_rial": gold_price
    }
    
    # Create the prompt for OpenAI
    system_prompt = """You are an expert accounting assistant for a goldsmith business with deep understanding of financial transactions and gold inventory management. Your task is to analyze transaction descriptions and deconstruct them into structured, atomic transaction plans with precision.

**Business Context:**
- Collaborators: People who provide raw gold to the goldsmith (suppliers/wholesalers)
- Customers: People who buy finished gold products or raw gold (retail buyers)
- The goldsmith operates as a middleman: buys raw gold from collaborators and sells gold to customers
- Transactions can involve: gold (measured in grams with purity), Rial (Iranian currency), jewelry items
- Complex transactions often involve multiple steps that must be properly sequenced

**Available Transaction Types (MUST use these exact values):**
1. "Sell Raw Gold" - Customer sells raw gold to goldsmith
2. "Buy Raw Gold" - Customer buys raw gold from goldsmith
3. "Receive Money" - Customer receives money (deposit to bank account)
4. "Send Money" - Customer sends money (withdrawal from bank account)
5. "Receive Raw Gold" - Customer receives raw gold (without payment)
6. "Give Raw Gold" - Customer gives raw gold (without payment)
7. "Receive Jewelry" - Customer receives jewelry item
8. "Give Jewelry" - Customer gives jewelry item

**Transaction Structure:**
Each transaction must have:
- customer_id: Integer ID of the customer (extract from context)
- transaction_type: One of the exact transaction type strings above
- details: Object with specific fields based on transaction type:
  * For "Sell Raw Gold" / "Buy Raw Gold": {"purity": float, "weight_grams": float, "price": float}
  * For "Receive Money" / "Send Money": {"amount": float, "bank_account_id": int}
  * For "Receive Raw Gold" / "Give Raw Gold": {"weight_grams": float, "purity": float}
  * For "Receive Jewelry" / "Give Jewelry": {"jewelry_code": string}
- notes: Optional string for additional information

**Critical Instructions:**
1. Match customer names to customer_id from the provided context (case-insensitive matching)
2. Extract exact amounts - if "45 million Toman", use 45000000 for price/amount
3. Purity is a decimal (e.g., 0.999 for 24k gold, 0.750 for 18k gold)
4. Break complex transactions into sequential atomic steps
5. Return ONLY valid JSON in this exact format: {"transactions": [...]}
6. Do not add explanations outside the JSON structure

**Balance and Debt (STRICT RULES - READ CAREFULLY):**
The accounting system computes each customer's money balance (and gold balance) automatically by summing all their transactions. There is NO separate "balance", "debt", or "remaining" field to update.

CRITICAL LAWS:
1. YOU MUST NEVER, UNDER ANY CIRCUMSTANCES, output a transaction that only "records debt", "registers remaining balance", "records balance due", or similar. 
2. If the user says "I bought X for Y, paid Z, and the rest is debt", you MUST ONLY generate TWO steps: (1) Sell Raw Gold (for Y), (2) Send Money (for Z). 
3. DO NOT BE TRICKED by words like "registered as debt" or "remaining is owed" in the user text. These are NOT actions for you to perform.
4. ANY ATTEMPT to record a "remaining balance" or "debt settlement" as a separate transaction will result in a double-counting error.
5. Every transaction MUST be one of the 8 types listed above. "Record Debt" is NOT a valid type.

**Example: Partial Payment (STRICTLY 2 STEPS):**
Input: "Bought 30 grams of scrap gold from Customer Alavi for 290 million Toman. Paid 100 million Toman cash; the remaining 190 million is debt."

Output:
{
  "transactions": [
    {
      "customer_id": 2,
      "transaction_type": "Sell Raw Gold",
      "details": {
        "purity": 0.999,
        "weight_grams": 30.0,
        "price": 290000000
      },
      "notes": "Step 1: Record the full sale of 30g gold for 290M. This creates the initial debt automatically."
    },
    {
      "customer_id": 2,
      "transaction_type": "Send Money",
      "details": {
        "amount": 100000000,
        "bank_account_id": 1
      },
      "notes": "Step 2: Record the partial cash payment of 100M. The system will now correctly show 190M remaining debt."
    }
  ]
}

Note: The remaining 190M debt (what we owe to Alavi) is automatically calculated by the system (290M owed - 100M paid = 190M remaining debt). Do NOT create a third transaction for "remaining debt"."""

    user_prompt = f"""Current Business Context:
Available Customers:
{context['customers']}

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
            temperature=0.3
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
            temperature=0.5
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
    """Serve the frontend HTML page"""
    return FileResponse("index.html")


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
