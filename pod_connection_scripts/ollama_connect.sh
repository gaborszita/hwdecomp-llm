#!/bin/bash

# Start the two scripts in background
./ollama_serve.sh &
pid1=$!
echo "Started ollama_serve.sh with PID $pid1"

./ollama_ssh_tunnel.sh &
pid2=$!
echo "Started ollama_ssh_tunnel.sh with PID $pid2"

echo "Both processes started"

cleanup() {
  echo "Caught signal, forwarding to children..."
  kill "$pid1"
  kill "$pid2"
  wait "$pid1"
  wait "$pid2"
  exit 1
}

trap cleanup SIGINT SIGTERM

wait "$pid1"
wait "$pid2"
