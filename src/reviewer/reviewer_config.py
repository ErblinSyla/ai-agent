from pathlib import Path
from dotenv import load_dotenv
import yaml

REQUIRED_KEYS={"reviewer","llm","rubric_policy"}

def load_local_environment(path=".env"):
    """Load repository-local environment defaults without overriding the shell."""
    return load_dotenv(dotenv_path=Path(path), override=False)

def load_reviewer_config(path="config/reviewer.yaml"):
    data=yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data,dict) or not REQUIRED_KEYS.issubset(data): raise ValueError("Reviewer config must contain reviewer, llm, and rubric_policy")
    if not isinstance(data["reviewer"].get("skills"),list) or not data["reviewer"]["skills"] or any(not isinstance(x,str) for x in data["reviewer"]["skills"]): raise ValueError("Reviewer skills must be configured")
    if not isinstance(data["reviewer"].get("rules"),list) or any(not isinstance(x,str) for x in data["reviewer"]["rules"]): raise ValueError("Reviewer rules must be a list of strings")
    llm=data["llm"]
    if llm.get("provider")!="openai-compatible": raise ValueError("Unsupported LLM provider; expected openai-compatible")
    if type(llm.get("max_source_chars")) is not int or llm["max_source_chars"]<1000: raise ValueError("llm.max_source_chars must be at least 1000")
    return data
