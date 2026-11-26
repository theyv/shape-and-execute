import os, socket, subprocess, sys
from pathlib import Path
root = Path(sys.argv[1]); worktrees = root / "worktrees"; job = worktrees / "job"
def root_write(): (worktrees / "outside-job.txt").write_text("probe\n")
def git(*a):
    subprocess.run(["git","-C",str(job),"-c","user.name=Probe","-c","user.email=probe@example.invalid",
                    "-c","core.hooksPath=/dev/null","-c","gc.auto=0",*a], check=True, capture_output=True)
def git_commit():
    (job/"job.txt").write_text("writer\n"); git("add","job.txt"); git("commit","-qm","writer")
def merge(): git("merge","-q","--no-ff","--no-edit","main")
def round_trip(family, address):
    with socket.socket(family, socket.SOCK_STREAM) as s:
        s.settimeout(3); s.bind(address); s.listen(1)
        with socket.socket(family, socket.SOCK_STREAM) as c:
            c.settimeout(3); c.connect(s.getsockname())
            with s.accept()[0] as a:
                c.sendall(b"x"); assert a.recv(1) == b"x"
def unix():
    os.chdir(root / "ipc")  # relative path keeps sun_path short
    try: round_trip(socket.AF_UNIX, "p.sock")
    finally:
        try: os.unlink("p.sock")
        except OSError: pass
def internet():
    socket.create_connection(("github.com", 443), timeout=5).close()
fails = 0
for name, chk in (("worktree-root-write", root_write), ("git-add-commit", git_commit), ("git-merge", merge),
                  ("tcp-loopback", lambda: round_trip(socket.AF_INET, ("127.0.0.1", 0))), ("unix-socket", unix),
                  ("internet", internet)):
    try: chk(); print("PASS", name, flush=True)
    except Exception as e: print("FAIL", name, type(e).__name__, str(e)[:120], flush=True); fails += 1
sys.exit(int(fails != 0))
