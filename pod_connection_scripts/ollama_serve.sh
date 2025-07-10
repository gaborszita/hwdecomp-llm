#!/bin/bash

set -m  # enable job control
echo 'Ollama serve started'

trap 'echo "Caught signal, sending SIGINT to remote process..."; ssh csc-pod "ssh pod-gpu \"pkill -SIGINT -f \\\"ollama serve\\\"\""' SIGINT SIGTERM

# Run SSH command in background so the trap can act
ssh csc-pod << EOF &
  set -e

  ssh pod-gpu << INNER_EOF
    set -e

    module load apptainer
    OLLAMA_KEEP_ALIVE=-1
    apptainer exec --nv ollama-container/ollama_container.sif ollama serve
INNER_EOF
EOF

wait