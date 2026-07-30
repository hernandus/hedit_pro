#!/bin/bash

# Obtener la ruta absoluta del directorio donde se encuentra este script
PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Función para detectar el emulador de terminal disponible (compatible con Wayland y X11)
launch_in_terminal() {
    local cmd="$1"
    if command -v ptyxis &> /dev/null; then
        ptyxis --title="Hedit Pro - Docking Test" -- bash -c "$cmd; exec bash"
    elif command -v konsole &> /dev/null; then
        konsole -e bash -c "$cmd; exec bash"
    elif command -v kitty &> /dev/null; then
        kitty --title="Hedit Pro - Docking Test" bash -c "$cmd; exec bash"
    elif command -v foot &> /dev/null; then
        foot -title="Hedit Pro - Docking Test" bash -c "$cmd; exec bash"
    elif command -v alacritty &> /dev/null; then
        alacritty -t "Hedit Pro - Docking Test" -e bash -c "$cmd; exec bash"
    elif command -v gnome-terminal &> /dev/null; then
        gnome-terminal --title="Hedit Pro - Docking Test" -- bash -c "$cmd; exec bash"
    elif command -v x-terminal-emulator &> /dev/null; then
        x-terminal-emulator -e "bash -c \"$cmd; exec bash\""
    elif command -v xterm &> /dev/null; then
        xterm -e "bash -c \"$cmd; exec bash\""
    else
        echo "No se encontró un emulador de terminal gráfico. Ejecutando en la terminal actual..."
        eval "$cmd"
    fi
}

ejecutar_test() {
    echo ""
    echo "========================================="
    echo "  Iniciando Docking Test (paneles vacíos)..."
    echo "========================================="

    local run_cmd="cd '$PROJECT_DIR' && source venv/bin/activate && python test_docking.py"

    launch_in_terminal "$run_cmd"

    echo "Test iniciado en una nueva ventana de terminal."
    echo ""
}

detener_test() {
    echo ""
    echo "========================================="
    echo "  Deteniendo Docking Test..."
    echo "========================================="

    PIDS=$(pgrep -f "python.*test_docking\.py" | grep -v "$$")

    if [ -n "$PIDS" ]; then
        echo "Finalizando proceso(s): $PIDS"
        kill -9 $PIDS 2>/dev/null
        echo "Test detenido con éxito."
    else
        echo "No se encontró ningún proceso de test_docking.py en ejecución."
    fi
    echo ""
}

# Menú principal
while true; do
    echo "========================================="
    echo "    HEDIT PRO - DOCKING SYSTEM TEST      "
    echo "========================================="
    echo " 1) Ejecutar Docking Test (paneles vacíos)"
    echo " 2) Detener Docking Test"
    echo " 3) Salir"
    echo "========================================="
    read -rp "Seleccione una opción [1-3]: " opcion

    case $opcion in
        1)
            ejecutar_test
            ;;
        2)
            detener_test
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
