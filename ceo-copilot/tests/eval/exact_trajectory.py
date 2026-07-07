"""Code-based metric to perform EXACT trajectory evaluation on tool calls."""

def evaluate(instance):
    # Retrieve expected tool calls from the case definition (default to empty list)
    expected_tool_calls = instance.get("expected_tool_calls", [])
    
    # Retrieve the agent trajectory turns
    agent_data = instance.get("agent_data") or {}
    turns = agent_data.get("turns", [])
    
    actual_tool_calls = []
    for turn in turns:
        events = turn.get("events", [])
        for event in events:
            # We only care about function calls made by model/agents
            content = event.get("content") or {}
            parts = content.get("parts") or []
            for part in parts:
                if "function_call" in part:
                    fn_name = part["function_call"].get("name")
                    if fn_name:
                        actual_tool_calls.append(fn_name)
                        
    # Exact match comparison
    if actual_tool_calls == expected_tool_calls:
        return {
            "score": 5.0,
            "explanation": f"Exact match! Expected: {expected_tool_calls}, Actual: {actual_tool_calls}."
        }
    else:
        return {
            "score": 1.0,
            "explanation": f"Trajectory mismatch. Expected: {expected_tool_calls}, Actual: {actual_tool_calls}."
        }
