import subprocess
def run(cmd):
    print(">", cmd)
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    out, _ = p.communicate()
    print(out.decode())

run("git branch -a")
run("git log --oneline -n 5")
run("git status")
