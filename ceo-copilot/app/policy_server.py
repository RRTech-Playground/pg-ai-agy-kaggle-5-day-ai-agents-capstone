import os
import re
import yaml
import json
import logging
from typing import Any, Optional
from google.adk.plugins.base_plugin import BasePlugin
from google.adk.tools import BaseTool, ToolContext
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

class PolicyServerPlugin(BasePlugin):
    """
    Context-as-a-Perimeter security harness middleware.
    Intercepts tool calls to perform structural checks (policies.yaml)
    and semantic checks (Gemini scan for PII/credentials/confidential data).
    """

    def __init__(self, policies_path: str = "specs/policies.yaml"):
        super().__init__(name="policy_server")
        self.policies_path = policies_path
        self.policies = self._load_policies()
        # Initialize the secondary Gemini model client
        self.genai_client = genai.Client()

    def _load_policies(self) -> dict:
        """Loads and parses the policies.yaml file."""
        path = self.policies_path
        if not os.path.isabs(path):
            # Try to resolve path relative to project root
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            resolved_path = os.path.join(project_root, path)
            if os.path.exists(resolved_path):
                path = resolved_path

        if not os.path.exists(path):
            logger.warning(f"Policies file not found at: {path}. Using default empty policy.")
            return {}

        try:
            with open(path, "r") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.error(f"Failed to parse policies file: {e}")
            return {}

    async def before_tool_callback(
        self,
        *,
        tool: BaseTool,
        tool_args: dict[str, Any],
        tool_context: ToolContext,
    ) -> Optional[dict]:
        """
        Callback executed before any tool is executed.
        Returns a dictionary containing the error details if policy is violated.
        """
        tool_name = tool.name
        logger.info(f"Intercepted tool call: {tool_name} with args: {tool_args}")

        # Reload policies dynamically to capture updates without restarting
        self.policies = self._load_policies()

        # ----------------------------------------------------
        # 1. Structural Check
        # ----------------------------------------------------

        # Localhost checks
        is_localhost = os.getenv("ENV", "localhost").lower() == "localhost"
        if is_localhost:
            localhost_policies = self.policies.get("environments", {}).get("localhost", {})
            blocked_tools = localhost_policies.get("blocked_tools", [])
            if tool_name in blocked_tools:
                reason = f"Security Violation: Tool '{tool_name}' is blocked in localhost environment."
                logger.warning(reason)
                return {
                    "error": reason,
                    "status": "blocked",
                    "code": "POLICY_VIOLATION_STRUCTURAL"
                }

        # Agent read-only checks
        agent_policies = self.policies.get("agents", {}).get("executive_agent", {})
        if not agent_policies:
            agent_policies = self.policies.get("agents", {}).get("root_agent", {})

        if agent_policies and agent_policies.get("restrict_to_read_only", True):
            blocked_write_patterns = agent_policies.get("blocked_write_patterns", [])
            for pattern in blocked_write_patterns:
                if re.search(pattern, tool_name):
                    reason = f"Security Violation: Executive agent is restricted to read-only. Tool '{tool_name}' violates write pattern '{pattern}'."
                    logger.warning(reason)
                    return {
                        "error": reason,
                        "status": "blocked",
                        "code": "POLICY_VIOLATION_READ_ONLY"
                    }

        # ----------------------------------------------------
        # 2. Semantic Check
        # ----------------------------------------------------
        if tool_args:
            prompt = f"""
            Analyze the following tool call arguments for security policy violations.
            Tool Name: {tool_name}
            Arguments: {json.dumps(tool_args, default=str)}

            Scan and detect:
            1. Unmasked PII (SSNs, credit card numbers, personal phone numbers, physical addresses - mock/test values are okay).
            2. Unmasked credentials (passwords, API keys, bearer tokens, secrets).
            3. Confidential business strings (sensitive internal project names, confidential financial targets, proprietary algorithms, private API endpoints).

            You must respond ONLY with a JSON object in this format:
            {{
              "violation": true/false,
              "reason": "explanation of violation or empty string"
            }}
            """
            try:
                # Ensure the secondary model call uses 'global' location if configured
                response = self.genai_client.models.generate_content(
                    model="gemini-3.5-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                    )
                )
                res_json = json.loads(response.text.strip())
                if res_json.get("violation"):
                    reason = f"Security Violation: {res_json.get('reason')}"
                    logger.warning(reason)
                    return {
                        "error": reason,
                        "status": "blocked",
                        "code": "POLICY_VIOLATION_SEMANTIC"
                    }
            except Exception as e:
                # Fail closed on security scan failure
                reason = f"Security Violation: Semantic security scan failed: {str(e)}"
                logger.error(reason)
                return {
                    "error": reason,
                    "status": "blocked",
                    "code": "POLICY_VIOLATION_SCAN_ERROR"
                }

        # Pass through if all checks pass
        return None
