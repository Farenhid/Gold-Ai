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

from adapters import MockAccountingAdapter

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="Gold Accounting Middleware",
    description="Smart middleware for translating conversational transactions into accounting API calls",
    version="1.0.0"
)

# Initialize the accounting adapter (mock for now)
adapter = MockAccountingAdapter()

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
    
    # Build context for the LLM
    context = {
        "collaborators": collaborators,
        "customers": customers,
        "gold_price_per_gram": gold_price
    }
    
    # Create the prompt for OpenAI
    system_prompt = """You are an expert accounting assistant for a goldsmith business with deep understanding of financial transactions and supply chain relationships. Your task is to analyze transaction descriptions and deconstruct them into structured, atomic transaction plans with precision.

**Business Context:**
- Collaborators: People who provide raw gold to the goldsmith (suppliers/wholesalers)
- Customers: People who buy finished gold products (retail buyers)
- The goldsmith operates as a middleman: buys raw gold from collaborators and sells finished gold to customers
- Transactions can involve: gold (measured in grams), Rial (Iranian currency), or USD
- Complex transactions often involve multiple steps that must be properly sequenced

**Transaction Flow Understanding:**
When a customer buys finished gold, the typical flow is:
  1. Customer purchases finished gold (sale transaction)
  2. Customer pays money (receipt of funds)
  3. Goldsmith pays collaborator for the raw gold used (payment transaction)
  4. If there are existing debts (gold or money), they should be settled

**Your Task:**
Carefully analyze the transaction description and deconstruct it into atomic steps. Return a JSON array where each transaction represents ONE atomic operation.

**Transaction Structure:**
Each transaction must have:
- action: Precise action type (e.g., "sell_finished_gold", "buy_raw_gold", "pay_rial", "receive_rial", "settle_gold_debt", "transfer_gold", "record_debt")
- from_account: Account ID of sender (use null if not applicable, e.g., for sales to customers)
- to_account: Account ID of receiver (use null if not applicable)
- amount: Numeric amount (be precise, extract exact numbers from text)
- currency: "gold_gr" (grams of gold), "rial", or "usd"
- description: Clear, human-readable description of this specific step

**Critical Instructions:**
1. Match person names to account IDs from the provided context (case-insensitive matching)
2. Extract exact amounts - if "45 million Toman", use 45000000 for rial
3. If "4 grams of finished gold for 45 million", understand that 4 grams refers to the finished gold sold
4. Break complex transactions into sequential atomic steps
5. Maintain the logical flow: sale → receipt → payment → debt settlement
6. Return ONLY valid JSON in this exact format: {"transactions": [...]}
7. Do not add explanations outside the JSON structure"""

    user_prompt = f"""Current Business Context:
{context}

Transaction Description:
{text}

Analyze this transaction and return a structured JSON array of atomic transactions."""

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
            plan.append({
                "step": i,
                "action": tx.get("action", "Unknown action"),
                "description": tx.get("description", ""),
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
        
        for transaction in execute_input.plan:
            # Extract the details from the transaction
            details = transaction.get("details", transaction)
            
            # Execute via adapter
            result = adapter.execute_transaction(details)
            results.append({
                "transaction": details,
                "result": result
            })
        
        return {
            "status": "success",
            "message": f"Successfully executed {len(results)} transaction(s)",
            "results": results
        }
        
    except Exception as e:
        print(f"Error in execute_plan: {e}")
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
    uvicorn.run(app, host="0.0.0.0", port=8000)
