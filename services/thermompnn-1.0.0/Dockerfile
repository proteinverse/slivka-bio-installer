FROM mambaorg/micromamba:cuda11.8.0-ubuntu22.04

ENV THERMO_MPNN=/usr/local/share/ThermoMPNN
ADD --chown=$MAMBA_USER:$MAMBA_USER \
    https://github.com/Kuhlman-Lab/ThermoMPNN.git#v1.0.0 \
    ${THERMO_MPNN}
RUN --mount=type=bind,source=./environment.yaml,target=/tmp/env.yaml \
    micromamba install -y -n base -f /tmp/env.yaml && \
    micromamba clean --all --yes
ENV PYTHONPATH=${THERMO_MPNN}
