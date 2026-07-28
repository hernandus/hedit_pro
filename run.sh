#!/bin/bash

# Obtener la ruta absoluta del directorio donde se encuentra este script
PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PID_FILE="$PROJECT_DIR/.app.pid"

# Función para detectar el emulador de terminal disponible (compatible con Wayland y X11)
launch_in_terminal() {
    local cmd="$1"
    if command -v ptyxis &> /dev/null; then
        ptyxis --title="Hedit Pro - Ejecución" -- bash -c "$cmd; exec bash"
    elif command -v konsole &> /dev/null; then
        konsole -e bash -c "$cmd; exec bash"
    elif command -v kitty &> /dev/null; then
        kitty --title="Hedit Pro - Ejecución" bash -c "$cmd; exec bash"
    elif command -v foot &> /dev/null; then
        foot -title="Hedit Pro - Ejecución" bash -c "$cmd; exec bash"
    elif command -v alacritty &> /dev/null; then
        alacritty -t "Hedit Pro - Ejecución" -e bash -c "$cmd; exec bash"
    elif command -v gnome-terminal &> /dev/null; then
        gnome-terminal --title="Hedit Pro - Ejecución" -- bash -c "$cmd; exec bash"
    elif command -v x-terminal-emulator &> /dev/null; then
        x-terminal-emulator -e "bash -c \"$cmd; exec bash\""
    elif command -v xterm &> /dev/null; then
        xterm -e "bash -c \"$cmd; exec bash\""
    else
        echo "No se encontró un emulador de terminal gráfico. Ejecutando en la terminal actual..."
        eval "$cmd"
    fi
}

ejecutar_proyecto() {
    echo ""
    echo "========================================="
    echo "  Iniciando Hedit Pro (NLE)..."
    echo "========================================="
    
    # Comando a ejecutar en la nueva terminal
    local run_cmd="cd '$PROJECT_DIR' && source venv/bin/activate && python main.py"
    
    launch_in_terminal "$run_cmd"
    
    echo "Proyecto iniciado en una nueva ventana de terminal."
    echo ""
}

detener_proyecto() {
    echo ""
    echo "========================================="
    echo "  Deteniendo Hedit Pro..."
    echo "========================================="
    
    # Buscar procesos de python ejecutando main.py, ffmpeg o melt en background
    PIDS=$(pgrep -f "python.*main\.py" | grep -v "$$")
    FFMPEG_PIDS=$(pgrep -f "ffmpeg.*hedit")
    MELT_PIDS=$(pgrep -f "melt.*avformat")

    if [ -n "$PIDS" ] || [ -n "$FFMPEG_PIDS" ] || [ -n "$MELT_PIDS" ]; then
        if [ -n "$PIDS" ]; then
            echo "Finalizando proceso(s) principal(es): $PIDS"
            kill -9 $PIDS 2>/dev/null
        fi
        if [ -n "$FFMPEG_PIDS" ]; then
            echo "Finalizando proceso(s) de ffmpeg: $FFMPEG_PIDS"
            kill -9 $FFMPEG_PIDS 2>/dev/null
        fi
        if [ -n "$MELT_PIDS" ]; then
            echo "Finalizando proceso(s) de renderizado melt: $MELT_PIDS"
            kill -9 $MELT_PIDS 2>/dev/null
        fi
        echo "El proyecto ha sido detenido por completo con éxito."
    else
        echo "No se encontró ningún proceso de Hedit Pro en ejecución."
    fi
    echo ""
}

# Menú principal
while true; do
    echo "========================================="
    echo "         HEDIT PRO - MENÚ PRINCIPAL      "
    echo "========================================="
    echo " 1) Ejecutar Hedit Pro (abrir app)"
    echo " 2) Detener Hedit Pro y renderers"
    echo " 3) Salir"
    echo "========================================="
    read -rp "Seleccione una opción [1-3]: " opcion

    case $opcion in
        1)
            ejecutar_proyecto
            ;;
        2)
            detener_proyecto
            ;;
        3)
            echo "Saliendo..."
            exit 0
            ;;
        *)
            echo "Opción inválida. Intente de nuevo."
            echo ""
            ;;
    esac
done
