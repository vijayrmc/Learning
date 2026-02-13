"""
Comprehensive Sanity Test Suite for YouTube Learning Orchestrator
Tests all critical components end-to-end.
"""

import os
import sys
import asyncio
from dotenv import load_dotenv

load_dotenv()

# Color codes for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"

def test_result(name, passed, details=""):
    status = f"{GREEN}✓ PASS{RESET}" if passed else f"{RED}✗ FAIL{RESET}"
    print(f"{status} | {name}")
    if details:
        print(f"       {details}")
    return passed

def test_env_vars():
    """Test 1: Environment Variables"""
    print("\n" + "="*60)
    print("TEST 1: Environment Variables")
    print("="*60)
    
    required = ["OPENAI_API_KEY", "SUPABASE_URL", "SUPABASE_KEY"]
    results = []
    
    for var in required:
        value = os.getenv(var)
        exists = value is not None and len(value) > 10
        results.append(test_result(f"ENV: {var}", exists, 
            f"Length: {len(value) if value else 0}"))
    
    return all(results)

def test_openai_connection():
    """Test 2: OpenAI API Connection"""
    print("\n" + "="*60)
    print("TEST 2: OpenAI API Connection")
    print("="*60)
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Say 'test'"}],
            max_tokens=5
        )
        
        success = response.choices[0].message.content is not None
        return test_result("OpenAI API", success, 
            f"Response: {response.choices[0].message.content}")
    except Exception as e:
        return test_result("OpenAI API", False, f"Error: {str(e)[:100]}")

def test_supabase_connection():
    """Test 3: Supabase Connection"""
    print("\n" + "="*60)
    print("TEST 3: Supabase Database Connection")
    print("="*60)
    
    try:
        from supabase import create_client
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        client = create_client(url, key)
        
        # Test each table
        tables = ["videos", "modules", "roadmaps", "sessions", "progress"]
        results = []
        
        for table in tables:
            try:
                res = client.table(table).select("count").limit(1).execute()
                results.append(test_result(f"Table: {table}", True, "Accessible"))
            except Exception as e:
                results.append(test_result(f"Table: {table}", False, str(e)[:50]))
        
        return all(results)
    except Exception as e:
        return test_result("Supabase Connection", False, str(e)[:100])

def test_transcript_extraction():
    """Test 4: Transcript Extraction"""
    print("\n" + "="*60)
    print("TEST 4: Transcript Extraction (Multi-Strategy)")
    print("="*60)
    
    try:
        from agents import fetch_transcript
        
        # Test with a known public video (short)
        test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        
        print(f"{YELLOW}⏳ Testing transcript extraction (may take 10-30s)...{RESET}")
        transcript = fetch_transcript(test_url)
        
        success = len(transcript) > 50
        return test_result("Transcript Extraction", success, 
            f"Length: {len(transcript)} chars")
    except Exception as e:
        return test_result("Transcript Extraction", False, str(e)[:100])

def test_material_agent():
    """Test 5: Material Agent"""
    print("\n" + "="*60)
    print("TEST 5: Material Agent (AI Processing)")
    print("="*60)
    
    try:
        from agents import material_agent
        
        sample_transcript = """
        Agentic AI systems use multiple specialized agents. A supervisor agent 
        coordinates worker agents. Each worker handles specific tasks like 
        research or code generation.
        """
        
        print(f"{YELLOW}⏳ Generating materials (may take 5-10s)...{RESET}")
        # material_agent is async and takes 1 argument
        model_result = asyncio.run(material_agent(sample_transcript))
        result = model_result.model_dump()
        
        checks = [
            ("Has title", "title" in result),
            ("Has summary", "summary" in result),
            ("Has concepts", "key_concepts" in result and len(result["key_concepts"]) > 0),
            ("Has scenarios", "transfer_scenarios" in result)
        ]
        
        results = [test_result(name, passed) for name, passed in checks]
        return all(results)
    except Exception as e:
        return test_result("Material Agent", False, str(e)[:100])

def test_storage_layer():
    """Test 6: Storage Layer"""
    print("\n" + "="*60)
    print("TEST 6: Storage Layer (CRUD Operations)")
    print("="*60)
    
    try:
        from storage_v2 import Storage
        from supabase import create_client
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        client = create_client(url, key)
        
        # Test requires a valid user_id for RLS - using a dummy or fetching if possible
        # For sanity test, we might just check if we can initialize it
        storage = Storage(user_id="00000000-0000-0000-0000-000000000000", client=client)
        
        # Test video save
        video_id = storage.save_video(
            "https://youtube.com/test",
            "Test Video",
            "Test transcript"
        )
        
        success = video_id is not None
        return test_result("Storage Operations", success, 
            f"Video ID: {video_id[:8] if video_id else 'None'}...")
    except Exception as e:
        return test_result("Storage Operations", False, str(e)[:100])

def main():
    print("\n" + "🧪 " + "="*58)
    print("   YOUTUBE LEARNING ORCHESTRATOR - SANITY TEST SUITE")
    print("="*60 + "\n")
    
    tests = [
        ("Environment Setup", test_env_vars),
        ("OpenAI Integration", test_openai_connection),
        ("Database Layer", test_supabase_connection),
        ("Transcript Engine", test_transcript_extraction),
        ("AI Agents", test_material_agent),
        ("Storage Layer", test_storage_layer)
    ]
    
    results = {}
    for name, test_func in tests:
        try:
            results[name] = test_func()
        except Exception as e:
            print(f"\n{RED}CRITICAL ERROR in {name}: {e}{RESET}")
            results[name] = False
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    passed = sum(results.values())
    total = len(results)
    
    for name, result in results.items():
        status = f"{GREEN}✓{RESET}" if result else f"{RED}✗{RESET}"
        print(f"{status} {name}")
    
    print("\n" + "="*60)
    if passed == total:
        print(f"{GREEN}ALL TESTS PASSED ({passed}/{total}){RESET}")
        print("✅ System is production-ready!")
    else:
        print(f"{YELLOW}PARTIAL SUCCESS ({passed}/{total}){RESET}")
        print(f"⚠️  {total - passed} test(s) failed - review above for details")
    print("="*60 + "\n")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
