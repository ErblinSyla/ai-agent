from pathlib import Path
import yaml

REQUIRED_TASKS = {"social_golfers", "sudoku", "latin_square", "search_trees"}
def load_assignment(path):
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not data.get("id") or not isinstance(data.get("tasks"), list): raise ValueError("Assignment spec must define id and tasks")
    ids = [t.get("id") for t in data["tasks"]]
    if len(ids) != len(set(ids)): raise ValueError("Task ids must be unique")
    if data["id"] == "ai-2026-27-assignment-01" and not REQUIRED_TASKS.issubset(ids): raise ValueError("Assignment 1 requires all four tasks")
    for c in data.get("rubric", {}).get("criteria", []):
        if not c.get("id") or float(c.get("max_points", -1)) < 0: raise ValueError("Each rubric criterion needs id and nonnegative max_points")
    return data
