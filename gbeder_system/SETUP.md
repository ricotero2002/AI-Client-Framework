# GBeder System - Setup Instructions

## ⚠️ Missing Dependencies Detected

The system requires the following to run with MCP integration:

### 1. Install Missing Python Packages

```bash
pip install mcp tavily-python
```

### 2. Set Environment Variables

Create or update your `.env` file in the project root:

```bash
# Required for Tavily MCP integration
TAVILY_API_KEY=tvly-dev-YOUR_KEY_HERE

# Required for Gemini models
GOOGLE_API_KEY=your_google_api_key_here

# Optional for DeepEval
OPENAI_API_KEY=your_openai_key_for_evaluation

# Optional for LangSmith tracing
LANGCHAIN_API_KEY=your_langsmith_key
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=gbeder-system
```

### 3. Load Environment Variables

Make sure to load the `.env` file before running:

**Option A: Using python-dotenv (recommended)**
```python
from dotenv import load_dotenv
load_dotenv()
```

**Option B: PowerShell**
```powershell
# Load .env manually
Get-Content .env | ForEach-Object {
    if ($_ -match '^([^=]+)=(.*)$') {
        [Environment]::SetEnvironmentVariable($matches[1], $matches[2], 'Process')
    }
}
```

**Option C: Command Prompt**
```cmd
set TAVILY_API_KEY=tvly-dev-YOUR_KEY
set GOOGLE_API_KEY=your_key
```

### 4. Verify Setup

Run the test script:

```bash
python gbeder_system/test_mcp_connection.py
```

You should see:
```
✅ Connected successfully!
Available tools: ['tavily_search', 'tavily_extract']
✅ Search successful!
```

### 5. Run the System

Once setup is complete:

```bash
# Test all patterns
python gbeder_system/results/run_comparison.py

# Test with specific query
python gbeder_system/results/run_comparison.py --query "Your question here"

# Run without MCP (fallback mode)
python gbeder_system/results/run_comparison.py --no-mcp
```

## Troubleshooting

### "ModuleNotFoundError: No module named 'mcp'"
```bash
pip install mcp
```

### "TAVILY_API_KEY not set"
1. Get API key from https://tavily.com
2. Add to `.env` file
3. Reload environment or restart terminal

### "Connection closed" error
- Check that `tavily_mcp_server.py` exists
- Verify TAVILY_API_KEY is valid
- Try running test script first

### Running without MCP
If you can't set up MCP, use fallback mode:
```bash
python gbeder_system/results/run_comparison.py --no-mcp
```

The system will work but without real web search (uses mock data).
