import os
import subprocess
import streamlit as st

def sync_to_github(commit_message="Auto-sync ingested note to GitHub"):
    """
    Automates staging, committing, and pushing updated notes and graph data
    to the remote GitHub repository so data persists across Streamlit Cloud
    redeployments and wake-ups after inactivity.
    """
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Files/directories to ensure tracked
        target_paths = ["raw", "wiki", "graph.json", "data/graph.json"]
        
        # Stage files (including file deletions)
        subprocess.run(["git", "add", "-A"] + target_paths, cwd=base_dir, check=False)

        
        # Check if there are changes to commit
        status_proc = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=base_dir,
            capture_output=True,
            text=True,
            check=False
        )
        
        if not status_proc.stdout.strip():
            print("Git sync: No changes to commit.")
            return True

        # Configure git commit author if not configured
        subprocess.run(["git", "config", "user.name", "Cerebro Bot"], cwd=base_dir, check=False)
        subprocess.run(["git", "config", "user.email", "cerebro-bot@users.noreply.github.com"], cwd=base_dir, check=False)

        # Commit changes
        commit_proc = subprocess.run(
            ["git", "commit", "-m", commit_message],
            cwd=base_dir,
            capture_output=True,
            text=True,
            check=False
        )
        print("Git commit output:", commit_proc.stdout)

        # Retrieve GITHUB_TOKEN if present (e.g. from st.secrets or os.environ)
        github_token = None
        try:
            if hasattr(st, "secrets") and "GITHUB_TOKEN" in st.secrets:
                github_token = str(st.secrets["GITHUB_TOKEN"]).strip()
            elif "GITHUB_TOKEN" in os.environ:
                github_token = os.environ["GITHUB_TOKEN"].strip()
            elif hasattr(st, "secrets") and "GH_TOKEN" in st.secrets:
                github_token = str(st.secrets["GH_TOKEN"]).strip()
        except Exception:
            pass

        if github_token:
            # Push with token authentication to origin HEAD:main
            remote_url_proc = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                cwd=base_dir,
                capture_output=True,
                text=True,
                check=False
            )
            remote_url = remote_url_proc.stdout.strip()
            
            clean_repo = "Niklaus2003/cerebro.git"
            if remote_url:
                url = remote_url.strip().rstrip("/")
                if "github.com" in url:
                    if "github.com:" in url:
                        url = url.split("github.com:")[-1]
                    elif "github.com/" in url:
                        url = url.split("github.com/")[-1]
                if "git@" in url:
                    url = url.split("git@")[-1]
                if ":" in url:
                    url = url.split(":")[-1]
                url = url.strip("/")
                if url and "/" in url:
                    clean_repo = url if url.endswith(".git") else url + ".git"

            if clean_repo.lower().startswith("niklaus2003/"):
                clean_repo = "Niklaus2003/" + clean_repo[len("niklaus2003/"):]

            auth_url = f"https://x-access-token:{github_token}@github.com/{clean_repo}"

            push_proc = subprocess.run(
                ["git", "push", auth_url, "HEAD:main"],
                cwd=base_dir,
                capture_output=True,
                text=True,
                check=False
            )
            print("Git authenticated push output:", push_proc.stdout, push_proc.stderr)
            return push_proc.returncode == 0



        
        # Standard git push fallback (uses local git credentials)
        push_proc = subprocess.run(
            ["git", "push"],
            cwd=base_dir,
            capture_output=True,
            text=True,
            check=False
        )
        print("Git push output:", push_proc.stdout, push_proc.stderr)
        return push_proc.returncode == 0

    except Exception as err:
        print(f"Git sync warning: {err}")
        return False

if __name__ == "__main__":
    sync_to_github("Manual git sync test")
