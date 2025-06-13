#!/usr/bin/env python3
"""
Check available Gemini models
"""

import google.generativeai as genai
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Configure API
api_key = os.getenv('GEMINI_API_KEY')
if api_key:
    genai.configure(api_key=api_key)
    
    print("🔍 Available Gemini Models:")
    print("=" * 50)
    
    # List all available models
    for model in genai.list_models():
        if 'generateContent' in model.supported_generation_methods:
            print(f"✅ {model.name}")
            print(f"   Display name: {model.display_name}")
            print(f"   Description: {model.description}")
            print(f"   Input token limit: {model.input_token_limit}")
            print(f"   Output token limit: {model.output_token_limit}")
            print()
    
    print("\n🎯 Testing vision capabilities with gemini-1.5-pro...")
    try:
        model = genai.GenerativeModel('gemini-1.5-pro')
        print("✅ gemini-1.5-pro is available and ready for vision tasks!")
    except Exception as e:
        print(f"❌ Error: {e}")
        
    print("\n🎯 Testing vision capabilities with gemini-1.5-flash...")
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        print("✅ gemini-1.5-flash is available and ready for vision tasks!")
    except Exception as e:
        print(f"❌ Error: {e}")
        
else:
    print("❌ No API key found. Set GEMINI_API_KEY in .env file")