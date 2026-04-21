#!/usr/bin/env python3
"""
The Tesseract — Dashboard Server

Endpoints:
    GET /              → dashboard/index.html
    GET /api/plans     → parsed plans from ../plans/*.md
    GET /api/git       → local git log + stats (current repo)
    GET /api/github    → GitHub profile events (all repos)
    GET /api/tokens    → token usage auto-scanned from ~/.claude/projects/
    GET /api/activity  → unified feed from plans + git

Environment variables (optional):
    GITHUB_USERNAME    → your GitHub username (for profile-wide events)
    GITHUB_TOKEN       → GitHub personal access token (for private events)
    GITHUB_ORG         → GitHub org name (for org push/PR events)
"""

import http.server, json, os, re, subprocess, argparse
from pathlib import Path
from urllib.parse import urlparse, urlencode
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from datetime import datetime, timedelta


# ── Plan Parser ──────────────────────────────────────────────

def parse_plan(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    meta = dict(file=os.path.basename(filepath), slug=os.path.basename(filepath).replace(".md",""),
                name="", status="Draft", created="", updated="", author="", overview="",
                acceptance_total=0, acceptance_done=0, requirements_total=0, requirements_done=0,
                sections=[], checklist=[])
    m = re.search(r"^#\s+Feature Plan:\s*(.+)$", content, re.MULTILINE)
    if m: meta["name"] = m.group(1).strip()
    sm = re.search(r"\*\*Status\*\*:\s*`?([^`\n|]+)`?", content)
    if sm:
        raw = sm.group(1).strip()
        smap = {"DRAFT":"Draft","IN_REVIEW":"In Review","APPROVED":"Approved","IN_PROGRESS":"In Progress","COMPLETE":"Complete",
                "Draft":"Draft","In Review":"In Review","Approved":"Approved","In Progress":"In Progress","Complete":"Complete"}
        meta["status"] = smap.get(raw, raw)
    for field, key in [("Created","created"),("Last Updated","updated"),("Author","author")]:
        fm = re.search(rf"\*\*{field}\*\*:\s*(.+)$", content, re.MULTILINE)
        if fm: meta[key] = fm.group(1).strip()
    om = re.search(r"##\s+1\.\s+Overview\s*\n(.+?)(?=\n##|\n---|\Z)", content, re.DOTALL)
    if om: meta["overview"] = om.group(1).strip()[:300]
    # Extract checklists with section context and agent attribution
    section_agent_map = {
        "Requirements": "odysseus", "Technical Design": "rocky",
        "Security": "marvin", "Acceptance Criteria": "marvin",
        "Edge Cases": "marvin", "Risk Register": "odysseus",
        "Rollback Plan": "rocky", "Open Questions": "odysseus",
    }
    for num, name, tk, dk in [(7,"Acceptance Criteria","acceptance_total","acceptance_done"),
                               (3,"Requirements","requirements_total","requirements_done"),
                               (6,"Security","_sec_t","_sec_d"),
                               (5,"Edge Cases","_edge_t","_edge_d")]:
        sec = re.search(rf"##\s+{num}\.\s+{re.escape(name)}\s*\n(.+?)(?=\n##|\n---|\Z)", content, re.DOTALL)
        if sec:
            txt = sec.group(1)
            total = len(re.findall(r"- \[[ x]\]", txt))
            done = len(re.findall(r"- \[x\]", txt))
            if tk in meta: meta[tk] = total
            if dk in meta: meta[dk] = done
            # Extract individual items
            agent = section_agent_map.get(name, "rocky")
            for match in re.finditer(r"- \[([ x])\]\s*(.+?)$", txt, re.MULTILINE):
                meta["checklist"].append(dict(
                    section=name, text=match.group(2).strip(),
                    done=match.group(1)=="x", agent=agent
                ))
    for s in ["Overview","Motivation","Requirements","Technical Design","Edge Cases",
              "Security","Acceptance Criteria","Risk Register","Rollback Plan","Open Questions"]:
        if re.search(rf"##\s+\d+\.\s+{re.escape(s)}", content): meta["sections"].append(s)
    return meta


# ── Git helpers ──────────────────────────────────────────────

def git_cmd(args, cwd, timeout=5):
    try:
        r = subprocess.run(["git"]+args, capture_output=True, text=True, cwd=cwd, timeout=timeout)
        return r.stdout.strip() if r.returncode == 0 else ""
    except: return ""

def get_git_log(repo, n=20):
    out = git_cmd(["log",f"--max-count={n}","--pretty=format:%H|%h|%an|%at|%s","--no-merges"], repo)
    commits = []
    for line in (out or "").split("\n"):
        if not line: continue
        p = line.split("|", 4)
        if len(p)==5:
            commits.append(dict(hash=p[0],short=p[1],author=p[2],timestamp=int(p[3]),
                                date=datetime.fromtimestamp(int(p[3])).strftime("%Y-%m-%d %H:%M"),message=p[4]))
    return commits

def get_git_stats(repo):
    out = git_cmd(["log","--since=14 days ago","--pretty=format:%at","--no-merges"], repo)
    dc = {}
    for line in (out or "").split("\n"):
        if not line: continue
        day = datetime.fromtimestamp(int(line)).strftime("%Y-%m-%d")
        dc[day] = dc.get(day,0)+1
    today = datetime.now()
    return [dict(date=(today-timedelta(days=i)).strftime("%Y-%m-%d"),
                 day=(today-timedelta(days=i)).strftime("%m-%d"),
                 count=dc.get((today-timedelta(days=i)).strftime("%Y-%m-%d"),0)) for i in range(13,-1,-1)]


# ── GitHub API ───────────────────────────────────────────────

def fetch_github(username, token=None, org=None):
    if not username:
        return {"error":"Set GITHUB_USERNAME env var","events":[],"heatmap":[]}
    headers = {"Accept":"application/vnd.github+json","User-Agent":"TheTesseract/1.0"}
    if token: headers["Authorization"] = f"Bearer {token}"

    all_events = []

    # Fetch personal events
    for url in [f"https://api.github.com/users/{username}/events?per_page=100"]:
        try:
            req = Request(url, headers=headers)
            with urlopen(req, timeout=8) as resp:
                all_events.extend(json.loads(resp.read()))
        except (URLError, HTTPError):
            pass

    # Fetch org events if org is set
    if org:
        try:
            url = f"https://api.github.com/users/{username}/events/orgs/{org}?per_page=100"
            req = Request(url, headers=headers)
            with urlopen(req, timeout=8) as resp:
                all_events.extend(json.loads(resp.read()))
        except (URLError, HTTPError):
            pass

    if not all_events:
        return {"error":"No events found","events":[],"heatmap":[],"username":username}

    # Deduplicate by event id and filter to only YOUR events
    seen = set()
    events = []
    for ev in all_events:
        eid = ev.get("id","")
        actor = ev.get("actor",{}).get("login","")
        if eid not in seen and actor.lower() == username.lower():
            seen.add(eid)
            events.append(ev)

    # Filter to code-related events only
    code_types = {"PushEvent","PullRequestEvent","CreateEvent","PullRequestReviewEvent"}
    pushes = []
    day_commits = {}

    for ev in events:
        t = ev.get("type","")
        if t not in code_types:
            continue
        repo = ev.get("repo",{}).get("name","")
        created = ev.get("created_at","")[:16].replace("T"," ")
        day = ev.get("created_at","")[:10]

        if t == "PushEvent":
            commits = ev.get("payload",{}).get("commits",[])
            day_commits[day] = day_commits.get(day, 0) + len(commits)
            for c in commits[:3]:
                pushes.append(dict(repo=repo, message=c.get("message","").split("\n")[0], date=created))
        elif t == "PullRequestEvent":
            action = ev.get("payload",{}).get("action","")
            title = ev.get("payload",{}).get("pull_request",{}).get("title","")
            pushes.append(dict(repo=repo, message=f"PR {action}: {title}", date=created))
            if action in ("opened","closed"):
                day_commits[day] = day_commits.get(day, 0) + 1

    # Build 28-day heatmap aligned to weekdays (Mon=0)
    today = datetime.now()
    start = today - timedelta(days=27)
    # Pad the start so it begins on a Monday
    start_weekday = start.weekday()  # 0=Mon, 6=Sun
    heatmap = []
    # Add empty padding cells for days before start
    for i in range(start_weekday):
        heatmap.append(dict(date="", day="", count=-1))  # -1 = empty/padding
    for i in range(27, -1, -1):
        d = today - timedelta(days=i)
        ds = d.strftime("%Y-%m-%d")
        heatmap.append(dict(date=ds, day=d.strftime("%a")[:2], count=day_commits.get(ds, 0)))

    return {"events":pushes[:15], "heatmap":heatmap, "username":username, "org":org or ""}


# ── Claude Code Local Usage ──────────────────────────────────

def scan_claude_usage(days=14):
    """Scan ~/.claude/projects/ JSONL files for token usage."""
    projects_dir = Path.home() / ".claude" / "projects"
    if not projects_dir.exists():
        return {"auto": True, "source": "local", "daily": [], "total_input": 0, "total_output": 0, "total": 0,
                "error": "~/.claude/projects/ not found — is Claude Code installed?"}

    cutoff = datetime.now() - timedelta(days=days)
    day_buckets = {}
    total_input = total_output = 0
    sessions_count = 0

    for jsonl_file in projects_dir.rglob("*.jsonl"):
        # Skip files older than cutoff based on mtime for performance
        try:
            if datetime.fromtimestamp(os.path.getmtime(str(jsonl_file))) < cutoff:
                continue
        except OSError:
            continue

        session_input = session_output = 0
        session_has_usage = False

        try:
            with open(jsonl_file, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    if obj.get("type") != "assistant":
                        continue

                    usage = obj.get("message", {}).get("usage", {})
                    if not usage:
                        continue

                    inp = (usage.get("input_tokens", 0)
                           + usage.get("cache_creation_input_tokens", 0)
                           + usage.get("cache_read_input_tokens", 0))
                    out = usage.get("output_tokens", 0)

                    if inp or out:
                        session_has_usage = True
                        session_input += inp
                        session_output += out

                        # Bucket by day using the record timestamp
                        ts = obj.get("timestamp", "")
                        day = ts[:10] if len(ts) >= 10 else ""
                        if day:
                            try:
                                record_date = datetime.fromisoformat(day)
                                if record_date >= cutoff:
                                    if day not in day_buckets:
                                        day_buckets[day] = {"input": 0, "output": 0, "total": 0}
                                    day_buckets[day]["input"] += inp
                                    day_buckets[day]["output"] += out
                                    day_buckets[day]["total"] += inp + out
                            except ValueError:
                                pass

        except (OSError, PermissionError):
            continue

        if session_has_usage:
            sessions_count += 1
            total_input += session_input
            total_output += session_output

    # Build sorted daily array, fill missing days
    daily = []
    today = datetime.now()
    for i in range(days - 1, -1, -1):
        d = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        bucket = day_buckets.get(d, {"input": 0, "output": 0, "total": 0})
        daily.append(dict(date=d, day=d[5:], input=bucket["input"], output=bucket["output"], total=bucket["total"]))

    return {
        "auto": True,
        "source": "local",
        "daily": daily,
        "total_input": total_input,
        "total_output": total_output,
        "total": total_input + total_output,
        "sessions": sessions_count,
    }


# ── Server ───────────────────────────────────────────────────

class Handler(http.server.SimpleHTTPRequestHandler):
    plans_dir = repo_dir = ""
    gh_user = gh_token = gh_org = ""

    def do_GET(self):
        p = urlparse(self.path).path
        routes = {
            "/api/plans": self._plans, "/api/git": self._git,
            "/api/github": self._github, "/api/tokens": self._tokens,
            "/api/activity": self._activity, "/api/memory": self._memory,
        }
        if p in routes:
            self._json(routes[p]())
        else:
            super().do_GET()

    def _plans(self):
        plans = []
        pp = Path(self.plans_dir)
        if pp.exists():
            for f in sorted(pp.glob("*.md")):
                try: plans.append(parse_plan(str(f)))
                except Exception as e: plans.append(dict(file=f.name,slug=f.stem,name=f.stem.replace("-"," ").title(),status="Draft",error=str(e)))
        return plans

    def _git(self):
        return dict(commits=get_git_log(self.repo_dir), stats=get_git_stats(self.repo_dir),
                    branch=git_cmd(["rev-parse","--abbrev-ref","HEAD"], self.repo_dir))

    def _github(self):
        return fetch_github(self.gh_user, self.gh_token, self.gh_org)

    def _tokens(self):
        return scan_claude_usage(14)

    def _activity(self):
        acts = []
        pp = Path(self.plans_dir)
        if pp.exists():
            for f in sorted(pp.glob("*.md")):
                try:
                    p = parse_plan(str(f))
                    mt = os.path.getmtime(str(f))
                    acts.append(dict(type="plan",timestamp=int(mt),date=datetime.fromtimestamp(mt).strftime("%Y-%m-%d %H:%M"),
                                     message=f"{p['name']} \u2014 {p['status']}",agent="odysseus",detail=p.get("overview","")[:120]))
                except: pass
        for c in get_git_log(self.repo_dir, 10):
            agent = "rocky"
            m = c["message"].lower()
            if m.startswith("test"): agent = "marvin"
            elif m.startswith("docs"): agent = "babel"
            elif "pr" in m or "merge" in m: agent = "muaddib"
            acts.append(dict(type="commit",timestamp=c["timestamp"],date=c["date"],message=c["message"],agent=agent,detail=c["short"]))
        acts.sort(key=lambda x:x["timestamp"], reverse=True)
        return acts[:20]

    def _memory(self):
        """Parse memory files for each agent — return entry counts and last modified."""
        memory_dir = Path(self.repo_dir) / "memory"
        agents = ["odysseus", "rocky", "marvin", "babel", "muaddib", "ratatouille"]
        result = []
        for agent in agents:
            fp = memory_dir / f"{agent}.md"
            if not fp.exists():
                result.append(dict(agent=agent, entries=0, last_modified="", sections=[]))
                continue
            try:
                content = fp.read_text(encoding="utf-8")
                mtime = os.path.getmtime(str(fp))
                # Count non-empty lines under section headers (skip comments and blanks)
                entries = 0
                sections = []
                current_section = None
                for line in content.split("\n"):
                    if line.startswith("## ") and not line.startswith("## Memory"):
                        current_section = line[3:].strip()
                        sections.append(dict(name=current_section, count=0))
                    elif current_section and line.strip() and not line.strip().startswith("<!--") and not line.strip().startswith(">") and not line.strip() == "---":
                        if not line.strip().endswith("-->"):
                            entries += 1
                            if sections:
                                sections[-1]["count"] += 1
                result.append(dict(
                    agent=agent, entries=entries,
                    last_modified=datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M"),
                    sections=sections,
                ))
            except Exception as e:
                result.append(dict(agent=agent, entries=0, error=str(e)))
        return result

    def _json(self, data):
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type","application/json")
        self.send_header("Content-Length",str(len(body)))
        self.send_header("Access-Control-Allow-Origin","*")
        self.send_header("Cache-Control","no-cache")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        if "/api/" in str(args[0]): super().log_message(fmt, *args)


def main():
    ap = argparse.ArgumentParser(description="The Tesseract Dashboard")
    ap.add_argument("--port", type=int, default=3000)
    ap.add_argument("--plans-dir", default=os.path.join(os.path.dirname(__file__),"..","plans"))
    ap.add_argument("--repo-dir", default=os.path.join(os.path.dirname(__file__),".."))
    args = ap.parse_args()

    Handler.plans_dir = os.path.abspath(args.plans_dir)
    Handler.repo_dir = os.path.abspath(args.repo_dir)
    Handler.gh_user = os.environ.get("GITHUB_USERNAME","")
    Handler.gh_token = os.environ.get("GITHUB_TOKEN","")
    Handler.gh_org = os.environ.get("GITHUB_ORG","")
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    srv = http.server.HTTPServer(("", args.port), Handler)
    print(f"\n  \033[1m\033[38;5;216m\U0001fae9  The Tesseract \u2014 Dashboard\033[0m")
    print(f"  \033[2m{'━'*37}\033[0m")
    print(f"  \033[38;5;150m✓\033[0m http://localhost:{args.port}")
    print(f"  \033[38;5;150m✓\033[0m Plans: {Handler.plans_dir}")
    if Handler.gh_user:
        gh_label = Handler.gh_user
        if Handler.gh_org: gh_label += f" + org:{Handler.gh_org}"
        print(f"  \033[38;5;150m✓\033[0m GitHub: {gh_label}")
    else: print(f"  \033[38;5;245m○\033[0m GitHub: set GITHUB_USERNAME for profile data")
    print(f"  \033[38;5;150m✓\033[0m Tokens: auto-scanning ~/.claude/projects/")
    print()
    try: srv.serve_forever()
    except KeyboardInterrupt: print("\n  \033[38;5;167m■\033[0m Shutting down."); srv.shutdown()

if __name__ == "__main__": main()
