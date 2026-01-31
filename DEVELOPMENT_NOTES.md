# Development Notes

## Integration Completed ✓

The integration between the NLP middleware and domain expert's accounting logic is complete and fully functional.

## What Changed

### 1. Core Integration
- Created `SqlAlchemyAdapter` that bridges your NLP system with the domain expert's database models
- The adapter implements all 8 transaction types defined in `GOLD AI/enums.py`
- Full validation for customers, bank accounts, and jewelry items

### 2. LLM Prompt Engineering
- Updated system prompt to output exact `TransactionType` values
- LLM now understands gold purity (karat) and generates accurate schemas
- Provides customer_id context so LLM can reference real database records

### 3. Transaction Execution
- Real database persistence with SQLite
- Proper error handling with partial success support
- Transaction rollback on errors

## Testing Status

All integration tests passed:
- ✓ Basic adapter operations (get_accounts, get_balance, get_gold_price)
- ✓ Transaction execution (Sell Raw Gold, Buy Raw Gold)
- ✓ Error handling (invalid customer, invalid transaction type)
- ✓ Database persistence verification

## Known Limitations

### 1. Customer Type Detection
Currently, the adapter uses a simple heuristic to distinguish between customers and collaborators (checking if "Collaborator" is in the name). 

**Future improvement**: Add a `type` field to the `Customer` model in `GOLD AI/models.py`:
```python
customer_type = Column(String(50), default="customer", nullable=False)
```

### 2. Gold Price
The gold price is currently hardcoded in the adapter initialization (10,000,000 Rial/gram).

**Future improvement**: 
- Add a `gold_prices` table to track historical prices
- Integrate with a live gold price API
- Add an admin endpoint to update the price

### 3. Complex Multi-Step Transactions
The LLM can generate multi-step plans, but currently each transaction is independent.

**Future improvement**:
- Add transaction grouping (batch_id)
- Implement atomic execution of transaction batches
- Add rollback for entire batch if one step fails

## Environment Variables

Required in `.env`:
```
OPENAI_API_KEY=your-api-key-here
OPENAI_MODEL=gpt-4o  # or gpt-4-turbo, gpt-3.5-turbo
DATABASE_URL=sqlite:///./gold_accounting.db  # or PostgreSQL URL
```

## Database Location

By default, the database is created at:
- Development: `./gold_accounting.db` (in project root)
- GOLD AI standalone: `GOLD AI/gold_accounting.db`

Both use the same schema, so you can copy the database file between them.

## Running the Application

### Development Mode
```bash
python3 main.py
# or
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Production Mode
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Domain Expert API Only
If you want to run just the accounting API without NLP:
```bash
cd "GOLD AI"
uvicorn main:app --reload --port 8001
```

## API Endpoints

### NLP Middleware (Port 8000)
- `GET /` - Web interface
- `POST /process-event` - Analyze natural language transaction
- `POST /execute-plan` - Execute approved plan
- `POST /get-suggestion` - Get smart suggestions
- `GET /accounts` - List all accounts
- `GET /gold-price` - Get current gold price

### Domain Expert API (Port 8001, when run separately)
- `POST /customers` - Create customer
- `GET /customers` - List customers
- `GET /customers/{id}` - Get customer details
- `GET /customers/{id}/transactions` - Get customer transactions
- `POST /bank_accounts` - Create bank account
- `GET /bank_accounts` - List bank accounts
- `POST /items/jewelry` - Create jewelry item
- `POST /items/standard` - Create standard item
- `POST /transactions` - Create transaction (direct, without NLP)

## Development Workflow

### Adding a New Transaction Type

1. **Domain Expert Side** (if new type needed):
   ```python
   # GOLD AI/enums.py
   class TransactionType(str, Enum):
       NEW_TYPE = "New Type Name"
   
   # GOLD AI/schemas.py
   class NewTypeSchema(BaseModel):
       field1: float
       field2: str
   ```

2. **Adapter Side**:
   ```python
   # adapters/sqlalchemy_adapter.py
   elif tx_type == TransactionType.NEW_TYPE:
       # Handle the new type
       pass
   ```

3. **LLM Prompt**:
   Update the system prompt in `main.py` to include the new transaction type in the available types list.

### Testing a New Feature

1. Add test case to `test_integration.py`
2. Run tests: `python3 test_integration.py`
3. Test manually via API: `curl -X POST ...`
4. Test via web UI: `http://localhost:8000`

## Debugging Tips

### Enable SQL Logging
In `GOLD AI/database.py`, change:
```python
engine = create_engine(DATABASE_URL, connect_args=connect_args, echo=True)
```

### Check LLM Output
The raw LLM response is printed to console. Look for:
```
[MOCK ADAPTER] Transaction executed: {...}
```

### Inspect Database
```bash
sqlite3 gold_accounting.db
.tables
.schema transactions
SELECT * FROM transactions;
```

## Common Issues

### Issue: "ModuleNotFoundError: No module named 'sqlalchemy'"
**Solution**: Install dependencies with `pip3 install -r requirements.txt`

### Issue: LLM generates wrong customer_id
**Solution**: Check that customers are properly listed in the context sent to LLM. The prompt includes all customers with their IDs.

### Issue: Transaction validation fails
**Solution**: Check the error message. Common causes:
- Customer doesn't exist in database
- Bank account doesn't exist
- Jewelry code not found
- Invalid transaction type string

### Issue: Database locked
**Solution**: Close any other connections to the database. SQLite doesn't handle concurrent writes well. For production, consider PostgreSQL.

## Next Steps for Production

1. **Switch to PostgreSQL**:
   ```python
   DATABASE_URL=postgresql://user:pass@localhost/gold_accounting
   ```

2. **Add Authentication**:
   - Implement JWT authentication
   - Add user roles (admin, operator, viewer)
   - Protect sensitive endpoints

3. **Add Logging**:
   ```python
   import logging
   logging.basicConfig(level=logging.INFO)
   ```

4. **Add Monitoring**:
   - Health check endpoint
   - Metrics collection (Prometheus)
   - Error tracking (Sentry)

5. **Add Backup System**:
   - Automated database backups
   - Transaction log archiving
   - Disaster recovery plan

6. **Optimize LLM Calls**:
   - Cache common queries
   - Use cheaper models for simple transactions
   - Implement retry logic with exponential backoff

## Contact

For questions about:
- **Domain Logic**: Refer to your domain expert (creator of `GOLD AI/` folder)
- **NLP/Integration**: This implementation
- **Deployment**: Standard FastAPI deployment guides

---

Last Updated: 2026-01-31
Integration Version: 1.0
