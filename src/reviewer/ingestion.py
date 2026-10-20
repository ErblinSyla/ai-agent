from pathlib import Path
import hashlib, json, subprocess
SKIP={".git","node_modules","vendor","dist","build","__pycache__",".venv",".pytest_cache",".mypy_cache",".ruff_cache",".tox"}
def ingest_local(path):
    root=Path(path).resolve(); files={} # read-only: never write cache data into submitted repository
    if not root.is_dir(): raise FileNotFoundError(f"Repository directory does not exist: {root}")
    for p in root.rglob("*"):
        if p.is_symlink() or not p.is_file() or any(part in SKIP for part in p.parts) or ".review-cache" in p.parts: continue
        if p.stat().st_size>1_000_000: continue
        try: files[p.relative_to(root).as_posix()]=p.read_text(encoding="utf-8")
        except (UnicodeDecodeError,OSError): pass
    try:
        sha=subprocess.run(["git","-C",str(root),"rev-parse","HEAD"],capture_output=True,text=True,timeout=5).stdout.strip() or "working-tree"
        dirty=bool(subprocess.run(["git","-C",str(root),"status","--porcelain"],capture_output=True,text=True,timeout=5).stdout.strip())
        log=subprocess.run(["git","-C",str(root),"log","-n","20","--format=%H%x09%s%x09%aI"],capture_output=True,text=True,timeout=5).stdout
        history=[{"sha":line.split("\t",2)[0],"message":line.split("\t",2)[1],"date":line.split("\t",2)[2]} for line in log.splitlines() if len(line.split("\t",2))==3]
    except Exception:
        sha="working-tree"; dirty=True; history=[]
    digest=hashlib.sha256()
    for name,content in sorted(files.items()): digest.update(name.encode()); digest.update(b"\0"); digest.update(content.encode()); digest.update(b"\0")
    return {"name":root.name,"sha":sha,"dirty_worktree":dirty,"tree_sha256":digest.hexdigest(),"files":files,"metadata":{"html_url":None},"history":history,"local_path":str(root)}
def summarize(repo):
    fs=repo["files"]; suffixes={}
    for path in fs:
        ext=Path(path).suffix.lower() or "[no extension]"; suffixes[ext]=suffixes.get(ext,0)+1
    return {"file_count":len(fs),"extensions":suffixes,"readme_files":[p for p in fs if Path(p).name.lower().startswith("readme")],"test_files":[p for p in fs if "test" in p.lower()],"manifest_files":[p for p in fs if Path(p).name.lower() in {"pyproject.toml","requirements.txt","package.json","pom.xml","cargo.toml","go.mod"}]}



