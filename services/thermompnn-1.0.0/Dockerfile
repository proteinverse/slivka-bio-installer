FROM mambaorg/micromamba:cuda11.8.0-ubuntu22.04

ENV THERMO_MPNN=/usr/local/share/ThermoMPNN
ADD --chown=$MAMBA_USER:$MAMBA_USER \
    https://github.com/Kuhlman-Lab/ThermoMPNN.git#c6275604f3de8d35d21377ae66e49d3bf7cd5c0f \
    ${THERMO_MPNN}
RUN --mount=type=bind,source=./environment.yaml,target=/tmp/env.yaml \
    micromamba install -y -n base -f /tmp/env.yaml && \
    micromamba clean --all --yes
ENV PYTHONPATH=${THERMO_MPNN}
