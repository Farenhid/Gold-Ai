# Smart Gold Accounting Middleware

A FastAPI-based middleware that translates conversational gold transaction descriptions into structured API calls using AI, featuring an Adapter pattern for accounting system integration.

## Features

- **Natural Language Processing**: Uses OpenAI to parse conversational transaction descriptions
- **Adapter Pattern**: Flexible architecture to connect with different accounting systems
- **Transaction Planning**: Generates transaction plans for user approval before execution
- **Smart Suggestions**: Recommends optimal collaborators based on debt relationships
- **Simple Web UI**: Easy-to-use interface for goldsmiths

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment:
```bash
cp .env.example .env
# Edit .env and add your OpenAI API key
```

3. Run the server:
```bash
uvicorn main:app --reload
```

4. Open your browser and navigate to:
```
http://localhost:8000
```

## Architecture

- **Adapter Layer**: Abstract base class for accounting system integration
- **NLP Core**: OpenAI integration for natural language understanding
- **Transaction Mapping**: Converts parsed intents into API calls
- **Frontend**: Simple HTML/JS interface

## API Endpoints

- `POST /process-event`: Analyze a transaction description and generate a plan
- `POST /get-suggestion`: Get smart suggestions for optimal collaborators
- `POST /execute-plan`: Execute an approved transaction plan

## Example Usage

**Register Event:**
```
"Customer Rezaei bought 4 grams of finished gold for 45 million Toman. 
Pay this money to Collaborator Akbari to settle 4.5 grams of gold debt."
```

**Get Suggestion:**
```
"A customer wants to buy 45 million Toman worth of gold"
```
