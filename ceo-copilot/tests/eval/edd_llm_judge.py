"""LLM-as-judge for EDD evaluating Intent Satisfaction, Bias Mitigation, and Trajectory Quality."""

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

class EDDVerdict(BaseModel):
    intent_satisfaction_score: int = Field(description="Score from 1-5 on how well the user's intent was satisfied.")
    bias_mitigation_score: int = Field(description="Score from 1-5 on how well cognitive biases and tunnel vision were mitigated (e.g. using FORDEC framework to challenge rushed decisions).")
    trajectory_quality_score: int = Field(description="Score from 1-5 on trajectory quality, verifying that the agent checked external facts (e.g. searched using google_search_mcp) before rendering judgment.")
    explanation: str = Field(description="Detailed explanation justifying the scores across all three dimensions.")

def evaluate(instance):
    prompt_text = instance.get("prompt", "")
    response_text = instance.get("response", "")
    agent_data = instance.get("agent_data", {})
    
    judge_prompt = (
        "You are an expert QA evaluator for an executive decision co-pilot agent. "
        "Evaluate the agent's performance on the following task based on three dimensions:\n\n"
        "1. Intent Satisfaction (1-5): Did the agent successfully address the user's request?\n"
        "2. Bias Mitigation (1-5): Did the agent apply the aviation FORDEC framework, uncover cognitive biases (like confirmation bias or tunnel vision) or challenge rushed decisions?\n"
        "3. Trajectory Quality (1-5): Did the agent verify external facts (like checking market tech crash rumors) via search before rendering final judgment?\n\n"
        f"User Prompt: {prompt_text}\n"
        f"Final Response: {response_text}\n"
        f"Full Agent Trace: {agent_data}\n"
    )

    client = genai.Client()
    response = client.models.generate_content(
        model="gemini-3.5-flash",
        contents=judge_prompt,
        config=types.GenerateContentConfig(
            temperature=0,  # deterministic grading
            response_mime_type="application/json",
            response_schema=EDDVerdict,
        ),
    )
    
    verdict = response.parsed
    if verdict is None:
        return {"score": 0.0, "explanation": f"Failed to parse model response: {response.text}"}
    
    # Calculate overall average score
    avg_score = (verdict.intent_satisfaction_score + verdict.bias_mitigation_score + verdict.trajectory_quality_score) / 3.0
    
    detailed_explanation = (
        f"Intent Satisfaction: {verdict.intent_satisfaction_score}/5\n"
        f"Bias Mitigation: {verdict.bias_mitigation_score}/5\n"
        f"Trajectory Quality: {verdict.trajectory_quality_score}/5\n"
        f"Explanation: {verdict.explanation}"
    )
    
    return {
        "score": round(avg_score, 2),
        "explanation": detailed_explanation
    }
