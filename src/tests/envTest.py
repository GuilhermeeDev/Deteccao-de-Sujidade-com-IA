from dotenv import load_dotenv
import os

load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
UPLOAD_PATH = os.getenv("UPLOAD_PATH")
REPO_OWNER = os.getenv("REPO_OWNER")
REPO_NAME = os.getenv("REPO_NAME")
BRANCH = os.getenv("BRANCH")
URL_API_PROCESSAMENTO = os.getenv("URL_API_PROCESSAMENTO")

def test_env_variables():
    assert GITHUB_TOKEN is not None, "GITHUB_TOKEN is not set"
    assert UPLOAD_PATH is not None, "UPLOAD_PATH is not set"
    assert REPO_OWNER is not None, "REPO_OWNER is not set"
    assert REPO_NAME is not None, "REPO_NAME is not set"
    assert BRANCH is not None, "BRANCH is not set"
    assert URL_API_PROCESSAMENTO is not None, "URL_API_PROCESSAMENTO is not set"
    print("All environment variables are set correctly.")

test_env_variables()