
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#██████╗ ███████╗████████╗██████╗  █████╗ ██╗     ███████╗
#██╔══██╗██╔════╝╚══██╔══╝██╔══██╗██╔══██╗██║     ██╔════╝
#██████╔╝███████╗   ██║   ██████╔╝███████║██║     ███████╗
#██╔══██╗╚════██║   ██║   ██╔══██╗██╔══██║██║     ╚════██║
#██║  ██║███████║   ██║   ██║  ██║██║  ██║███████╗███████║
#╚═╝  ╚═╝╚══════╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚══════╝

#🚀 ASTRALS.IO 🚀
# Versión v2.3.7 - utils.py
# Desarrollado por @Neith07 y @Holows

"""
utils.py - UTILIDADES GENERALES
================================
✅ Formateo de números (abreviar_numero)
✅ Formateo de tiempo (formatear_tiempo)
✅ Formateo de tiempo corto (formatear_tiempo_corto) 👈 NUEVO
✅ Validaciones
✅ Logging
================================
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Union, Dict, List, Optional, Any

logger = logging.getLogger(__name__)

# ================= CONSTANTES =================
ADMIN_PRINCIPAL = 7470037078

# ================= FORMATO DE NÚMEROS =================

def abreviar_numero(num: Union[int, float]) -> str:
    """
    Convierte números grandes en formato abreviado:
    1000 -> 1K
    1500000 -> 1.5M
    2500000000 -> 2.5B
    """
    try:
        num = float(num)
        
        if num == 0:
            return "0"
        
        abs_num = abs(num)
        sign = "-" if num < 0 else ""
        
        if abs_num >= 1_000_000_000:
            return f"{sign}{abs_num/1_000_000_000:.1f}B"
        elif abs_num >= 1_000_000:
            return f"{sign}{abs_num/1_000_000:.1f}M"
        elif abs_num >= 1_000:
            return f"{sign}{abs_num/1_000:.1f}K"
        elif abs_num >= 1:
            if abs_num == int(abs_num):
                return f"{sign}{int(abs_num)}"
            else:
                return f"{sign}{abs_num:.1f}"
        else:
            return f"{sign}{abs_num:.2f}"
    except Exception as e:
        logger.error(f"Error en abreviar_numero({num}): {e}")
        return str(num)

def formatear_numero(num: Union[int, float], decimales: int = 0) -> str:
    """Formatea un número con separadores de miles"""
    try:
        num = float(num)
        if decimales > 0:
            formatted = f"{num:,.{decimales}f}"
        else:
            formatted = f"{int(num):,}"
        return formatted.replace(",", ".")
    except Exception as e:
        logger.error(f"Error en formatear_numero({num}): {e}")
        return str(num)

# ================= FORMATO DE TIEMPO =================

def formatear_tiempo(segundos: int) -> str:
    """
    Formatea segundos a formato legible:
    3661 -> "1h 1m 1s"
    """
    if segundos <= 0:
        return "0s"
    
    horas = segundos // 3600
    minutos = (segundos % 3600) // 60
    segs = segundos % 60
    
    partes = []
    
    if horas > 0:
        partes.append(f"{horas}h")
    if minutos > 0:
        partes.append(f"{minutos}m")
    if segs > 0 or not partes:
        partes.append(f"{segs}s")
    
    return " ".join(partes)

def formatear_tiempo_largo(segundos: int) -> str:
    """Formatea tiempo en formato largo"""
    if segundos <= 0:
        return "0 segundos"
    
    dias = segundos // 86400
    horas = (segundos % 86400) // 3600
    minutos = (segundos % 3600) // 60
    segs = segundos % 60
    
    partes = []
    
    if dias > 0:
        partes.append(f"{dias} día{'s' if dias > 1 else ''}")
    if horas > 0:
        partes.append(f"{horas} hora{'s' if horas > 1 else ''}")
    if minutos > 0:
        partes.append(f"{minutos} minuto{'s' if minutos > 1 else ''}")
    if segs > 0 or not partes:
        partes.append(f"{segs} segundo{'s' if segs > 1 else ''}")
    
    return ", ".join(partes)

# ================= 🔥 FUNCIÓN AGREGADA - formatear_tiempo_corto 🔥 =================

def formatear_tiempo_corto(segundos: int) -> str:
    """
    🔥 NUEVA FUNCIÓN - Alias de formatear_tiempo()
    Formatea tiempo en formato corto (ej: 1h 23m 45s)
    Mantiene compatibilidad con código existente
    """
    return formatear_tiempo(segundos)

# ================= VALIDACIONES =================

def es_id_valido(user_id: Any) -> bool:
    """Verifica si un ID de usuario es válido"""
    try:
        if user_id is None:
            return False
        id_str = str(user_id).strip()
        if not id_str.isdigit():
            return False
        id_int = int(id_str)
        return 1 <= id_int <= 9999999999
    except Exception:
        return False

def es_admin_principal(user_id: int) -> bool:
    """Verifica si el usuario es el administrador principal"""
    return user_id == ADMIN_PRINCIPAL

def validar_nombre_usuario(nombre: str) -> tuple:
    """Valida un nombre de usuario"""
    if not nombre or not nombre.strip():
        return False, "El nombre no puede estar vacío"
    
    nombre_limpio = nombre.strip()
    
    if len(nombre_limpio) < 2:
        return False, "El nombre debe tener al menos 2 caracteres"
    
    if len(nombre_limpio) > 32:
        return False, "El nombre no puede tener más de 32 caracteres"
    
    import re
    if not re.match(r'^[a-zA-Z0-9áéíóúÁÉÍÓÚñÑ\s\-_]+$', nombre_limpio):
        return False, "Solo se permiten letras, números, espacios, guiones y guiones bajos"
    
    return True, nombre_limpio

# ================= LOGGING =================

def registrar_evento(tipo: str, usuario_id: int, detalles: str = ""):
    """Registra un evento en el sistema de logs"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    mensaje = f"[{timestamp}] [{tipo.upper()}] User:{usuario_id} - {detalles}"
    
    print(mensaje)
    
    try:
        os.makedirs("log", exist_ok=True)
        with open("log/eventos.log", "a", encoding="utf-8") as f:
            f.write(mensaje + "\n")
    except Exception as e:
        print(f"Error escribiendo log: {e}")

# ================= EXPORTAR =================

__all__ = [
    'abreviar_numero',
    'formatear_numero',
    'formatear_tiempo',
    'formatear_tiempo_largo',
    'formatear_tiempo_corto',  # 👈 AGREGADO
    'es_id_valido',
    'es_admin_principal',
    'validar_nombre_usuario',
    'registrar_evento'
]