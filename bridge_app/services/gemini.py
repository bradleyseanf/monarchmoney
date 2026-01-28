import os
import json
import google.generativeai as genai
from PIL import Image
import io

# Verify API Key
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

def extract_transaction_data(image_bytes: bytes) -> dict:
    if not api_key:
        # Fallback for testing or if key missing
        return {"error": "GEMINI_API_KEY not set"}

    model = genai.GenerativeModel("gemini-3-flash-preview")
    
    # Prompt engineering
    prompt = """
    You are a financial data extractor. Extract the following from the receipt image:
    - date (YYYY-MM-DD)
    - amount (float)
    - currency (ISO code, assume EUR if not specified but likely European)
    - merchant (string, clean name)
    
    Return strictly valid JSON with keys: date, amount, currency, merchant.
    """
    
    try:
        image = Image.open(io.BytesIO(image_bytes))
        response = model.generate_content([prompt, image])
        
        # Clean response to ensure it's JSON
        text_response = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(text_response)
    except Exception as e:
        print(f"Gemini Extraction Error: {e}")
        raise e
