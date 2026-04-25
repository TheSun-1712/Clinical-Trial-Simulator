import subprocess
try:
    print(subprocess.check_output("git status -s", shell=True, text=True))
except Exception as e:
    print(e)
