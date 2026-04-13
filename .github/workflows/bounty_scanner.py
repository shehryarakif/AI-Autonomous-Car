import os
import requests

GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}"}

def find_bounties():
    # Query: issues with label "bounty" across public repos
    # You can customize this search query
    query = "is:issue is:open label:bounty"
    url = f"https://api.github.com/search/issues?q={query}"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    return response.json()["items"]

if __name__ == "__main__":
    bounties = find_bounties()
    for issue in bounties:
        print(f"Found bounty: {issue['html_url']} - {issue['title']}")

      - name: Run bounty scanner
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          TARGET_REPO: "zio/zio"
          TARGET_ISSUE: "9909"
        run: python scripts/bounty_scanner.py

import requests
from datetime import datetime

OPIRE_URL = "https://api.opire.dev/rewards"

def fetch_opire_bounties():
    resp = requests.get(OPIRE_URL)
    resp.raise_for_status()
    return resp.json()

def is_issue_still_open(issue_url: str) -> bool:
    """Quick GitHub API check to filter out closed issues."""
    # Extract owner/repo/number from URL
    parts = issue_url.replace("https://github.com/", "").split("/")
    owner, repo, _, issue_number = parts[0], parts[1], parts[2], parts[3]
    
    url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}
    resp = requests.get(url, headers=headers)
    return resp.status_code == 200 and resp.json().get("state") == "open"

if __name__ == "__main__":
    bounties = fetch_opire_bounties()
    print(f"Total Opire bounties fetched: {len(bounties)}\n")
    
    open_bounties = []
    for b in bounties:
        if is_issue_still_open(b["issue_url"]):
            open_bounties.append(b)
            print(f"💰 ${b['amount']} - {b['title']}")
            print(f"   🔗 {b['issue_url']}")
            print(f"   🏷️  Labels: {', '.join(b.get('labels', []))}")
            print()
        else:
            print(f"❌ Skipped (issue closed): {b['issue_url']}")
    
    print(f"Open bounties available: {len(open_bounties)}")
