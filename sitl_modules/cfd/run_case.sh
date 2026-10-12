#!/usr/bin/env bash
set -euo pipefail

CASE_DIR="${1:-/case}"
SOLVER="${OPENFOAM_SOLVER:-simpleFoam}"

if [[ ! -d "$CASE_DIR/system" || ! -d "$CASE_DIR/constant" || ! -d "$CASE_DIR/0" ]]; then
  echo "Cas OpenFOAM incomplet: $CASE_DIR doit contenir 0/, constant/ et system/" >&2
  exit 2
fi

# Les images OpenFOAM fournissent généralement cette fonction d’environnement.
if [[ -f /opt/openfoam*/etc/bashrc ]]; then
  # shellcheck disable=SC1090
  source /opt/openfoam*/etc/bashrc
fi

cd "$CASE_DIR"
blockMesh 2>&1 | tee log.blockMesh
checkMesh 2>&1 | tee log.checkMesh
"$SOLVER" 2>&1 | tee "log.$SOLVER"
echo "Calcul CFD SITL terminé: $CASE_DIR"
