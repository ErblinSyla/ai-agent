import pytest
from reviewer.grading import score_report
from reviewer.specs import load_assignment
from reviewer.validators import validate_latin_square, validate_golf_schedule, validate_sudoku, search_space_summary
from reviewer.similarity import compare_repositories

def test_assignment_spec_loads_all_four_tasks():
    spec=load_assignment("assignments/2026-27/assignment-01.yaml")
    assert len(spec["tasks"]) == 4 and spec["rubric"]["provisional"]

def test_rubric_calculation_and_range_validation():
    c=[{"id":"a","max_points":4},{"id":"b","max_points":6}]
    assert score_report(c,{"a":3})["total"]==3
    with pytest.raises(ValueError): score_report(c,{"a":5})

def test_latin_square_valid_and_invalid():
    assert validate_latin_square([[1,2],[2,1]])["valid"]
    assert not validate_latin_square([[1,1],[2,1]])["valid"]

def test_sudoku_checks_clues_and_units():
    solved=[[((r*3+r//3+c)%9)+1 for c in range(9)] for r in range(9)]
    clues=[row[:] for row in solved]; clues[0][0]=0
    assert validate_sudoku(solved,clues)["valid"]
    clues[0][1]=9
    assert not validate_sudoku(solved,clues)["valid"]

def test_golf_schedule_rejects_repeated_pair():
    week1=[[0,1],[2,3]]; week2=[[0,1],[2,3]]
    result=validate_golf_schedule([week1,week2],4,2,2)
    assert not result["valid"]

def test_search_space_is_explicit_raw_upper_bound():
    result=search_space_summary("latin_square",{"n":2})
    assert result["value"]=="16" and "before Latin constraints" in result["assumption"]

def test_similarity_reports_exact_match_non_accusatorily():
    repos=[{"name":"a","sha":"1","files":{"main.py":"x = 3\n"*30}}, {"name":"b","sha":"2","files":{"copy.py":"x = 3\n"*30}}]
    result=compare_repositories(repos)
    assert len(result)==1 and result[0]["commit_a"]=="1"
import json
from pathlib import Path
from reviewer.algorithms import analyze_python_algorithms
from reviewer.cli import main
from reviewer.orchestration import review
from reviewer.validators import validate_search_tree

def test_ast_requires_structure_not_names_or_comments():
    files={"misleading.py":"# BFS and backtracking\ndef bfs():\n    return sorted([3, 2, 1])\n"}
    result=analyze_python_algorithms(files)
    assert result["BFS"]["status"]=="not detected statically"
    structural=analyze_python_algorithms({"s.py":"from collections import deque\ndef walk(start):\n q=deque([start])\n while q:\n  x=q.popleft()\n"})
    assert structural["BFS"]["evidence"]

def test_search_tree_rejects_illegal_8puzzle_transition():
    tree={"initial":[[1,2,3],[4,5,6],[7,8,0]],"goal":[[1,2,3],[4,5,6],[7,8,0]],"states":[[1,2,3,4,5,6,7,8,0],[1,2,3,4,5,6,8,7,0]],"edges":[{"from":[1,2,3,4,5,6,7,8,0],"to":[1,2,3,4,5,6,8,7,0]}]}
    assert not validate_search_tree("eight_puzzle",tree)["valid"]

def test_search_tree_missionaries_safety():
    tree={"initial":[3,3,0],"goal":[0,0,1],"states":[[3,3,0],[0,3,1]],"edges":[{"from":[3,3,0],"to":[0,3,1]}]}
    assert not validate_search_tree("missionaries_cannibals",tree)["valid"]

def test_review_structured_output_and_report_generation(tmp_path):
    evidence={"outputs":{"latin_square":{"n":2,"board":[[1,2],[2,1]]}}}
    files={"review-evidence.json":json.dumps(evidence),"solver.py":"def dfs(x):\n return dfs(x)\n"}
    repo={"name":"synthetic","sha":"abc123","files":files,"local_path":str(tmp_path)}
    spec={"id":"test-assignment","version":"1","tasks":[{"id":"latin_square","title":"Latin","algorithms":["IDDFS","backtracking"]}],"rubric":{"version":"none","provisional":True,"criteria":[]}}
    report=review(repo,spec,tmp_path/"reports","latin_square")
    assert report["findings"][0]["status"]=="validated output"
    assert report["score"] is None
    assert (tmp_path/"reports"/"synthetic.md").exists()

def test_cli_help_and_local(tmp_path,capsys):
    import pytest
    with pytest.raises(SystemExit) as ex: main(["--help"])
    assert ex.value.code==0




def test_cli_local_end_to_end(tmp_path,capsys):
    repo=tmp_path/"student"; repo.mkdir()
    (repo/"latin.py").write_text("def make_latin(n):\n    return [[(i+j)%n for j in range(n)] for i in range(n)]\n",encoding="utf-8")
    (repo/"review-evidence.json").write_text(json.dumps({"outputs":{"latin_square":{"n":2,"board":[[1,2],[2,1]]}}}),encoding="utf-8")
    main(["review-local",str(repo),"--task","latin_square","--out",str(tmp_path/"reports")])
    assert (tmp_path/"reports"/"student.json").exists()
    result=json.loads((tmp_path/"reports"/"student.json").read_text())
    assert result["findings"][0]["status"]=="validated output"
    assert "Ungraded" in (tmp_path/"reports"/"student.md").read_text()

def test_github_repo_pagination_without_network():
    from reviewer.github import GitHubClient
    class Client(GitHubClient):
        def __init__(self): self.pages=0
        def get(self, endpoint):
            self.pages+=1
            if self.pages==1: return ([{"full_name":"a/one"}],{"Link":"<https://api.github.com/orgs/a/repos?page=2>; rel=\"next\""})
            return ([{"full_name":"a/two"}],{})
    client=Client()
    assert len(client.list_repositories(organization="a"))==2

def test_ingestion_is_read_only_and_rejects_missing_path(tmp_path):
    import pytest
    from reviewer.ingestion import ingest_local
    repo=tmp_path/"repo"; repo.mkdir(); (repo/"main.py").write_text("pass\n")
    ingest_local(repo)
    assert not (repo/".review-cache").exists()
    with pytest.raises(FileNotFoundError): ingest_local(tmp_path/"missing")

def test_golf_validator_handles_malformed_values():
    from reviewer.validators import validate_golf_schedule
    result=validate_golf_schedule([[[[],1],[2,3]]],4,2,2)
    assert result["valid"] is False

def test_golf_validator_accepts_distinct_weeks():
    from reviewer.validators import validate_golf_schedule
    schedule=[[[0,1],[2,3]],[[0,2],[1,3]]]
    assert validate_golf_schedule(schedule,4,2,2,expected_weeks=2)["valid"]

def test_structural_iddfs_evidence_is_reported_as_unconfirmed():
    source='''def depth_limited_search(state, depth):
    if goal(state): return True
    for child in successors(state):
        if depth_limited_search(child, depth - 1): return True
    return False
def solve(start):
    for limit in range(10):
        if depth_limited_search(start, limit): return True
'''
    result=analyze_python_algorithms({"latin.py":source})
    assert result["IDDFS"]["evidence"]
    only_dls=analyze_python_algorithms({"dls.py":"def depth_limited_search(state, depth):\n    for child in successors(state):\n        depth_limited_search(child, depth-1)\n"})
    assert only_dls["IDDFS"]["status"]=="not detected statically"
    assert result["IDDFS"]["confidence"].startswith("medium")
    assert "not behavioral proof" in result["IDDFS"]["limitation"]

def test_conventional_python_constants_and_csv_are_extracted_without_execution():
    from reviewer.evidence import extract_outputs
    files={"latin.py":"LATIN_SQUARE = [[1, 2], [2, 1]]\n", "sudoku_clues.csv":"0,2\n2,1\n", "sudoku_solution.csv":"1,2\n2,1\n"}
    outputs,paths=extract_outputs(files)
    assert outputs["latin_square"]["board"]==[[1,2],[2,1]]
    assert outputs["sudoku"]["clues"]==[[0,2],[2,1]]
    assert len(paths)==3

def test_all_four_task_final_cli_report_with_conventional_fixtures(tmp_path,capsys):
    import yaml
    from reviewer.cli import main
    from pathlib import Path
    repo=tmp_path/"submission"; repo.mkdir()
    solved=[[((r*3+r//3+c)%9)+1 for c in range(9)] for r in range(9)]
    clues=[row[:] for row in solved]; clues[0][0]=0
    (repo/"latin_solver.py").write_text("LATIN_SQUARE = [[1,2],[2,1]]\n# BFS DFS IDDFS are names only\ndef dfs(): return LATIN_SQUARE\n",encoding="utf-8")
    (repo/"sudoku_clues.csv").write_text("\n".join(",".join(map(str,r)) for r in clues),encoding="utf-8")
    (repo/"sudoku_solution.csv").write_text("\n".join(",".join(map(str,r)) for r in solved),encoding="utf-8")
    (repo/"social_golfers.py").write_text("SOCIAL_GOLFERS_SCHEDULE = [[[0,1],[2,3]], [[0,2],[1,3]]]\n",encoding="utf-8")
    trees={
      "eight_puzzle":{"initial":[1,2,3,4,5,6,7,0,8],"goal":[1,2,3,4,5,6,7,8,0],"states":[[1,2,3,4,5,6,7,0,8],[1,2,3,4,5,6,7,8,0]],"edges":[{"from":[1,2,3,4,5,6,7,0,8],"to":[1,2,3,4,5,6,7,8,0],"action":"right"}]},
      "missionaries_cannibals":{"initial":[3,3,0],"goal":[0,0,1],"states":[[3,3,0],[3,1,1],[3,2,0],[3,0,1],[3,1,0],[1,1,1],[2,2,0],[0,2,1],[0,3,0],[0,1,1],[0,2,0],[0,0,1]],"edges":[]},
      "rotating_workforce":{"initial":{"day":0,"worker":"A"},"goal":{"day":1,"worker":"B"},"states":[{"day":0,"worker":"A"},{"day":1,"worker":"B"}],"edges":[{"from":{"day":0,"worker":"A"},"to":{"day":1,"worker":"B"},"action":"assign"}]}}
    trees["missionaries_cannibals"]["edges"]=[{"from":a,"to":b,"action":"cross"} for a,b in zip(trees["missionaries_cannibals"]["states"],trees["missionaries_cannibals"]["states"][1:])]
    (repo/"eight_puzzle.json").write_text(json.dumps(trees["eight_puzzle"]),encoding="utf-8")
    (repo/"missionaries_cannibals.json").write_text(json.dumps(trees["missionaries_cannibals"]),encoding="utf-8")
    (repo/"rotating_workforce.json").write_text(json.dumps(trees["rotating_workforce"]),encoding="utf-8")
    spec=yaml.safe_load(Path("assignments/2026-27/assignment-01.yaml").read_text(encoding="utf-8"))
    # Each problem may also carry instructor-provided generic workforce rules.
    spec["tasks"][3]["problems"][2]["validation_rules"]={"required_state_fields":["day","worker"],"allowed_actions":["assign"],"goal_reachable":True}
    spec_path=tmp_path/"assignment.yaml"; spec_path.write_text(yaml.safe_dump(spec),encoding="utf-8")
    main(["review-local",str(repo),"--assignment",str(spec_path),"--task","all","--out",str(tmp_path/"reports")])
    report=json.loads((tmp_path/"reports"/"submission.json").read_text(encoding="utf-8"))
    assert len(report["findings"])==4
    by_id={x["task_id"]:x for x in report["findings"]}
    assert by_id["social_golfers"]["output_validation"]["valid"]
    assert by_id["sudoku"]["output_validation"]["valid"]
    assert by_id["sudoku"]["status"]=="manual review"  # one valid puzzle is not evidence for all difficulty levels
    assert by_id["latin_square"]["output_validation"]["valid"]
    tree_result=by_id["search_trees"]["output_validation"]
    assert tree_result["problems"]["eight_puzzle"]["valid"]
    assert tree_result["problems"]["missionaries_cannibals"]["valid"]
    assert tree_result["problems"]["rotating_workforce"]["valid"]
    assert by_id["latin_square"]["algorithm_compliance"]["analysis"]["IDDFS"]["status"]=="not detected statically"
    md=(tmp_path/"reports"/"submission.md").read_text(encoding="utf-8")
    assert "ungraded" in md and "not behavioral proof" in md

def test_invalid_search_tree_transition_and_configured_workforce_rule():
    from reviewer.validators import validate_search_tree
    puzzle={"initial":[1,2,3,4,5,6,7,0,8],"goal":[1,2,3,4,5,6,7,8,0],"states":[[1,2,3,4,5,6,7,0,8],[1,2,3,4,5,6,8,7,0]],"edges":[{"from":[1,2,3,4,5,6,7,0,8],"to":[1,2,3,4,5,6,8,7,0]}]}
    assert not validate_search_tree("eight_puzzle",puzzle)["valid"]
    work={"initial":{"slot":0},"goal":{"slot":1},"states":[{"slot":0},{"slot":1}],"edges":[{"from":{"slot":0},"to":{"slot":1},"action":"assign"}]}
    assert not validate_search_tree("rotating_workforce",work,{"allowed_actions":["cover"]})["valid"]

def test_ast_does_not_call_stack_pop_bfs():
    bad="""def bfs(start):
    stack = [start]
    while stack:
        state = stack.pop()
        stack.extend(successors(state))
"""
    result=analyze_python_algorithms({"wrong.py":bad})
    assert result["BFS"]["status"]=="not detected statically"
    assert result["DFS"]["evidence"]



def test_social_golfers_raw_partition_count_is_not_feasibility_claim():
    result=search_space_summary("social_golfers",{"n":4,"groups":2,"group_size":2,"weeks":2})
    assert result["weekly_partitions"]=="3"
    assert result["value"]=="9"
    assert "not a feasible schedule count" in result["assumption"]

def test_github_snapshot_uses_exact_commit_and_reads_content_through_mock():
    import base64
    from reviewer.github import GitHubClient
    class MockClient(GitHubClient):
        def __init__(self): self.calls=[]
        def get(self, endpoint):
            self.calls.append(endpoint)
            if endpoint=="/repos/course/student": return ({"full_name":"course/student","default_branch":"main"},{})
            if endpoint=="/repos/course/student/commits/main": return ({"sha":"deadbeef"},{})
            if endpoint.startswith("/repos/course/student/git/trees/"): return ({"tree":[{"path":"README.md","type":"blob","size":5}]},{})
            if endpoint.startswith("/repos/course/student/contents/"): return ({"encoding":"base64","content":base64.b64encode(b"hello").decode()},{})
            if endpoint=="/repos/course/student/commits?per_page=20": return ([{"sha":"deadbeef","commit":{"message":"submission","author":{"date":"2026-01-01"}}}],{})
            raise AssertionError(endpoint)
    client=MockClient(); snapshot=client.repo_snapshot("course/student")
    assert snapshot["sha"]=="deadbeef" and snapshot["files"]=={"README.md":"hello"}
    assert any("ref=deadbeef" in x for x in client.calls)

def test_persistent_fixture_directories_are_ordinary_read_only_inputs():
    from pathlib import Path
    from reviewer.ingestion import ingest_local
    from reviewer.evidence import extract_outputs
    fixture_root=Path(__file__).parent/"fixtures"
    conventional=ingest_local(fixture_root/"conventional")
    outputs,paths=extract_outputs(conventional["files"])
    assert outputs["latin_square"]["board"]==[[1,2],[2,1]]
    assert outputs["social_golfers"]["weeks"]==2
    misleading=ingest_local(fixture_root/"misleading")
    assert analyze_python_algorithms(misleading["files"])["BFS"]["status"]=="not detected statically"
    invalid=ingest_local(fixture_root/"invalid")
    bad=json.loads(invalid["files"]["eight_puzzle.json"])
    assert not validate_search_tree("eight_puzzle",bad)["valid"]
    incomplete=ingest_local(fixture_root/"incomplete")
    extracted,_=extract_outputs(incomplete["files"])
    assert "sudoku" in extracted and "solution" not in extracted["sudoku"]


def test_cli_refuses_report_directory_inside_submission(tmp_path):
    import pytest
    from reviewer.cli import main
    repo=tmp_path/"student"; repo.mkdir(); (repo/"main.py").write_text("pass\n")
    with pytest.raises(SystemExit): main(["review-local",str(repo),"--out",str(repo/"reports")])
    assert not (repo/"reports").exists()

def test_github_http_client_uses_read_only_token_header_under_mock():
    from unittest.mock import patch
    from reviewer.github import GitHubClient
    class Response:
        headers={"X-GitHub-Request-Id":"test"}
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def read(self): return b'{"ok": true}'
    seen={}
    def fake_open(req,timeout):
        seen["method"]=req.get_method(); seen["authorization"]=req.get_header("Authorization"); seen["timeout"]=timeout
        return Response()
    with patch("reviewer.github.urllib.request.urlopen",fake_open):
        payload,_=GitHubClient(token="test-token",timeout=3).get("/user")
    assert payload=={"ok":True}
    assert seen=={"method":"GET","authorization":"Bearer test-token","timeout":3}

def test_reviewer_configuration_and_qualitative_rubric_have_unset_weights():
    from reviewer.reviewer_config import load_reviewer_config
    import yaml
    from pathlib import Path
    config=load_reviewer_config()
    assert config["reviewer"]["skills"] and config["reviewer"]["definition_of_done"]
    framework=yaml.safe_load(Path("rubrics/assignment-01-framework.yaml").read_text(encoding="utf-8"))
    assert framework["approved_by_instructor"] is False
    assert all(x["weight"] is None for x in framework["criteria"])

def test_openai_compatible_llm_mock_call_schema_citations_and_source_gate():
    from unittest.mock import patch
    from reviewer.llm import OpenAICompatibleProvider
    from reviewer.reviewer_config import load_reviewer_config
    config=load_reviewer_config(); config["llm"]["enabled"]=True
    result={"summary":"The source declares a square.","findings":[{"task_id":"latin_square","category":"correctness","observations":["A constant is present."],"assessment":"Its declared output meets the validator, but this does not establish IDDFS.","confidence":"medium","uncertainties":["The solver path was not executed."],"evidence":[{"path":"latin.py","line_start":1,"line_end":1}],"recommendation":"Inspect the search path separately."}]}
    seen={}
    class Response:
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def read(self): return json.dumps({"choices":[{"message":{"content":json.dumps(result)}}],"usage":{"total_tokens":42}}).encode()
    def fake_open(req,timeout):
        body=json.loads(req.data)
        seen["method"]=req.get_method(); seen["system"]=body["messages"][0]["content"]; seen["user"]=body["messages"][1]["content"]
        return Response()
    repo={"name":"synthetic","sha":"abc","files":{"latin.py":"LATIN_SQUARE = [[1,2],[2,1]]"}}
    deterministic={"findings":[{"task_id":"latin_square","evidence_search":[{"path":"latin.py","lines":[1]}]}]}
    with patch("reviewer.llm.urllib.request.urlopen",fake_open):
        response=OpenAICompatibleProvider("http://localhost:1234/v1","local-model").review(repo,{"tasks":[]},deterministic,config,include_source=False)
    assert response["status"]=="completed" and response["usage"]["total_tokens"]==42
    assert response["source_code_sent"] is False and seen["method"]=="POST"
    assert "untrusted data" in seen["system"] and '"source_excerpts": []' in seen["user"]

def test_llm_rejects_invalid_schema_and_fabricated_citation():
    from reviewer.llm import validate_response
    valid_shape={"summary":"ok","findings":[{"task_id":"latin_square","category":"general","observations":[],"assessment":"unclear","confidence":"low","uncertainties":[],"evidence":[{"path":"missing.py","line_start":1,"line_end":1}],"recommendation":""}]}
    with pytest.raises(ValueError,match="path not present"):
        validate_response(valid_shape,{"solver.py":"x"},{"findings":[{"task_id":"latin_square"}]},True)
    with pytest.raises(ValueError,match="only summary and findings"):
        validate_response({"summary":"ok","findings":[],"score":100},{},{"findings":[]},False)

def test_ai_report_is_separate_and_does_not_grade(tmp_path):
    from reviewer.reviewer_config import load_reviewer_config
    config=load_reviewer_config(); config["llm"]["enabled"]=True
    class FakeProvider:
        def review(self,repo,assignment,deterministic,reviewer_config,include_source=False):
            return {"status":"completed","interpretation_type":"AI qualitative interpretation","source_code_sent":include_source,"result":{"summary":"Interpretation only.","findings":[]}}
    repo={"name":"ai-case","sha":"abc","files":{"latin.py":"LATIN_SQUARE = [[1,2],[2,1]]"}}
    spec={"id":"test","version":"1","tasks":[{"id":"latin_square","title":"Latin","algorithms":["IDDFS"]}],"rubric":{"version":"none","provisional":True,"criteria":[]}}
    report=review(repo,spec,tmp_path/"reports","latin_square",config,FakeProvider(),True,False)
    assert report["ai_review"]["status"]=="completed" and report["score"] is None
    md=(tmp_path/"reports"/"ai-case.md").read_text(encoding="utf-8")
    assert "Optional AI interpretation" in md and "Interpretation only" in md

def test_source_upload_requires_both_config_and_cli_authorization():
    from reviewer.llm import review_allowed
    from reviewer.reviewer_config import load_reviewer_config
    config=load_reviewer_config()
    config["llm"]["allow_source_upload"]=True
    assert review_allowed(config,True)
    assert not review_allowed(config,False)
    config["llm"]["allow_source_upload"]=False
    assert not review_allowed(config,True)

def test_llm_citations_are_limited_to_evidence_actually_sent():
    from reviewer.llm import validate_response
    finding={"task_id":"latin_square","category":"general","observations":[],"assessment":"review","confidence":"low","uncertainties":[],"evidence":[{"path":".env","line_start":1,"line_end":1}],"recommendation":""}
    result={"summary":"review","findings":[finding]}
    files={".env":"API_KEY=not-for-upload\n","solver.py":"pass\npass\n"}
    deterministic={"findings":[{"task_id":"latin_square","evidence_search":[{"path":"solver.py","lines":[1]}]}]}
    with pytest.raises(ValueError,match="not supplied"):
        validate_response(result,files,deterministic,True,{"solver.py":[1]})
    finding["evidence"][0]={"path":"solver.py","line_start":1,"line_end":1}
    assert validate_response(result,files,deterministic,True,{"solver.py":[1]})
    finding["evidence"][0]={"path":"solver.py","line_start":2,"line_end":2}
    with pytest.raises(ValueError,match="not supplied"):
        validate_response(result,files,deterministic,True,{"solver.py":[1]})
