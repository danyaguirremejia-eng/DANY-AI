#!/data/data/com.termux/files/usr/bin/bash

ROOT="$HOME/DANY-AI"
cd "$ROOT" || exit 1

server_ready() {
    curl -fsS http://127.0.0.1:8080/v1/models >/dev/null 2>&1
}

start_server() {
    if server_ready; then
        return 0
    fi

    echo ""
    echo "Iniciando servidor Qwen..."
    nohup bash "$ROOT/servidor.sh" \
        > "$ROOT/servidor.log" 2>&1 < /dev/null &

    for i in {1..120}; do
        if server_ready; then
            echo "Servidor listo."
            sleep 1
            return 0
        fi
        sleep 2
    done

    echo "No se pudo iniciar el servidor."
    echo "Revisa: $ROOT/servidor.log"
    return 1
}

while true; do
    clear
    echo ""
    echo "================================"
    echo "          DANY AI"
    echo "       COMMAND CENTER"
    echo "================================"
    echo ""
    echo "  [1] DANY AI"
    echo "      Asistente conversacional"
    echo ""
    echo "  [2] DANY DEV"
    echo "      Developer Engine v3"
    echo ""
    echo "  [0] SALIR"
    echo ""
    echo "================================"

    read -r -p "Selecciona una opcion: " option

    case "$option" in
        1)
            if start_server; then
                python "$ROOT/chat.py"
            fi
            ;;
        2)
            if start_server; then
                python "$ROOT/dany_dev_v3.py"
            fi
            ;;
        0)
            echo "Cerrando DANY COMMAND CENTER..."
            exit 0
            ;;
        *)
            echo "Opcion no valida."
            sleep 2
            ;;
    esac

    echo ""
    read -r -p "Presiona ENTER para volver al menu..."
done
