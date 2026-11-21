#!/data/data/com.termux/files/usr/bin/bash
set -Eeuo pipefail

REPO="https://github.com/danyaguirremejia-eng/DANY-AI.git"
DIR="$HOME/DANY-AI"
MODEL="$DIR/models/qwen-1.5b-q3.gguf"
PART="$MODEL.part"

MODEL_SIZE=924455968
MODEL_SHA256="58cb5c05ecef48e82961f1a2be6544145ea26136f69dddda4bbbd092f0e4b993"
MODEL_URL="https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/91cad51170dc346986eccefdc2dd33a9da36ead9/qwen2.5-1.5b-instruct-q3_k_m.gguf"

echo "=================================="
echo "       DANY AI INSTALLER"
echo "=================================="

if [ -z "${PREFIX:-}" ] || [ ! -x "$PREFIX/bin/pkg" ]; then
    echo "ERROR: Este instalador necesita Termux."
    exit 1
fi

pkg update -y
pkg install -y git python curl coreutils llama-cpp

if [ ! -d "$DIR/.git" ]; then
    if [ -e "$DIR" ]; then
        echo "ERROR: $DIR existe y no es un repositorio Git."
        echo "No se modificó esa carpeta."
        exit 1
    fi
    git clone "$REPO" "$DIR"
fi

cd "$DIR"
mkdir -p models

verify_model() {
    [ -f "$1" ] || return 1
    [ "$(stat -c %s "$1")" -eq "$MODEL_SIZE" ] || return 1
    printf '%s  %s\n' "$MODEL_SHA256" "$1" | sha256sum -c - >/dev/null 2>&1
}

if verify_model "$MODEL"; then
    echo "Modelo Qwen verificado."
else
    FREE_KB=$(df -Pk "$HOME" | awk 'END {print $4}')
    if [ "$FREE_KB" -lt 1200000 ]; then
        echo "ERROR: Necesitas al menos 1.2 GB libres."
        exit 1
    fi

    echo "Descargando modelo Qwen 1.5B Q3_K_M..."

    if [ -f "$PART" ] && [ "$(stat -c %s "$PART")" -gt "$MODEL_SIZE" ]; then
        rm -f "$PART"
    fi

    if [ ! -f "$PART" ] || [ "$(stat -c %s "$PART")" -ge "$MODEL_SIZE" ]; then
        rm -f "$PART"
    fi

    curl -fL --retry 5 --retry-delay 3 \
        -C - "$MODEL_URL" -o "$PART"

    if ! verify_model "$PART"; then
        echo "ERROR: El modelo no superó la verificación SHA-256."
        rm -f "$PART"
        exit 1
    fi

    mv -f "$PART" "$MODEL"
    echo "Modelo descargado y verificado correctamente."
fi

chmod +x dany_menu.sh servidor.sh

ALIAS='alias Dany="bash ~/DANY-AI/dany_menu.sh"'
touch "$HOME/.bashrc"
grep -qxF "$ALIAS" "$HOME/.bashrc" || echo "$ALIAS" >> "$HOME/.bashrc"

echo ""
echo "=================================="
echo "       INSTALACION COMPLETA"
echo "=================================="
echo "Abre una nueva sesión de Termux."
echo "Escribe: Dany"
