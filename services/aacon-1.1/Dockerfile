FROM eclipse-temurin:17-jre-jammy
ADD --chown=root:root --chmod=705 https://github.com/bartongroup/aacon/releases/download/v1.1/compbio-conservation-1.1.jar /usr/local/share/aacon/compbio-conservation.jar
ADD --chown=root:root --chmod=705 docker-build-files/aacon.sh /usr/local/bin/aacon

ENV COMPBIO_CONSERVATION=/usr/local/share/aacon/compbio-conservation.jar
