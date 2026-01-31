# Quick Start Guide

## Prerequisites

- Python 3.8 or higher
- An OpenAI API key ([Get one here](https://platform.openai.com/api-keys))

## Installation & Running

### Option 1: Using the startup script (Recommended)

**On macOS/Linux:**
```bash
chmod +x run.sh
./run.sh
```

**On Windows:**
```bash
run.bat
```

The script will:
1. Create a virtual environment if it doesn't exist
2. Install all dependencies
3. Create a `.env` file from `.env.example` if needed
4. Start the server

### Option 2: Manual setup

1. **Create a virtual environment:**
```bash
python3 -m venv venv
```

2. **Activate it:**
- macOS/Linux: `source venv/bin/activate`
- Windows: `venv\Scripts\activate`

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Configure environment:**
```bash
cp .env.example .env
# Edit .env and add your OpenAI API key
```

5. **Run the server:**
```bash
uvicorn main:app --reload
```

## Using the Application

1. Open your browser and go to: http://localhost:8000

2. You'll see three main buttons:
   - **📝 Register Event**: Enter a transaction description in natural language
   - **💡 Get Suggestion**: Get smart recommendations for transactions
   - **👥 View Accounts**: See all customer and collaborator accounts

### Example Transactions

**Register Event Example:**
```
Customer Rezaei bought 4 grams of finished gold for 45 million Toman. 
Pay this money to Collaborator Akbari to settle 4.5 grams of gold debt.
```

The system will:
1. Analyze the text using AI
2. Extract entities (people, amounts, currencies)
3. Generate a transaction plan
4. Show you the plan for approval
5. Execute the transactions when you approve

**Get Suggestion Example:**
```
A customer wants to buy 45 million Toman worth of gold
```

The system will analyze your collaborators' balances and suggest the best person to work with based on debts and relationships.

## Troubleshooting

### "OpenAI API key not configured"
- Make sure you've created a `.env` file
- Add your OpenAI API key: `OPENAI_API_KEY=sk-...`
- Restart the server

### "Port 8000 already in use"
- Stop any other process using port 8000
- Or run on a different port: `uvicorn main:app --reload --port 8001`

### Dependencies installation fails
- Make sure you have Python 3.8+: `python3 --version`
- Try upgrading pip: `pip install --upgrade pip`
- Then retry: `pip install -r requirements.txt`

## API Documentation

Once the server is running, visit:
- Interactive API docs: http://localhost:8000/docs
- Alternative docs: http://localhost:8000/redoc

## Project Structure

```
GoldAI/
├── adapters/              # Adapter layer for accounting systems
│   ├── base.py           # Abstract base class
│   └── mock_adapter.py   # Mock implementation
├── main.py               # FastAPI application
├── index.html            # Frontend UI
├── requirements.txt      # Python dependencies
├── .env                  # Environment configuration (you create this)
├── .env.example          # Environment template
└── README.md            # Full documentation
```

## Next Steps

1. **Test the mock system**: Use the provided examples to see how it works
2. **Explore the API**: Check out http://localhost:8000/docs
3. **Customize**: Modify the mock data in `adapters/mock_adapter.py`
4. **Integrate**: Create a new adapter to connect to your real accounting system

## Support

For issues or questions:
- Check the main README.md for detailed documentation
- Review the API documentation at `/docs`
- Examine the adapter pattern in `adapters/base.py`
