from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess


def main() -> int:
    parser = argparse.ArgumentParser(description="Lance un cas OpenFOAM dans Docker, sans matériel réel.")
    parser.add_argument("case", type=Path, help="répertoire contenant 0/, constant/ et system/")
    parser.add_argument("--image", default=os.getenv("AEROMIND_SITL_OPENFOAM_IMAGE", "opencfd/openfoam-default:latest"))
    parser.add_argument("--solver", default=os.getenv("OPENFOAM_SOLVER", "simpleFoam"))
    parser.add_argument("--build", action="store_true", help="reconstruire l’image locale avant exécution")
    args = parser.parse_args()
    case = args.case.resolve()
    for required in ("0", "constant", "system"):
        if not (case / required).is_dir():
            raise SystemExit(f"Cas invalide: dossier manquant {case / required}")
    image = "aeromind-sitl-openfoam"
    if args.build:
        subprocess.run(["docker", "build", "--build-arg", f"OPENFOAM_IMAGE={args.image}", "-t", image, str(Path(__file__).parent)], check=True)
    else:
        image = args.image
    subprocess.run(["docker", "run", "--rm", "-v", f"{case}:/case", "-e", f"OPENFOAM_SOLVER={args.solver}", image, "/case"], check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
