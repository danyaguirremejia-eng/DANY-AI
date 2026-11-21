import json
import os
import urllib.request
import urllib.error

BASE = os.path.expanduser("~/DANY-AI")
URL = "http://127.0.0.1:8080/v1/chat/completions"
MEMORY = os.path.join(BASE, "memoria.json")
IDENTITY = os.path.join(BASE, "identidad.txt")

MAX_HISTORY = 6
MAX_TOKENS = 120

with open(IDENTITY, encoding="utf-8") as f:
    SYSTEM = f.read().strip()


def load_memories():
    try:
        with open(MEMORY, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            return []
        result = []
        for item in data:
            if isinstance(item, str) and item.strip():
                item = item.strip()
                if item not in result:
                    result.append(item)
        return result
    except (OSError, ValueError):
        return []


def save_memories(data):
    temp = MEMORY + ".tmp"
    with open(temp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(temp, MEMORY)


def system_message():
    saved = load_memories()
    memory_text = "\n".join("- " + x for x in saved)
    if not memory_text:
        memory_text = "No hay recuerdos guardados."
    return SYSTEM + "\n\nRECUERDOS AUTORIZADOS:\n" + memory_text


def help_menu():
    print("""
===== COMANDOS DANY AI =====
/help       Mostrar comandos
/remember   Guardar un recuerdo
/memory     Consultar recuerdos
/forget     Borrar todos los recuerdos
/clear      Limpiar conversación actual
/exit       Salir de DANY AI
============================
""")


history = []

print("\n===== DANY AI v4 =====")
print("Asistente iniciado. Memoria selectiva activada.")
print("Escribe /help para ver los comandos.")

# Elimina duplicados antiguos sin guardar conversaciones.
save_memories(load_memories())

while True:
    try:
        msg = input("\nTU: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nDANY AI: Hasta pronto.")
        break

    if not msg:
        continue

    command = msg.lower()

    if command == "/exit":
        print("DANY AI: Hasta pronto.")
        break

    if command == "/help":
        help_menu()
        continue

    if command == "/clear":
        history.clear()
        print("DANY AI: Conversación limpiada. Tus recuerdos siguen guardados.")
        continue

    if command == "/memory":
        saved = load_memories()
        print("\nRECUERDOS:")
        print("\n".join("- " + x for x in saved) if saved else "Sin recuerdos.")
        continue

    if command.startswith("/remember "):
        note = msg[len("/remember "):].strip()
        if not note:
            print("DANY AI: Escribe el recuerdo después de /remember.")
            continue

        saved = load_memories()
        if note in saved:
            print("DANY AI: Ese recuerdo ya existe.")
        else:
            saved.append(note)
            save_memories(saved)
            print("DANY AI: Recuerdo guardado.")
        continue

    if command == "/forget":
        save_memories([])
        print("DANY AI: Todos los recuerdos fueron borrados.")
        continue

    history.append({"role": "user", "content": msg})

    messages = [
        {"role": "system", "content": system_message()}
    ] + history

    payload = {
        "model": "DANY-AI",
        "messages": messages,
        "temperature": 0.65,
        "top_p": 0.9,
        "repeat_penalty": 1.1,
        "max_tokens": MAX_TOKENS,
        "stream": False
    }

    try:
        request = urllib.request.Request(
            URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )

        with urllib.request.urlopen(request, timeout=180) as response:
            result = json.loads(response.read().decode("utf-8"))

        answer = result["choices"][0]["message"]["content"].strip()
        print("\nDANY AI:", answer)

        history.append({"role": "assistant", "content": answer})

        if len(history) > MAX_HISTORY:
            history[:] = history[-MAX_HISTORY:]

    except urllib.error.URLError as error:
        history.pop()
        print("\nDANY AI: No pude conectar con el servidor:", error)

    except Exception as error:
        history.pop()
        print("\nDANY AI: Ocurrió un error:", error)
