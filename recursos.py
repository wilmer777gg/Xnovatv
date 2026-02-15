#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#██████╗ ███████╗████████╗██████╗  █████╗ ██╗     ███████╗
#██╔══██╗██╔════╝╚══██╔══╝██╔══██╗██╔══██╗██║     ██╔════╝
#██████╔╝███████╗   ██║   ██████╔╝███████║██║     ███████╗
#██╔══██╗╚════██║   ██║   ██╔══██╗██╔══██║██║     ╚════██║
#██║  ██║███████║   ██║   ██║  ██║██║  ██║███████╗███████║
#╚═╝  ╚═╝╚══════╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚══════╝

#🚀 ASTRO.IO v2.4.0 🚀
#💰 recursos.py - SISTEMA DE RECURSOS Y PRODUCCIÓN AUTOMÁTICA
#============================================================
#✅ PRODUCCIÓN AUTOMÁTICA - Se calcula cada vez que se consulta
#✅ RECURSOS INICIALES SINCRONIZADOS con login.py (200M, 100C, 0D)
#✅ BALANCE ENERGÉTICO - Consumo vs producción con penalización
#✅ ENERGÍA NEGATIVA - Reduce producción de minas proporcionalmente
#✅ TIEMPO REAL - Siempre lee/escribe JSON directamente
#============================================================

import os
import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from login import AuthSystem, requiere_login, RECURSOS_INICIALES
from database import load_json, save_json
from utils import abreviar_numero

logger = logging.getLogger(__name__)

# ================= CONSTANTES =================
DATA_DIR = "data"
RECURSOS_FILE = os.path.join(DATA_DIR, "recursos.json")
MINAS_FILE = os.path.join(DATA_DIR, "minas.json")
EDIFICIOS_USUARIO_FILE = os.path.join(DATA_DIR, "edificios_usuario.json")
DATA_FILE = os.path.join(DATA_DIR, "data.json")

# ================= FUNCIONES DE RECURSOS =================

def obtener_recursos_usuario(user_id: int) -> dict:
    """💰 Obtiene recursos del usuario desde recursos.json"""
    user_id_str = str(user_id)
    recursos_data = load_json(RECURSOS_FILE) or {}
    
    # Si no existe, crear con valores por defecto (SINCRONIZADO con login.py)
    if user_id_str not in recursos_data:
        recursos_data[user_id_str] = RECURSOS_INICIALES.copy()
        save_json(RECURSOS_FILE, recursos_data)
        logger.info(f"💰 Recursos iniciales ({RECURSOS_INICIALES['metal']}M, {RECURSOS_INICIALES['cristal']}C, {RECURSOS_INICIALES['deuterio']}D) asignados a {AuthSystem.obtener_username(user_id)}")
    
    return recursos_data.get(user_id_str, {
        "metal": 0,
        "cristal": 0,
        "deuterio": 0,
        "materia_oscura": 0,
        "nxt20": 0,
        "energia": 0
    })

def guardar_recursos_usuario(user_id: int, recursos: dict) -> bool:
    """💾 Guarda recursos del usuario en recursos.json"""
    user_id_str = str(user_id)
    recursos_data = load_json(RECURSOS_FILE) or {}
    recursos_data[user_id_str] = recursos
    return save_json(RECURSOS_FILE, recursos_data)

def obtener_nivel_mina(user_id: int, tipo: str) -> int:
    """⛏️ Obtiene nivel de una mina específica"""
    user_id_str = str(user_id)
    minas_data = load_json(MINAS_FILE) or {}
    minas_usuario = minas_data.get(user_id_str, {})
    
    nivel_data = minas_usuario.get(tipo, 0)
    if isinstance(nivel_data, dict):
        return nivel_data.get("nivel", 0)
    return int(nivel_data) if isinstance(nivel_data, (int, float)) else 0

def obtener_nivel_energia(user_id: int) -> int:
    """⚡ Obtiene nivel de la planta de energía"""
    user_id_str = str(user_id)
    edificios_data = load_json(EDIFICIOS_USUARIO_FILE) or {}
    edificios_usuario = edificios_data.get(user_id_str, {})
    
    nivel_data = edificios_usuario.get("energia", 0)
    if isinstance(nivel_data, dict):
        return nivel_data.get("nivel", 0)
    return int(nivel_data) if isinstance(nivel_data, (int, float)) else 0

def obtener_nivel_edificio(user_id: int, edificio: str) -> int:
    """🏢 Obtiene nivel de un edificio específico"""
    user_id_str = str(user_id)
    edificios_data = load_json(EDIFICIOS_USUARIO_FILE) or {}
    edificios_usuario = edificios_data.get(user_id_str, {})
    
    nivel_data = edificios_usuario.get(edificio, 0)
    if isinstance(nivel_data, dict):
        return nivel_data.get("nivel", 0)
    return int(nivel_data) if isinstance(nivel_data, (int, float)) else 0

def calcular_produccion_mina(nivel: int, base: int = 30, factor: float = 1.1) -> int:
    """📈 Calcula producción por hora de una mina"""
    if nivel <= 0:
        return 0
    return int(base * (factor ** nivel))

def calcular_produccion_energia(nivel: int, base: int = 50, factor: float = 1.1) -> int:
    """⚡ Calcula producción de energía por hora"""
    if nivel <= 0:
        return 0
    return int(base * (factor ** nivel))

def obtener_ultima_actualizacion(user_id: int) -> datetime:
    """⏰ Obtiene la última vez que se actualizaron los recursos"""
    user_id_str = str(user_id)
    data = load_json(DATA_FILE) or {}
    usuario = data.get(user_id_str, {})
    
    # Intentar obtener timestamp específico de recursos
    ultima_str = usuario.get("ultima_actualizacion_recursos")
    if ultima_str:
        try:
            return datetime.strptime(ultima_str, "%Y-%m-%d %H:%M:%S")
        except:
            pass
    
    # Fallback: usar ultima_actualizacion general
    ultima_general = usuario.get("ultima_actualizacion")
    if ultima_general:
        try:
            logger.warning(f"⚠️ Usando ultima_actualizacion general para {AuthSystem.obtener_username(user_id)}")
            return datetime.strptime(ultima_general, "%Y-%m-%d %H:%M:%S")
        except:
            pass
    
    # Si no hay registro, asumir hace 1 minuto
    logger.warning(f"⚠️ Sin timestamp para {AuthSystem.obtener_username(user_id)} - usando hace 1 min")
    return datetime.now() - timedelta(minutes=1)

def guardar_ultima_actualizacion(user_id: int) -> bool:
    """⏰ Guarda la hora de última actualización"""
    user_id_str = str(user_id)
    data = load_json(DATA_FILE) or {}
    
    if user_id_str not in data:
        data[user_id_str] = {}
    
    ahora = datetime.now()
    data[user_id_str]["ultima_actualizacion"] = ahora.strftime("%Y-%m-%d %H:%M:%S")
    data[user_id_str]["ultima_actualizacion_recursos"] = ahora.strftime("%Y-%m-%d %H:%M:%S")
    return save_json(DATA_FILE, data)

def obtener_produccion(user_id: int) -> dict:
    """📊 Obtiene producción por minuto y hora (SIEMPRE EN TIEMPO REAL)"""
    # Niveles actuales
    nivel_metal = obtener_nivel_mina(user_id, "metal")
    nivel_cristal = obtener_nivel_mina(user_id, "cristal")
    nivel_deuterio = obtener_nivel_mina(user_id, "deuterio")
    nivel_energia = obtener_nivel_energia(user_id)
    
    # Producción por hora
    metal_hora = calcular_produccion_mina(nivel_metal, 30)
    cristal_hora = calcular_produccion_mina(nivel_cristal, 20)
    deuterio_hora = calcular_produccion_mina(nivel_deuterio, 15)
    energia_hora = calcular_produccion_energia(nivel_energia, 50)
    
    # Producción por minuto
    metal_minuto = metal_hora // 60
    cristal_minuto = cristal_hora // 60
    deuterio_minuto = deuterio_hora // 60
    energia_minuto = energia_hora // 60
    
    return {
        "por_hora": {
            "metal": metal_hora,
            "cristal": cristal_hora,
            "deuterio": deuterio_hora,
            "energia": energia_hora
        },
        "por_minuto": {
            "metal": metal_minuto,
            "cristal": cristal_minuto,
            "deuterio": deuterio_minuto,
            "energia": energia_minuto
        },
        "niveles": {
            "metal": nivel_metal,
            "cristal": nivel_cristal,
            "deuterio": nivel_deuterio,
            "energia": nivel_energia
        }
    }

# ================= 🔥 NUEVA FUNCIÓN - CONSUMO DE ENERGÍA CORREGIDA =================

def obtener_consumo_energia(user_id: int) -> int:
    """⚡ Calcula el consumo total de energía (minas + edificios)"""
    consumo_total = 0
    
    # Consumo de minas
    consumo_total += obtener_nivel_mina(user_id, "metal") * 5      # 5 energía por nivel
    consumo_total += obtener_nivel_mina(user_id, "cristal") * 5    # 5 energía por nivel
    consumo_total += obtener_nivel_mina(user_id, "deuterio") * 10  # 10 energía por nivel
    
    # Consumo de edificios
    consumo_total += obtener_nivel_edificio(user_id, "laboratorio") * 20
    consumo_total += obtener_nivel_edificio(user_id, "hangar") * 30
    consumo_total += obtener_nivel_edificio(user_id, "terraformer") * 50
    
    # La planta de energía NO consume, solo produce
    # (Eliminada la línea redundante)
    
    return consumo_total

# ================= 🔥 FUNCIÓN PRINCIPAL - ACTUALIZAR RECURSOS CON ENERGÍA =================

def actualizar_recursos_tiempo(user_id: int) -> dict:
    """
    ⏰ ACTUALIZA LOS RECURSOS BASADO EN EL TIEMPO TRANSCURRIDO
    AHORA con ajuste por energía negativa
    """
    user_id_str = str(user_id)
    
    # 1. Obtener recursos actuales
    recursos = obtener_recursos_usuario(user_id)
    
    # 2. Obtener última actualización
    ultima = obtener_ultima_actualizacion(user_id)
    ahora = datetime.now()
    
    # 3. Calcular minutos transcurridos
    minutos_transcurridos = (ahora - ultima).total_seconds() / 60
    
    # 4. LIMITAR a máximo 60 minutos para evitar producciones enormes
    if minutos_transcurridos > 60:
        minutos_transcurridos = 60
    elif minutos_transcurridos < 0:
        minutos_transcurridos = 0
    
    # 5. Obtener producción base
    produccion = obtener_produccion(user_id)
    
    # 6. Calcular consumo y energía disponible
    consumo = obtener_consumo_energia(user_id)
    produccion_energia = produccion["por_minuto"]["energia"]
    energia_disponible = produccion_energia - consumo
    
    # 7. 🔥 CALCULAR FACTOR DE PRODUCCIÓN SEGÚN ENERGÍA
    if energia_disponible >= 0:
        # Energía suficiente - producción normal
        factor_metal = 1.0
        factor_cristal = 1.0
        factor_deuterio = 1.0
        estado_energia = "✅"
    else:
        # Energía negativa - penalizar producción
        # El factor es proporcional al déficit
        if consumo > 0:
            # Factor = 1 + (energia_negativa / consumo_total)
            # Ejemplo: energía = -50, consumo = 100 → factor = 0.5
            factor_base = 1 + (energia_disponible / consumo)
            factor_base = max(0.1, min(1.0, factor_base))  # Entre 10% y 100%
        else:
            factor_base = 0.1  # Si no hay consumo, mínimo
        
        # Mismo factor para todas las minas
        factor_metal = factor_base
        factor_cristal = factor_base
        factor_deuterio = factor_base
        estado_energia = "⚠️"
        
        logger.info(f"⚠️ Energía negativa para {AuthSystem.obtener_username(user_id)}: {energia_disponible:.0f}, factor: {factor_base:.2f}")
    
    # 8. CALCULAR producción real con factores
    metal_producido = int(produccion["por_minuto"]["metal"] * minutos_transcurridos * factor_metal)
    cristal_producido = int(produccion["por_minuto"]["cristal"] * minutos_transcurridos * factor_cristal)
    deuterio_producido = int(produccion["por_minuto"]["deuterio"] * minutos_transcurridos * factor_deuterio)
    
    # 9. SUMAR a los recursos existentes
    recursos["metal"] = recursos.get("metal", 0) + metal_producido
    recursos["cristal"] = recursos.get("cristal", 0) + cristal_producido
    recursos["deuterio"] = recursos.get("deuterio", 0) + deuterio_producido
    
    # 10. Actualizar energía (guardamos el balance actual)
    recursos["energia"] = energia_disponible  # Este valor puede ser negativo
    
    # 11. GUARDAR en recursos.json
    guardar_recursos_usuario(user_id, recursos)
    
    # 12. GUARDAR timestamp
    guardar_ultima_actualizacion(user_id)
    
    # 13. LOG con información de energía
    if minutos_transcurridos > 0.1:
        logger.info(
            f"⏰ {AuthSystem.obtener_username(user_id)}: "
            f"+{metal_producido}M +{cristal_producido}C +{deuterio_producido}D "
            f"en {minutos_transcurridos:.1f}min | "
            f"Energía: {estado_energia} {energia_disponible:.0f}/h "
            f"(prod:{produccion_energia} - cons:{consumo})"
        )
    
    return {
        "recursos": recursos,
        "produccion": produccion,
        "producido": {
            "metal": metal_producido,
            "cristal": cristal_producido,
            "deuterio": deuterio_producido
        },
        "minutos": minutos_transcurridos,
        "consumo": consumo,
        "produccion_energia": produccion_energia,
        "energia_disponible": energia_disponible,
        "estado_energia": estado_energia,
        "factor_produccion": {
            "metal": factor_metal,
            "cristal": factor_cristal,
            "deuterio": factor_deuterio
        }
    }

# ================= HANDLERS =================

@requiere_login
async def mostrar_recursos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """💰 Muestra los recursos del usuario (SIEMPRE ACTUALIZADO)"""
    user = update.effective_user
    user_id = user.id
    username_tag = AuthSystem.obtener_username(user_id)
    
    # ✅ ACTUALIZAR RECURSOS AUTOMÁTICAMENTE
    resultado = actualizar_recursos_tiempo(user_id)
    recursos = resultado["recursos"]
    produccion = resultado["produccion"]
    minutos = resultado["minutos"]
    
    # Mensaje de alerta si energía negativa
    alerta_energia = ""
    if resultado["energia_disponible"] < 0:
        factor_pct = int(resultado["factor_produccion"]["metal"] * 100)
        alerta_energia = (
            f"\n⚠️ <b>¡ALERTA ENERGÉTICA!</b>\n"
            f"   Energía negativa: {abreviar_numero(resultado['energia_disponible'])}/h\n"
            f"   Producción reducida al {factor_pct}%\n"
        )
    
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"💰 <b>RECURSOS DEL IMPERIO</b> - {username_tag}\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"📊 <b>RECURSOS ACTUALES:</b>\n"
        f"🔩 Metal: {abreviar_numero(recursos.get('metal', 0))}\n"
        f"💎 Cristal: {abreviar_numero(recursos.get('cristal', 0))}\n"
        f"🧪 Deuterio: {abreviar_numero(recursos.get('deuterio', 0))}\n"
        f"⚡ Energía: {abreviar_numero(recursos.get('energia', 0))}/h {resultado['estado_energia']}\n"
        f"{alerta_energia}"
        f"\n"
        f"⛏️ <b>PRODUCCIÓN POR HORA:</b>\n"
        f"🔩 Mina Metal Nv.{produccion['niveles']['metal']}: +{abreviar_numero(produccion['por_hora']['metal'])}/h\n"
        f"💎 Mina Cristal Nv.{produccion['niveles']['cristal']}: +{abreviar_numero(produccion['por_hora']['cristal'])}/h\n"
        f"🧪 Sint. Deuterio Nv.{produccion['niveles']['deuterio']}: +{abreviar_numero(produccion['por_hora']['deuterio'])}/h\n"
        f"⚡ Planta Energía Nv.{produccion['niveles']['energia']}: +{abreviar_numero(produccion['por_hora']['energia'])}/h\n\n"
        f"⚡ <b>BALANCE ENERGÉTICO:</b>\n"
        f"   Producción: +{abreviar_numero(resultado['produccion_energia']*60)}/h\n"
        f"   Consumo: -{abreviar_numero(resultado['consumo'])}/h\n"
        f"   Balance: {resultado['estado_energia']} {abreviar_numero(resultado['energia_disponible'])}/h\n\n"
        f"⏱️ Última actualización: hace {minutos:.1f} min\n"
        f"🔄 Producción acumulada: +{abreviar_numero(resultado['producido']['metal'])}M +{abreviar_numero(resultado['producido']['cristal'])}C +{abreviar_numero(resultado['producido']['deuterio'])}D\n\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("🔄 ACTUALIZAR", callback_data="menu_recursos"),
            InlineKeyboardButton("🏠 MENÚ", callback_data="menu_principal")
        ]
    ]
    
    if update.message:
        await update.message.reply_text(
            text=mensaje,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )

@requiere_login
async def menu_recursos_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """💰 Menú de recursos (callback) - SIEMPRE ACTUALIZA"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    username_tag = AuthSystem.obtener_username(user_id)
    
    # ✅ ACTUALIZAR RECURSOS AUTOMÁTICAMENTE
    resultado = actualizar_recursos_tiempo(user_id)
    recursos = resultado["recursos"]
    produccion = resultado["produccion"]
    
    # Mensaje de alerta si energía negativa
    alerta_energia = ""
    if resultado["energia_disponible"] < 0:
        factor_pct = int(resultado["factor_produccion"]["metal"] * 100)
        alerta_energia = f"\n⚠️ Producción al {factor_pct}% por déficit energético"
    
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"💰 <b>PANEL DE RECURSOS</b> - {username_tag}\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"🔩 Metal: {abreviar_numero(recursos.get('metal', 0))}\n"
        f"💎 Cristal: {abreviar_numero(recursos.get('cristal', 0))}\n"
        f"🧪 Deuterio: {abreviar_numero(recursos.get('deuterio', 0))}\n"
        f"⚡ Energía: {abreviar_numero(recursos.get('energia', 0))}/h {resultado['estado_energia']}\n"
        f"{alerta_energia}\n\n"
        f"⛏️ Producción/hora:\n"
        f"🔩 +{abreviar_numero(produccion['por_hora']['metal'])} | "
        f"💎 +{abreviar_numero(produccion['por_hora']['cristal'])} | "
        f"🧪 +{abreviar_numero(produccion['por_hora']['deuterio'])}\n\n"
        f"Selecciona una opción:\n\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("📊 PRODUCCIÓN", callback_data="produccion_detalle"),
            InlineKeyboardButton("⚡ ENERGÍA", callback_data="energia_detalle")
        ],
        [
            InlineKeyboardButton("🏗️ MEJORAR MINAS", callback_data="menu_edificios"),
            InlineKeyboardButton("🔄 ACTUALIZAR", callback_data="menu_recursos")
        ],
        [InlineKeyboardButton("◀️ VOLVER", callback_data="menu_principal")]
    ]
    
    await query.edit_message_text(
        text=mensaje,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

# ================= EXPORTAR =================

__all__ = [
    'mostrar_recursos',
    'menu_recursos_handler',
    'obtener_recursos_usuario',
    'guardar_recursos_usuario',
    'actualizar_recursos_tiempo',
    'obtener_produccion',
    'obtener_consumo_energia'
]

