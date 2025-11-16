# Installation Guide

## Required Packages

Install all dependencies using one of these methods:

### Option 1: Using pip (Recommended)
```bash
pip install streamlit>=1.28.0 pydantic>=2.0.0 google-genai>=0.2.0 python-dotenv>=1.0.0
```

### Option 2: Using requirements.txt
```bash
pip install -r requirements.txt
```

### Option 3: Using uv (if you have uv installed)
```bash
uv pip install -r requirements.txt
```

## Package Details

- **streamlit>=1.28.0** - Web UI framework
- **pydantic>=2.0.0** - Data validation and settings management
- **google-genai>=0.2.0** - Google Gemini AI SDK (newer version)
- **python-dotenv>=1.0.0** - Load environment variables from .env file

## Setup API Key

1. Create a `.env` file in the project root:
```bash
GEMINI_API_KEY=your_api_key_here
```

2. Get your API key from: https://makersuite.google.com/app/apikey

## Verify Installation

```bash
python -c "import streamlit; import pydantic; from google import genai; from dotenv import load_dotenv; print('✅ All packages installed successfully!')"
```

