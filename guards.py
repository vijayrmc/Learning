from typing import List, Dict, Any, Tuple

class RoadmapGuard:
    @staticmethod
    def validate(roadmap: Dict[str, Any], profile: Dict[str, Any]) -> Tuple[bool, str]:
        # Enforce DAG
        # For simplicity in MVP, we might just check structure.
        # Real DAG check requires checking dependencies.
        # Assuming roadmap has 'weeks' and 'concepts' references.
        
        if "weeks" not in roadmap:
            return False, "Missing 'weeks' in roadmap"

        total_sessions = 0
        for week in roadmap["weeks"]:
             total_sessions += len(week.get("sessions", []))
        
        # Estimate hours: 20 mins per session = 1/3 hour
        total_hours = (total_sessions * 20) / 60
        max_hours = profile.get("hours_week", 3) * profile.get("weeks", 4)
        
        if total_hours > max_hours * 1.5: # Allow some buffer
            return False, f"Time budget exceeded: {total_hours:.1f}h > {max_hours}h"
        
        return True, "OK"

class SessionGuard:
    @staticmethod
    def validate_session_result(result: Dict[str, Any]) -> Tuple[bool, str]:
        if "practice_attempts" in result: # If result structure follows prompt exactly
             if len(result["practice_attempts"]) < 3:
                return False, "Insufficient practice"
        
        # Check engagement if present
        if result.get("engagement", 1.0) < 0.5:
            return False, "Low engagement"
            
        return True, "OK"
