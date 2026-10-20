import json, shutil, subprocess
from pathlib import Path
from .ingestion import summarize
from .algorithms import analyze_python_algorithms
from .evidence import extract_outputs
from .validators import (search_space_summary, validate_golf_schedule, validate_latin_square, validate_sudoku, validate_search_tree)
from .grading import score_report
from .reporting import write_report

def _as_int(value, default):
    try:
        if isinstance(value,bool): return default
        return int(value)
    except (TypeError,ValueError,OverflowError): return default

def review(repo, spec, outdir, selected_task="all", reviewer_config=None, ai_provider=None, ai_enabled=False, source_upload_cli_authorized=False, ai_setup_error=None, similarity_context=None):
    task_by_id={t["id"]:t for t in spec["tasks"]}; outputs, evidence_files=extract_outputs(repo["files"])
    findings=[]
    algo=analyze_python_algorithms(repo["files"])
    aliases={"social_golfers":["golf","social"],"sudoku":["sudoku"],"latin_square":["latin"],"search_trees":["puzzle","missionar","workforce","search tree"]}
    for tid,task in task_by_id.items():
        if tid not in aliases or selected_task not in ("all",tid): continue
        algo_names={"social_golfers":["DFS","backtracking"],"sudoku":["BFS","backtracking"],"latin_square":["IDDFS","backtracking"],"search_trees":[]}[tid]
        relevant={k:algo[k] for k in algo_names}
        evidence=outputs.get(tid); validation={"status":"not supplied","manual_review":["Provide a supported structured output file or manually review the implementation/result."]}
        if isinstance(evidence,dict):
            if tid=="social_golfers":
                par=task.get("parameters",{}); validation=validate_golf_schedule(evidence.get("schedule",[]),_as_int(evidence.get("n",par.get("n",32)),32),_as_int(evidence.get("groups",par.get("groups",8)),8),_as_int(evidence.get("group_size",par.get("group_size",4)),4),evidence.get("weeks",par.get("weeks")))
            elif tid=="sudoku":
                fixtures=evidence.get("fixtures",{})
                if isinstance(fixtures,list): fixtures={str(x.get("difficulty","unknown")).lower():x for x in fixtures if isinstance(x,dict)}
                if isinstance(fixtures,dict) and fixtures:
                    expected={str(x).lower() for x in task.get("difficulty_levels",["Easy","Medium","Hard"])}
                    results={name:validate_sudoku(item.get("solution",[]),item.get("clues",[]),_as_int(item.get("box_size",evidence.get("box_size",3)),3)) for name,item in fixtures.items() if isinstance(item,dict)}
                    missing=sorted(expected-set(results)); validation={"valid":all(x["valid"] for x in results.values()),"fixtures":results,"missing_difficulty_levels":missing,"manual_review":[f"Missing configured difficulty fixture: {x}" for x in missing]}
                else:
                    validation=validate_sudoku(evidence.get("solution",[]),evidence.get("clues",[]),_as_int(evidence.get("box_size",3),3))
                    expected=task.get("difficulty_levels",["Easy","Medium","Hard"])
                    validation["difficulty_coverage"]={"provided":"single puzzle; level unspecified","required":expected}
                    validation["manual_review"]=["Difficulty labels/fixtures are not demonstrated for every configured level."]
            elif tid=="latin_square": validation=validate_latin_square(evidence.get("board",[]),evidence.get("n"))
            elif tid=="search_trees":
                validation={"problems":{},"valid":True,"manual_review":[]}
                rules={r["id"]:r for r in task.get("problems",[])}
                for pid,tree in evidence.items():
                    problem_rules=rules.get(pid,{})
                    result=validate_search_tree(pid,tree,{**problem_rules,**problem_rules.get("validation_rules",{})}); validation["problems"][pid]=result
                    validation["valid"] &= result["valid"]
                    validation["manual_review"].extend([f"{pid}: {x}" for x in result["manual_review"]])
                for pid in {x["id"] for x in task.get("problems",[])}-set(evidence): validation["manual_review"].append(f"{pid}: structured tree missing or diagram format unsupported")
        # Structural AST evidence never confirms runtime behavior.
        if "valid" not in validation: status="manual review"
        elif not validation["valid"]: status="invalid output"
        elif validation.get("manual_review"): status="manual review"
        else: status="validated output"
        findings.append({"task_id":tid,"task":task.get("title",tid),"status":status,"output_validation":validation,"algorithm_compliance":{"required":algo_names,"analysis":relevant,"summary":"Repository-wide Python AST clues only; task attribution and runtime behavior require human verification. No algorithm is marked behaviorally confirmed." if algo_names else "Search tree construction is checked separately; executable search is not required."},"evidence_files":evidence_files,"required_deliverables":task.get("deliverables",[]),"evidence_search":[{"path":p,"lines":[i for i,line in enumerate(txt.splitlines(),1) if any(term in (p+line).lower() for term in aliases[tid])][:8]} for p,txt in repo["files"].items() if any(term in (p+txt[:5000]).lower() for term in aliases[tid])][:10]})
    for finding in findings:
        tid=finding["task_id"]; data=outputs.get(tid,{})
        if tid=="social_golfers":
            params={k:data.get(k,task_by_id[tid].get("parameters",{}).get(k)) for k in ("n","groups","group_size","weeks")}
            finding["search_space"]=search_space_summary(tid,params)
        elif tid=="latin_square":
            board=data.get("board",[]); finding["search_space"]=search_space_summary(tid,{"n":data.get("n",len(board))})
        elif tid=="sudoku":
            fixtures=data.get("fixtures",{})
            puzzles=fixtures.values() if isinstance(fixtures,dict) else fixtures if isinstance(fixtures,list) else []
            if puzzles:
                finding["search_space"]={str(x.get("difficulty","unspecified")):search_space_summary(tid,{"n":9,"empty_cells":sum(v==0 for row in x.get("clues",[]) for v in row)}) for x in puzzles if isinstance(x,dict)}
            else:
                clues=data.get("clues",[]); finding["search_space"]=search_space_summary(tid,{"n":9,"empty_cells":sum(v==0 for row in clues for v in row)}) if clues else search_space_summary(tid,{})
        else:
            trees=data.get("search_trees",{})
            finding["search_space"]={name:{"quantity":"states in submitted representation","state_count":len(tree.get("states",[])) if isinstance(tree,dict) and isinstance(tree.get("states",[]),list) else None,"edge_count":len(tree.get("edges",[])) if isinstance(tree,dict) and isinstance(tree.get("edges",[]),list) else None,"assumption":"Counts only the supplied representation; does not estimate all reachable states."} for name,tree in trees.items()}
    rubric=spec.get("rubric",{}); score=None
    if rubric.get("provisional") is False and rubric.get("criteria"):
        awards={}
        for c in rubric["criteria"]:
            target=next((f for f in findings if f["task_id"]==c.get("task_id")),None)
            basis=c.get("basis","output_validation")
            if basis=="algorithm_compliance": outcome="manual_review" # static structure cannot prove behavior
            else: outcome="pass" if target and target["status"]=="validated output" else "fail" if target and target["status"]=="invalid output" else "manual_review"
            award=c.get("awards",{}).get(outcome)
            if award is not None: awards[c["id"]]=award
        score=score_report(rubric["criteria"],awards)
    metrics={"available":False,"limitation":"scc executable not found"}
    scc=shutil.which("scc")
    if scc and repo.get("local_path"):
        try:
            run=subprocess.run([scc,"--format","json",repo["local_path"]],capture_output=True,text=True,timeout=30)
            ver=subprocess.run([scc,"--version"],capture_output=True,text=True,timeout=5)
            metrics={"available":run.returncode==0,"version":ver.stdout.strip(),"output":run.stdout[:500000] if run.returncode==0 else run.stderr[:2000]}
        except Exception as e: metrics={"available":False,"limitation":f"scc failed: {e}"}
    rep={"repository":repo["name"],"commit_sha":repo["sha"],"dirty_worktree":repo.get("dirty_worktree"),"reviewed_tree_sha256":repo.get("tree_sha256"),"recent_history":repo.get("history",[]),"git_history_analysis":{"available":bool(repo.get("history")),"commit_count_included":len(repo.get("history",[])),"scope":"retrieved history window only","interpretation":"Commit count/messages are contextual evidence, not a direct measure of student effort or quality."},"assignment_id":spec["id"],"assignment_version":spec.get("version"),"selected_task":selected_task,"evaluation_mode":"read-only static analysis; no student code executed","rubric_version":rubric.get("version","unconfigured"),"assessment_status":"official rubric configured" if score is not None else "ungraded; rubric absent or provisional","provisional":score is None,"repository_summary":summarize(repo),"findings":findings,"algorithm_analysis":algo,"similarity_context":similarity_context or [],"score":score,"code_metrics":metrics,"limitations":["Algorithm clues come from repository-wide Python AST analysis and may not belong to the selected task; verify source paths and behavior manually. Non-Python source is not analyzed.","Structured outputs are extracted from supported JSON/CSV/TXT files and literal Python constants; executed program results, diagrams and unsupported formats require manual review.","No student source is executed and no private source is sent to an AI provider.","GitHub API retrieval does not yet cache content."]}
    rep["ai_review"]={"status":"not requested","interpretation_type":"none"}
    if ai_enabled:
        if reviewer_config is None or not reviewer_config.get("llm",{}).get("enabled",False):
            rep["ai_review"]={"status":"disabled by reviewer config","interpretation_type":"none"}
        elif ai_setup_error:
            rep["ai_review"]={"status":"unavailable","error":str(ai_setup_error),"interpretation_type":"none"}
        elif ai_provider is None:
            rep["ai_review"]={"status":"unavailable","error":"No AI provider configured","interpretation_type":"none"}
        else:
            from .llm import review_allowed
            send_source=review_allowed(reviewer_config,source_upload_cli_authorized)
            try: rep["ai_review"]=ai_provider.review(repo,spec,rep,reviewer_config,include_source=send_source)
            except Exception as e: rep["ai_review"]={"status":"failed","error":str(e),"interpretation_type":"AI result not available"}
    write_report(rep,outdir); return rep




