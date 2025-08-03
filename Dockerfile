FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# 安装所有依赖
RUN apt-get update && apt-get install -y \
    python3 python3-pip \
    git curl wget \
    build-essential cmake \
    meson ninja-build \
    pkg-config \
    && update-alternatives --install /usr/bin/python python /usr/bin/python3 1 \
    && rm -rf /var/lib/apt/lists/*

# 安装Radare2
RUN git clone https://github.com/radareorg/radare2.git /tmp/radare2 && \
    cd /tmp/radare2 && \
    ./sys/install.sh && \
    rm -rf /tmp/radare2

# 安装Rizin v0.8.1
RUN git clone https://github.com/rizinorg/rizin.git /tmp/rizin && \
    cd /tmp/rizin && \
    git checkout v0.8.1 && \
    meson setup build && \
    meson compile -C build && \
    meson install -C build && \
    ldconfig && \
    rm -rf /tmp/rizin

# Python包
RUN pip3 install r2pipe rzpipe capstone pwntools

WORKDIR /workspace

# ==========================================
# 使用方法
# ==========================================

# 安装Rizin (可能需要从源码编译，因为没有macOS ARM包)
RUN git clone https://github.com/rizinorg/rizin.git /tmp/rizin && \
    cd /tmp/rizin && \
    git checkout v0.8.1 && \
    meson setup build && \
    meson compile -C build && \
    meson install -C build && \
    rm -rf /tmp/rizin

# 安装rz-ghidra插件 (使用cmake，参考macOS脚本)
RUN git clone --recurse-submodules https://github.com/rizinorg/rz-ghidra.git /tmp/rz-ghidra && \
    cd /tmp/rz-ghidra && \
    mkdir build && cd build && \
    cmake -DCMAKE_INSTALL_PREFIX=/usr/local .. && \
    make -j$(nproc) && \
    make install && \
    rm -rf /tmp/rz-ghidra

# Python包
RUN pip3 install rzpipe r2pipe capstone pwntools

ENV PATH="/usr/local/bin:$PATH"

WORKDIR /workspace