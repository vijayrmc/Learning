import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

def test():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    print(f"URL: {url}")
    # print(f"KEY: {key}") # Don't print secret
    
    try:
        supabase = create_client(url, key)
        res = supabase.table("videos").select("count").execute()
        print(f"✅ Connection successful. Videos count: {res.data}")
    except Exception as e:
        print(f"❌ Connection failed: {e}")

if __name__ == "__main__":
    test()
