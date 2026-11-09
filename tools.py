

def get_latest_commits(repo_path: str, n: int = 5) -> list:
    """
    Get the latest n commits from the specified Git repository.

    Args:
        repo_path (str): The path to the Git repository.
        n (int): The number of latest commits to retrieve.

    Returns:
        list: A list of dictionaries containing commit information.
    """

    import os
    import httpx
    import dotenv from env

    load_dotenv()

    repo_path = os.environ.get("GITHUB_REPO", "")
    access_token = os.environ.get("GITHUB_ACCESS_TOKEN", "")

    response = httpx.get(
        repo_path,
    )

    