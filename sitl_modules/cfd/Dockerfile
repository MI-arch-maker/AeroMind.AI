# Image isolée pour un cas OpenFOAM local. Aucun accès matériel requis.
ARG OPENFOAM_IMAGE=opencfd/openfoam-default:latest
FROM ${OPENFOAM_IMAGE}

WORKDIR /case
COPY run_case.sh /usr/local/bin/run-sitl-cfd
RUN chmod +x /usr/local/bin/run-sitl-cfd

ENTRYPOINT ["/usr/local/bin/run-sitl-cfd"]
