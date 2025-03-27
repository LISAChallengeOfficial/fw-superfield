FROM nvidia/cuda:12.1.1-cudnn8-devel-ubuntu22.04

ENV HOME=/root/
ENV FLYWHEEL="/flywheel/v0"
WORKDIR $FLYWHEEL
RUN mkdir -p $FLYWHEEL/input

# Installing the current project (most likely to change, above layer can be cached)
COPY ./ $FLYWHEEL/


RUN apt-get update && apt-get install -y \
    python3.10 \
    python3.10-distutils \
    wget \
    && rm -rf /var/lib/apt/lists/*

RUN wget https://bootstrap.pypa.io/get-pip.py \
    && python3.10 get-pip.py \
    && rm get-pip.py

RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.10 1

RUN apt-get update && \
    apt-get clean && \
    apt-get install bc && \
    apt-get install unzip && \
    apt-get install -y jq && \
    apt-get install -y git && \
    pip install flywheel-gear-toolkit && \
    pip install flywheel-sdk && \
    pip install nibabel && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

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

