#!/bin/bash

ssh -L 8894:localhost:8894 -J csc-pod gaborszita@pod-gpu \
'module load apptainer && apptainer run --nv ollama-container/dev_env.sif bash -c \
"jupyter notebook --ip=0.0.0.0 --no-browser --allow-root --port=8894 --NotebookApp.port_retries=0"'