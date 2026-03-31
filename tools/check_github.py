"""Check GitHub API connection with the provided PAT."""

import os
import asyncio
from dotenv import load_dotenv
from github import Github

load_dotenv()

def check_connection():
    token = os.getenv("GITHUB_PAT")
    repo_name = os.getenv("GITHUB_REPO")
    
    if not token:
        print("❌ GITHUB_PAT not found in .env")
        return
        
    print(f"📡 Testing connection to {repo_name}...")
    try:
        g = Github(token)
        repo = g.get_repo(repo_name)
        print(f"✅ Successfully connected to {repo.full_name}")
        print(f"📄 Description: {repo.description}")
        print(f"⭐ Stars: {repo.stargazers_count}")
    except Exception as e:
        print(f"❌ Connection failed: {e}")

if __name__ == "__main__":
    check_connection()
