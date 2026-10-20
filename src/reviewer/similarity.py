from pathlib import Path
import fnmatch, hashlib, re
EXCLUDED={"vendor","node_modules","dist","build","generated","__pycache__",".git"}
def normalize(text):
    text=re.sub(r"(?m)#.*$|//.*$", " ", text)
    text=re.sub(r"\b\d+\b", "NUM", text)
    text=re.sub(r"\b[A-Za-z_][A-Za-z_0-9]*\b", "ID", text)
    return " ".join(text.split())
def _windows(text, size=4):
    lines=[normalize(x) for x in text.splitlines() if x.strip()]
    return {"\n".join(lines[i:i+size]): i+1 for i in range(max(0,len(lines)-size+1)) if len(" ".join(lines[i:i+size]))>=80}
def compare_repositories(repos, config=None):
    config=config or {}
    excluded=set(EXCLUDED)|set(config.get("exclude_paths",[]))
    starter=config.get("starter_code",[])
    def is_excluded(path):
        parts=Path(path).parts
        return any(part in excluded for part in parts) or any(fnmatch.fnmatch(path,pattern) for pattern in starter)
    results=[]
    for i,a in enumerate(repos):
        for b in repos[i+1:]:
            fa={p:t for p,t in a["files"].items() if not is_excluded(p)}
            fb={p:t for p,t in b["files"].items() if not is_excluded(p)}
            exact=[]; normalized=[]; fragments=[]
            for pa,ta in fa.items():
                for pb,tb in fb.items():
                    if min(len(ta.strip()),len(tb.strip()))<80: continue
                    if hashlib.sha256(ta.encode()).digest()==hashlib.sha256(tb.encode()).digest(): exact.append({"file_a":pa,"file_b":pb,"lines_a":[1,len(ta.splitlines())],"lines_b":[1,len(tb.splitlines())]})
                    na,nb=normalize(ta),normalize(tb)
                    if na==nb: normalized.append({"file_a":pa,"file_b":pb,"method":"identifier/literal normalized exact file"})
                    wa,wb=_windows(ta),_windows(tb)
                    for snippet in wa.keys() & wb.keys():
                        fragments.append({"file_a":pa,"file_b":pb,"line_a":wa[snippet],"line_b":wb[snippet],"normalized_fragment":snippet[:500]})
            if exact or normalized or fragments:
                results.append({"repository_a":a["name"],"commit_a":a["sha"],"repository_b":b["name"],"commit_b":b["sha"],"exact_matches":exact,"normalized_matches":normalized,"matching_fragments":fragments[:50],"methodology":"SHA-256 exact files, whole-file identifier/literal normalization, and matching 4-line normalized windows (minimum 80 characters). Configured generated/dependency/starter-code exclusions applied. Shared/common solutions can explain matches; human review required.","confidence":"review required"})
    return results
