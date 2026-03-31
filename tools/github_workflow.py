"""AXIOM GitHub Workflow — Automated branch, commit, and PR management for Shadow Agents."""

import os
from github import Github
from core.logger import get_logger

logger = get_logger(__name__)

class GitHubWorkflow:
    def __init__(self):
        self.token = os.getenv("GITHUB_PAT")
        self.repo_name = os.getenv("GITHUB_REPO", "logeshv586-code/AITradra")
        self.g = Github(self.token) if self.token else None

    async def create_feature_pr(self, branch_name: str, title: str, body: str, files: list[dict]):
        """
        Creates a new branch, commits files, and opens a PR.
        files: [{"path": "src/app.py", "content": "..."}, ...]
        """
        if not self.g:
            logger.warning("[GitHub] No GITHUB_PAT found. Skipping PR creation.")
            return None

        try:
            repo = self.g.get_repo(self.repo_name)
            main_branch = repo.get_branch("main")
            
            # 1. Create branch
            repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=main_branch.commit.sha)
            
            # 2. Commit files
            for f in files:
                repo.create_file(
                    path=f["path"],
                    message=f"Shadow Agent: {title}",
                    content=f["content"],
                    branch=branch_name
                )
            
            # 3. Create PR
            pr = repo.create_pull(
                title=f"[Shadow Agent] {title}",
                body=body,
                head=branch_name,
                base="main"
            )
            
            logger.info(f"🚀 [GitHub] PR created: {pr.html_url}")
            return pr.html_url
        except Exception as e:
            logger.error(f"❌ [GitHub] PR creation failed: {e}")
            return None

# Singleton
github_workflow = GitHubWorkflow()
