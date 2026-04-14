#!/usr/bin/env python3
"""
Automated Bounty Solver using Gemini AI.
"""

import os
import sys
import tempfile
import random
import subprocess
from datetime import datetime
from typing import List, Optional, Tuple

from github import Github, GithubException
from github.Issue import Issue
import google.generativeai as genai

# ---------- Configuration ----------
DEFAULT_REPOS = [
    "owner/repo1",   # Replace with your actual repos
    "owner/repo2",
]
LABELS = os.environ.get("LABELS", "bounty").split(",")
DRY_RUN = os.environ.get("DRY_RUN", "false").lower() == "true"
SELECTION_STRATEGY = os.environ.get("SELECTION_STRATEGY", "oldest")
GEMINI_MODEL = "gemini-1.5-flash"

# ---------- Logging ----------
def log(level, msg):
    print(f"[{datetime.utcnow().isoformat()}] {level}: {msg}", file=sys.stderr)

# ---------- Helpers ----------
def get_target_repos() -> List[str]:
    repos_env = os.environ.get("TARGET_REPOS")
    if repos_env:
        return [r.strip() for r in repos_env.split(",") if r.strip()]
    return DEFAULT_REPOS

def fetch_bounty_issues(g: Github, repos: List[str]) -> List[Tuple[str, Issue]]:
    candidates = []
    for repo_name in repos:
        try:
            repo = g.get_repo(repo_name)
        except GithubException as e:
            log("WARNING", f"Cannot access repo {repo_name}: {e}")
            continue
        try:
            issues = repo.get_issues(state='open', labels=LABELS)
            for issue in issues:
                if not issue.pull_request:
                    candidates.append((repo_name, issue))
        except GithubException as e:
            log("WARNING", f"Failed to fetch issues from {repo_name}: {e}")
    return candidates

def select_issue(candidates):
    if not candidates:
        return None
    if SELECTION_STRATEGY == "random":
        return random.choice(candidates)
    return min(candidates, key=lambda x: x[1].created_at)

def clone_repo(repo_full_name: str, target_dir: str, token: str) -> bool:
    clone_url = f"https://{token}@github.com/{repo_full_name}.git"
    try:
        subprocess.run(
            ["git", "clone", clone_url, target_dir],
            check=True, capture_output=True, text=True
        )
        log("INFO", f"Cloned {repo_full_name} into {target_dir}")
        return True
    except subprocess.CalledProcessError as e:
        log("ERROR", f"Git clone failed: {e.stderr}")
        return False

def get_issue_context(issue: Issue) -> str:
    context = f"# Issue #{issue.number}: {issue.title}\n\n"
    if issue.body:
        context += f"## Description\n{issue.body}\n\n"
    comments = issue.get_comments()
    if comments.totalCount > 0:
        context += "## Comments\n"
        for i, comment in enumerate(comments[:10]):
            context += f"**{comment.user.login}**: {comment.body}\n\n"
    return context

def call_gemini(prompt: str, api_key: str) -> Optional[str]:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(GEMINI_MODEL)
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        log("ERROR", f"Gemini API error: {e}")
        return None

def build_gemini_prompt(issue_context: str, repo_path: str) -> str:
    return f"""
You are an expert software engineer. You are given a GitHub issue and a cloned repository at `{repo_path}`.
Your task is to produce a fix that resolves the issue.

Instructions:
1. Understand the problem from the issue.
2. Explore the codebase (you may assume you have filesystem access).
3. Output a **unified git diff** (like `git diff`) that, when applied, fixes the issue.
4. The diff must be complete and correct.
5. Begin the diff with a code block labeled `diff`.

Here is the issue context:
{issue_context}

Now produce the diff. Begin with:
```diff
... your diff here ...
```"""

def parse_diff_from_response(response: str) -> Optional[str]:
    if "```diff" in response:
        start = response.find("```diff") + 7
        end = response.find("```", start)
        if end != -1:
            return response[start:end].strip()
    if response.strip().startswith("diff --git"):
        return response.strip()
    log("WARNING", "Could not parse diff from Gemini response")
    return None

def apply_diff(repo_path: str, diff_text: str) -> bool:
    with tempfile.NamedTemporaryFile(mode='w', suffix='.diff', delete=False) as f:
        f.write(diff_text)
        diff_file = f.name
    try:
        subprocess.run(
            ["git", "apply", "--whitespace=fix", diff_file],
            cwd=repo_path, check=True, capture_output=True, text=True
        )
        log("INFO", "Diff applied successfully")
        return True
    except subprocess.CalledProcessError as e:
        log("ERROR", f"Failed to apply diff: {e.stderr}")
        return False
    finally:
        os.unlink(diff_file)

def create_branch_and_commit(repo_path: str, branch_name: str, issue_number: int, title: str) -> bool:
    try:
        subprocess.run(["git", "checkout", "-b", branch_name], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
        commit_msg = f"Fix #{issue_number}: {title}\n\nAuto-generated by Bounty Solver (Gemini)"
        subprocess.run(["git", "commit", "-m", commit_msg], cwd=repo_path, check=True, capture_output=True)
        log("INFO", f"Committed changes on branch {branch_name}")
        return True
    except subprocess.CalledProcessError as e:
        log("ERROR", f"Git commit failed: {e.stderr}")
        return False

def push_branch(repo_path: str, branch_name: str, repo_full_name: str, token: str) -> bool:
    remote_url = f"https://{token}@github.com/{repo_full_name}.git"
    try:
        subprocess.run(["git", "remote", "set-url", "origin", remote_url], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(["git", "push", "-u", "origin", branch_name], cwd=repo_path, check=True, capture_output=True)
        log("INFO", f"Pushed branch {branch_name} to origin")
        return True
    except subprocess.CalledProcessError as e:
        log("ERROR", f"Push failed: {e.stderr}")
        return False

def create_pull_request(g: Github, repo_full_name: str, branch_name: str, issue_number: int, title: str) -> bool:
    try:
        repo = g.get_repo(repo_full_name)
        default_branch = repo.default_branch
        pr_title = f"Auto-solve bounty: {title}"
        pr_body = f"Fixes #{issue_number}\n\nThis PR was automatically generated by the Bounty Solver using Gemini AI."
        pr = repo.create_pull(
            title=pr_title,
            body=pr_body,
            head=branch_name,
            base=default_branch
        )
        log("INFO", f"Created PR #{pr.number}: {pr.html_url}")
        return True
    except GithubException as e:
        log("ERROR", f"Failed to create PR: {e}")
        return False

# ---------- Main ----------
def main():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        log("ERROR", "GITHUB_TOKEN environment variable not set")
        sys.exit(1)

    gemini_key = os.environ.get("GEMINI_API_KEY")
    if not gemini_key:
        log("ERROR", "GEMINI_API_KEY environment variable not set")
        sys.exit(1)

    repos = get_target_repos()
    if not repos:
        log("ERROR", "No target repositories configured")
        sys.exit(1)

    g = Github(token)

    log("INFO", f"Scanning repos: {repos} with labels {LABELS}")
    candidates = fetch_bounty_issues(g, repos)
    log("INFO", f"Found {len(candidates)} open bounty issues")

    selected = select_issue(candidates)
    if not selected:
        log("INFO", "No bounty issues to solve. Exiting.")
        sys.exit(0)

    repo_full_name, issue = selected
    log("INFO", f"Selected issue: {repo_full_name}#{issue.number}: {issue.title}")

    if DRY_RUN:
        log("INFO", "DRY_RUN enabled – no changes will be made.")
        sys.exit(0)

    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = os.path.join(tmpdir, "repo")
        if not clone_repo(repo_full_name, repo_path, token):
            sys.exit(1)

        issue_context = get_issue_context(issue)
        prompt = build_gemini_prompt(issue_context, repo_path)
        log("INFO", "Calling Gemini API...")
        gemini_response = call_gemini(prompt, gemini_key)
        if not gemini_response:
            sys.exit(1)

        diff = parse_diff_from_response(gemini_response)
        if not diff:
            log("ERROR", "No diff found. Gemini response:\n" + gemini_response[:1000])
            sys.exit(1)

        if not apply_diff(repo_path, diff):
            sys.exit(1)

        branch_name = f"bounty-solve-{issue.number}"
        if not create_branch_and_commit(repo_path, branch_name, issue.number, issue.title):
            sys.exit(1)

        if not push_branch(repo_path, branch_name, repo_full_name, token):
            sys.exit(1)

        if not create_pull_request(g, repo_full_name, branch_name, issue.number, issue.title):
            sys.exit(1)

    log("INFO", "Bounty solving completed successfully")

if __name__ == "__main__":
    main()
