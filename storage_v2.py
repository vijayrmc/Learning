import os
from typing import Dict, Any, List, Optional
from supabase import create_client, Client
import logging

logger = logging.getLogger(__name__)

class Storage:
    """
    Clean storage layer for YouTube Learning Orchestrator v2.
    Requires an authenticated Supabase client to respect RLS policies.
    """
    
    def __init__(self, user_id: str, client: Client):
        """
        Initialize storage with authenticated client.
        
        Args:
            user_id: The authenticated user's ID (from auth.uid())
            client: Authenticated Supabase client instance
        """
        self.client = client
        self.user_id = user_id

    # --- Video & Modules ---
    def save_video(self, url: str, title: str, transcript: str) -> Optional[str]:
        """Save or update a video. Returns video ID."""
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
        """Save a learning module. Returns module ID."""
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

    def get_module(self, module_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a module by ID."""
        try:
            res = self.client.table("modules").select("*").eq("id", module_id).execute()
            return res.data[0] if res.data else None
        except Exception as e:
            logger.error(f"Error fetching module: {e}")
            return None

    # --- Roadmap ---
    def save_roadmap(self, sequence: List[Dict[str, Any]]) -> bool:
        """Save or update user's roadmap."""
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
        """Get user's current roadmap."""
        try:
            res = self.client.table("roadmaps").select("*").eq("user_id", self.user_id).order("created_at", desc=True).limit(1).execute()
            return res.data[0] if res.data else None
        except Exception as e:
            logger.error(f"Error fetching roadmap: {e}")
            return None

    # --- Sessions ---
    def create_session(self, module_id: str) -> Optional[str]:
        """Create a new learning session. Returns session ID."""
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
        """Update session data."""
        try:
            self.client.table("sessions").update(updates).eq("id", session_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error updating session: {e}")
            return False

    def increment_reconstruction_attempts(self, session_id: str) -> bool:
        """Increments the reconstruction attempt counter for a session."""
        try:
            res = self.client.table("sessions").select("reconstruction_attempts").eq("id", session_id).execute()
            if res.data:
                count = res.data[0].get("reconstruction_attempts", 0) + 1
                self.client.table("sessions").update({"reconstruction_attempts": count}).eq("id", session_id).execute()
                return True
            return False
        except Exception as e:
            logger.error(f"Error incrementing reconstruction attempts: {e}")
            return False

    def increment_attack_attempts(self, session_id: str) -> bool:
        """Increments the attack attempt counter for a session."""
        try:
            res = self.client.table("sessions").select("attack_attempts").eq("id", session_id).execute()
            if res.data:
                count = res.data[0].get("attack_attempts", 0) + 1
                self.client.table("sessions").update({"attack_attempts": count}).eq("id", session_id).execute()
                return True
            return False
        except Exception as e:
            logger.error(f"Error incrementing attack attempts: {e}")
            return False

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session with module data."""
        try:
            res = self.client.table("sessions").select("*, modules(*)").eq("id", session_id).execute()
            return res.data[0] if res.data else None
        except Exception as e:
            logger.error(f"Error fetching session: {e}")
            return None

    # --- Progress ---
    def update_progress(self, module_id: str, mastery_score: float) -> bool:
        """Update or create progress record."""
        try:
            self.client.table("progress").upsert({
                "user_id": self.user_id,
                "module_id": module_id,
                "mastery_score": mastery_score
            }, on_conflict="user_id,module_id").execute()
            return True
        except Exception as e:
            logger.error(f"Error updating progress: {e}")
            return False

    def get_progress(self, module_id: str) -> Optional[Dict[str, Any]]:
        """Get user's progress for a module."""
        try:
            res = self.client.table("progress").select("*").eq("user_id", self.user_id).eq("module_id", module_id).execute()
            return res.data[0] if res.data else None
        except Exception as e:
            logger.error(f"Error fetching progress: {e}")
            return None
