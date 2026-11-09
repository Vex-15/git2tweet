import os
import httpx

repo_path = os.environ.get("GITHUB_REPO", "")
os.environ["GITHUB_REPO"] = repo_path
  
response = httpx.get(
        repo_path,
    )

print(response)