"""
Migration script to clean database and apply schema v2.
Run this in your Supabase SQL Editor.
"""

-- Step 1: Drop all existing tables (CAUTION: This deletes all data!)
DROP TABLE IF EXISTS progress CASCADE;
DROP TABLE IF EXISTS sessions CASCADE;
DROP TABLE IF EXISTS roadmaps CASCADE;
DROP TABLE IF EXISTS modules CASCADE;
DROP TABLE IF EXISTS videos CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- Step 2: Apply new schema
-- Copy and paste the contents of schema_v2.sql here, or run it separately
