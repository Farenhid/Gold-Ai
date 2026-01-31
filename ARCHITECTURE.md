# Architecture Documentation

## System Overview

The Smart Gold Accounting Middleware is designed using a **three-tier architecture** with clear separation of concerns:

```
┌─────────────────┐
│   Frontend      │  HTML/JavaScript (index.html)
│   (Client)      │  - User Interface
└────────┬────────┘  - API Communication
         │
         ↓
┌─────────────────┐
│   API Layer     │  FastAPI (main.py)
│   (Middleware)  │  - Request Handling
└────────┬────────┘  - NLP Processing
         │            - Business Logic
         ↓
┌─────────────────┐
│  Adapter Layer  │  Adapter Pattern (adapters/)
│   (Backend)     │  - Abstract Interface
└─────────────────┘  - Mock Implementation
```

## Design Patterns

### 1. Adapter Pattern

**Purpose**: Allow the middleware to work with different accounting systems without changing the core business logic.

**Implementation**:
- `AccountingAdapter` (Abstract Base Class): Defines the interface
- `MockAccountingAdapter` (Concrete Implementation): Mock implementation for testing

**Benefits**:
- **Flexibility**: Easy to add new accounting system integrations
- **Testability**: Mock adapter for development without real system
- **Maintainability**: Changes to accounting systems don't affect business logic

```python
# Easy to add new adapters:
class QuickBooksAdapter(AccountingAdapter):
    def get_accounts(self, account_type):
        # Connect to QuickBooks API
        pass
```

### 2. Stateless Architecture

**Design Decision**: The middleware doesn't store any data persistently.

**Rationale**:
- All account data comes from the accounting system in real-time
- No data synchronization issues
- Simpler deployment and scaling
- Single source of truth (the accounting system)

**Trade-offs**:
- More API calls to the accounting system
- Dependent on accounting system availability
- No offline capability

## Component Deep Dive

### Frontend Layer (index.html)

**Responsibilities**:
- Render user interface
- Capture user input
- Display results
- Handle user interactions

**Key Features**:
- Single-page application (SPA) design
- Responsive layout
- Real-time feedback
- Example transactions for easy testing

**Technology**: Vanilla JavaScript (no frameworks for simplicity)

### API Layer (main.py)

**Responsibilities**:
- Receive and validate HTTP requests
- Process natural language with OpenAI
- Orchestrate adapter calls
- Format and return responses

**Endpoints**:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Serve frontend HTML |
| `/process-event` | POST | Analyze transaction text |
| `/get-suggestion` | POST | Generate smart suggestions |
| `/execute-plan` | POST | Execute approved transactions |
| `/accounts` | GET | Retrieve account list |
| `/gold-price` | GET | Get current gold price |

**NLP Integration**:
- Uses OpenAI's GPT models for natural language understanding
- Structured prompts for consistent output
- JSON response format for easy parsing
- Context-aware analysis (includes current accounts and prices)

### Adapter Layer (adapters/)

**Responsibilities**:
- Define standardized interface for accounting operations
- Implement connections to specific accounting systems
- Abstract away accounting system differences

**Current Implementations**:
- `MockAccountingAdapter`: In-memory mock for development

**Interface Methods**:
- `get_accounts()`: Retrieve account list
- `get_account_balance()`: Get specific account balance
- `get_live_gold_price()`: Fetch current gold price
- `execute_transaction()`: Execute a transaction

## Data Flow

### Transaction Processing Flow

```
1. User enters description
   ↓
2. Frontend sends to /process-event
   ↓
3. FastAPI validates request
   ↓
4. Get context from adapter (accounts, prices)
   ↓
5. Send to OpenAI with context
   ↓
6. OpenAI analyzes and returns structured JSON
   ↓
7. FastAPI formats as transaction plan
   ↓
8. Frontend displays plan for approval
   ↓
9. User approves
   ↓
10. Frontend sends to /execute-plan
    ↓
11. FastAPI calls adapter.execute_transaction()
    ↓
12. Adapter executes in accounting system
    ↓
13. Results returned to user
```

### Suggestion Flow

```
1. User describes scenario
   ↓
2. Frontend sends to /get-suggestion
   ↓
3. FastAPI gets all collaborators from adapter
   ↓
4. Analyzes balances and debts
   ↓
5. (Optional) Uses OpenAI for smart suggestions
   ↓
6. Returns recommendation
   ↓
7. Frontend displays suggestion
```

## NLP Design

### Prompt Engineering

The system uses carefully crafted prompts to ensure accurate transaction extraction:

**System Prompt**:
- Defines the business domain (goldsmith operations)
- Explains entity types (collaborators, customers, gold, rial, USD)
- Specifies output format (JSON array)
- Provides transaction examples

**User Prompt**:
- Includes current business context (accounts, balances, prices)
- Contains the user's transaction description
- Requests structured output

**Response Format**:
```json
{
  "transactions": [
    {
      "action": "sell_finished_gold",
      "to_account": "u1",
      "amount": 45000000,
      "currency": "rial",
      "description": "Sale of 4g finished gold to Customer Rezaei"
    }
  ]
}
```

### Entity Extraction

The NLP layer extracts:
- **Persons**: Names matched to account IDs
- **Amounts**: Numeric values with proper parsing
- **Currencies**: Gold (grams), Rial, USD
- **Actions**: Buy, sell, pay, settle, etc.
- **Relationships**: Who owes whom

## Extensibility

### Adding New Accounting Systems

1. Create a new adapter class:
```python
from adapters.base import AccountingAdapter

class MySystemAdapter(AccountingAdapter):
    def __init__(self, api_key, api_url):
        self.api_key = api_key
        self.api_url = api_url
    
    def get_accounts(self, account_type):
        # Implement using your system's API
        pass
    
    # Implement other required methods...
```

2. Update `main.py` to use your adapter:
```python
# Replace MockAccountingAdapter with your adapter
adapter = MySystemAdapter(
    api_key=os.getenv("MY_SYSTEM_API_KEY"),
    api_url=os.getenv("MY_SYSTEM_API_URL")
)
```

### Adding New Transaction Types

1. Update the NLP system prompt in `main.py`
2. Add new action types to the prompt
3. Implement handling in `execute_transaction()`

### Scaling Considerations

**Current Design**:
- Synchronous request handling
- Single-server deployment
- No caching

**For Production Scale**:
- Add request queuing (Celery, Redis)
- Implement caching (Redis) for account data
- Add rate limiting for OpenAI API
- Use async/await for I/O operations
- Deploy with multiple workers (Gunicorn)
- Add monitoring and logging

## Security Considerations

**Current Implementation**:
- Environment variables for API keys
- No authentication (prototype)
- No authorization checks
- No data encryption

**For Production**:
- Add user authentication (OAuth2, JWT)
- Implement role-based access control
- Encrypt sensitive data in transit (HTTPS)
- Add request validation and sanitization
- Implement rate limiting
- Add audit logging
- Secure OpenAI API key storage

## Testing Strategy

**Unit Tests** (to implement):
- Test each adapter method independently
- Test NLP parsing with various inputs
- Test business logic in endpoints

**Integration Tests** (to implement):
- Test complete transaction flows
- Test error handling
- Test with real OpenAI API

**End-to-End Tests** (to implement):
- Test frontend → backend → adapter flow
- Test user scenarios
- Test edge cases

## Configuration

**Environment Variables**:
```bash
OPENAI_API_KEY=sk-...        # Required for NLP
OPENAI_MODEL=gpt-4o-mini     # Optional, default: gpt-4o-mini
```

**Future Configuration Options**:
- Database connection strings
- Accounting system API credentials
- Logging levels
- Cache configuration
- Rate limit settings

## Performance Considerations

**Bottlenecks**:
1. OpenAI API calls (200-2000ms)
2. Accounting system API calls (varies)

**Optimization Strategies**:
- Cache account data with TTL
- Batch similar transactions
- Use faster OpenAI models for simple queries
- Implement request queuing for high load
- Add CDN for static assets

## Future Enhancements

1. **Multi-language Support**: Support for Persian/Farsi input
2. **Voice Input**: Speech-to-text for hands-free operation
3. **Advanced Analytics**: Transaction history and insights
4. **Mobile App**: Native mobile applications
5. **Offline Mode**: Queue transactions when offline
6. **Bulk Import**: Import multiple transactions from files
7. **Custom Reports**: Generate business reports
8. **Webhooks**: Real-time notifications for events
