import os
from typing import Dict, Any, List, Optional
from supabase import create_client, Client
import logging

logger = logging.getLogger(__name__)

class Storage:
    def __init__(self, user_id: Optional[str] = None, client: Optional[Client] = None):
        if client:
            self.client = client
        else:
            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_KEY")
            if not url or not key:
                self.client = None
                logger.error("Supabase credentials missing.")
            else:
                self.client = create_client(url, key)
        self.user_id = user_id

    def set_user(self, user_id: str, client: Optional[Client] = None):
        """Update authenticated user context and optionally the client."""
        self.user_id = user_id
        if client:
            self.client = client

    def ensure_user(self, user_id: str, email: str) -> bool:
        """Ensures the user exists in the public users table for foreign key integrity."""
        if not self.client: return False
        try:
            self.client.table("users").upsert({
                "id": user_id,
                "email": email,
                "last_login": "now()"
            }).execute()
            return True
        except Exception as e:
            logger.error(f"Error syncing user {user_id}: {e}")
            return False

    # --- Video & Modules ---
    def save_video(self, url: str, title: str, transcript: str) -> Optional[str]:
        if not self.client: 
            logger.error("No Supabase client available")
            return None
        try:
            res = self.client.table("videos").upsert({
                "youtube_url": url,
                "title": title,
                "transcript": transcript,
                "processed_status": "completed"
            }, on_conflict="youtube_url").execute()
            return res.data[0]["id"] if res.data else None
        except Exception as e:
            logger.error(f"Error saving video: {e}")
            return None

    def save_module(self, video_id: str, module_data: Dict[str, Any]) -> Optional[str]:
        if not self.client: return None
        try:
            res = self.client.table("modules").insert({
                "video_id": video_id,
                "title": module_data["title"],
                "summary": module_data["summary"],
                "key_concepts": module_data["key_concepts"],
                "transfer_scenarios": module_data["transfer_scenarios"]
            }).execute()
            return res.data[0]["id"] if res.data else None
        except Exception as e:
            logger.error(f"Error saving module: {e}")
            return None

    # --- Roadmap ---
    def save_roadmap(self, sequence: List[Dict[str, Any]]) -> bool:
        if not self.client or not self.user_id: return False
        try:
            self.client.table("roadmaps").upsert({
                "user_id": self.user_id,
                "sequence": sequence
            }, on_conflict="user_id").execute()
            return True
        except Exception as e:
            logger.error(f"Error saving roadmap for user {self.user_id}: {e}")
            return False

    def get_roadmap(self) -> Optional[Dict[str, Any]]:
        if not self.client or not self.user_id: return None
        try:
            res = self.client.table("roadmaps").select("*").eq("user_id", self.user_id).order("created_at", desc=True).limit(1).execute()
            return res.data[0] if res.data else None
        except Exception as e:
            logger.error(f"Error fetching roadmap: {e}")
            return None

    # --- Sessions ---
    def create_session(self, module_id: str) -> Optional[str]:
        if not self.client or not self.user_id: return None
        try:
            res = self.client.table("sessions").insert({
                "user_id": self.user_id,
                "module_id": module_id,
                "status": "in_progress"
            }).execute()
            return res.data[0]["id"] if res.data else None
        except Exception as e:
            logger.error(f"Error creating session: {e}")
            return None

    def update_session(self, session_id: str, updates: Dict[str, Any]) -> bool:
        if not self.client: return False
        try:
            self.client.table("sessions").update(updates).eq("id", session_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error updating session: {e}")
            return False

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        if not self.client: return None
        try:
            res = self.client.table("sessions").select("*, modules(*)").eq("id", session_id).execute()
            return res.data[0] if res.data else None
        except Exception as e:
            logger.error(f"Error fetching session: {e}")
            return None

    def get_module(self, module_id: str) -> Optional[Dict[str, Any]]:
        if not self.client: return None
        try:
            res = self.client.table("modules").select("*").eq("id", module_id).execute()
            return res.data[0] if res.data else None
        except Exception as e:
            logger.error(f"Error fetching module: {e}")
            return None
