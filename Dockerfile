FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PATH="/usr/local/bin:$PATH"

# 安装所有依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-dev build-essential cmake meson ninja-build \
    pkg-config git curl wget \
    libffi-dev libssl-dev libgomp1 \
    graphviz graphviz-dev zlib1g-dev libbz2-dev liblzma-dev \
    && update-alternatives --install /usr/bin/python python /usr/bin/python3 1 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# 安装Radare2
RUN git clone --depth 1 https://github.com/radareorg/radare2.git /tmp/radare2 \
    && /tmp/radare2/sys/install.sh \
    && rm -rf /tmp/radare2

# 安装Rizin v0.8.1
RUN git clone --depth 1 --branch v0.8.1 https://github.com/rizinorg/rizin.git /tmp/rizin \
    && cd /tmp/rizin \
    && meson setup build \
    && meson compile -C build \
    && meson install -C build \
    && cd / && rm -rf /tmp/rizin

# 安装rz-ghidra插件 (使用cmake，参考macOS脚本)
RUN git clone --depth 1 --recurse-submodules https://github.com/rizinorg/rz-ghidra.git /tmp/rz-ghidra \
    && cmake -S /tmp/rz-ghidra -B /tmp/rz-ghidra/build -DCMAKE_INSTALL_PREFIX=/usr/local \
    && cmake --build /tmp/rz-ghidra/build -- -j$(nproc) \
    && cmake --install /tmp/rz-ghidra/build \
    && rm -rf /tmp/rz-ghidra \
    && ldconfig

# 安装Python包 (包括angr[full])
RUN pip3 install --no-cache-dir \
      r2pipe rzpipe capstone pwntools "angr[full]"

WORKDIR /workspace
