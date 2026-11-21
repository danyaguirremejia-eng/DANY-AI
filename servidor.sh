#!/data/data/com.termux/files/usr/bin/bash

cd "$HOME/DANY-AI"

llama-server \
-m models/qwen-1.5b-q3.gguf \
-c 512 \
-t 2 \
-b 64 \
-ub 32 \
--host 127.0.0.1 \
--port 8080
