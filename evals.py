"""
Automated Evaluation System for YouTube Learning Orchestrator
Uses golden datasets and LLM-as-judge for quality metrics.
"""

import json
from typing import Dict, List, Any
from openai import OpenAI
import os

class EvalSystem:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    # --- Eval 1: Concept Coverage ---
    def eval_concept_coverage(self, transcript: str, extracted_concepts: List[str]) -> Dict[str, Any]:
        """
        Measures if extracted concepts cover the key ideas in the transcript.
        Uses LLM-as-judge.
        """
        prompt = f"""
        Transcript (first 2000 chars): {transcript[:2000]}
        
        Extracted Concepts: {json.dumps(extracted_concepts)}
        
        Task: Rate the concept coverage on a scale of 0-1.
        - 1.0 = All major ideas captured
        - 0.5 = Half the ideas missing
        - 0.0 = Completely off-topic
        
        Output ONLY JSON: {{"coverage_score": 0.0-1.0, "missing_concepts": ["..."]}}
        """
        
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    
    # --- Eval 2: Vagueness Detection ---
    def eval_vagueness(self, explanation: str) -> Dict[str, Any]:
        """
        Detects vague phrases like 'basically', 'stuff', 'kind of'.
        Deterministic + LLM hybrid.
        """
        vague_phrases = ["basically", "stuff", "kind of", "sort of", "things", "etc"]
        detected = [p for p in vague_phrases if p in explanation.lower()]
        
        # LLM check for semantic vagueness
        prompt = f"""
        User explanation: {explanation}
        
        Rate vagueness on 0-1 scale:
        - 0.0 = Precise, specific
        - 1.0 = Extremely vague
        
        Output JSON: {{"vagueness_score": 0.0-1.0, "reason": "..."}}
        """
        
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        llm_result = json.loads(response.choices[0].message.content)
        
        return {
            "vague_phrases_detected": detected,
            "vagueness_score": llm_result["vagueness_score"],
            "reason": llm_result["reason"]
        }
    
    # --- Eval 3: Repair Delta ---
    def eval_repair_delta(self, initial: str, repaired: str) -> Dict[str, Any]:
        """
        Measures meaningful change between initial and repaired explanations.
        """
        prompt = f"""
        Initial: {initial}
        Repaired: {repaired}
        
        Did the user make SUBSTANTIVE changes (not just rephrasing)?
        
        Output JSON: {{"repair_delta": 0.0-1.0, "substantive_changes": ["..."]}}
        - 0.0 = Just rephrased
        - 1.0 = Deep conceptual revision
        """
        
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    
    # --- Eval 4: Transfer Success ---
    def eval_transfer(self, concept: str, scenario: str, user_attempt: str) -> Dict[str, Any]:
        """
        Judges if user correctly applied concept to novel scenario.
        """
        prompt = f"""
        Concept: {concept}
        Novel Scenario: {scenario}
        User Attempt: {user_attempt}
        
        Did the user correctly apply the concept?
        
        Output JSON: {{"transfer_success": true/false, "correctness": 0.0-1.0, "feedback": "..."}}
        """
        
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)


# --- Golden Dataset ---
GOLDEN_DATASET = [
    {
        "id": "test_1",
        "transcript": "Agentic AI systems use multiple specialized agents. A supervisor agent coordinates worker agents. Each worker handles a specific task like research or code generation.",
        "expected_concepts": ["Agentic AI", "Supervisor agent", "Worker agents", "Task specialization"],
        "vague_explanation": "Basically, agentic AI is like when you have stuff that does things and coordinates other things.",
        "precise_explanation": "Agentic AI uses a supervisor agent to coordinate multiple worker agents, each specialized for specific tasks like research or code generation.",
        "transfer_scenario": "Design an agentic system for a restaurant kitchen.",
        "correct_transfer": "The head chef acts as the supervisor agent, coordinating specialized workers: prep cook (ingredient preparation), line cook (cooking), and expediter (plating and delivery)."
    },
    {
        "id": "test_2",
        "transcript": "Guardrails in AI prevent harmful outputs. Input guardrails validate user requests. Output guardrails check model responses before showing them to users.",
        "expected_concepts": ["Guardrails", "Input validation", "Output validation", "Safety"],
        "vague_explanation": "Guardrails are kind of like safety things that check stuff.",
        "precise_explanation": "Guardrails are safety mechanisms with two types: input guardrails that validate user requests, and output guardrails that verify model responses before delivery.",
        "transfer_scenario": "Apply guardrails to a financial advice chatbot.",
        "correct_transfer": "Input guardrails reject requests for illegal activities. Output guardrails block responses that give specific stock picks or guarantee returns."
    }
]


def run_golden_set_eval():
    """Run automated evals on golden dataset."""
    evaluator = EvalSystem()
    results = []
    
    for item in GOLDEN_DATASET:
        print(f"\n=== Evaluating {item['id']} ===")
        
        # Test 1: Concept Coverage
        coverage = evaluator.eval_concept_coverage(item["transcript"], item["expected_concepts"])
        print(f"Concept Coverage: {coverage['coverage_score']}")
        
        # Test 2: Vagueness Detection
        vague_result = evaluator.eval_vagueness(item["vague_explanation"])
        precise_result = evaluator.eval_vagueness(item["precise_explanation"])
        print(f"Vague Score: {vague_result['vagueness_score']}, Precise Score: {precise_result['vagueness_score']}")
        
        # Test 3: Transfer
        transfer = evaluator.eval_transfer(
            ", ".join(item["expected_concepts"]),
            item["transfer_scenario"],
            item["correct_transfer"]
        )
        print(f"Transfer Success: {transfer['transfer_success']}")
        
        results.append({
            "test_id": item["id"],
            "coverage": coverage,
            "vagueness_vague": vague_result,
            "vagueness_precise": precise_result,
            "transfer": transfer
        })
    
    # Save results
    with open("eval_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print("\n✅ Eval complete. Results saved to eval_results.json")


if __name__ == "__main__":
    run_golden_set_eval()
