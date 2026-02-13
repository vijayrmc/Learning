# Quick Setup Guide

## Step 1: Get OpenAI API Key
1. Go to https://platform.openai.com/api-keys
2. Click "Create new secret key"
3. Copy the key (starts with `sk-proj-...`)
4. Add to `.env`: `OPENAI_API_KEY=sk-proj-...`

## Step 2: Setup Supabase
1. Create account at https://supabase.com
2. Click "New Project"
3. Choose a name, database password, and region
4. Wait ~2 minutes for project to initialize

### Get Supabase Credentials
1. Go to Project Settings (⚙️ icon) → API
2. Copy **Project URL** → Add to `.env`: `SUPABASE_URL=https://xxx.supabase.co`
3. Copy **anon public** key → Add to `.env`: `SUPABASE_KEY=eyJ...`

### Initialize Database
1. Go to SQL Editor in Supabase Dashboard
2. Click "New Query"
3. Copy entire contents of `schema.sql`
4. Paste and click "Run"
5. You should see: "Success. No rows returned"

### Enable Email Authentication
1. Go to Authentication → Providers
2. Enable "Email" provider
3. (Optional) Disable email confirmation for testing:
   - Go to Authentication → Settings
   - Turn off "Enable email confirmations"

## Step 3: Create .env File
```bash
# Copy the example file
cp .env.example .env

# Edit .env with your actual keys
# (Use notepad, VS Code, or any text editor)
```

## Step 4: Install & Run
```bash
pip install -r requirements.txt
python verify_setup.py  # Check everything is configured
streamlit run app.py    # Launch the app
```

## Your .env Should Look Like:
```env
OPENAI_API_KEY=sk-proj-abc123...
SUPABASE_URL=https://abcdefgh.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

## Troubleshooting
- **"Missing environment variables"**: Check `.env` file exists and has all 3 keys
- **"Supabase connection failed"**: Make sure you ran `schema.sql`
- **"OpenAI API failed"**: Check your API key is valid and has credits
