import subprocess
import sys

def run(cmd):
    return subprocess.check_output(cmd, shell=True, text=True)

try:
    print("Searching Git history for real_data_loader.py...")
    # Find all commits that touched this file
    log_out = run("git log --all --format=%H -- src/cts/data/real_data_loader.py")
    commits = [c for c in log_out.splitlines() if c.strip()]
    
    if not commits:
        print("Could not find any commit with real_data_loader.py!")
        sys.exit(1)
        
    latest_commit = commits[0]
    print(f"Found the file in an older commit: {latest_commit}. Restoring...")
    
    # Restore the file from that exact commit
    run(f"git checkout {latest_commit} -- src/cts/data/real_data_loader.py")
    print("SUCCESS: real_data_loader.py has been restored!")
except Exception as e:
    print("Error:", e)
