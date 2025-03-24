# 1. 选用 CUDA 12.x + cuDNN8 + Ubuntu 22.04 的镜像 (仅示例，实际可根据需要调整)
FROM nvidia/cuda:12.1.1-cudnn8-devel-ubuntu22.04

ENV HOME=/root/
ENV FLYWHEEL="/flywheel/v0"
WORKDIR $FLYWHEEL
RUN mkdir -p $FLYWHEEL/input

# Installing the current project (most likely to change, above layer can be cached)
COPY ./ $FLYWHEEL/

# 2. 安装 Python 3.10 及 pip
#    默认 Ubuntu 22.04 自带 python3.10，但最好显式安装一下并升级 pip
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3.10-distutils \
    wget \
    && rm -rf /var/lib/apt/lists/*

# 安装 pip (如果容器里没有 `pip3` 或需要升级到新版本)
RUN wget https://bootstrap.pypa.io/get-pip.py \
    && python3.10 get-pip.py \
    && rm get-pip.py

# 建立软链接，让默认 'python' 命令指向 python3.10（可选）
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.10 1

RUN apt-get update && \
    apt-get clean && \
    apt-get install bc && \
    apt-get install unzip && \
    apt-get install -y git && \
    pip install flywheel-gear-toolkit && \
    pip install flywheel-sdk && \
    pip install nibabel && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
# 3. 复制代码并安装依赖（假设有 requirements.txt）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Installing main dependencies
# FSL (add additional dep here)
# RUN /opt/conda/bin/conda install -n base -c $FSL_CONDA_CHANNEL fsl-base fsl-utils fsl-avwutils -c conda-forge
# set FSLDIR so FSL tools can use it, in this minimal case, the FSLDIR will be the root conda directory
ENV PATH="/opt/conda/bin:${PATH}"
ENV FSLDIR="/opt/conda"
# activate FSL
#RUN $FSLDIR/etc/fslconf/fsl.sh

# Configure entrypoint
RUN bash -c 'chmod +rx $FLYWHEEL/run.py' && \
    bash -c 'chmod +rx $FLYWHEEL/SF.sh' \
ENTRYPOINT ["python","/flywheel/v0/run.py"] 

