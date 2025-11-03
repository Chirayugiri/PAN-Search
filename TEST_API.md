# API Testing Guide

## Quick Start

### 1. Start the API Server

First, make sure your database is built:
```bash
# If not already done:
python src/build_index.py --parquet data/parquet --db data/tx.duckdb
```

Then start the API:
```bash
# Windows PowerShell
$env:TX_DB_PATH="data/tx.duckdb"
python -m uvicorn src.api:app --host 0.0.0.0 --port 8000 --reload

# Or on Windows CMD
set TX_DB_PATH=data/tx.duckdb
python -m uvicorn src.api:app --host 0.0.0.0 --port 8000 --reload

# Or Linux/Mac
export TX_DB_PATH=data/tx.duckdb
python -m uvicorn src.api:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at: `http://localhost:8000`

---

## Testing Methods

### Method 1: FastAPI Interactive Documentation (Recommended)

FastAPI automatically generates interactive API documentation:

1. **Swagger UI** (Visual, easy to use):
   - Open: http://localhost:8000/docs
   - Click on `/search` endpoint
   - Click "Try it out"
   - Enter parameters (pan or seed_name)
   - Click "Execute"
   - See results with full response

2. **ReDoc** (Alternative documentation):
   - Open: http://localhost:8000/redoc
   - Browse API structure and parameters

### Method 2: Browser Testing

Test endpoints directly in your browser:

1. **Health Check:**
   ```
   http://localhost:8000/health
   ```
   Should return: `{"status":"ok"}`

2. **Search by PAN:**
   ```
   http://localhost:8000/search?pan=ABCDE1234F
   ```

3. **Search by Name:**
   ```
   http://localhost:8000/search?seed_name=John%20Doe
   ```

4. **Search with Limit:**
   ```
   http://localhost:8000/search?pan=ABCDE1234F&limit=100
   ```

### Method 3: Using curl (Command Line)

**Windows PowerShell:**
```powershell
# Health check
curl http://localhost:8000/health

# Search by PAN
curl "http://localhost:8000/search?pan=ABCDE1234F"

# Search by name
curl "http://localhost:8000/search?seed_name=John%20Doe"

# Search with limit
curl "http://localhost:8000/search?pan=ABCDE1234F&limit=50"
```

**Linux/Mac:**
```bash
# Health check
curl http://localhost:8000/health

# Search by PAN
curl "http://localhost:8000/search?pan=ABCDE1234F"

# Search by name
curl "http://localhost:8000/search?seed_name=John%20Doe"

# Pretty print JSON
curl "http://localhost:8000/search?pan=ABCDE1234F" | python -m json.tool
```

### Method 4: Using Python requests

Create a test script (see `test_api.py` below) or use Python REPL:

```python
import requests

# Health check
response = requests.get("http://localhost:8000/health")
print(response.json())  # {'status': 'ok'}

# Search by PAN
response = requests.get("http://localhost:8000/search", params={
    "pan": "ABCDE1234F",
    "limit": 100
})
data = response.json()
print(f"Found {data['count']} results")
print(data['data'][:2])  # First 2 results

# Search by name
response = requests.get("http://localhost:8000/search", params={
    "seed_name": "चिरायु संजय गिरी"
})
print(response.json())
```

### Method 5: Using Postman or Insomnia

1. Create a new GET request
2. URL: `http://localhost:8000/search`
3. Add query parameters:
   - `pan`: `ABCDE1234F` (or)
   - `seed_name`: `John Doe`
   - `limit`: `100` (optional)
4. Send request

### Method 6: Using the Frontend

1. Start the API server (see above)
2. Open `frontend/index.html` in your browser
3. Enter a PAN or name in the search form
4. Click "Search"
5. Results will display in the table below

---

## Expected Response Format

### Success Response:
```json
{
  "count": 42,
  "data": [
    {
      "pan_numbers": "ABCDE1234F",
      "buyer": "...",
      "seller": "...",
      "age": 35,
      "score": 100,
      ...
    },
    ...
  ]
}
```

### Error Response:
```json
{
  "detail": "Provide either pan or seed_name"
}
```

---

## Common Issues

1. **Database not found:**
   - Error: `DB not found at data/tx.duckdb`
   - Solution: Run `python src/build_index.py --parquet data/parquet --db data/tx.duckdb`

2. **Port already in use:**
   - Error: `Address already in use`
   - Solution: Change port: `--port 8001` or kill the process using port 8000

3. **Import errors:**
   - Make sure you're in the project root directory
   - Activate virtual environment: `.venv/Scripts/Activate.ps1` (Windows)

---

## Tips

- Use `/docs` endpoint for interactive testing - it's the easiest way!
- Check `/health` first to verify the API is running
- Start with a small `limit` parameter for testing
- The API supports CORS, so the frontend can call it from any origin

