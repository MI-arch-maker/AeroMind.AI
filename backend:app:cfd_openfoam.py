"""Runner OpenFOAM RANS (simpleFoam/airFoil2D) — actif uniquement si l'image de déploiement
inclut OpenFOAM (Dockerfile.openfoam). Sinon la méthode de panneaux prend le relais."""
import os, shutil, subprocess, tempfile, math, re

def available() -> bool:
    return (os.environ.get("AEROMIND_OPENFOAM") == "1"
            or shutil.which("simpleFoam") is not None
            or os.path.isdir("/opt/openfoam11"))

def run_airfoil2d(U=20.0, aoa_deg=4.0):
    wd = tempfile.mkdtemp(prefix="am-of-")
    a = math.radians(aoa_deg)
    script = f"""
set -e
for rc in /opt/openfoam*/etc/bashrc /usr/lib/openfoam/*/etc/bashrc; do [ -f "$rc" ] && . "$rc" && break; done
cp -r "$FOAM_TUTORIALS/incompressible/simpleFoam/airFoil2D" case
cd case
if [ -d 0.orig ]; then UFILE=0.orig/U; else UFILE=0/U; fi
sed -i "s|internalField.*uniform.*|internalField   uniform ({U*math.cos(a):.6f} {U*math.sin(a):.6f} 0);|" "$UFILE"
blockMesh > /dev/null
simpleFoam > log.simpleFoam || true
"""
    p = subprocess.run(["bash", "-c", script], cwd=wd, capture_output=True, text=True, timeout=900)
    forces = os.path.join(wd, "case", "postProcessing", "forces", "0", "force.dat")
    if not os.path.exists(forces):
        return {"ok": False, "stderr_tail": p.stderr[-2000:], "workdir": wd}
    last = open(forces).read().strip().splitlines()[-1]
    fx, fy = [float(v) for v in re.findall(r"[-+0-9.eE]+", last)[1:3]]
    q = 0.5*1.225*U*U
    return {"ok": True, "cl": round(fy/q, 4), "cd": round(fx/q, 5),
            "solver": "simpleFoam (airFoil2D, RANS kOmegaSST)", "workdir": wd}