"""
Pre-deployment verification script.
Checks all critical components before launch.
"""

import os
from dotenv import load_dotenv

load_dotenv()

def check_env_vars():
    """Verify all required environment variables."""
    required = ["OPENAI_API_KEY", "SUPABASE_URL", "SUPABASE_KEY"]
    missing = [var for var in required if not os.getenv(var)]
    
    if missing:
        print(f"❌ Missing environment variables: {', '.join(missing)}")
        return False
    print("✅ All environment variables present")
    return True

def check_supabase_connection():
    """Test Supabase connection."""
    try:
        from supabase import create_client
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        client = create_client(url, key)
        
        # Try a simple query
        result = client.table("videos").select("id").limit(1).execute()
        print("✅ Supabase connection successful")
        return True
    except Exception as e:
        print(f"❌ Supabase connection failed: {e}")
        print("   → Make sure you've run schema.sql in Supabase SQL Editor")
        return False

def check_openai_connection():
    """Test OpenAI API key."""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Simple test call
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "test"}],
            max_tokens=5
        )
        print("✅ OpenAI API connection successful")
        return True
    except Exception as e:
        print(f"❌ OpenAI API failed: {e}")
        return False

def check_dependencies():
    """Verify all Python packages are installed."""
    required_packages = [
        "streamlit",
        "pydantic",
        "openai",
        "youtube_transcript_api",
        "supabase",
        "tenacity"
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
        except ImportError:
            missing.append(package)
    
    if missing:
        print(f"❌ Missing packages: {', '.join(missing)}")
        print(f"   → Run: pip install {' '.join(missing)}")
        return False
    print("✅ All dependencies installed")
    return True

def main():
    print("=" * 50)
    print("YouTube Learning Orchestrator - Pre-Deploy Check")
    print("=" * 50)
    
    checks = [
        ("Dependencies", check_dependencies),
        ("Environment Variables", check_env_vars),
        ("OpenAI API", check_openai_connection),
        ("Supabase", check_supabase_connection)
    ]
    
    results = []
    for name, check_fn in checks:
        print(f"\n[{name}]")
        results.append(check_fn())
    
    print("\n" + "=" * 50)
    if all(results):
        print("✅ ALL CHECKS PASSED - Ready to deploy!")
        print("\nRun: streamlit run app.py")
    else:
        print("❌ Some checks failed. Fix the issues above.")
    print("=" * 50)

if __name__ == "__main__":
    main()
