import json
import os
import requests
from urllib.parse import urlparse

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
OPIRE_URL = "https://api.opire.dev/rewards"

def get_open_bounties():
    resp = requests.get(OPIRE_URL)
    resp.raise_for_status()
    bounties = resp.json()
    
    open_bounties = []
    for b in bounties:
        # Quick check if issue is still open (optional, but recommended)
        issue_url = b["issue_url"]
        # Skip if you can't check; for now we assume all are open
        open_bounties.append(b)
    return open_bounties

if __name__ == "__main__":
    bounties = get_open_bounties()
    if not bounties:
        print("No bounties found.")
        exit(0)
    
    # Select the highest reward bounty
    selected = max(bounties, key=lambda x: x.get("amount", 0))
    
    # Extract repo owner/name from issue URL
    # e.g., https://github.com/owner/repo/issues/123
    parts = selected["issue_url"].replace("https://github.com/", "").split("/")
    repo_url = f"{parts[0]}/{parts[1]}"
    issue_number = parts[3]
    
    output = {
        "repo_url": repo_url,
        "issue_number": issue_number,
        "title": selected["title"],
        "amount": selected["amount"]
    }
    
    print(json.dumps(output))
