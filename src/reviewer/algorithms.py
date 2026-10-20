import ast
from pathlib import PurePosixPath

def analyze_python_algorithms(files):
    """Collect conservative AST clues; never confirms algorithm behavior."""
    functions=[]
    for path,source in files.items():
        if PurePosixPath(path).suffix.lower()!=".py": continue
        try: tree=ast.parse(source)
        except (SyntaxError,ValueError) as e:
            functions.append({"path":path,"parse_error":str(e)}); continue
        for node in ast.walk(tree):
            if not isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)): continue
            calls=[]
            for x in ast.walk(node):
                if isinstance(x,ast.Call):
                    attr=x.func.attr if isinstance(x.func,ast.Attribute) else x.func.id if isinstance(x.func,ast.Name) else ""
                    calls.append((attr,x))
            names={name for name,_ in calls}
            receivers={}
            for name,call in calls:
                if isinstance(call.func,ast.Attribute) and isinstance(call.func.value,ast.Name): receivers.setdefault(call.func.value.id,set()).add(name)
            recursive=node.name in names
            loop=any(isinstance(x,(ast.For,ast.While)) for x in ast.walk(node))
            pop_zero=any(name=="pop" and len(call.args)==1 and isinstance(call.args[0],ast.Constant) and call.args[0].value==0 for name,call in calls)
            queue_dequeue="popleft" in names or pop_zero
            mutate_add=bool(names & {"append","add"}); mutate_undo=bool(names & {"remove","discard"}) or "pop" in names
            depth_param=any(x.arg in {"depth","limit","max_depth","depth_limit"} for x in node.args.args)
            loop_depth=any(isinstance(x,ast.For) and isinstance(x.target,ast.Name) and x.target.id.lower() in {"depth","limit","max_depth","depth_limit"} for x in ast.walk(node))
            calls_depth_search=any(name in {"depth_limited_search","dls"} and name!=node.name for name,_ in calls)
            reversible_mutation=any(("append" in ops or "add" in ops) and ("pop" in ops or "remove" in ops or "discard" in ops) for ops in receivers.values())
            s={"loop":loop,"recursion":recursive,"stack_pop":"pop" in names,"queue_dequeue":queue_dequeue,"depth_parameter":depth_param,"iterates_depth_limit":loop_depth,"calls_depth_limited_search":calls_depth_search,"mutation_and_undo":reversible_mutation}
            functions.append({"path":path,"name":node.name,"line":node.lineno,"end_line":node.end_lineno,"calls":sorted(names),"structures":s})
    results={}
    for algo in ("DFS","BFS","IDDFS","backtracking"):
        matched=[]
        for f in functions:
            s=f.get("structures",{})
            if algo=="DFS": score=int(s.get("stack_pop") and s.get("loop"))+int(s.get("recursion") and s.get("loop"))
            elif algo=="BFS": score=int(s.get("queue_dequeue"))
            elif algo=="IDDFS": score=int(s.get("loop") and s.get("iterates_depth_limit") and s.get("calls_depth_limited_search"))
            else: score=int(s.get("recursion") and s.get("mutation_and_undo"))
            if score: matched.append({**f,"structural_score":score})
        results[algo]={"status":"static structural evidence" if matched else "not detected statically","confidence":"medium; manual verification required" if matched else "low","evidence":matched[:20],"limitation":"AST structure is only a clue, not behavioral proof. It cannot prove execution paths or behavior; aliases and other languages may be missed."}
    return results

