import subprocess

try:
    print("--- GIT LOG ---")
    print(subprocess.check_output("git log -3", shell=True, text=True))
    print("--- GIT STATUS ---")
    print(subprocess.check_output("git status", shell=True, text=True))
except Exception as e:
    print(e)
