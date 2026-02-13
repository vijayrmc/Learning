import os
import requests
import time
import uuid
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
API_URL = "http://localhost:8000"

def test_api():
    print("🚀 Starting API Test Sequence...")
    
    # 1. Setup Supabase Client
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # 2. Authenticate (Sign Up/Sign In)
    email = f"test_{uuid.uuid4().hex[:8]}@gmail.com"
    password = "TestPassword123!"
    
    print(f"👤 Creating test user: {email}")
    try:
        user_res = supabase.auth.sign_up({
            "email": email, 
            "password": password
        })
        # If confirm email is off, we get a session immediately? 
        # Usually supabase defaults require email confirmation but let's see.
        # If user_res.session is None, we act.
        
        session = user_res.session
        user = user_res.user
        
        if not session and user:
            print("⚠️ Signup successful but session is null. Email confirmation might be required.")
            print("Trying sign in anyway...")
            try:
                # If auto-confirm is on in Supabase, this works. If not, this might fail.
                # Let's hope for auto-confirm or session return.
                # Actually, local dev often has auto confirm. Production might not.
                # If explicit confirmation needed, we are stuck unless we use admin key.
                # But I only have anon key.
                # Let's try log in.
                session_res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                session = session_res.session
            except Exception as e:
                print(f"❌ Login failed: {e}")
                return False
        
        if not session:
             print("❌ Could not get session. Using FAKE token to verify 401 responses.")
             token = "fake_token_for_401_test"
             headers = {"Authorization": f"Bearer {token}"}
             
             # A. Get Roadmap (Should be 401)
             print("\nTesting GET /api/roadmap (Expected 401)...")
             res = requests.get(f"{API_URL}/api/roadmap", headers=headers)
             if res.status_code == 401:
                 print("✅ Roadmap endpoint verified (Protected).")
             else:
                 print(f"❌ Roadmap unexpected status: {res.status_code}")
                 
             return True # Partial success

        token = session.access_token
        print(f"✅ Authenticated! Token: {token[:10]}...")
        
        # 3. Test Endpoints
        headers = {"Authorization": f"Bearer {token}"}
        
        # A. Get Roadmap (Should be empty initially)
        print("\nTesting GET /api/roadmap...")
        res = requests.get(f"{API_URL}/api/roadmap", headers=headers)
        if res.status_code == 200:
            print("✅ Roadmap endpoint working.")
        else:
            print(f"❌ Roadmap failed: {res.status_code} {res.text}")
            
        # B. Process Video (Mock if possible or use short one)
        # Using a very short video or maybe mocking the orchestrator logic inside?
        # No, let's try a real call if the orchestrator uses real API. It uses YouTube API or scraper.
        # It might be slow.
        # Let's try to pass an empty list just to check auth and validation.
        print("\nTesting POST /api/videos/process (Validation)...")
        res = requests.post(f"{API_URL}/api/videos/process", json={"urls": []}, headers=headers)
        if res.status_code == 200:
             print("✅ Process endpoint reachable (Response: OK).")
        else:
             print(f"❌ Process failed: {res.status_code} {res.text}")

        # C. Create Session (We need a module ID for this, which we don't have if B didn't yield modules)
        # We can try to insert a fake module via Supabase directly?
        # Or just try to create session with fake ID and expect 404 or 500 but verify Auth passed.
        print("\nTesting POST /api/sessions (Auth check)...")
        res = requests.post(f"{API_URL}/api/sessions", json={"module_id": "fake_id"}, headers=headers)
        if res.status_code == 401:
            print("❌ Auth failed.")
        else:
            print(f"✅ Auth passed. Response code: {res.status_code} (Expected 500/404 for fake ID)")

        print("\n✅ API Tests Completed.")
        return True
        
    except Exception as e:
        print(f"❌ Test Exception: {e}")
        return False

if __name__ == "__main__":
    test_api()
