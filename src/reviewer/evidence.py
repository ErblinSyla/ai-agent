import ast, json, re
from pathlib import PurePosixPath

LATIN_NAMES={"latin","latin_square","latin_board","latin_solution","board","square"}
SUDOKU_SOLUTIONS={"sudoku_solution","solved_board","solution","solved_grid"}
SUDOKU_CLUES={"sudoku_clues","clues","puzzle","initial_board","initial_grid"}
GOLF_NAMES={"social_golfers","golf_schedule","social_golfers_schedule","schedule"}

def _matrix(text):
    rows=[]
    for line in text.splitlines():
        line=line.strip()
        if not line or line.startswith(("#","//")): continue
        vals=re.findall(r"-?\d+",line)
        if not vals: return None
        rows.append([int(x) for x in vals])
    return rows or None

def _is_matrix(value):
    return isinstance(value,list) and bool(value) and all(isinstance(row,list) for row in value) and all(not isinstance(x,(list,dict)) for row in value for x in row)

def extract_outputs(files):
    """Collect output data from normal JSON/CSV/TXT files or literal Python constants, without executing code."""
    outputs={}; evidence=[]; constants={}
    for path,text in files.items():
        suffix=PurePosixPath(path).suffix.lower(); stem=PurePosixPath(path).stem.lower().replace("-","_")
        if suffix==".json":
            try: obj=json.loads(text)
            except (json.JSONDecodeError,UnicodeError): obj=None
            if isinstance(obj,dict):
                if isinstance(obj.get("outputs"),dict): outputs.update(obj["outputs"]); evidence.append(path)
                for tid in ("social_golfers","sudoku","latin_square","search_trees"):
                    if isinstance(obj.get(tid),dict): outputs[tid]=obj[tid]; evidence.append(path)
                if stem in {"social_golfers","sudoku","latin_square","search_trees"}: outputs[stem]=obj; evidence.append(path)
                if stem in {"eight_puzzle","8_puzzle","missionaries_cannibals","rotating_workforce"} and {"initial","goal","states","edges"}.issubset(obj):
                    pid="eight_puzzle" if stem in {"eight_puzzle","8_puzzle"} else stem
                    outputs.setdefault("search_trees",{})[pid]=obj; evidence.append(path)
        if suffix==".py":
            try: tree=ast.parse(text)
            except (SyntaxError,ValueError): continue
            for node in tree.body:
                if isinstance(node,ast.Assign): names=[x.id for x in node.targets if isinstance(x,ast.Name)]
                elif isinstance(node,ast.AnnAssign) and isinstance(node.target,ast.Name): names=[node.target.id]
                else: continue
                try: value=ast.literal_eval(node.value)
                except (ValueError,TypeError,MemoryError,RecursionError): continue
                for name in names: constants[(path,name.lower())]=value
        if suffix in {".txt",".csv"}:
            board=_matrix(text)
            if board and "latin" in stem: outputs["latin_square"]={"board":board,"n":len(board)}; evidence.append(path)
            elif board and ("sudoku" in stem or any(level in stem for level in ("easy","medium","hard"))):
                sudoku=outputs.setdefault("sudoku",{})
                level=next((x for x in ("easy","medium","hard") if x in stem),None)
                target=sudoku.setdefault("fixtures",{}).setdefault(level,{}) if level else sudoku
                if any(k in stem for k in ("clue","puzzle","initial")): target["clues"]=board
                else: target["solution"]=board
                evidence.append(path)
    for (path,name),value in constants.items():
        lowerpath=path.lower()
        if _is_matrix(value):
            square=len(value)==len(value[0]) and all(len(row)==len(value) for row in value)
            if "latin" in lowerpath or name in LATIN_NAMES and square:
                outputs.setdefault("latin_square",{"board":value,"n":len(value)}); evidence.append(path)
            if "sudoku" in lowerpath or name in SUDOKU_SOLUTIONS or name in SUDOKU_CLUES:
                sudoku=outputs.setdefault("sudoku",{})
                if name in SUDOKU_CLUES or "clue" in name or "puzzle" in name: sudoku.setdefault("clues",value)
                elif name in SUDOKU_SOLUTIONS: sudoku.setdefault("solution",value)
                if "sudoku" in lowerpath: evidence.append(path)
        if isinstance(value,list) and value and isinstance(value[0],list) and value[0] and isinstance(value[0][0],list):
            if "golf" in lowerpath or "social" in lowerpath or name in GOLF_NAMES:
                flat=[x for week in value for group in week for x in group if type(x) is int]
                if flat:
                    outputs.setdefault("social_golfers",{"schedule":value,"n":max(flat)+1,"groups":len(value[0]),"group_size":len(value[0][0]),"weeks":len(value)}); evidence.append(path)
        if isinstance(value,dict) and {"initial","goal","states","edges"}.issubset(value):
            key=next((k for k in ("eight_puzzle","missionaries_cannibals","rotating_workforce") if k in name or k in lowerpath),None)
            if key: outputs.setdefault("search_trees",{})[key]=value; evidence.append(path)
    return outputs,sorted(set(evidence))

