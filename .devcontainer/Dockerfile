FROM ubuntu:24.04 as build

# setup build directory
RUN mkdir -p /root/build_dir        && \
    mkdir -p /root/stage/usr/local  && \
    mkdir -p /root/stage/usr/lib

RUN apt-get update -y
RUN apt-get upgrade -y

RUN apt-get install -y build-essential clang bison flex libreadline-dev                \
    gawk tcl-dev libffi-dev git mercurial graphviz                  \
    xdot pkg-config libftdi-dev zlib1g-dev gperf                    \
    libboost-program-options-dev autoconf libgmp-dev                \
    meson ninja-build cmake gnat curl lld                           \
    libboost-system-dev libboost-python-dev libboost-filesystem-dev \
    python3 python3-pip python3.12-venv python3-pyparsing           \
    ghdl ghdl-gcc libghdl-dev

RUN cd /root/build_dir                                      && \
    git clone https://github.com/YosysHQ/yosys              && \
    cd yosys                                                && \
    git checkout 32ec5a9ccd4e41f774e8bcae5fff70a568b2a36c   && \
    git submodule update --init --recursive                 && \
    make -j 4                                               && \
    make install PREFIX=/root/stage/usr/local

RUN cd /root/build_dir                                      && \
    git clone https://github.com/YosysHQ/SymbiYosys         && \
    cd SymbiYosys                                           && \
    git checkout 1b36b27d90c99f4bd8c732532ccd88e361d5b5d9   && \
    make install PREFIX=/root/stage/usr/local

RUN cd /root/build_dir                                      && \
    git clone https://github.com/SRI-CSL/yices2             && \
    cd yices2                                               && \
    git checkout fda0a325ea7923f152ea9f9a5d20eddfd1d96224   && \
    autoconf                                                && \
    ./configure                                             && \
    make -j 4                                               && \
    make install prefix=/root/stage/usr/local

RUN cd /root/build_dir                                      && \
    git clone https://bitbucket.org/arieg/extavy.git        && \
    cd extavy                                               && \
    git checkout f2e304405f3aac81159eb2861b18ae03ef9aa1ad   && \
    cp bin/avy /root/stage/usr/local/bin/avy

RUN cd /root/build_dir                                      && \
    git clone https://github.com/boolector/boolector        && \
    cd boolector                                            && \
    git checkout 43dae91c1070e5e2633e036ebd75ffb13fe261e1   && \
    ./contrib/setup-btor2tools.sh                           && \
    ./contrib/setup-picosat.sh                              && \
    ./configure.sh && cd build                              && \
    make -j 4                                               && \
    mv bin/* /root/stage/usr/local/bin                      && \
    mv lib/* /root/stage/usr/local/lib                      && \
    cd /root/build_dir/boolector/deps/btor2tools/build      && \
    mv bin/* /root/stage/usr/local/bin                      && \
    cp -r /root/build_dir/boolector/deps/picosat /root/build_dir

RUN cd /root/build_dir                                      && \
    git clone https://github.com/arminbiere/aiger.git       && \
    cd aiger                                                && \
    git checkout 57594d2f95b286289da02ea37e2c3c934893dff5   && \
    ./configure.sh && make                                  && \
    make install PREFIX=/root/stage/usr/local

RUN cd /root/build_dir                                      && \
    git clone https://github.com/upscale-project/pono.git   && \
    cd pono                                                 && \
    git checkout b6f8ccea10c2df5c7a6ff326f37ce8307ee44a25   && \
    ./contrib/setup-bison.sh                                && \
    ./contrib/setup-flex.sh                                 && \
    ./contrib/setup-smt-switch.sh                           && \
    ./contrib/setup-btor2tools.sh                           && \
    ./configure.sh                                          && \
    make -C build -j4 PREFIX="/root/stage/usr/local"        && \
    cp build/pono       /root/stage/usr/local/bin           && \
    cp build/libpono.so /root/stage/usr/lib/libpono.so

RUN cd /root/build_dir                                      && \
    cd yosys                                                && \
    make install

# ghdl-yosys-plugin is a shared library
# build it and copy to plugins directory of yosys installation
RUN cd /root/build_dir                                      && \
    git clone https://github.com/ghdl/ghdl-yosys-plugin.git && \
    cd ghdl-yosys-plugin                                    && \
    git checkout 4ea20ad3f1c1177b912a93308a8e926d5981792d   && \
    make                                                    && \
    mkdir   -p /root/stage/usr/local/share/yosys/plugins/   && \
    cp ghdl.so /root/stage/usr/local/share/yosys/plugins/

COPY requirements.txt /root/stage/opt/requirements.txt

ENV VIRTUAL_ENV=/root/stage/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN pip install -r /root/stage/opt/requirements.txt

FROM ubuntu:24.04 as final

COPY --from=build /root/stage/usr/local/bin/*           /usr/local/bin/
COPY --from=build /root/stage/usr/local/lib/*           /usr/local/lib/
COPY --from=build /root/stage/usr/local/include/*       /usr/local/include/
COPY --from=build /root/stage/usr/local/share/yosys     /usr/local/share/yosys
COPY --from=build /root/stage/usr/lib/libpono.so        /usr/lib/libpono.so

RUN apt-get update -y
RUN apt-get upgrade -y

RUN apt-get install -y ghdl ghdl-gcc libghdl-dev tcl-dev    \
    python3 python3-pip python3.12-venv

ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
COPY --from=build /root/stage/opt/venv  /opt/venv
