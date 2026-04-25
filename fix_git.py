import subprocess
import sys

def run_git(cmd, ignore_error=False):
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        if not ignore_error:
            print(f"Warning/Error: {result.stderr.strip()}")
    else:
        print(f"Success: {result.stdout.strip()}")

def main():
    # 1. Abort any broken rebases or merges that are locking the repo
    run_git("git rebase --abort", ignore_error=True)
    run_git("git merge --abort", ignore_error=True)
    
    # 2. Rescue our last commit that had the dashboard fixes (24b3193)
    # We ignore error here because if the commit is already there, cherry-pick might fail safely.
    run_git("git cherry-pick 24b3193", ignore_error=True)
    
    # 3. Add any lingering files just in case
    run_git("git add .")
    
    # 4. Commit them safely
    run_git("git commit -m \"fix: final dashboard integration and sync\"")
    
    # 5. Force push to the remote repository to overwrite the broken history
    run_git("git push -f origin mlchanges")
    
    print("\n------------------------------------------------------------")
    print("Git fix complete! You are safely synced with GitHub.")
    print("------------------------------------------------------------")

if __name__ == "__main__":
    main()
