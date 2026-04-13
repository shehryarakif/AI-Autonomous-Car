import os
import requests

GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}"}

# Allow overriding via environment variables
TARGET_REPO = os.environ.get("TARGET_REPO", "zio/zio")
TARGET_ISSUE = os.environ.get("TARGET_ISSUE", "9909")

def fetch_single_issue(repo: str, issue_number: str):
    url = f"https://api.github.com/repos/{repo}/issues/{issue_number}"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    return response.json()

if __name__ == "__main__":
    issue = fetch_single_issue(TARGET_REPO, TARGET_ISSUE)
    print(f"🎯 Targeting: {issue['html_url']}")
    print(f"📝 Title: {issue['title']}")
    print(f"📄 Body:\n{issue['body']}")
