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
    
    system_prompt = """تو دستیار حسابداری طلای متخصصی هستی. کاربر یک توضیح تراکنش داده که ممکن است مبهم باشد. 
بر اساس context داده‌شده (مشتریان، همکاران، حساب‌های بانکی، قیمت طلا)، حداکثر ۳ تفسیر محتمل از منظور کاربر تولید کن. 
هر تفسیر باید یک جملهٔ واضح و دقیق به فارسی باشد که دقیقاً چه اتفاقی افتاده (مثلاً «مشتری الف ۱۰ گرم طلا به مغازه فروخت به مبلغ X»). 
آن‌ها را به ترتیب احتمال (از بیشتر به کمتر) مرتب کن.

Context:
- مشتریان/همکاران: {customers}
- حساب‌های بانکی: {bank_accounts}
- قیمت طلا: {gold_price} ریال/گرم

خروجی را فقط به صورت JSON در این قالب دقیق برگردان: 
{{
  "interpretations": [
    {{"text": "توضیح دقیق ۱ به فارسی", "probability": 0.9}},
    {{"text": "توضیح دقیق ۲ به فارسی", "probability": 0.7}}
  ]
}}"""

    user_prompt = f"""توضیح تراکنش کاربر: {text}

گزینه‌های شفاف‌سازی را تولید کن."""

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
            detail=f"شفاف‌سازی تراکنش ناموفق بود: {str(e)}"
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
            
        formatted_output = "**الگوهای سناریو و مثال‌ها (برگرفته از پایگاه دانش):**\n\n"
        
        for i, scenario in enumerate(data.get("scenarios", []), 1):
            title = scenario.get("title", f"Scenario {i}")
            user_input = scenario.get("user_input", "")
            reasoning = scenario.get("reasoning", "")
            rules = scenario.get("rules_for_ai", [])
            output = scenario.get("expected_output", [])
            
            formatted_output += f"{i}) {title}\n"
            formatted_output += f"- ورودی کاربر: \"{user_input}\"\n"
            formatted_output += f"- تحلیل: {reasoning}\n"
            if rules:
                formatted_output += f"- قوانین: {'; '.join(rules)}\n"
            formatted_output += f"- خروجی مورد انتظار (JSON): {json.dumps(output, ensure_ascii=False)}\n\n"
            
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
    # Output JSON MUST use English: transaction_type exact values, field names (customer_id, details, weight_grams, etc.)
    scenarios_context = load_scenarios_context()
    
    system_prompt = f"""تو دستیار حسابداری متخصص برای کسب‌وکار طلافروشی هستی. وظیفه‌ات تحلیل توضیحات تراکنش و تبدیل آن‌ها به طرح تراکنش‌های اتمی و ساخت‌یافته است. context (مانده‌ها، حساب‌ها) از دیتابیس به تو داده می‌شود؛ user_input همان چیزی است که کاربر می‌گوید.

**زمینه کسب‌وکار:**
- همکاران: کسانی که طلای خام به طلافروش می‌دهند (تأمین‌کننده/عمده‌فروش)
- مشتریان: کسانی که محصول طلا یا طلای خام می‌خرند
- طلافروش واسط است: از همکار طلا می‌خرد و به مشتری می‌فروشد
- تراکنش‌ها می‌توانند طلا (گرم و عیار)، پول (دلار، ریال، تومان)، جنس (طلا/جواهر) باشند
- تراکنش‌های پیچیده چند مرحله‌ای باید به ترتیب درست تفکیک شوند

**انواع تراکنش (حتماً از همین مقادیر انگلیسی استفاده کن):**
- "Sell Raw Gold"
- "Buy Raw Gold"
- "Receive Money"
- "Send Money"
- "Receive Raw Gold"
- "Give Raw Gold"
- "Receive Jewelry"
- "Give Jewelry"

**ساختار هر تراکنش (خروجی JSON حتماً به انگلیسی):**
- customer_id: عدد صحیح از context (نام اشخاص/حساب‌ها را به ID تبدیل کن)
- transaction_type: یکی از رشته‌های دقیق بالا به انگلیسی
- details: آبجکت با فیلدهای مشخص بر اساس نوع تراکنش (نام فیلدها به انگلیسی):
  * برای "Sell Raw Gold" / "Buy Raw Gold": {{"purity": number, "weight_grams": float, "price": float}}
  * برای "Receive Money" / "Send Money": {{"amount": float, "bank_account_id": int}}
  * برای "Receive Raw Gold" / "Give Raw Gold": {{"weight_grams": float, "purity": number}}
  * برای "Receive Jewelry" / "Give Jewelry": {{"jewelry_code": string}}
- notes: رشتهٔ اختیاری (می‌توانی فارسی باشد)

**دستورات مهم:**
1. نام اشخاص و حساب‌ها را از context به customer_id و bank_account_id نگاشت کن.
2. مبالغ دقیق استخراج کن (مثلاً "۴۵ میلیون تومان" → 45000000).
3. اگر عیار گفته نشد پیش‌فرض (مثلاً 18) بگذار.
4. تراکنش‌های پیچیده را به مراحل اتمی پشت‌سرهم بشکن؛ خروجی نهایی فقط JSON با کلید "transactions" به انگلیسی.
5. هرگز توضیح خارج از JSON ننویس.

**قوانین مانده و بدهی:**
سیستم ماندهٔ پول و طلای هر مشتری را خودکار محاسبه می‌کند. تراکنش جدا برای «ثبت بدهی» یا «ماندهٔ باقی‌مانده» وجود ندارد.
- هرگز یک تراکنش که فقط «ثبت بدهی» است خروجی نده.
- تراکنش جدا برای «باقی‌ماندهٔ بدهی» نساز؛ دوبارشمارشی می‌شود.
- هر تراکنش باید یکی از ۸ نوع بالا باشد. "Record Debt" مجاز نیست.

{scenarios_context}

خروجی را فقط به صورت JSON معتبر با کلید "transactions" و مقادیر transaction_type و نام فیلدها به انگلیسی برگردان."""

    user_prompt = f"""Context فعلی کسب‌وکار:
مشتریان/همکاران (نام را به customer_id نگاشت کن):
{context['customers']}

حساب‌های بانکی (نام حساب مثل haspa را به bank_account_id نگاشت کن):
{context['bank_accounts']}

قیمت طلا: {context['gold_price_per_gram_rial']:,.0f} ریال/گرم

توضیح تراکنش:
{text}

این تراکنش را تحلیل کن و یک آرایهٔ JSON ساخت‌یافته از تراکنش‌های اتمی برگردان. transaction_type و نام فیلدهای details حتماً به انگلیسی باشند."""

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
            detail=f"تحلیل تراکنش ناموفق بود: {str(e)}"
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
    
    system_prompt = """تو مشاور مالی متخصص برای کسب‌وکار طلافروشی هستی. وظیفه‌ات دادن پیشنهاد هوشمند برای مدیریت رابطه با همکاران (تأمین‌کنندگان طلا) است.

**اصول:**
- اگر طلافروش به همکار طلا بدهکار است (ماندهٔ طلا منفی)، اولویت با پرداخت به اوست
- اگر طلافروش به همکار پول بدهکار است (ماندهٔ ریال منفی)، اولویت با تسویه آن بدهی است
- رابطهٔ خوب با تسویه به‌موقع بدهی‌ها حفظ می‌شود
- همکاری که بیشتر بدهکارش هستیم برای دریافت پرداخت بعدی پیشنهاد شود

پیشنهاد را در ۱ تا ۲ جملهٔ واضح و مختصر به فارسی بده."""

    user_prompt = f"""سناریو: {scenario}

همکاران و مانده‌های فعلی:
{collaborators}

بر اساس بدهی‌ها و مانده‌ها، کدام همکار برای این تراکنش در اولویت است؟ یک پیشنهاد کوتاه به فارسی بده."""

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
            detail=f"دریافت پیشنهاد ناموفق بود: {str(e)}"
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
            "message": f"از توضیح شما {len(plan)} تراکنش استخراج شد."
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
                "message": f"{len(results)} تراکنش با موفقیت اجرا شد، {len(errors)} ناموفق بود.",
                "results": results,
                "errors": errors
            }
        
        return {
            "status": "success",
            "message": f"{len(results)} تراکنش با موفقیت اجرا شد.",
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
            "formatted": f"{price:,.0f} ریال/گرم"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
