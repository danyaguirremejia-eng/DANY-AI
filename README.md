# DANY AI

Asistente local para Android mediante Termux.

## Componentes

- DANY AI: asistente conversacional en español.
- DANY DEV: Developer Engine v3.
- DANY COMMAND CENTER.
- Servidor local mediante llama.cpp.
- Memoria selectiva: solo guarda recuerdos cuando el usuario lo solicita.

## Instalación

En Termux:

    pkg update -y
    pkg install git curl -y
    git clone https://github.com/danyaguirremejia-eng/DANY-AI.git
    cd DANY-AI
    bash install.sh

Después abre una nueva sesión de Termux y escribe:

    Dany

## Requisitos

- Android con Termux y arquitectura ARM64 compatible.
- Conexión a Internet para instalar los componentes.
- Al menos 1.2 GB de espacio libre para descargar el modelo.

## Privacidad

Los modelos, recuerdos personales, proyectos y credenciales
se excluyen del repositorio público.
