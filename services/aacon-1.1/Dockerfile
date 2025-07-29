FROM eclipse-temurin:17-jre-jammy
RUN apt-get update && \
    apt-get install -y --no-install-recommends python3 python-is-python3 && \
    rm -rf /var/lib/apt/lists/*
ADD --chown=root:root --chmod=705 https://github.com/bartongroup/aacon/releases/download/v1.1/compbio-conservation-1.1.jar /usr/local/share/aacon/compbio-conservation.jar
ADD --chown=root:root --chmod=705 docker-build-files/aacon.sh /usr/local/bin/aacon

ENV COMPBIO_CONSERVATION=/usr/local/share/aacon/compbio-conservation.jar
