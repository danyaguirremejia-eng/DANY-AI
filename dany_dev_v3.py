import json
import shlex
import shutil
import urllib.request
import difflib
import tempfile
import subprocess
import os
import re
from pathlib import Path
from datetime import datetime

ROOT = Path.home() / "DANY-AI"
PROJECTS = ROOT / "workspace" / "projects"
BACKUPS = ROOT / "workspace" / "backups"
OUTPUT = ROOT / "workspace" / "output"
API = "http://127.0.0.1:8080/v1/chat/completions"
MODEL = "models/qwen-1.5b-q3.gguf"
MAX_FILE_SIZE = 2500
selected = None

GITIGNORE = """
.env
.env.*
*.pem
*.key
*.p12
*.pfx
id_rsa
id_ed25519
credentials.json
secrets.json
__pycache__/
*.pyc
.venv/
venv/
node_modules/
.git/
"""

def run(args, cwd=None):
    result = subprocess.run(
        args, cwd=cwd, text=True,
        capture_output=True
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return result.stdout.strip()

def valid_name(name):
    if not re.fullmatch(r"[A-Za-z0-9_-]+", name):
        raise ValueError("Nombre no válido. Usa letras, números, _ o -.")

def get_project(name=None):
    name = name or selected
    if not name:
        raise ValueError("Primero selecciona un proyecto.")
    base = (PROJECTS / name).resolve()
    if base.parent != PROJECTS.resolve() or not base.is_dir():
        raise ValueError("Proyecto no válido.")
    return base

def get_file(filename):
    base = get_project()
    path = (base / filename).resolve()
    if not path.is_relative_to(base) or path.is_symlink():
        raise ValueError("Ruta no permitida.")
    return path

def ask_qwen(system, prompt, tokens=300):
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2,
        "max_tokens": tokens
    }
    request = urllib.request.Request(
        API,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        result = json.loads(response.read())
    return result["choices"][0]["message"]["content"]

def validate(path, content):
    if path.suffix == ".py":
        compile(content, str(path), "exec")
    elif path.suffix == ".json":
        json.loads(content)

def backup_file(path):
    base = get_project()
    relative = path.relative_to(base).as_posix()
    folder = BACKUPS / selected
    folder.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    backup = folder / (relative.replace("/", "__") + "." + stamp + ".bak")
    shutil.copy2(path, backup)
    return backup

def projects():
    items = sorted(p.name for p in PROJECTS.iterdir() if p.is_dir())
    print("\nPROYECTOS:", ", ".join(items) if items else "Ninguno")

def files():
    base = get_project()
    for item in sorted(base.rglob("*")):
        if item.is_file() and ".git" not in item.parts:
            print(item.relative_to(base))

def read_file(filename):
    path = get_file(filename)
    if not path.is_file():
        raise ValueError("El archivo no existe.")
    if path.stat().st_size > MAX_FILE_SIZE:
        raise ValueError("Archivo demasiado grande.")
    print(path.read_text(encoding="utf-8"))

def new_project(name):
    valid_name(name)
    path = PROJECTS / name
    if path.exists():
        raise ValueError("Ese proyecto ya existe.")
    path.mkdir(parents=True)
    print("PROYECTO CREADO:", path)

def create_file(filename, content):
    path = get_file(filename)
    if path.exists():
        raise ValueError("El archivo ya existe. Usa /edit para modificarlo.")
    path.parent.mkdir(parents=True, exist_ok=True)
    validate(path, content)
    approval = input("¿Crear este archivo? Escribe SI: ").strip()
    if approval != "SI":
        print("Creación cancelada.")
        return
    path.write_text(content, encoding="utf-8")
    print("ARCHIVO CREADO:", path)

def edit_file(filename, instruction):
    path = get_file(filename)
    if not path.is_file():
        raise ValueError("El archivo no existe.")
    if path.stat().st_size > MAX_FILE_SIZE:
        raise ValueError("Límite de 2500 bytes.")

    original = path.read_text(encoding="utf-8")
    system = (
        "Eres DANY AI, experto en programación. Modifica únicamente "
        "lo solicitado. Devuelve el archivo completo entre "
        "<<<DANY_CODE>>> y <<<END_DANY_CODE>>>. Sin explicaciones."
    )
    prompt = (
        "INSTRUCCIÓN:\n" + instruction +
        "\n\nARCHIVO ORIGINAL:\n" + original
    )

    print("\nDANY está analizando el archivo...")
    answer = ask_qwen(system, prompt)
    start = "<<<DANY_CODE>>>"
    end = "<<<END_DANY_CODE>>>"

    if start not in answer:
        raise ValueError("Qwen no devolvió el inicio del código.")

    proposed = answer.split(start, 1)[1]
    match = re.search(re.escape(end) + r">?", proposed)
    if not match:
        raise ValueError("Respuesta incompleta de Qwen.")

    proposed = proposed[:match.start()].strip()
    if not proposed:
        raise ValueError("La propuesta está vacía.")

    validate(path, proposed)
    diff = difflib.unified_diff(
        original.splitlines(), proposed.splitlines(),
        fromfile="ORIGINAL", tofile="PROPUESTA", lineterm=""
    )
    print("\n===== CAMBIOS PROPUESTOS =====")
    print("\n".join(diff) or "No hay cambios.")
    print("===== FIN DE LA PROPUESTA =====")

    proposal = OUTPUT / (path.name + ".propuesta")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    proposal.write_text(proposed, encoding="utf-8")
    print("Propuesta guardada:", proposal)

    if original == proposed:
        print("No hay cambios.")
        return

    if input("¿Aplicar cambios? Escribe SI: ").strip() != "SI":
        print("Cambios rechazados.")
        return

    backup = backup_file(path)
    fd, temporary = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(proposed)
        os.chmod(temporary, path.stat().st_mode)
        os.replace(temporary, path)
    except Exception:
        if os.path.exists(temporary):
            os.unlink(temporary)
        raise

    print("CAMBIOS APLICADOS.")
    print("Respaldo:", backup)

def test_file(filename):
    path = get_file(filename)
    if not path.is_file():
        raise ValueError("Archivo inexistente.")
    content = path.read_text(encoding="utf-8")
    validate(path, content)
    if path.suffix == ".py":
        print("Python: sintaxis correcta.")
    elif path.suffix == ".json":
        print("JSON: formato correcto.")
    elif path.suffix in (".js", ".mjs"):
        run(["node", "--check", str(path)])
        print("JavaScript: sintaxis correcta.")
    else:
        print("No hay validador configurado para", path.suffix)

def undo_file(filename):
    path = get_file(filename)
    if not path.is_file():
        raise ValueError("Archivo inexistente.")
    relative = path.relative_to(get_project()).as_posix()
    prefix = relative.replace("/", "__") + "."
    options = sorted(
        (BACKUPS / selected).glob(prefix + "*.bak"),
        key=lambda p: p.stat().st_mtime
    )
    if not options:
        raise ValueError("No hay respaldos para este archivo.")
    backup = options[-1]
    print("Respaldo elegido:", backup.name)
    if input("¿Restaurar? Escribe SI: ").strip() != "SI":
        print("Restauración cancelada.")
        return
    current_backup = backup_file(path)
    shutil.copy2(backup, path)
    print("ARCHIVO RESTAURADO.")
    print("Copia del archivo anterior:", current_backup)

def github_status():
    print(run(["gh", "auth", "status"]))
    base = get_project()
    try:
        print("\nRepositorio:", run(["git", "remote", "get-url", "origin"], base))
        print(run(["git", "status", "--short"], base))
    except Exception:
        print("Este proyecto todavía no tiene repositorio remoto.")

def github_repos():
    print(run(["gh", "repo", "list", "--limit", "20"]))

def safe_stage(base):
    ignore = base / ".gitignore"
    if not ignore.exists():
        ignore.write_text(GITIGNORE.strip() + "\n", encoding="utf-8")

    safe = []
    blocked = []
    for item in base.rglob("*"):
        if not item.is_file() or item.is_symlink():
            continue
        relative = item.relative_to(base)
        if ".git" in relative.parts:
            continue
        parts = relative.parts
        name = item.name.lower()
        forbidden = (
            name == ".env" or name.startswith(".env.") or
            name.endswith((".pem", ".key", ".p12", ".pfx")) or
            name in ("id_rsa", "id_ed25519", "credentials.json", "secrets.json") or
            any(x in ("node_modules", "__pycache__", ".venv", "venv") for x in parts)
        )
        if forbidden:
            blocked.append(str(relative))
        elif item.stat().st_size <= 20 * 1024 * 1024:
            safe.append("./" + str(relative))
        else:
            blocked.append(str(relative) + " (más de 20 MB)")

    if blocked:
        print("\nArchivos excluidos por seguridad:")
        for item in blocked:
            print("-", item)
    if not safe:
        raise ValueError("No hay archivos seguros para subir.")
    run(["git", "add", "--"] + safe, base)

def git_commit(base):
    try:
        run(["git", "rev-parse", "--is-inside-work-tree"], base)
    except Exception:
        run(["git", "init"], base)
        run(["git", "branch", "-M", "main"], base)

    safe_stage(base)
    result = subprocess.run(
        ["git", "diff", "--cached", "--quiet"], cwd=base
    )
    if result.returncode == 0:
        print("No hay cambios nuevos para confirmar.")
        return False

    message = "Actualización desde DANY AI"
    run(["git", "commit", "-m", message], base)
    print("Commit creado.")
    return True

def github_create(repo):
    base = get_project()
    if not repo:
        repo = selected
    if not re.fullmatch(r"[A-Za-z0-9_.-]+(/[A-Za-z0-9_.-]+)?", repo):
        raise ValueError("Nombre de repositorio no válido.")

    try:
        run(["git", "remote", "get-url", "origin"], base)
    except Exception:
        pass
    else:
        raise ValueError("Este proyecto ya tiene un remoto. Usa /github push.")

    print("\\nELIGE LA VISIBILIDAD DEL REPOSITORIO:")
    print("1. PUBLICO")
    print("2. PRIVADO")
    choice = input("Selecciona 1 o 2: ").strip()

    if choice == "1":
        visibility = "--public"
        label = "PUBLICO"
    elif choice == "2":
        visibility = "--private"
        label = "PRIVADO"
    else:
        print("Opción no válida. Operación cancelada.")
        return

    print("\\nRepositorio:", repo)
    print("Visibilidad:", label)

    if input("¿Crear y publicar? Escribe SI: ").strip() != "SI":
        print("Operación cancelada.")
        return

    git_commit(base)
    run([
        "gh", "repo", "create", repo,
        visibility, "--source", str(base),
        "--remote", "origin", "--push"
    ], base)
    print("REPOSITORIO", label, "CREADO Y PUBLICADO.")


def github_push():
    base = get_project()
    try:
        run(["git", "remote", "get-url", "origin"], base)
    except Exception:
        raise ValueError("Primero usa /github create NOMBRE.")

    print("Proyecto:", selected)
    if input("¿Preparar y subir cambios? Escribe SI: ").strip() != "SI":
        print("Publicación cancelada.")
        return

    git_commit(base)
    run(["git", "push", "-u", "origin", "HEAD"], base)
    print("PUBLICACIÓN COMPLETADA.")

def github_clone(repo):
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        raise ValueError("Usa el formato usuario/repositorio.")
    name = repo.split("/")[-1]
    valid_name(name)
    destination = PROJECTS / name
    if destination.exists():
        raise ValueError("Ya existe un proyecto con ese nombre.")
    run(["gh", "repo", "clone", repo, str(destination)])
    print("PROYECTO DESCARGADO:", destination)

def main():
    global selected
    PROJECTS.mkdir(parents=True, exist_ok=True)
    BACKUPS.mkdir(parents=True, exist_ok=True)
    OUTPUT.mkdir(parents=True, exist_ok=True)

    print("\n===== DANY AI ADVANCED DEVELOPER v3 =====")
    print("/projects")
    print("/newproject NOMBRE")
    print("/select NOMBRE")
    print("/files")
    print("/read ARCHIVO")
    print('/create ARCHIVO "CONTENIDO"')
    print('/edit ARCHIVO "INSTRUCCION"')
    print("/test ARCHIVO")
    print("/undo ARCHIVO")
    print("/github status")
    print("/github repos")
    print("/github create REPOSITORIO")
    print("/github push")
    print("/github clone USUARIO/REPOSITORIO")
    print("/exit")

    while True:
        try:
            line = input("\nDANY-DEV> ").strip()
            if not line:
                continue
            parts = shlex.split(line)
            action = parts[0]

            if action == "/exit":
                break
            elif action == "/projects" and len(parts) == 1:
                projects()
            elif action == "/newproject" and len(parts) == 2:
                new_project(parts[1])
            elif action == "/select" and len(parts) == 2:
                get_project(parts[1])
                selected = parts[1]
                print("Proyecto seleccionado:", selected)
            elif action == "/files" and len(parts) == 1:
                files()
            elif action == "/read" and len(parts) == 2:
                read_file(parts[1])
            elif action == "/create" and len(parts) == 3:
                create_file(parts[1], parts[2])
            elif action == "/edit" and len(parts) == 3:
                edit_file(parts[1], parts[2])
            elif action == "/test" and len(parts) == 2:
                test_file(parts[1])
            elif action == "/undo" and len(parts) == 2:
                undo_file(parts[1])
            elif action == "/github" and len(parts) >= 2:
                sub = parts[1]
                if sub == "status" and len(parts) == 2:
                    github_status()
                elif sub == "repos" and len(parts) == 2:
                    github_repos()
                elif sub == "create" and len(parts) <= 3:
                    github_create(parts[2] if len(parts) == 3 else None)
                elif sub == "push" and len(parts) == 2:
                    github_push()
                elif sub == "clone" and len(parts) == 3:
                    github_clone(parts[2])
                else:
                    print("Uso: /github status|repos|create|push|clone")
            else:
                print("Comando incorrecto. Revisa el menú.")
        except Exception as error:
            print("ERROR:", error)

if __name__ == "__main__":
    main()
