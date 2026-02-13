"""
Simplified sanity test - no color codes for Windows compatibility
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

def test_env_vars():
    print("\n" + "="*60)
    print("TEST 1: Environment Variables")
    print("="*60)
    
    required = ["OPENAI_API_KEY", "SUPABASE_URL", "SUPABASE_KEY"]
    all_pass = True
    
    for var in required:
        value = os.getenv(var)
        exists = value is not None and len(value) > 10
        status = "PASS" if exists else "FAIL"
        print(f"[{status}] {var}: {len(value) if value else 0} chars")
        all_pass = all_pass and exists
    
    return all_pass

def test_openai():
    print("\n" + "="*60)
    print("TEST 2: OpenAI API")
    print("="*60)
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Say 'OK'"}],
            max_tokens=5
        )
        
        print(f"[PASS] OpenAI API: {response.choices[0].message.content}")
        return True
    except Exception as e:
        print(f"[FAIL] OpenAI API: {str(e)[:80]}")
        return False

def test_supabase():
    print("\n" + "="*60)
    print("TEST 3: Supabase Database")
    print("="*60)
    
    try:
        from supabase import create_client
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        client = create_client(url, key)
        
        tables = ["users", "videos", "modules", "roadmaps", "sessions", "progress"]
        all_pass = True
        
        for table in tables:
            try:
                client.table(table).select("count").limit(1).execute()
                print(f"[PASS] Table: {table}")
            except Exception as e:
                print(f"[FAIL] Table: {table} - {str(e)[:50]}")
                all_pass = False
        
        return all_pass
    except Exception as e:
        print(f"[FAIL] Supabase: {str(e)[:80]}")
        return False

def test_agents():
    print("\n" + "="*60)
    print("TEST 4: AI Agents")
    print("="*60)
    
    try:
        from agents import material_agent
        
        sample = "Agentic AI uses supervisor and worker agents for task coordination."
        
        print("Testing material_agent...")
        result = material_agent(sample, "Test")
        
        checks = [
            ("title" in result, "Has title"),
            ("summary" in result, "Has summary"),
            ("key_concepts" in result, "Has concepts"),
            ("transfer_scenarios" in result, "Has scenarios")
        ]
        
        all_pass = True
        for passed, name in checks:
            status = "PASS" if passed else "FAIL"
            print(f"[{status}] {name}")
            all_pass = all_pass and passed
        
        return all_pass
    except Exception as e:
        print(f"[FAIL] Agents: {str(e)[:80]}")
        return False

def main():
    print("\n" + "="*60)
    print("YOUTUBE LEARNING ORCHESTRATOR - SANITY TEST")
    print("="*60)
    
    tests = [
        ("Environment", test_env_vars),
        ("OpenAI", test_openai),
        ("Database", test_supabase),
        ("AI Agents", test_agents)
    ]
    
    results = {}
    for name, func in tests:
        try:
            results[name] = func()
        except Exception as e:
            print(f"\n[ERROR] {name}: {e}")
            results[name] = False
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    for name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"[{status}] {name}")
    
    passed = sum(results.values())
    total = len(results)
    
    print("\n" + "="*60)
    print(f"RESULT: {passed}/{total} tests passed")
    
    if passed == total:
        print("STATUS: All systems operational!")
    else:
        print(f"STATUS: {total - passed} test(s) failed")
    print("="*60 + "\n")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
