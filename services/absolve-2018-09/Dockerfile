ARG DEBIAN_VERSION=12

FROM debian:${DEBIAN_VERSION}-slim AS build

ARG ABSOLVE_GIT_BRANCH=master

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends build-essential libz-dev cmake && \
	apt-get clean

ENV ABSOLVE_ROOT=/usr/local/absolve/
ADD https://github.com/Genentech/Absolve.git#${ABSOLVE_GIT_BRANCH} ${ABSOLVE_ROOT}
ADD --checksum=sha256:66a469b6e608a51f8347236f4912e27dc5c60c60d7d53ae9bfe4683316c6f04c \
    https://archives.boost.io/release/1.82.0/source/boost_1_82_0.tar.gz /tmp/boost.tar.gz
RUN tar -zxf /tmp/boost.tar.gz -C /usr/local/
ENV BOOST_ROOT=/usr/local/boost_1_82_0

WORKDIR ${BOOST_ROOT}
RUN ./bootstrap.sh --with-libraries=system,filesystem,iostreams,regex && ./b2 install

WORKDIR ${ABSOLVE_ROOT}
RUN tar -zxf "dep/bwa-0.7.12.tar.gz" -C dep/ && \
    rm "dep/bwa-0.7.12.tar.gz" && \
    tar -zxf "dep/hmmer-3.1b2.tar.gz" -C dep/ && \
    rm "dep/hmmer-3.1b2.tar.gz"
RUN (cd "dep/bwa-0.7.12/" && make)
RUN (cd "dep/hmmer-3.1b2/" && ./configure && make)
RUN cmake CMakeLists.txt && \
    make clean && \
    make

FROM debian:${DEBIAN_VERSION}-slim

COPY --from=build /usr/local/lib/* /usr/local/lib/
COPY --from=build /usr/local/absolve /usr/local/absolve
ENV LD_LIBRARY_PATH=/usr/local/lib:/usr/lib:/lib
ENV ABSOLVE_HOME=/usr/local/absolve
ENV	ABSOLVE_HMMFILE_SCFV=${ABSOLVE_HOME}/hmm/absolveSCFV.hmm \
    ABSOLVE_HMMFILE_HEAVY=${ABSOLVE_HOME}/hmm/absolveVH.hmm \
    ABSOLVE_HMMFILE_LIGHT=${ABSOLVE_HOME}/hmm/absolveVL.hmm

RUN echo "#! /bin/sh\nexec /usr/local/absolve/absolve_rel \"\$@\"\n" >/usr/local/bin/absolve && \
    chmod +x /usr/local/bin/absolve
ENTRYPOINT /usr/local/absolve/absolve_rel
