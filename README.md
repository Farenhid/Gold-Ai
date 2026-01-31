# Smart Gold Accounting Middleware

A FastAPI-based middleware that translates conversational gold transaction descriptions into structured API calls using AI, integrated with domain expert accounting logic for accurate gold trading operations.

## Features

- **Natural Language Processing**: Uses OpenAI to parse conversational transaction descriptions
- **Domain Expert Integration**: Uses professionally-designed accounting logic from `GOLD AI/` folder
- **Real Database Persistence**: SQLAlchemy-based storage with full transaction history
- **Transaction Planning**: Generates transaction plans for user approval before execution
- **Smart Suggestions**: Recommends optimal collaborators based on debt relationships
- **Comprehensive Validation**: Validates customers, bank accounts, and jewelry items
- **Pure Gold Calculations**: Accurate calculations based on weight and purity (karat)
- **Simple Web UI**: Easy-to-use interface for goldsmiths

## Transaction Types Supported

1. **Sell Raw Gold** - Customer sells raw gold to goldsmith
2. **Buy Raw Gold** - Customer buys raw gold from goldsmith
3. **Receive Money** - Customer receives money (bank deposit)
4. **Send Money** - Customer sends money (bank withdrawal)
5. **Receive Raw Gold** - Customer receives raw gold (no payment)
6. **Give Raw Gold** - Customer gives raw gold (no payment)
7. **Receive Jewelry** - Customer receives jewelry item
8. **Give Jewelry** - Customer gives jewelry item

## Setup

1. Install dependencies:
```bash
pip3 install -r requirements.txt
```

2. (Optional) Run integration tests:
```bash
python3 test_integration.py
```

3. Configure environment:
```bash
cp .env.example .env
# Edit .env and add your OpenAI API key
```

4. Run the server:
```bash
python3 main.py
# OR
uvicorn main:app --reload
```

5. Open your browser and navigate to:
```
http://localhost:8000
```

The application will automatically create the SQLite database (`gold_accounting.db`) on first run.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Frontend (index.html)                                  │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│  NLP Middleware (main.py)                               │
│  - OpenAI LLM Analysis                                  │
│  - Transaction Plan Generation                          │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│  Adapter Layer (adapters/)                              │
│  - SqlAlchemyAdapter: Production database               │
│  - MockAccountingAdapter: Testing/development           │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│  Domain Expert Logic (GOLD AI/)                         │
│  - Models: Customer, Transaction, Jewelry, BankAccount  │
│  - Schemas: Transaction type validation                 │
│  - Routers: Business logic and calculations             │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│  Database (SQLite via SQLAlchemy)                       │
│  - gold_accounting.db                                   │
└─────────────────────────────────────────────────────────┘
```

### Key Components:

- **NLP Core**: OpenAI integration for natural language understanding
- **Adapter Pattern**: Flexible architecture to swap accounting backends
- **Domain Expert Logic**: Professional accounting rules and validations (in `GOLD AI/` folder)
- **Transaction Planning**: Multi-step transaction decomposition
- **Database**: Persistent storage with full audit trail

## API Endpoints

- `POST /process-event`: Analyze a transaction description and generate a plan
- `POST /get-suggestion`: Get smart suggestions for optimal collaborators
- `POST /execute-plan`: Execute an approved transaction plan

## Example Usage

### Via API:

**Process Natural Language Event:**
```bash
curl -X POST http://localhost:8000/process-event \
  -H "Content-Type: application/json" \
  -d '{"text": "Customer Rezaei sold 10 grams of 24k gold for 100 million Rial"}'
```

**Response:**
```json
{
  "status": "plan_generated",
  "plan": [
    {
      "step": 1,
      "action": "Sell Raw Gold",
      "details": {
        "customer_id": 3,
        "transaction_type": "Sell Raw Gold",
        "details": {
          "purity": 0.999,
          "weight_grams": 10.0,
          "price": 100000000
        }
      }
    }
  ]
}
```

**Execute Plan:**
```bash
curl -X POST http://localhost:8000/execute-plan \
  -H "Content-Type: application/json" \
  -d '{"plan": [...]}'  # Use plan from above
```

### Via Web Interface:

1. Open `http://localhost:8000` in your browser
2. Type: "Customer Mohammadi bought 5 grams of 18k gold for 37.5 million"
3. Review the generated transaction plan
4. Click "Execute" to save to database

## Database Schema

The application uses the following tables (defined in `GOLD AI/models.py`):

- **customers**: Customer/collaborator records with initial balances
- **bank_accounts**: Bank account information
- **standard_items**: Standard gold item templates
- **jewelry_items**: Jewelry inventory with codes and specifications
- **transactions**: All transaction records with amounts and metadata

## Testing

Run the comprehensive integration test suite:

```bash
python3 test_integration.py
```

This will:
- Create sample customers, bank accounts, and jewelry items
- Test all transaction types
- Verify balance calculations
- Check error handling
- Validate database persistence

## Project Structure

```
GoldAI/
├── main.py                    # Main application with NLP logic
├── adapters/                  # Adapter pattern implementations
│   ├── base.py               # Abstract base class
│   ├── mock_adapter.py       # Mock for testing
│   └── sqlalchemy_adapter.py # Production database adapter
├── GOLD AI/                   # Domain expert's accounting logic
│   ├── models.py             # SQLAlchemy models
│   ├── schemas.py            # Pydantic schemas
│   ├── enums.py              # Transaction type enums
│   ├── database.py           # Database configuration
│   └── routers/              # Business logic routers
├── test_integration.py        # Integration tests
├── requirements.txt           # Python dependencies
├── INTEGRATION_SUMMARY.md     # Detailed integration documentation
└── README.md                  # This file
```

## Documentation

- **[INTEGRATION_SUMMARY.md](INTEGRATION_SUMMARY.md)**: Detailed documentation of the integration between NLP middleware and domain expert logic
- **[ARCHITECTURE.md](ARCHITECTURE.md)**: System architecture and design patterns
- **[TESTING_GUIDE.md](TESTING_GUIDE.md)**: Testing strategies and examples
- **[QUICK_START.md](QUICK_START.md)**: Quick start guide for development
