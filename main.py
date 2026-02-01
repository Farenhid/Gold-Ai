"""
FastAPI Application - Smart Gold Accounting Middleware

This middleware translates conversational transaction descriptions
into structured API calls using OpenAI's language models.
"""

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
import os
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
import httpx

from adapters.sqlalchemy_adapter import SqlAlchemyAdapter
from adapters.mock_adapter import MockAccountingAdapter

# Live gold price API (RapidAPI - gold-price-live)
GOLD_PRICE_API_URL = "https://gold-price-live.p.rapidapi.com/get_metal_prices"
RAPIDAPI_HOST = "gold-price-live.p.rapidapi.com"
GRAMS_PER_OZ = 31.1035  # troy ounce to grams
DEFAULT_GOLD_USD_PER_GRAM = 157.0  # mock/fallback USD per gram when API unavailable

# Load .env from project root (same folder as this file) so the key is found
_env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=_env_path)

# Use mock adapter when no database is configured; otherwise use SQLAlchemy
_database_url = os.getenv("DATABASE_URL")
if _database_url:
    adapter = SqlAlchemyAdapter(gold_price_per_gram=DEFAULT_GOLD_USD_PER_GRAM)
    print("Using SqlAlchemy adapter (DATABASE_URL set).")
else:
    adapter = MockAccountingAdapter()
    adapter.update_gold_price(DEFAULT_GOLD_USD_PER_GRAM)
    print("Using Mock adapter (no DATABASE_URL). Accounts and counts are from mock data.")

# Initialize OpenAI client
openai_api_key = os.getenv("OPENAI_API_KEY")
openai_client = None
if openai_api_key:
    try:
        openai_client = OpenAI(api_key=openai_api_key)
    except Exception as e:
        print(f"WARNING: OpenAI client init failed ({e}). NLP features will not work.")
else:
    print("WARNING: OPENAI_API_KEY not found in environment. NLP features will not work.")

openai_model = os.getenv("OPENAI_MODEL", "gpt-5.2")  # Using most powerful model for best reasoning


def _parse_gold_price_usd_per_gram(data: dict) -> Optional[float]:
    """
    Parse gold-price-live get_metal_prices response: gold price in USD per gram.
    API typically returns USD per troy ounce; we convert to per gram.
    """
    try:
        # get_metal_prices often returns { "gold": price_usd_oz } or { "prices": { "gold": ... } }
        gold_val = None
        for key in ("gold", "Gold", "GOLD", "xau", "XAU"):
            val = data.get(key)
            if isinstance(val, (int, float)):
                gold_val = float(val)
                break
        if gold_val is None:
            prices = data.get("prices") or data.get("data") or data.get("rates") or {}
            if isinstance(prices, dict):
                for k in ("gold", "Gold", "GOLD", "xau", "XAU"):
                    if isinstance(prices.get(k), (int, float)):
                        gold_val = float(prices[k])
                        break
        if gold_val is None:
            return None
        # Metal APIs usually return USD per troy ounce (e.g. 2000–2700)
        if 500 < gold_val < 50000:
            return gold_val / GRAMS_PER_OZ
        if gold_val > 0 and gold_val < 0.01:
            return (1.0 / gold_val) / GRAMS_PER_OZ
        return None
    except (TypeError, ZeroDivisionError, KeyError):
        return None


async def fetch_live_gold_price_from_api() -> Optional[float]:
    """Fetch current gold price (USD per gram) from RapidAPI. Returns None on failure."""
    api_key = os.getenv("RAPIDAPI_KEY") or os.getenv("RAPIDAPI_API_KEY") or "f57d9efabfmsh1ce5f873529eacap1380c1jsn4c8a2e45e2a6"
    host = os.getenv("RAPIDAPI_HOST", RAPIDAPI_HOST)
    if not api_key:
        return None
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(
                GOLD_PRICE_API_URL,
                headers={
                    "x-rapidapi-key": api_key,
                    "x-rapidapi-host": host,
                },
            )
            r.raise_for_status()
            data = r.json()
            return _parse_gold_price_usd_per_gram(data)
    except Exception as e:
        print(f"Gold price API error: {e}")
        return None


async def gold_price_updater_task():
    """Background task: fetch gold price on start and every 30 minutes."""
    while True:
        price = await fetch_live_gold_price_from_api()
        if price is not None:
            adapter.update_gold_price(price)
            print(f"Gold price updated: {price:.2f} USD/gram")
        else:
            adapter.update_gold_price(DEFAULT_GOLD_USD_PER_GRAM)
            print(f"Gold price API unavailable, using mock: {DEFAULT_GOLD_USD_PER_GRAM} USD/gram")
        await asyncio.sleep(30 * 60)  # 30 minutes


@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(gold_price_updater_task())
    yield


# Initialize FastAPI app (after adapter and lifespan are defined)
app = FastAPI(
    title="Gold Accounting Middleware",
    description="Smart middleware for translating conversational transactions into accounting API calls",
    version="1.0.0",
    lifespan=lifespan,
)


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
    
    system_prompt = """You are an expert gold accounting assistant. The user has given a transaction description that may be ambiguous.
Based on the provided context (customers, collaborators, bank accounts, gold price), produce up to 3 likely interpretations of what the user meant.
Each interpretation must be one clear, precise sentence in English describing exactly what happened (e.g. "Customer A sold 10g gold to the shop for amount X").
Order them by probability (highest to lowest).

Context:
- Customers/collaborators: {customers}
- Bank accounts: {bank_accounts}
- Gold price: {gold_price} Rial/gram

Return output only as valid JSON in this exact format:
{{
  "interpretations": [
    {{"text": "Precise description 1 in English", "probability": 0.9}},
    {{"text": "Precise description 2 in English", "probability": 0.7}}
  ]
}}"""

    user_prompt = f"""User transaction description: {text}

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
            detail=f"Transaction clarification failed: {str(e)}"
        )


# Helper to load scenarios
def load_scenarios_context() -> str:
    """Load and format scenarios from JSON file for the LLM prompt."""
    try:
        import json
        scenarios_path = Path(__file__).resolve().parent / "prompts" / "jewelry_deal_scenarios.json"
        
        if not scenarios_path.exists():
            return "No scenarios available."
            
        with open(scenarios_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        formatted_output = "**Scenario patterns and examples (from knowledge base):**\n\n"
        
        for i, scenario in enumerate(data.get("scenarios", []), 1):
            title = scenario.get("title", f"Scenario {i}")
            user_input = scenario.get("user_input", "")
            reasoning = scenario.get("reasoning", "")
            rules = scenario.get("rules_for_ai", [])
            output = scenario.get("expected_output", [])
            
            formatted_output += f"{i}) {title}\n"
            formatted_output += f"- User input: \"{user_input}\"\n"
            formatted_output += f"- Reasoning: {reasoning}\n"
            if rules:
                formatted_output += f"- Rules: {'; '.join(rules)}\n"
            formatted_output += f"- Expected output (JSON): {json.dumps(output, ensure_ascii=False)}\n\n"
            
        return formatted_output
        
    except Exception as e:
        print(f"Error loading scenarios: {e}")
        return "Error loading scenarios."


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
    
    # Build context for the LLM with customer_id mapping (mock uses string ids e.g. u1, c1)
    customer_list = []
    for customer in customers + collaborators:
        raw_id = customer['id']
        try:
            cid = int(raw_id) if isinstance(raw_id, (int, float)) or str(raw_id).isdigit() else raw_id
        except (TypeError, ValueError):
            cid = raw_id
        customer_list.append({
            "customer_id": cid,
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
    # Output JSON MUST use English: transaction_type exact values, field names (customer_id, details, weight_grams, etc.)
    scenarios_context = load_scenarios_context()
    
    system_prompt = f"""You are an expert accounting assistant for a gold/jewelry business. Your task is to analyze transaction descriptions and turn them into atomic, structured transaction plans. Context (balances, accounts) is provided from the database; user_input is what the user says.

**Business context:**
- Collaborators: those who supply raw gold to the jeweler (supplier/wholesaler)
- Customers: those who buy gold products or raw gold
- The jeweler is the middleman: buys from collaborators, sells to customers
- Transactions can be gold (grams and purity), money (USD, Rial, etc.), or goods (gold/jewelry)
- Complex multi-step transactions must be split in the correct order

**Transaction types (use these exact English values):**
- "Sell Raw Gold"
- "Buy Raw Gold"
- "Receive Money"
- "Send Money"
- "Receive Raw Gold"
- "Give Raw Gold"
- "Receive Jewelry"
- "Give Jewelry"

**Structure of each transaction (output JSON in English):**
- customer_id: integer from context (map person/account names to ID)
- transaction_type: one of the exact strings above in English
- details: object with fields per transaction type (field names in English):
  * For "Sell Raw Gold" / "Buy Raw Gold": {{"purity": number, "weight_grams": float, "price": float}}
  * For "Receive Money" / "Send Money": {{"amount": float, "bank_account_id": int}}
  * For "Receive Raw Gold" / "Give Raw Gold": {{"weight_grams": float, "purity": number}}
  * For "Receive Jewelry" / "Give Jewelry": {{"jewelry_code": string}}
- notes: optional string (may be in any language)

**Important rules:**
1. Map person and account names from context to customer_id and bank_account_id.
2. Extract amounts precisely (e.g. "45 million" → 45000000).
3. If purity is not given, use default (e.g. 18).
4. Break complex transactions into atomic steps; final output is JSON with key "transactions" in English only.
5. Never write explanation outside the JSON.

**Balance and debt rules:**
The system automatically computes each customer's money and gold balance. There is no separate transaction for "recording debt" or "remaining balance".
- Never output a transaction that is only "record debt".
- Do not create a separate transaction for "remaining debt"; it would be double-counted.
- Every transaction must be one of the 8 types above. "Record Debt" is not allowed.

{scenarios_context}

Return only valid JSON with key "transactions" and transaction_type and field names in English."""

    user_prompt = f"""Current business context:
Customers/collaborators (map name to customer_id):
{context['customers']}

Bank accounts (map account name e.g. haspa to bank_account_id):
{context['bank_accounts']}

Gold price: {context['gold_price_per_gram_rial']:,.0f} Rial/gram

Transaction description:
{text}

Analyze this transaction and return a structured JSON array of atomic transactions. transaction_type and details field names must be in English."""

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
            detail=f"Transaction analysis failed: {str(e)}"
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
    
    system_prompt = """You are an expert financial advisor for a gold/jewelry business. Your task is to give smart suggestions for managing relationships with collaborators (gold suppliers).

**Principles:**
- If the jeweler owes a collaborator gold (negative gold balance), priority is to pay them
- If the jeweler owes a collaborator money (negative Rial balance), priority is to settle that debt
- Good relationships are maintained by settling debts on time
- Suggest the collaborator we owe the most for the next payment

Give your suggestion in 1–2 clear, concise sentences in English."""

    user_prompt = f"""Scenario: {scenario}

Collaborators and current balances:
{collaborators}

Based on debts and balances, which collaborator should be prioritized for this transaction? Give a short suggestion in English."""

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
            detail=f"Failed to get suggestion: {str(e)}"
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


@app.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    """
    Transcribe audio to text using OpenAI Whisper and translate to English.
    
    Accepts audio files in various formats (webm, mp3, wav, etc.).
    Regardless of spoken language, returns English text in the input box.
    """
    if not openai_client:
        raise HTTPException(
            status_code=503,
            detail="OpenAI client not initialized. Please check OPENAI_API_KEY."
        )
    
    try:
        # Read the uploaded file content
        audio_content = await file.read()
        
        # Create a file-like object with proper name for Whisper
        filename = file.filename or "audio.webm"
        
        # Use Whisper translations API: any language -> English text
        translation = openai_client.audio.translations.create(
            model="whisper-1",
            file=(filename, audio_content),
            response_format="text"
        )
        
        return {"text": translation, "success": True}
    
    except Exception as e:
        print(f"Error in transcribe_audio: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")


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
            "message": f"{len(plan)} transaction(s) extracted from your description."
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
                "message": f"{len(results)} transaction(s) executed successfully, {len(errors)} failed.",
                "results": results,
                "errors": errors
            }
        
        return {
            "status": "success",
            "message": f"{len(results)} transaction(s) executed successfully.",
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
            "formatted": f"{price:,.0f}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
