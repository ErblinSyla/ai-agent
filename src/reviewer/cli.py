import argparse, json, sys
from pathlib import Path
import yaml
from .specs import load_assignment
from .ingestion import ingest_local
from .github import GitHubClient
from .orchestration import review
from .similarity import compare_repositories
from .reviewer_config import load_local_environment, load_reviewer_config
from .llm import create_provider

def _run(repos,spec,args,reviewer_config,provider=None,ai_setup_error=None):
    out=Path(args.out).resolve()
    for repo in repos:
        root=repo.get("local_path")
        if root and out.is_relative_to(Path(root).resolve()):
            raise ValueError(f"Report output directory must be outside the submitted repository: {root}")
    pairs=compare_repositories(repos,spec.get("similarity",{}))
    reports=[]
    for repo in repos:
        related=[pair for pair in pairs if repo["name"] in {pair["repository_a"],pair["repository_b"]}]
        reports.append(review(repo,spec,args.out,args.task,reviewer_config,provider,args.ai_review,args.allow_source_upload,ai_setup_error,related))
    if pairs:
        Path(args.out).mkdir(parents=True,exist_ok=True)
        Path(args.out,"similarity.json").write_text(json.dumps({"pairs":pairs,"non_accusatory":True},indent=2),encoding="utf-8")
        Path(args.out,"similarity.md").write_text("# Similarity review\n\nPotential similarities require human review and are not proof of misconduct.\n\n"+"\n".join(f"- {x['repository_a']} ↔ {x['repository_b']}: {len(x['exact_matches'])} exact, {len(x['normalized_matches'])} normalized, {len(x['matching_fragments'])} matching fragments. {x['methodology']}" for x in pairs),encoding="utf-8")
    print(json.dumps({"reviewed":len(reports),"similarity_pairs":len(pairs),"out":str(Path(args.out).resolve())},indent=2))

def main(argv=None):
    load_local_environment()
    p=argparse.ArgumentParser(prog="ai-reviewer",description="Read-only evidence-based AI course submission reviewer")
    sub=p.add_subparsers(dest="command",required=True)
    def common(q):
        q.add_argument("--assignment",default="assignments/2026-27/assignment-01.yaml")
        q.add_argument("--out",default="reports")
        q.add_argument("--task",choices=["all","social_golfers","sudoku","latin_square","search_trees"],default="all")
        q.add_argument("--reviewer-config",default="config/reviewer.yaml")
        q.add_argument("--ai-review",action="store_true",help="Request optional qualitative LLM interpretation")
        q.add_argument("--allow-source-upload",action="store_true",help="Authorize source excerpts only if reviewer config also enables upload")
    q=sub.add_parser("review-local",help="Review explicitly supplied local repositories"); q.add_argument("repositories",nargs="*"); common(q)
    q=sub.add_parser("review-github",help="Review explicit repos or repositories discovered in an org/account"); q.add_argument("--repo",action="append",help="owner/name; repeat to scope repositories"); q.add_argument("--org"); q.add_argument("--account"); common(q)
    args=p.parse_args(argv)
    try:
        spec=load_assignment(args.assignment)
        reviewer_config=load_reviewer_config(args.reviewer_config)
    except Exception as e: p.error(f"Cannot load review configuration: {e}")
    if args.command=="review-local":
        if not args.repositories: p.error("Pass one or more local repositories")
        try: repos=[ingest_local(x) for x in args.repositories]
        except OSError as e: p.error(str(e))
    else:
        client=GitHubClient()
        if not client.token: print("GITHUB_TOKEN is unset; only public repositories can be read.",file=sys.stderr)
        configured=spec.get("repositories",[])
        names=args.repo or [r if isinstance(r,str) else r.get("name") for r in configured]
        names=[n for n in names if n]
        if not names:
            if not (args.org or args.account): p.error("Pass --repo, configure repositories in the spec, or specify --org/--account")
            try: names=[x["full_name"] for x in client.list_repositories(organization=args.org,account=args.account)]
            except Exception as e: p.error(str(e))
        repos=[]
        for name in names:
            try: repos.append(client.repo_snapshot(name))
            except Exception as e: print(f"Skipping {name}: {e}",file=sys.stderr)
    if not repos: p.error("No repositories were successfully retrieved")
    provider=None; ai_setup_error=None
    if args.ai_review and reviewer_config.get("llm",{}).get("enabled",False):
        try: provider=create_provider(reviewer_config)
        except Exception as e: ai_setup_error=str(e)
    try: _run(repos,spec,args,reviewer_config,provider,ai_setup_error)
    except (OSError,ValueError) as e: p.error(str(e))
if __name__=="__main__": main()
