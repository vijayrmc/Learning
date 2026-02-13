import asyncio
import os
import json
from orchestrator import LearningOrchestrator, LearningState
from agents import Concept
import agents

# Mock agents
async def mock_ingestion(urls, domain):
    print(f"[Mock] Ingesting {len(urls)} URLs for {domain}")
    return [
        Concept(id="concept_1", name="Intro to GenAI", difficulty=1, prereqs=[], content_refs=["url1"]),
        Concept(id="concept_2", name="Prompt Engineering", difficulty=2, prereqs=["concept_1"], content_refs=["url2"])
    ]

async def mock_curriculum(profile, concepts):
    print(f"[Mock] Building curriculum for {profile['weeks']} weeks")
    return {
        "roadmap_id": "mock_map",
        "weeks": [
            {
                "week": 1,
                "goals": ["concept_1"],
                "sessions": [
                    {"concept_id": "concept_1", "duration_min": 20, "session_id": "sess_1"}
                ]
            }
        ]
    }

async def mock_session(session_def, concept_name):
    print(f"[Mock] Coaching session for {concept_name}")
    return {
        "session_id": session_def.get("session_id"),
        "events": [{"type": "recall", "content": "What is AI?"}],
        "mastery_deltas": [],
        "engagement": 0.9
    }

# Patch orchestrator module where functions are imported
import orchestrator
orchestrator.ingestion_agent = mock_ingestion
orchestrator.curriculum_agent = mock_curriculum
orchestrator.session_coach_agent = mock_session

async def run_test():
    print("--- Starting Verification ---")
    
    # 1. Init
    orc = LearningOrchestrator("test_user_v1")
    # Reset state for test
    orc.data = {}
    orc.state = LearningState.PROFILE
    orc.save()
    
    print(f"State: {orc.state}")
    
    # 2. Profile -> Ingested
    res = await orc.next_step({
        "domain": "genai_pm",
        "goals": "Learn",
        "weeks": 4,
        "hours_week": 3
    })
    print(f"Result (Profile): {res}")
    assert orc.state == LearningState.INGESTED
    
    # 3. Ingested -> Roadmap
    res = await orc.next_step()
    print(f"Result (Ingest): {res}")
    assert orc.state == LearningState.ROADMAP
    assert len(orc.data["concepts"]) == 2
    
    # 4. Roadmap -> Scheduled
    res = await orc.next_step()
    print(f"Result (Roadmap): {res}")
    assert orc.state == LearningState.SCHEDULED
    assert "roadmap" in orc.data
    
    # 5. Scheduled -> Session
    res = await orc.next_step()
    print(f"Result (Schedule): {res}")
    assert orc.state == LearningState.SESSION
    
    # 6. Session -> Eval (Start Session)
    # The first call to SESSION state starts it (returns content) but doesn't transition
    res = await orc.next_step()
    print(f"Result (Start Session): {res.keys()}") 
    # Logic in orchestrator: if state=SESSION and input lacks result, just return content.
    assert "session_content" in res
    assert orc.state == LearningState.SESSION # Should stay in session
    
    # 7. Session -> Eval (Complete Session)
    # Orchestrator.complete_session() is the explicit completion method
    orc.complete_session({"start": "end", "engagement": 0.9, "practice": [1,2,3]})
    assert orc.state == LearningState.EVAL
    
    print("--- Verification Passed ---")

if __name__ == "__main__":
    asyncio.run(run_test())
