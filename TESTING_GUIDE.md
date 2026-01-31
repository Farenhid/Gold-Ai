# Testing Guide

## Quick System Test

This guide will help you verify that all components of the Smart Gold Accounting Middleware are working correctly.

## Prerequisites Check

Before testing, ensure:
- [x] Python 3.8+ is installed
- [x] Dependencies are installed (`pip install -r requirements.txt`)
- [x] `.env` file exists with valid `OPENAI_API_KEY`
- [x] Server is running on http://localhost:8000

## Test 1: Server Health Check

**Test**: Verify the server is running

**Steps**:
1. Open browser to http://localhost:8000
2. You should see the Smart Gold Accounting interface

**Expected Result**: 
- Beautiful gradient purple/blue UI loads
- Three main buttons are visible
- System information panel shows gold price and account counts

**Troubleshooting**:
- If page doesn't load: Check if server is running
- If "Error" appears: Check console logs

## Test 2: Gold Price API

**Test**: Verify the adapter layer is working

**Steps**:
1. Look at the "Gold Price" card in the info section
2. It should display a formatted price

**Expected Result**: 
- Shows "10,000,000 Rial/gram" (mock data)

**API Test**:
```bash
curl http://localhost:8000/gold-price
```

**Expected Response**:
```json
{
  "status": "success",
  "price_per_gram_rial": 10000000.0,
  "formatted": "10,000,000 Rial/gram"
}
```

## Test 3: View Accounts

**Test**: Verify account retrieval

**Steps**:
1. Click "👥 View Accounts" button
2. Review the displayed accounts

**Expected Result**:
- **Collaborators Section**:
  - Collaborator Akbari (owes 5 grams gold)
  - Collaborator Saeedi (has 80M Rial, 8g gold)
- **Customers Section**:
  - Customer Rezaei (zero balance)
  - Customer Mohammadi (owes 5M Rial, has 2g gold)

**API Test**:
```bash
curl http://localhost:8000/accounts?account_type=all
```

## Test 4: Process Event (NLP Core)

**Test**: Verify OpenAI integration and transaction analysis

**Steps**:
1. Click "📝 Register Event" button
2. Click the example text to auto-fill
3. Click "Analyze Transaction"
4. Wait for AI processing (2-5 seconds)

**Expected Result**:
- Loading spinner appears briefly
- Transaction plan is generated with multiple steps
- Each step shows:
  - Action description
  - Transaction details
- "✅ Approve & Execute" button appears

**Example Input**:
```
Customer Rezaei bought 4 grams of finished gold for 45 million Toman. 
Pay this money to Collaborator Akbari to settle 4.5 grams of gold debt.
```

**Expected Output** (approximate):
- Step 1: Sell finished gold to customer
- Step 2: Receive payment from customer
- Step 3: Pay Rial to collaborator
- Step 4: Settle gold debt

**API Test**:
```bash
curl -X POST http://localhost:8000/process-event \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Customer Rezaei bought 4 grams of finished gold for 45 million Toman. Pay this money to Collaborator Akbari to settle 4.5 grams of gold debt."
  }'
```

**If This Fails**:
- Check `.env` file has valid `OPENAI_API_KEY`
- Check OpenAI account has credits
- Check console for error messages
- Verify network connectivity

## Test 5: Execute Transaction Plan

**Test**: Verify transaction execution via adapter

**Steps**:
1. After generating a plan (Test 4)
2. Click "✅ Approve & Execute"
3. Wait for execution

**Expected Result**:
- Success message appears in green
- Shows "Successfully executed X transaction(s)"
- "Done" button appears

**Console Output**:
```
[MOCK ADAPTER] Transaction executed: {...}
```

## Test 6: Get Suggestion

**Test**: Verify suggestion generation

**Steps**:
1. Click "💡 Get Suggestion" button
2. Click the example text to auto-fill
3. Click "Get Suggestion"
4. Wait for AI processing

**Expected Result**:
- Smart suggestion appears
- Recommends "Collaborator Akbari" (who has -5g gold balance)
- Explains the debt relationship
- Shows recommended account details

**Example Input**:
```
A customer wants to buy 45 million Toman worth of gold
```

**API Test**:
```bash
curl -X POST http://localhost:8000/get-suggestion \
  -H "Content-Type: application/json" \
  -d '{
    "scenario": "A customer wants to buy 45 million Toman worth of gold"
  }'
```

## Test 7: Custom Transaction Scenarios

Try these scenarios to test different transaction types:

### Scenario A: Simple Sale
```
Customer Mohammadi bought a gold necklace for 25 million Toman cash.
```

**Expected**: System should recognize sale, amount, and customer

### Scenario B: Gold Trade
```
Collaborator Saeedi brought 10 grams of raw gold. I need to settle this later.
```

**Expected**: System should recognize gold deposit from collaborator

### Scenario C: Multi-Currency
```
Customer wants to pay 1000 USD for 10 grams of gold.
```

**Expected**: System should handle USD currency

### Scenario D: Complex Transaction
```
Customer Rezaei returned 2 grams of gold, and I refunded him 20 million Toman 
from Collaborator Saeedi's account.
```

**Expected**: System should handle multiple accounts and reverse transactions

## Test 8: Error Handling

**Test**: Verify error handling works correctly

### Test 8.1: Empty Input
**Steps**:
1. Click "📝 Register Event"
2. Leave text area empty
3. Click "Analyze Transaction"

**Expected**: Alert: "Please enter a transaction description"

### Test 8.2: Invalid OpenAI Key
**Steps**:
1. Edit `.env` and set `OPENAI_API_KEY=invalid`
2. Restart server
3. Try to process an event

**Expected**: Error message about API key configuration

### Test 8.3: Network Error
**Steps**:
1. Disconnect from internet
2. Try to process an event

**Expected**: Network error message displayed

## Test 9: UI/UX Elements

**Test**: Verify user experience elements

**Checklist**:
- [x] Buttons have hover effects
- [x] Loading spinners appear during processing
- [x] Cards slide in smoothly
- [x] Colors are consistent with brand
- [x] Text is readable
- [x] Examples are clickable
- [x] Cancel buttons work
- [x] Success messages are clear
- [x] Error messages are informative

## Test 10: API Documentation

**Test**: Verify FastAPI auto-generated docs

**Steps**:
1. Navigate to http://localhost:8000/docs
2. Explore the interactive API documentation

**Expected Result**:
- Swagger UI interface loads
- All endpoints are listed
- Can test endpoints interactively
- Request/response schemas are documented

**Alternative Docs**:
- ReDoc format: http://localhost:8000/redoc

## Performance Tests

### Test 11: Response Time

**Test**: Measure API response times

```bash
# Test gold price endpoint (should be fast)
time curl http://localhost:8000/gold-price

# Test accounts endpoint
time curl http://localhost:8000/accounts?account_type=all

# Test process-event (will be slower due to OpenAI)
time curl -X POST http://localhost:8000/process-event \
  -H "Content-Type: application/json" \
  -d '{"text": "Customer bought gold for 1000 Rial"}'
```

**Expected Times**:
- `gold-price`: < 100ms
- `accounts`: < 100ms
- `process-event`: 1000-3000ms (depends on OpenAI)

## Integration Tests

### Test 12: Complete Workflow

**Full User Journey**:

1. **Start**: User opens application
2. **View Info**: Check gold price and accounts
3. **Register Event**: Enter transaction description
4. **Review Plan**: AI generates transaction plan
5. **Approve**: User approves the plan
6. **Execute**: System executes via adapter
7. **Confirm**: Success message shown
8. **Get Suggestion**: Ask for recommendation
9. **View Accounts**: Check updated balances (in real system)

**Time**: Should complete in < 2 minutes

## Troubleshooting Common Issues

### Issue: "OpenAI API key not configured"
**Solution**: 
1. Check `.env` file exists
2. Verify `OPENAI_API_KEY` is set
3. Restart the server

### Issue: "No module named 'fastapi'"
**Solution**:
```bash
pip install -r requirements.txt
```

### Issue: "Port 8000 already in use"
**Solution**:
```bash
# Find and kill the process
lsof -ti:8000 | xargs kill -9

# Or use a different port
uvicorn main:app --reload --port 8001
```

### Issue: Slow response times
**Possible Causes**:
- Slow internet connection
- OpenAI API rate limits
- High server load

**Solutions**:
- Check network connectivity
- Use a faster OpenAI model
- Add caching for account data

### Issue: Transactions not parsing correctly
**Solution**:
- Check the transaction description clarity
- Try simpler language
- Review OpenAI system prompt in `main.py`
- Ensure account names match those in the adapter

## Automated Testing (Future)

To implement automated tests:

```bash
# Install pytest
pip install pytest pytest-asyncio httpx

# Run tests
pytest tests/
```

**Test Structure** (to be created):
```
tests/
├── test_adapters.py       # Unit tests for adapters
├── test_api.py            # API endpoint tests
├── test_nlp.py            # NLP processing tests
└── test_integration.py    # End-to-end tests
```

## Success Criteria

All tests pass if:
- [x] Server starts without errors
- [x] All endpoints respond correctly
- [x] NLP successfully parses transactions
- [x] Transaction plans are generated
- [x] Suggestions are provided
- [x] Transactions can be executed
- [x] UI is responsive and functional
- [x] Error handling works properly
- [x] API documentation is accessible

## Next Steps After Testing

1. **Customize Mock Data**: Edit `adapters/mock_adapter.py`
2. **Test Edge Cases**: Try unusual transaction descriptions
3. **Monitor Costs**: Track OpenAI API usage
4. **Performance Tune**: Optimize slow operations
5. **Add Real Adapter**: Connect to actual accounting system
6. **Deploy**: Move to production environment

## Reporting Issues

When reporting issues, include:
- Error message (full text)
- Steps to reproduce
- Expected vs actual behavior
- Console logs
- System information (OS, Python version)
- Network status (online/offline)
