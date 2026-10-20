import json, os, time, urllib.error, urllib.parse, urllib.request
from dataclasses import dataclass

@dataclass
class GitHubClient:
    token: str | None = None
    base_url: str = "https://api.github.com"
    timeout: int = 20
    def __post_init__(self):
        self.token = self.token or os.getenv("GITHUB_TOKEN")
        self.base_url = os.getenv("GITHUB_API_URL", self.base_url).rstrip("/")
    def get(self, endpoint):
        url = endpoint if endpoint.startswith("http") else f"{self.base_url}{endpoint}"
        headers={"Accept":"application/vnd.github+json","X-GitHub-Api-Version":"2022-11-28","User-Agent":"ai-university-project-reviewer"}
        if self.token: headers["Authorization"]=f"Bearer {self.token}"
        req=urllib.request.Request(url,headers=headers)
        for attempt in range(4):
            try:
                with urllib.request.urlopen(req,timeout=self.timeout) as res:
                    body=res.read()
                    return json.loads(body),res.headers
            except urllib.error.HTTPError as e:
                if e.code==403 and (e.headers.get("X-RateLimit-Remaining")=="0") and attempt<3:
                    time.sleep(min(2**attempt,8)); continue
                raise RuntimeError(f"GitHub API returned HTTP {e.code} for {urllib.parse.urlparse(url).path}") from e
            except (urllib.error.URLError, TimeoutError) as e:
                if attempt==3: raise RuntimeError(f"GitHub request failed: {e}") from e
                time.sleep(2**attempt)
    def list_repositories(self, organization=None, account=None, explicit=None):
        if explicit:
            repos=[]
            for name in explicit:
                data,_=self.get(f"/repos/{name}"); repos.append(data)
            return repos
        if organization: endpoint=f"/orgs/{organization}/repos?per_page=100&type=all"
        elif account: endpoint=f"/users/{account}/repos?per_page=100&type=owner"
        else: endpoint="/user/repos?per_page=100&affiliation=owner,collaborator,organization_member"
        out=[]
        while endpoint:
            page,headers=self.get(endpoint); out.extend(page)
            link=headers.get("Link",""); endpoint=None
            for part in link.split(","):
                if 'rel="next"' in part: endpoint=part[part.find("<")+1:part.find(">")]
        return out
    def repo_snapshot(self, full_name):
        meta,_=self.get(f"/repos/{full_name}"); branch=meta["default_branch"]
        commit,_=self.get(f"/repos/{full_name}/commits/{branch}"); sha=commit["sha"]
        tree,_=self.get(f"/repos/{full_name}/git/trees/{sha}?recursive=1")
        files={}
        for item in tree.get("tree",[]):
            path=item.get("path","")
            if item.get("type")!="blob" or item.get("size",0)>1_000_000: continue
            try:
                blob,_=self.get(f"/repos/{full_name}/contents/{urllib.parse.quote(path)}?ref={sha}")
                if blob.get("encoding")=="base64":
                    import base64
                    files[path]=base64.b64decode(blob["content"]).decode("utf-8",errors="replace")
            except (RuntimeError, KeyError): continue
        history,_=self.get(f"/repos/{full_name}/commits?per_page=20")
        return {"name":full_name,"sha":sha,"metadata":meta,"files":files,"history":[{"sha":c["sha"],"message":c["commit"]["message"],"date":c["commit"]["author"]["date"]} for c in history]}
