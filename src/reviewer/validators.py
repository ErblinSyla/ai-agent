from itertools import combinations
from math import factorial

def validate_latin_square(board, n=None):
    if not isinstance(board,list): return {"valid":False,"errors":["board must be a list of rows"]}
    n=len(board) if n is None else n
    if type(n) is not int or n<=0: return {"valid":False,"errors":["n must be a positive integer"]}
    errors=[]; expected=set(range(1,n+1))
    if len(board)!=n or any(not isinstance(row,list) or len(row)!=n for row in board): return {"valid":False,"errors":["board must be n by n"]}
    for i,row in enumerate(board):
        if len(row)==n and (any(type(v) is not int for v in row) or set(row)!=expected): errors.append(f"row {i+1} must contain each symbol 1..n once")
    if len(board)==n and all(len(r)==n for r in board):
        for j in range(n):
            col=[board[i][j] for i in range(n)]
            if any(type(v) is not int for v in col) or set(col)!=expected: errors.append(f"column {j+1} must contain each symbol 1..n once")
    return {"valid":not errors,"errors":errors}

def validate_sudoku(board, clues, box_size=3):
    if type(box_size) is not int or box_size<=0: return {"valid":False,"errors":["box_size must be a positive integer"]}
    if not isinstance(board,list) or not isinstance(clues,list): return {"valid":False,"errors":["board and clues must be lists of rows"]}
    errors=[]; n=box_size*box_size
    if len(board)!=n or any(not isinstance(r,list) or len(r)!=n for r in board): return {"valid":False,"errors":[f"board must be {n}x{n}"]}
    if len(clues)!=n or any(not isinstance(r,list) or len(r)!=n for r in clues): return {"valid":False,"errors":[f"clues must be {n}x{n}"]}
    expected=set(range(1,n+1))
    for i in range(n):
        if any(type(v) is not int for v in board[i]) or set(board[i])!=expected: errors.append(f"row {i+1} invalid")
        if any(type(board[r][i]) is not int for r in range(n)) or set(board[r][i] for r in range(n))!=expected: errors.append(f"column {i+1} invalid")
        for j in range(n):
            if type(clues[i][j]) is not int or not 0<=clues[i][j]<=n: errors.append(f"invalid clue at ({i+1},{j+1})")
            elif clues[i][j] and clues[i][j]!=board[i][j]: errors.append(f"clue changed at ({i+1},{j+1})")
    for r in range(0,n,box_size):
        for c in range(0,n,box_size):
            box=[board[i][j] for i in range(r,r+box_size) for j in range(c,c+box_size)]
            if any(type(v) is not int for v in box) or set(box)!=expected: errors.append(f"subgrid at ({r+1},{c+1}) invalid")
    return {"valid":not errors,"errors":errors}

def validate_golf_schedule(schedule,n,groups,group_size,expected_weeks=None):
    if not isinstance(schedule,list): return {"valid":False,"errors":["schedule must be a list of weeks"],"weeks":0,"distinct_pairs":0}
    errors=[]; seen=set()
    if n<=0 or groups<=0 or group_size<=0 or n!=groups*group_size: errors.append("require positive n, groups, group_size and n=groups*group_size")
    if expected_weeks is not None and len(schedule)!=expected_weeks: errors.append(f"expected {expected_weeks} weeks, found {len(schedule)}")
    for wi,week in enumerate(schedule):
        if not isinstance(week,list): errors.append(f"week {wi+1}: must be a list of groups"); continue
        if len(week)!=groups: errors.append(f"week {wi+1}: wrong group count")
        if any(not isinstance(group,list) for group in week): errors.append(f"week {wi+1}: groups must be lists"); continue
        flat=[x for group in week for x in group]
        if any(type(x) is not int for x in flat) or sorted(x for x in flat if type(x) is int)!=list(range(n)) or len(flat)!=n: errors.append(f"week {wi+1}: every golfer must appear exactly once using IDs 0..n-1")
        for gi,group in enumerate(week):
            if len(group)!=group_size or any(type(x) is not int for x in group) or len(set(x for x in group if type(x) is int))!=group_size: errors.append(f"week {wi+1}, group {gi+1}: wrong size or duplicate golfer")
            for pair in combinations(sorted(set(x for x in group if type(x) is int)),2):
                if pair in seen: errors.append(f"pair {pair} repeats in week {wi+1}")
                seen.add(pair)
    return {"valid":not errors,"errors":errors,"weeks":len(schedule),"distinct_pairs":len(seen)}

def _edge_parts(edge):
    if isinstance(edge,dict): return edge.get("from"),edge.get("to"),edge.get("action")
    if isinstance(edge,(list,tuple)) and len(edge)>=2: return edge[0],edge[1],edge[2] if len(edge)>2 else None
    return None,None,None

def validate_search_tree(problem, tree, rules=None):
    """Validate a portable structure: initial, goal, states, edges. State checks are domain-aware."""
    if not isinstance(tree,dict): return {"valid":False,"errors":["tree must be a structured object"],"manual_review":[],"state_count":0,"edge_count":0}
    rules=rules or {}; errors=[]; manual=[]
    states=tree.get("states",[]); edges=tree.get("edges",[]); initial=tree.get("initial"); goal=tree.get("goal")
    if not isinstance(states,list) or not isinstance(edges,list): return {"valid":False,"errors":["states and edges must be lists"],"manual_review":[],"state_count":0,"edge_count":0}
    canon=lambda x: str(x)
    state_keys={canon(s) for s in states}
    if len(state_keys)!=len(states): errors.append("duplicate state entries found; repeated-state policy needs explicit handling")
    if initial is None or goal is None: errors.append("initial and goal are required")
    if initial is not None and canon(initial) not in state_keys: errors.append("initial state missing from states")
    if goal is not None and canon(goal) not in state_keys: errors.append("goal state missing from states")
    valid_edges=[]
    for i,e in enumerate(edges):
        a,b,action=_edge_parts(e)
        if canon(a) not in state_keys or canon(b) not in state_keys: errors.append(f"edge {i} references an unknown state"); continue
        valid_edges.append((a,b,action))
        if rules.get("allowed_actions") is not None and action not in rules["allowed_actions"]: errors.append(f"edge {i} uses an unconfigured action")
    if not edges: manual.append("no successor edges provided")
    required_fields=rules.get("required_state_fields",[])
    if required_fields:
        for i,state in enumerate(states):
            if not isinstance(state,dict) or not set(required_fields).issubset(state): errors.append(f"state {i} is missing configured required fields")
    if rules.get("goal_reachable") and initial is not None and goal is not None:
        graph={canon(s):[] for s in states}
        for a,b,_ in valid_edges: graph.setdefault(canon(a),[]).append(canon(b))
        reached={canon(initial)}; todo=[canon(initial)]
        while todo:
            for nxt in graph.get(todo.pop(),[]):
                if nxt not in reached: reached.add(nxt); todo.append(nxt)
        if canon(goal) not in reached: errors.append("configured goal is not reachable from initial state")
    p=problem.lower().replace("-","_").replace(" ","_")
    if ("puzzle" in p or "8" in p or "mission" in p or "cannibal" in p) and initial is not None and goal is not None:
        graph={canon(s):[] for s in states}
        for a,b,_ in valid_edges: graph.setdefault(canon(a),[]).append(canon(b))
        reached={canon(initial)}; todo=[canon(initial)]
        while todo:
            for nxt in graph.get(todo.pop(),[]):
                if nxt not in reached: reached.add(nxt); todo.append(nxt)
        if canon(goal) not in reached: errors.append("goal state is not reachable from initial through supplied transitions")
    if "puzzle" in p or "8" in p:
        expected=sorted(range(9)); goal_expected=rules.get("goal",[1,2,3,4,5,6,7,8,0])
        for idx,s in enumerate(states):
            try:
                flat=[v for row in s for v in row] if s and isinstance(s[0],list) else list(s)
                if sorted(flat)!=expected: errors.append(f"8-puzzle state {idx} is not a permutation of 0..8"); continue
            except (TypeError,ValueError): errors.append(f"8-puzzle state {idx} must be a flat or 3x3 array"); continue
        for i,(a,b,action) in enumerate(valid_edges):
            try:
                fa=[x for row in a for x in row] if a and isinstance(a[0],list) else list(a); fb=[x for row in b for x in row] if b and isinstance(b[0],list) else list(b)
                ia,ib=fa.index(0),fb.index(0); adjacent=abs(ia//3-ib//3)+abs(ia%3-ib%3)==1
                if not adjacent or sorted(fa)!=sorted(fb) or sum(x!=y for x,y in zip(fa,fb))!=2: errors.append(f"8-puzzle edge {i} is not one legal blank swap")
            except Exception: errors.append(f"8-puzzle edge {i} has malformed state")
        if goal is not None:
            gf=[x for row in goal for x in row] if goal and isinstance(goal[0],list) else list(goal)
            if gf!=goal_expected: errors.append("8-puzzle goal differs from configured goal")
    elif "mission" in p or "cannibal" in p:
        population=int(rules.get("population",3)); capacity=int(rules.get("boat_capacity",2))
        def valid_state(s):
            try:
                m,c,side=s
                return 0<=m<=population and 0<=c<=population and side in (0,1) and (m==0 or m>=c) and (population-m==0 or population-m>=population-c)
            except Exception: return False
        if initial is not None and initial!=rules.get("initial",[population,population,0]): errors.append("missionaries/cannibals initial state differs from configured initial state")
        if goal is not None and goal!=rules.get("goal",[0,0,1]): errors.append("missionaries/cannibals goal differs from configured goal")
        for idx,s in enumerate(states):
            if not valid_state(s): errors.append(f"missionaries/cannibals state {idx} violates bank safety or bounds")
        for i,(a,b,_) in enumerate(valid_edges):
            try:
                delta=abs(a[0]-b[0])+abs(a[1]-b[1]);
                direction_ok=(b[0]<=a[0] and b[1]<=a[1]) if a[2]==0 else (b[0]>=a[0] and b[1]>=a[1])
                if abs(a[2]-b[2])!=1 or not 1<=delta<=capacity or not direction_ok: errors.append(f"missionaries/cannibals edge {i} violates boat capacity, direction, or crossing")
            except Exception: errors.append(f"missionaries/cannibals edge {i} malformed")
    else:
        if not rules.get("complete",False): manual.append("no complete domain transition rules are configured")
    manual.extend(rules.get("manual_checks",[]))
    return {"valid":not errors,"errors":errors,"manual_review":manual,"state_count":len(states),"edge_count":len(edges)}

def search_space_summary(task_id,params):
    if task_id=="latin_square" and type(params.get("n")) is int and params["n"]>0:
        n=params["n"]; return {"quantity":"raw cell assignments upper bound","expression":f"{n}^({n}*{n})","value":str(n**(n*n)),"assumption":"Each of n*n cells independently takes one of n symbols before Latin constraints."}
    if task_id=="sudoku":
        n=params.get("n",9); empty=params.get("empty_cells")
        if type(n) is int and n>0 and type(empty) is int and 0<=empty<=n*n: return {"quantity":"raw assignments to empty cells upper bound","expression":f"{n}^{empty}","value":str(n**empty),"assumption":"Each empty cell independently takes any of n symbols before row, column, and subgrid constraints."}
    if task_id=="social_golfers":
        n,g,p=params.get("n"),params.get("groups"),params.get("group_size")
        w=params.get("weeks")
        if all(type(x) is int and x>0 for x in (n,g,p)) and n==g*p:
            one=factorial(n)//(factorial(p)**g*factorial(g))
            expression=f"{n}! / (({p}!)^{g} * {g}!)"
            result={"quantity":"ordered weekly sequences of unlabeled group partitions; raw upper bound","weekly_partitions_expression":expression,"weekly_partitions":str(one),"assumption":"Groups are unlabeled within a week; weeks are ordered. This ignores repeated-pair constraints, so it is not a feasible schedule count or maximum proof."}
            if type(w) is int and w>=0: result.update({"weeks":w,"expression":f"({one})^{w}","value":str(one**w)})
            return result
    return {"quantity":"unresolved","assumption":"State and landscape definitions must be configured; no numeric estimate invented."}
