import asyncio
from typing import List, Dict, Any, Optional
from agents import material_agent, roadmap_agent, coach_agent, fetch_transcript
from storage_v2 import Storage
import logging

logger = logging.getLogger(__name__)

class YouTubeOrchestrator:
    def __init__(self, user_id: str, storage: Optional[Storage] = None):
        self.user_id = user_id
        self.storage = storage or Storage(user_id)

    async def register_videos(self, urls: List[str]) -> Dict[str, Any]:
        """Ingests videos and creates a roadmap. Returns status and errors."""
        modules_meta = []
        errors = []
        
        for url in urls:
            try:
                transcript = fetch_transcript(url)
                if not transcript:
                    errors.append({"url": url, "error": "No transcript available"})
                    continue
                
                # 1. Extract Materials
                module_obj = await material_agent(transcript)
                video_id = self.storage.save_video(url, module_obj.title, transcript)
                
                if not video_id:
                    errors.append({"url": url, "error": "Failed to save video"})
                    continue
                
                # 2. Save Module
                module_id = self.storage.save_module(video_id, module_obj.model_dump())
                if module_id:
                    modules_meta.append({
                        "module_id": module_id,
                        "title": module_obj.title,
                        "summary": module_obj.summary
                    })
                else:
                    errors.append({"url": url, "error": "Failed to save module"})
                    
            except Exception as e:
                logger.error(f"Error processing {url}: {e}")
                errors.append({"url": url, "error": str(e)})

        # 3. Build Roadmap
        if modules_meta:
            try:
                roadmap_obj = await roadmap_agent(modules_meta)
                success = self.storage.save_roadmap(roadmap_obj.model_dump()["modules"])
                return {
                    "success": success,
                    "modules_count": len(modules_meta),
                    "errors": errors
                }
            except Exception as e:
                logger.error(f"Error creating roadmap: {e}")
                return {"success": False, "error": str(e), "errors": errors}
        
        return {"success": False, "error": "No modules created", "errors": errors}

    async def start_session(self, module_id: str) -> Optional[str]:
        """Starts a learning session for a module."""
        return self.storage.create_session(module_id)

    async def handle_reconstruction(self, session_id: str, explanation: str) -> Dict[str, Any]:
        """Step 2 & 4: Handle user's attempt to explain the concept. Forces progress after 3 attempts."""
        try:
            session = self.storage.get_session(session_id)
            if not session:
                return {"error": "Session not found"}
            
            concept = session["modules"]["title"]
            current_status = session.get("status", "in_progress")
            attempts = session.get("reconstruction_attempts", 0)
            
            # Increment attempts immediately
            self.storage.increment_reconstruction_attempts(session_id)
            attempts += 1
            
            result = await coach_agent("RECONSTRUCTION", {"concept": concept}, explanation)
            
            # Transition Logic with Cost Guardrail (Max 3 attempts per stage)
            new_status = current_status
            forced_pass = False
            
            if attempts >= 3 and not result["is_valid"]:
                forced_pass = True
                result["is_valid"] = True
                result["feedback"] = "MAX ATTEMPTS REACHED. Forcing progression to prevent loop."
            
            if current_status == "in_progress" or current_status == "reconstruction_1":
                if result["is_valid"]:
                    new_status = "attack"
                else:
                    new_status = "reconstruction_1"
            elif current_status == "reconstruction_2":
                # Step 4: Repair
                if result["is_valid"]:
                    new_status = "gated_unlock"
                else:
                    new_status = "reconstruction_2"

            updates = {"status": new_status}
            if current_status == "reconstruction_2":
                updates["repaired_explanation"] = explanation
            else:
                updates["initial_explanation"] = explanation
                
            self.storage.update_session(session_id, updates)
            result["attempts"] = attempts
            result["forced_pass"] = forced_pass
            return result
        except Exception as e:
            logger.error(f"Error in reconstruction: {e}")
            return {"error": str(e)}

    async def get_attack_question(self, session_id: str) -> Dict[str, Any]:
        """Step 3: Get an adversarial challenge. Also capped attempts."""
        try:
            session = self.storage.get_session(session_id)
            if not session:
                return {"error": "Session not found"}
            
            self.storage.increment_attack_attempts(session_id)
            
            explanation = session.get("initial_explanation", "")
            # Re-analyze for gaps specifically for the attack
            analysis = await coach_agent("RECONSTRUCTION", {"concept": session["modules"]["title"]}, explanation)
            
            attack = await coach_agent("ATTACK", {
                "explanation": explanation, 
                "gaps": analysis.get("gaps", [])
            })
            
            self.storage.update_session(session_id, {
                "attack_feedback": [attack],
                "status": "reconstruction_2" # Move to repair stage
            })
            return attack
        except Exception as e:
            logger.error(f"Error getting attack question: {e}")
            return {"error": str(e)}

    async def handle_transfer(self, session_id: str, attempt: str) -> Dict[str, Any]:
        """Step 7: Handle user's application/transfer attempt."""
        try:
            session = self.storage.get_session(session_id)
            if not session:
                return {"error": "Session not found"}
            
            # Here we could add AI feedback on the transfer attempt if desired.
            # For now, we just save it and move to quiz.
            
            self.storage.update_session(session_id, {
                "transfer_attempt": attempt,
                "status": "quiz"
            })
            return {"status": "success", "next_step": "quiz"}
        except Exception as e:
            logger.error(f"Error handling transfer: {e}")
            return {"error": str(e)}

    async def get_generative_quiz(self, session_id: str) -> Dict[str, Any]:
        """Step 8: Generate a 10-question open-ended quiz."""
        try:
            session = self.storage.get_session(session_id)
            if not session: return {"error": "Session not found"}
            
            module = session["modules"]
            quiz = await coach_agent("GEN_QUIZ", {
                "concept": module["title"],
                "summary": module["summary"]
            })
            
            self.storage.update_session(session_id, {"status": "quiz"})
            return quiz
        except Exception as e:
            logger.error(f"Error generating quiz: {e}")
            return {"error": str(e)}

    async def complete_session(self, session_id: str) -> Dict[str, Any]:
        """Finalize the session."""
        try:
            self.storage.update_session(session_id, {
                "status": "completed",
                "completed_at": "now()"
            })
            return {"status": "success"}
        except Exception as e:
            logger.error(f"Error completing session: {e}")
            return {"error": str(e)}
