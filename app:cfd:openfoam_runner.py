# app/cfd/openfoam_runner.py
import subprocess, tempfile, math, re
from pathlib import Path

IMAGE = "openfoam/openfoam11-paraview510"
RHO, CHORD, SPAN = 1.225, 1.0, 1.0   # cas tutoriel airFoil2D

def run_airfoil_cfd(U=20.0, aoa_deg=4.0):
    """Écoulement 2D autour d'un profil (tutoriel simpleFoam/airFoil2D),
       angle d'attaque imposé via les composantes de U."""
    wd = Path(tempfile.mkdtemp(prefix="aeromind-cfd-"))
    aoa = math.radians(aoa_deg)
    cmds = (
        f"cp -r $FOAM_TUTORIALS/incompressible/simpleFoam/airFoil2D/* /case/ && "
        f"sed -i 's/internalField.*uniform.*/internalField   uniform "
        f"({U*math.cos(aoa):.4f} {U*math.sin(aoa):.4f} 0)/' /case/0.orig/U && "
        f"cd /case && blockMesh && simpleFoam | tail -5"
    )
    subprocess.run(["docker", "run", "--rm", "-v", f"{wd}:/case", IMAGE,
                    "bash", "-c", cmds], check=True, capture_output=True)

    f = (wd / "postProcessing/forces/0/force.dat").read_text().strip().splitlines()
    last = re.findall(r"[-\d.e+]+", f[-1])
    fx, fy = float(last[0]), float(last[1])
    q = 0.5 * RHO * U**2 * CHORD * SPAN
    return {"aoa_deg": aoa_deg, "U": U,
            "cl": fy / q, "cd": fx / q,
            "l_over_d": fy / fx if fx else None,
            "workdir": str(wd)}