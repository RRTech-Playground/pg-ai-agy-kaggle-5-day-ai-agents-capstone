#!/usr/bin/env python3
"""CI script to run agents-cli eval and enforce quality gates + stop-ship constraints."""

import sys
import os
import glob
import json
import subprocess

def check_for_hacks():
    """Verify that there are no hacks faking tests or bypassing verification."""
    print("Checking for test hacks or bypasses...")
    suspicious_patterns = [
        "unittest.mock.patch",
        "mock.patch",
        "disable-edd",
        "skip-ci",
        "bypass-eval"
    ]
    
    # Files to check
    files_to_check = []
    for root, _, files in os.walk("."):
        if ".venv" in root or ".git" in root or ".pytest_cache" in root or "artifacts" in root:
            continue
        for file in files:
            if "run_eval_ci" in file:
                continue
            if file.endswith(".py") or file.endswith(".sh") or file.endswith(".yaml"):
                files_to_check.append(os.path.join(root, file))
                
    for filepath in files_to_check:
        try:
            with open(filepath, "r", errors="ignore") as f:
                content = f.read()
                for pattern in suspicious_patterns:
                    if pattern in content:
                        print(f"CRITICAL STOP-SHIP: Suspicious pattern '{pattern}' found in {filepath}!")
                        sys.exit(1)
        except Exception as e:
            print(f"Warning: Could not read {filepath}: {e}")

def run_eval_suite():
    """Executes the agents-cli evaluation run."""
    print("Running evaluation suite via agents-cli...")
    cmd = [
        "uv", "run", "agents-cli", "eval", "run",
        "--dataset", "evals/golden_dataset.json",
        "--config", "tests/eval/eval_config.yaml",
        "--output", "artifacts/grade_results"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    print("--- Eval stdout ---")
    print(result.stdout)
    print("--- Eval stderr ---")
    print(result.stderr)
    
    if result.returncode != 0:
        print("CRITICAL STOP-SHIP: agents-cli eval run failed to execute successfully!")
        sys.exit(result.returncode)

def verify_results():
    """Locates and parses the latest results JSON file to check scores."""
    print("Verifying evaluation results...")
    results_pattern = os.path.join("artifacts", "grade_results", "results_*.json")
    files = glob.glob(results_pattern)
    if not files:
        print("CRITICAL STOP-SHIP: No evaluation results JSON file found!")
        sys.exit(1)
        
    # Get the latest modified file
    latest_file = max(files, key=os.path.getmtime)
    print(f"Loading results from: {latest_file}")
    
    with open(latest_file, "r") as f:
        data = json.load(f)
        
    eval_case_results = data.get("eval_case_results", [])
    eval_cases = data.get("evaluation_dataset", [{}])[0].get("eval_cases", [])
    
    if not eval_case_results:
        print("CRITICAL STOP-SHIP: No evaluation cases were processed in results!")
        sys.exit(1)
        
    failures = 0
    for item in eval_case_results:
        idx = item.get("eval_case_index")
        original_case = eval_cases[idx] if idx < len(eval_cases) else {}
        case_id = original_case.get("eval_case_id", f"index_{idx}")
        
        cand_results = item.get("response_candidate_results", [{}])[0]
        metrics = cand_results.get("metric_results", {})
        
        # Check Exact Trajectory
        exact_traj = metrics.get("exact_trajectory_evaluation", {})
        exact_score = exact_traj.get("score", 0.0)
        
        # Check LLM Judge
        llm_judge = metrics.get("edd_llm_judge", {})
        llm_score = llm_judge.get("score", 0.0)
        
        print(f"Case: {case_id}")
        print(f"  - Exact Trajectory score: {exact_score}/5.0")
        print(f"  - LLM Judge score: {llm_score}/5.0")
        
        if exact_score < 5.0:
            print(f"  [FAIL] Exact Trajectory failed match for case {case_id}")
            failures += 1
        if llm_score < 4.0:
            # Note: For Case 2 & 3, since bias mitigation isn't applicable,
            # they might score lower naturally until we have the final agent.
            # During setup phase, we still flag them to establish the EDD baseline.
            print(f"  [FAIL] LLM Judge score too low for case {case_id}")
            failures += 1
            
    if failures > 0:
        print(f"CRITICAL STOP-SHIP: {failures} metric quality gate failures detected!")
        sys.exit(1)
        
    print("Success: All evaluation cases passed quality gates!")

def main():
    check_for_hacks()
    run_eval_suite()
    verify_results()

if __name__ == "__main__":
    main()
