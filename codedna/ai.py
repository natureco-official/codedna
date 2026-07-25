"""
AI Analysis Layer - Interprets user command outputs using AI.

Supported providers:
  - Anthropic (Claude)
  - MiniMax
  - OpenAI

The key is used only for analysis, no chat/completion.
"""
import base64
import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

AI_CONFIG_PATH = Path.home() / ".codedna" / "ai_config.json"

# Provider list
PROVIDERS = ["anthropic", "minimax", "openai"]

# Default models
DEFAULT_MODELS = {
    "anthropic": "claude-sonnet-4-20250514",
    "minimax": "MiniMax-M2.5",
    "openai": "gpt-4o-mini",
}

# Provider API endpoints
API_ENDPOINTS = {
    "anthropic": "https://api.anthropic.com/v1/messages",
    "minimax": "https://api.minimax.io/v1/text/chatcompletion_v2",
    "openai": "https://api.openai.com/v1/chat/completions",
}


@dataclass
class AIConfig:
    """AI analysis configuration."""
    provider: str
    api_key: str
    model: str
    enabled: bool = True

    @classmethod
    def load(cls) -> Optional["AIConfig"]:
        """Load from config file."""
        if not AI_CONFIG_PATH.exists():
            return None
        try:
            data = json.loads(AI_CONFIG_PATH.read_text())
            return cls(
                provider=data.get("provider", "anthropic"),
                api_key=data.get("api_key", ""),
                model=data.get("model", DEFAULT_MODELS.get(data.get("provider", "anthropic"), "")),
                enabled=data.get("enabled", True),
            )
        except Exception:
            return None

    def save(self) -> None:
        """Write config to file."""
        AI_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "provider": self.provider,
            "api_key": self.api_key,
            "model": self.model,
            "enabled": self.enabled,
        }
        AI_CONFIG_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2))
        try:
            os.chmod(AI_CONFIG_PATH, 0o600)
        except OSError:
            pass

    @classmethod
    def clear(cls) -> None:
        """Delete the config file."""
        if AI_CONFIG_PATH.exists():
            AI_CONFIG_PATH.unlink()


def _call_anthropic(api_key: str, model: str, prompt: str) -> str:
    """Call the Anthropic Claude API."""
    payload = {
        "model": model,
        "max_tokens": 500,
        "messages": [{"role": "user", "content": prompt}],
    }
    req = urllib.request.Request(
        API_ENDPOINTS["anthropic"],
        data=json.dumps(payload).encode(),
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read())
        return result.get("content", [{}])[0].get("text", "")


def _call_minimax(api_key: str, model: str, prompt: str) -> str:
    """Call the MiniMax API."""
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are CodeDNA's AI analysis assistant. You interpret user command outputs. Do not chat — only provide analysis and insights."},
            {"role": "user", "content": prompt}
        ],
    }
    req = urllib.request.Request(
        API_ENDPOINTS["minimax"],
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read())
        return result.get("choices", [{}])[0].get("message", {}).get("content", "")


def _call_openai(api_key: str, model: str, prompt: str) -> str:
    """Call the OpenAI API."""
    payload = {
        "model": model,
        "max_tokens": 500,
        "messages": [
            {"role": "system", "content": "You are CodeDNA's AI analysis assistant. You interpret user command outputs. Do not chat — only provide analysis and insights."},
            {"role": "user", "content": prompt}
        ],
    }
    req = urllib.request.Request(
        API_ENDPOINTS["openai"],
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read())
        return result.get("choices", [{}])[0].get("message", {}).get("content", "")


def ai_analyze(command: str, output: str, config: Optional[AIConfig] = None, extra_context: str = "") -> Optional[str]:
    """
    Analyze command output using AI.

    Args:
        command: Command that was run
        output: Command output
        config: AI configuration
        extra_context: Additional context (file contents, etc.)

    Returns:
        Analysis text or None
    """
    if config is None:
        config = AIConfig.load()
    if config is None or not config.enabled or not config.api_key:
        return None

    # Plan check — only Pro+ users can use AI analysis
    try:
        from codedna.plan import get_current_plan, Plan as PlanEnum
        plan = get_current_plan()
        if plan == PlanEnum.FREE:
            return None  # No AI analysis on free plan
    except Exception:
        return None  # Cannot load plan, skip

    context_block = f"\n\nFILE CONTENTS:\n{extra_context}" if extra_context else ""
    prompt = f"""You are CodeDNA's code verification assistant. NEVER give general recommendations, only analyze.

OUTPUT:
{output[:3000]}{context_block[:4000]}

Respond in this exact format:

**File Inspection**
For each file:
- filename.py: [AI, human, or mixed?] + [evidence: comment ratio, function length, etc.]

**Syntax Check**  (IMPORTANT - for each file)
- filename.py: [NO ERRORS / ERRORS FOUND] 
  - If errors: line X: error description
  - Example: 'main.py: line 4: IndentationError: unindent does not match'
  - Check: Python syntax, JavaScript syntax, undefined variables, import errors, bracket mismatches, logic errors

**Verification**
- AI probability accuracy: [high/medium/low] + [reason]
- Could it be false positive? [yes/no] + [reason]

**Status**
- Confidence: [high/medium/low]
- Concern: [possible AI / natural code]

Rules:
- NO general advice (like "do more scanning")
- ONLY look at files and COMMENT
- English, max 350 words (syntax added)
- Evidence-based (file content-based) talk
- MUST include line number for syntax errors"""

    try:
        if config.provider == "anthropic":
            return _call_anthropic(config.api_key, config.model, prompt)
        elif config.provider == "minimax":
            return _call_minimax(config.api_key, config.model, prompt)
        elif config.provider == "openai":
            return _call_openai(config.api_key, config.model, prompt)
        else:
            return None
    except Exception as e:
        return f"AI analysis error: {type(e).__name__}"


def is_enabled() -> bool:
    """Is AI analysis active? (Pro+ users only)"""
    config = AIConfig.load()
    if config is None or not config.enabled or not config.api_key:
        return False
    try:
        from codedna.plan import get_current_plan, Plan as PlanEnum
        plan = get_current_plan()
        if plan == PlanEnum.FREE:
            return False
    except Exception:
        return False
    return True
