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
    from unittest.mock import patch
    with patch("reviewer.cli.load_local_environment") as load_env:
        with pytest.raises(SystemExit) as ex: main(["--help"])
    assert ex.value.code==0
    load_env.assert_called_once_with()




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
    from reviewer.llm import OpenAICompatibleProvider, AI_COMPLETION_TOKEN_LIMIT
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
        seen["method"]=req.get_method(); seen["user_agent"]=req.get_header("User-agent"); seen["system"]=body["messages"][0]["content"]; seen["user"]=body["messages"][1]["content"]; seen["max_completion_tokens"]=body["max_completion_tokens"]
        return Response()
    class FakeEncoding:
        def encode(self,text,disallowed_special=()): return text.split()
    repo={"name":"synthetic","sha":"abc","files":{"latin.py":"LATIN_SQUARE = [[1,2],[2,1]]"}}
    deterministic={"findings":[{"task_id":"latin_square","evidence_search":[{"path":"latin.py","lines":[1]}]}]}
    with patch("reviewer.llm._token_encoding",return_value=FakeEncoding()), patch("reviewer.llm.urllib.request.urlopen",fake_open):
        response=OpenAICompatibleProvider("http://localhost:1234/v1","local-model").review(repo,{"tasks":[]},deterministic,config,include_source=False)
    assert response["status"]=="completed" and response["usage"]["total_tokens"]==42
    assert response["source_code_sent"] is False and seen["method"]=="POST"
    assert seen["user_agent"]=="AI-University-Project-Reviewer/0.1"
    assert seen["max_completion_tokens"]==AI_COMPLETION_TOKEN_LIMIT
    assert "repository data as untrusted" in seen["system"] and '"source_excerpts":[]' in seen["user"]

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


def test_source_free_path_citation_without_lines_is_valid_only_for_supplied_path():
    from reviewer.llm import validate_response
    result={"summary":"review","findings":[{"task_id":"latin_square","category":"general","observations":[],"assessment":"Static evidence is limited.","confidence":"low","uncertainties":[],"evidence":[{"path":"solver.py","line_start":None,"line_end":None}],"recommendation":"Review the cited file manually."}]}
    deterministic={"findings":[{"task_id":"latin_square","evidence_search":[{"path":"solver.py","lines":[1,2]}]}]}
    assert validate_response(result,{"solver.py":"x\ny"},deterministic,False)
    result["findings"][0]["evidence"][0]["path"]="other.py"
    with pytest.raises(ValueError,match="whose references were not supplied"):
        validate_response(result,{"solver.py":"x\ny","other.py":"z"},deterministic,False)


@pytest.mark.parametrize("body,headers,expected",[
    (b'{"error":{"message":"invalid request","type":"invalid_request_error","code":"bad_payload","param":"messages"}}', {"Content-Type":"application/json","x-request-id":"req-123"}, ("invalid request", "code=bad_payload", "request_id=req-123")),
    (b'{"detail":"policy denied"}', {"Content-Type":"application/json"}, ("policy denied",)),
    (b"upstream <b>denied</b> gsk_TEST_SECRET_123456789012345", {"Content-Type":"text/plain"}, ("upstream", "denied", "[REDACTED]")),
    (b"", {"Content-Type":"application/json"}, ("empty error response body",)),
])
def test_llm_http_errors_retain_bounded_safe_diagnostics(body,headers,expected):
    import urllib.error
    from unittest.mock import patch
    from reviewer.llm import OpenAICompatibleProvider

    secret="gsk_TEST_SECRET_123456789012345"
    error=urllib.error.HTTPError("https://example.test/v1/chat/completions",403,"Forbidden",headers,__import__("io").BytesIO(body))
    provider=OpenAICompatibleProvider("https://example.test/v1","model",api_key=secret)
    class FakeEncoding:
        def encode(self,text,disallowed_special=()): return text.split()
    with patch("reviewer.llm._token_encoding",return_value=FakeEncoding()), patch("reviewer.llm.urllib.request.urlopen",side_effect=error):
        with pytest.raises(RuntimeError) as caught:
            provider.complete("system", "user")
    message=str(caught.value)
    assert "HTTP 403" in message
    assert all(piece in message for piece in expected), message
    assert secret not in message
    assert "Bearer " not in message


def test_llm_http_error_does_not_return_provider_text_when_source_was_sent():
    import urllib.error
    from unittest.mock import patch
    from reviewer.llm import OpenAICompatibleProvider

    error=urllib.error.HTTPError("https://example.test/v1/chat/completions",403,"Forbidden",{"Content-Type":"text/plain"},__import__("io").BytesIO(b"private source excerpt echoed by provider"))
    provider=OpenAICompatibleProvider("https://example.test/v1","model",api_key="secret")
    class FakeEncoding:
        def encode(self,text,disallowed_special=()): return text.split()
    with patch("reviewer.llm._token_encoding",return_value=FakeEncoding()), patch("reviewer.llm.urllib.request.urlopen",side_effect=error):
        with pytest.raises(RuntimeError) as caught:
            provider.complete("system", "user", source_sent=True)
    assert "HTTP 403" in str(caught.value)
    assert "omitted because source excerpts" in str(caught.value)
    assert "private source excerpt" not in str(caught.value)


def test_groq_gpt_oss_uses_strict_json_schema_without_changing_generic_endpoints():
    from reviewer.llm import OpenAICompatibleProvider, AI_RESPONSE_SCHEMA
    from unittest.mock import patch
    class FakeEncoding:
        def encode(self,text,disallowed_special=()): return text.split()
    provider=OpenAICompatibleProvider("https://api.groq.com/openai/v1","openai/gpt-oss-20b")
    response_format=provider._response_format()
    assert response_format["type"]=="json_schema"
    assert response_format["json_schema"]["strict"] is True
    assert response_format["json_schema"]["schema"]["required"]==AI_RESPONSE_SCHEMA["required"]
    def assert_strict_compatible(node):
        if isinstance(node,dict):
            if node.get("type")=="object":
                assert set(node.get("properties",{}))==set(node.get("required",[]))
                assert node.get("additionalProperties") is False
            for child in node.values(): assert_strict_compatible(child)
        elif isinstance(node,list):
            for child in node: assert_strict_compatible(child)
    assert_strict_compatible(response_format["json_schema"]["schema"])
    evidence_properties=response_format["json_schema"]["schema"]["properties"]["findings"]["items"]["properties"]["evidence"]["items"]["properties"]
    assert evidence_properties["line_start"]=={"type":"null"} and evidence_properties["line_end"]=={"type":"null"}
    uploaded_properties=provider._response_format(source_sent=True)["json_schema"]["schema"]["properties"]["findings"]["items"]["properties"]["evidence"]["items"]["properties"]
    assert uploaded_properties["line_start"]["type"]==["integer","null"]
    assert OpenAICompatibleProvider("https://example.test/v1","openai/gpt-oss-20b")._response_format()=={"type":"json_object"}

    class Response:
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def read(self): return b'{"choices":[{"message":{"content":"{\\"summary\\":\\"ok\\",\\"findings\\":[]}"}}]}'
    seen={}
    def fake_open(request,timeout):
        seen.update(json.loads(request.data))
        return Response()
    with patch("reviewer.llm._token_encoding",return_value=FakeEncoding()), patch("reviewer.llm.urllib.request.urlopen",fake_open):
        result,_=provider.complete("system","user")
    assert result=={"summary":"ok","findings":[]}
    assert seen["response_format"]==response_format
    assert seen["model"]=="openai/gpt-oss-20b"


@pytest.mark.parametrize("response_body,expected",[
    (b"not-json", "malformed JSON response body"),
    (b"{}", "did not return valid JSON content"),
    (b'{"choices":[{"message":{"content":"{"}}]}', "did not return valid JSON content"),
])
def test_llm_rejects_malformed_or_incomplete_success_responses(response_body,expected):
    from reviewer.llm import OpenAICompatibleProvider
    from unittest.mock import patch
    class FakeEncoding:
        def encode(self,text,disallowed_special=()): return text.split()
    class Response:
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def read(self): return response_body
    with patch("reviewer.llm._token_encoding",return_value=FakeEncoding()), patch("reviewer.llm.urllib.request.urlopen",return_value=Response()):
        with pytest.raises(ValueError,match=expected):
            OpenAICompatibleProvider("https://api.groq.com/openai/v1","openai/gpt-oss-20b").complete("system","user")


def test_llm_groq_json_validation_error_reports_only_safe_failed_generation_metadata():
    import urllib.error
    from unittest.mock import patch
    from reviewer.llm import OpenAICompatibleProvider
    failed=json.dumps({"summary":"PRIVATE_GENERATION_DO_NOT_REPORT","findings":[{"task_id":"latin_square","category":"general","observations":[],"assessment":"uncertain","confidence":"low","uncertainties":[],"evidence":[]}]})
    body=json.dumps({"error":{"message":"Failed to validate JSON. Please adjust your prompt.","type":"json_validate_failed","code":"json_validate_failed","failed_generation":failed}}).encode()
    error=urllib.error.HTTPError("https://api.groq.com/openai/v1/chat/completions",400,"Bad Request",{"Content-Type":"application/json","x-request-id":"req-safe"},__import__("io").BytesIO(body))
    class FakeEncoding:
        def encode(self,text,disallowed_special=()): return text.split()
    provider=OpenAICompatibleProvider("https://api.groq.com/openai/v1","openai/gpt-oss-20b",api_key="do-not-show")
    with patch("reviewer.llm._token_encoding",return_value=FakeEncoding()), patch("reviewer.llm.urllib.request.urlopen",side_effect=error):
        with pytest.raises(RuntimeError) as caught: provider.complete("system","user")
    message=str(caught.value)
    assert "json_validate_failed" in message and "request_id=req-safe" in message
    assert "failed_generation_type=string" in message and "failed_generation_json=valid" in message
    assert "failed_generation_missing_schema_fields=$/findings/0/recommendation" in message
    assert "PRIVATE_GENERATION_DO_NOT_REPORT" not in message and "do-not-show" not in message


def test_ai_prompt_compacts_redundancy_within_budget_and_preserves_all_tasks():
    from reviewer.llm import _build_ai_prompt, estimate_prompt_tokens, AI_INPUT_TOKEN_BUDGET
    from unittest.mock import patch
    class FakeEncoding:
        def encode(self,text,disallowed_special=()): return text.split()

    assignment={"id":"assignment-01","version":"1","title":"Constraint search","tasks":[
        {"id":task,"title":task.replace("_"," "),"requirements":["validate output", "show required algorithm"]}
        for task in ("social_golfers","sudoku","latin_square","search_trees")
    ]}
    findings=[]
    for task in assignment["tasks"]:
        findings.append({
            "task_id":task["id"],"task":task,"status":"review",
            "output_validation":{"valid":False,"errors":[f"constraint error {i}: duplicated diagnostic detail" for i in range(100)]},
            "algorithm_compliance":{"required":["IDDFS"],"analysis":{"IDDFS":{"status":"uncertain","confidence":"low","evidence":[{"path":"solver.py","line":i,"name":"search"} for i in range(100)]}}},
            "evidence_search":[{"path":f"task/{task['id']}/solver.py","lines":list(range(1,50))} for _ in range(20)],
            "evidence_files":[f"task/{task['id']}/solver.py" for _ in range(100)],
            "required_deliverables":["repeated metadata"]*100,
        })
    deterministic={"findings":findings}
    repo={"name":"synthetic","sha":"abc","files":{"solver.py":"private raw source must never enter prompt"*1000}}
    system,user=_build_ai_prompt(assignment,deterministic,repo,False,[])
    with patch("reviewer.llm._token_encoding",return_value=FakeEncoding()):
        estimate=estimate_prompt_tokens("openai/gpt-oss-20b",system,user,{"type":"json_object"})
    compact=json.loads(user.split("Evidence JSON:\n",1)[1])
    compact_findings=compact["deterministic_findings"]["findings"]
    assert estimate<=AI_INPUT_TOKEN_BUDGET
    assert {finding["task_id"] for finding in compact_findings}=={task["id"] for task in assignment["tasks"]}
    assert all(finding["output_validation"]["errors"]["count"]==100 for finding in compact_findings)
    assert all(finding["output_validation"]["errors"]["omitted_distinct"]==97 for finding in compact_findings)
    assert all(finding["algorithm_compliance"]["analysis"]["IDDFS"]["omitted_evidence_count"]==97 for finding in compact_findings)
    assert compact["source_excerpts"]==[] and "private raw source" not in user
    assert all("omitted_redundant_fields" in finding for finding in compact_findings)


def test_ai_prompt_budget_rejects_irreducibly_large_request_before_http():
    from reviewer.llm import OpenAICompatibleProvider
    from unittest.mock import patch
    class FakeEncoding:
        def encode(self,text,disallowed_special=()): return text.split()
    provider=OpenAICompatibleProvider("http://localhost:1234/v1","local-model")
    with patch("reviewer.llm._token_encoding",return_value=FakeEncoding()), patch("reviewer.llm.urllib.request.urlopen") as send:
        with pytest.raises(ValueError,match="exceeds the safe input budget"):
            provider.complete("system", "important "*6000)
    send.assert_not_called()


def _representative_source_free_findings():
    return {"findings": [
        {"task_id": "social_golfers", "status": "validated output", "output_validation": {"valid": True, "weeks": 4, "distinct_pairs": 36, "errors": []}, "algorithm_compliance": {"required": ["DFS", "backtracking"], "analysis": {"DFS": {"status": "static structural evidence", "confidence": "medium"}, "backtracking": {"status": "static structural evidence", "confidence": "medium"}}}},
        {"task_id": "sudoku", "status": "validated output", "output_validation": {"valid": True, "fixtures": {name: {"valid": True, "errors": []} for name in ("easy", "medium", "hard")}, "missing_difficulty_levels": []}, "algorithm_compliance": {"required": ["BFS", "backtracking"], "analysis": {"BFS": {"status": "static structural evidence"}, "backtracking": {"status": "static structural evidence"}}}},
        {"task_id": "latin_square", "status": "validated output", "output_validation": {"valid": True, "errors": []}, "algorithm_compliance": {"required": ["IDDFS", "backtracking"], "analysis": {"IDDFS": {"status": "not detected statically"}, "backtracking": {"status": "static structural evidence"}}}},
        {"task_id": "search_trees", "status": "invalid output", "output_validation": {"valid": False, "problems": {
            "eight_puzzle": {"valid": True, "state_count": 10, "edge_count": 10, "errors": [], "manual_review": []},
            "missionaries_cannibals": {"valid": False, "state_count": 14, "edge_count": 13, "errors": ["missionaries/cannibals initial state differs from configured initial state", "missionaries/cannibals goal differs from configured goal", "missionaries/cannibals edge 0 violates boat capacity, direction, or crossing"], "manual_review": []},
            "rotating_workforce": {"valid": True, "state_count": 7, "edge_count": 6, "errors": [], "manual_review": ["no complete domain transition rules are configured"]},
        }}, "algorithm_compliance": {"required": [], "analysis": {}}},
    ]}


def test_source_free_ai_prompt_prioritizes_four_tasks_and_specific_validator_facts():
    from reviewer.llm import _build_ai_prompt, _source_free_review_facts
    deterministic = _representative_source_free_findings()
    assignment = load_assignment("assignments/2026-27/assignment-01.yaml")
    repo = {"name": "student", "sha": "abc", "files": {"private.py": "PRIVATE_SOURCE_MUST_NOT_BE_SENT"}}
    system, user = _build_ai_prompt(assignment, deterministic, repo, False, [], response_schema_in_api=True)
    evidence = json.loads(user.split("Evidence JSON:\n", 1)[1])
    compact = {item["task_id"]: item for item in evidence["deterministic_findings"]["findings"]}
    tasks = {item["id"]: item for item in evidence["assignment"]["tasks"]}
    assert {"social_golfers", "sudoku", "latin_square", "search_trees"} == set(compact)
    assert tasks["social_golfers"]["algorithms"] == ["DFS", "backtracking"]
    assert "no_pair_repeats" in tasks["social_golfers"]["constraints"]
    assert tasks["sudoku"]["difficulty_levels"] == ["Easy", "Medium", "Hard"]
    assert "depth_and_termination" in tasks["latin_square"]["constraints"]
    assert "rotating_workforce" in {problem["id"] for problem in tasks["search_trees"]["problems"]}
    assert all(compact[key]["source_free_review_facts"] for key in compact)
    assert "task attribution and runtime behavior are not established" in compact["sudoku"]["algorithm_compliance"]["scope_note"]
    assert "edge 0 violates boat capacity, direction, or crossing" in " ".join(compact["search_trees"]["source_free_review_facts"])
    assert "no complete domain transition rules are configured" in " ".join(compact["search_trees"]["source_free_review_facts"])
    assert "for search_trees, cover every listed problem fact" in system
    assert "Never ask for source to be uploaded or provided to this service" in system
    assert evidence["source_excerpts"] == [] and evidence["source_upload_included"] is False
    assert "PRIVATE_SOURCE_MUST_NOT_BE_SENT" not in user


def test_source_free_ai_result_must_address_validator_facts_not_generic_algorithm_uncertainty():
    from reviewer.llm import validate_response, _source_free_review_facts
    deterministic = _representative_source_free_findings()
    findings = []
    for item in deterministic["findings"]:
        facts = _source_free_review_facts(item)
        findings.append({
            "task_id": item["task_id"], "category": "correctness", "observations": facts,
            "assessment": f"The deterministic task result is: {facts[0]}", "confidence": "low",
            "uncertainties": ["This does not establish that the student solver ran or used the required algorithm."],
            "evidence": [], "recommendation": "Check this result with targeted local tests and instructor-side inspection; do not upload source.",
        })
    specific = {"summary": "The submitted outputs include both accepted cases and concrete transition failures; no code was executed.", "findings": findings}
    assert validate_response(specific, {}, deterministic, False)
    paraphrased = json.loads(json.dumps(specific))
    search = next(item for item in paraphrased["findings"] if item["task_id"] == "search_trees")
    search["observations"] = [
        "Eight puzzle: validator accepted graph (10 states, 10 edges).",
        "Missionaries/cannibals: invalid (3 validator errors); 14 states, 13 edges; initial state, goal state, and edge constraints mismatched.",
        "Rotating workforce: 7 states, 6 edges; manual review required because transition rules are not configured.",
    ]
    search["recommendation"] = "Compare the submitted missionaries/cannibals states and crossings to the configured rules; ask the instructor to define workforce transitions before validating that tree."
    assert validate_response(paraphrased, {}, deterministic, False)
    generic = json.loads(json.dumps(specific))
    for finding in generic["findings"]:
        finding["observations"] = ["Cannot confirm algorithm compliance."]
        finding["assessment"] = "Cannot confirm algorithm compliance."
        finding["recommendation"] = "Provide source code and tests."
    with pytest.raises(ValueError, match="did not address supplied deterministic evidence"):
        validate_response(generic, {}, deterministic, False)
    source_request = json.loads(json.dumps(specific))
    source_request["findings"][0]["recommendation"] = "Provide source code and tests."
    with pytest.raises(ValueError, match="asks for source code despite source-free mode"):
        validate_response(source_request, {}, deterministic, False)
    source_request["findings"][0]["recommendation"] = "Do not upload source code; inspect it locally and run targeted tests."
    assert validate_response(source_request, {}, deterministic, False)


def test_local_dotenv_loads_missing_values_and_preserves_shell_precedence(tmp_path,monkeypatch):
    from reviewer.reviewer_config import load_local_environment
    env_file=tmp_path/".env"
    env_file.write_text("GROQ_API_KEY=test-key-do-not-print\nAI_REVIEW_BASE_URL=https://api.groq.com/openai/v1\nAI_REVIEW_MODEL=from-dotenv\n",encoding="utf-8")
    for name in ("GROQ_API_KEY","AI_REVIEW_BASE_URL","AI_REVIEW_MODEL"):
        monkeypatch.delenv(name,raising=False)
    monkeypatch.setenv("AI_REVIEW_MODEL","from-shell")
    load_local_environment(env_file)
    assert __import__("os").environ["GROQ_API_KEY"]=="test-key-do-not-print"
    assert __import__("os").environ["AI_REVIEW_BASE_URL"]=="https://api.groq.com/openai/v1"
    assert __import__("os").environ["AI_REVIEW_MODEL"]=="from-shell"


def test_provider_missing_configuration_names_variables_without_values(monkeypatch):
    from reviewer.llm import create_provider
    config={"llm":{"base_url_env":"AI_REVIEW_BASE_URL","model_env":"AI_REVIEW_MODEL","api_key_env":"GROQ_API_KEY"}}
    for name in ("AI_REVIEW_BASE_URL","AI_REVIEW_MODEL","GROQ_API_KEY"):
        monkeypatch.delenv(name,raising=False)
    with pytest.raises(RuntimeError) as caught:
        create_provider(config)
    assert "AI_REVIEW_BASE_URL, AI_REVIEW_MODEL" in str(caught.value)
    monkeypatch.setenv("AI_REVIEW_BASE_URL","https://api.groq.com/openai/v1")
    monkeypatch.setenv("AI_REVIEW_MODEL","openai/gpt-oss-20b")
    with pytest.raises(RuntimeError) as caught:
        create_provider(config)
    assert "GROQ_API_KEY is required" in str(caught.value)
    assert "openai/gpt-oss-20b" not in str(caught.value)


def _demo_report():
    return {
        "findings": [{"task_id": "latin_square", "status": "validated output"}],
        "ai_review": {
            "status": "completed", "source_code_sent": False,
            "result": {"summary": "Static evidence is limited.", "findings": [{
                "task_id": "latin_square", "category": "general", "observations": [],
                "assessment": "Runtime correctness was not verified.", "confidence": "low",
                "uncertainties": ["The solver was not run."], "evidence": [],
                "recommendation": "Run instructor-approved tests.",
            }]},
        },
    }


def test_report_verifier_uses_correct_paths_and_accepts_zero_ai_findings():
    from reviewer.verify_report import report_errors
    report = _demo_report()
    assert report_errors(report) == []
    report["ai_review"]["result"]["findings"] = []
    assert report_errors(report) == []


@pytest.mark.parametrize("mutate,expected", [
    (lambda r: r["ai_review"].pop("result"), "ai_review.result must be an object"),
    (lambda r: r["ai_review"]["result"].pop("summary"), "summary must be a non-empty string"),
    (lambda r: r["ai_review"]["result"].__setitem__("findings", None), "findings must be a list"),
    (lambda r: r["ai_review"]["result"]["findings"][0].pop("recommendation"), "missing required fields: recommendation"),
    (lambda r: r["ai_review"]["result"]["findings"][0].__setitem__("category", []), "category is outside the response schema"),
    (lambda r: r["ai_review"]["result"]["findings"][0].__setitem__("evidence", [{"path": "x.py", "line_start": 1, "line_end": None}]), "has invalid line bounds"),
    (lambda r: r["findings"].clear(), "deterministic findings must be a non-empty list"),
    (lambda r: r["ai_review"].__setitem__("source_code_sent", True), "source_code_sent must be false"),
])
def test_report_verifier_rejects_malformed_completed_reports(mutate, expected):
    from reviewer.verify_report import report_errors
    report = _demo_report()
    mutate(report)
    assert any(expected in error for error in report_errors(report))
