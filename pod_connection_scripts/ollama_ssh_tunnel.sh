#!/bin/bash

echo 'Ollama ssh tunnel started'

trap 'echo "Caught signal, stopping SSH tunnel..."; kill $SSH_PID; exit 0' SIGINT SIGTERM

# Run SSH in the background and capture its PID
ssh -N -L 11434:localhost:11434 -J csc-pod gaborszita@pod-gpu &
SSH_PID=$!

# Wait for the SSH process so the trap can catch Ctrl+C
wait $SSH_PID