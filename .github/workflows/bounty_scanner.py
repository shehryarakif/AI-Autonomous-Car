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
