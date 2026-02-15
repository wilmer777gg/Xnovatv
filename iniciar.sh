#!/data/data/com.termux/files/usr/bin/bash

echo "🚀 Iniciando AstroIO..."
echo "📱 Presiona Ctrl+C para detener"
echo ""

# Verificar que estamos en la carpeta correcta
cd /storage/emulated/0/Termux

# Loop infinito con reintentos
while true; do
    echo "⏳ $(date '+%Y-%m-%d %H:%M:%S') - Iniciando bot..."
    
    # Ejecutar el bot
    python AstroIO.py
    
    # Si llega aquí, el bot se detuvo
    echo "⚠️ $(date '+%Y-%m-%d %H:%M:%S') - Bot detenido. Reintentando en 10 segundos..."
    echo ""
    sleep 10
done
