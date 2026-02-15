#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#██████╗ ███████╗████████╗██████╗  █████╗ ██╗     ███████╗
#██╔══██╗██╔════╝╚══██╔══╝██╔══██╗██╔══██╗██║     ██╔════╝
#██████╔╝███████╗   ██║   ██████╔╝███████║██║     ███████╗
#██╔══██╗╚════██║   ██║   ██╔══██╗██╔══██║██║     ╚════██║
#██║  ██║███████║   ██║   ██║  ██║██║  ██║███████╗███████║
#╚═╝  ╚═╝╚══════╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚══════╝

#🚀 ASTRO.IO v2.4.0 🚀
#🏆 puntuacion.py - SISTEMA DE PUNTUACIÓN Y RANKING
#====================================================
#✅ MISMO ESTILO que menú principal
#✅ Separadores con 🌀
#✅ Formato consistente en todos los mensajes
#====================================================

import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from login import AuthSystem, requiere_login
from database import load_json, save_json
from utils import abreviar_numero

logger = logging.getLogger(__name__)

# ================= CONSTANTES =================
DATA_DIR = "data"

# Archivos de juego
MINAS_FILE = os.path.join(DATA_DIR, "minas.json")
EDIFICIOS_USUARIO_FILE = os.path.join(DATA_DIR, "edificios_usuario.json")
FLOTA_USUARIO_FILE = os.path.join(DATA_DIR, "flota_usuario.json")
DEFENSA_USUARIO_FILE = os.path.join(DATA_DIR, "defensa_usuario.json")
INVESTIGACIONES_USUARIO_FILE = os.path.join(DATA_DIR, "investigaciones.json")
RECURSOS_FILE = os.path.join(DATA_DIR, "recursos.json")

# Archivos de alianza
ALIANZA_MIEMBROS_FILE = os.path.join(DATA_DIR, "alianza_miembros.json")
ALIANZA_DATOS_FILE = os.path.join(DATA_DIR, "alianza_datos.json")

# ================= PESOS DE PUNTUACIÓN (AJUSTADOS) =================

PESOS = {
    # ========== EDIFICIOS (sin minas) ==========
    "edificios": {
        "energia": 15,        # ⚡ Planta de Energía
        "laboratorio": 30,    # 🔬 Laboratorio
        "hangar": 45,         # 🚀 Hangar
        "terraformer": 120    # 🌍 Terraformer
    },
    
    # ========== INVESTIGACIONES ==========
    "investigaciones": {
        "base": 60            # Cada nivel de investigación
    },
    
    # ========== FLOTA ==========
    "flota": {
        "cazador_ligero": 30,
        "cazador_pesado": 60,
        "crucero": 120,
        "nave_batalla": 240,
        "acorazado": 360,
        "destructor": 480,
        "estrella_muerte": 3000,
        "nave_carga_pequena": 18,
        "nave_carga_grande": 36,
        "reciclador": 48,
        "sonda_espionaje": 6,
        "satelite_solar": 12
    },
    
    # ========== DEFENSA ==========
    "defensa": {
        "lanza_misiles": 12,
        "laser_ligero": 15,
        "laser_pesado": 30,
        "canion_ionico": 48,
        "canion_gauss": 90,
        "canion_plasma": 180,
        "escudo_pequeno": 60,
        "escudo_grande": 240,
        "misil_interceptor": 18,
        "misil_interplanetario": 300
    },
    
    # ========== RECURSOS (BONUS) ==========
    "recursos": {
        "metal": 0.0005,      # 5000 metal = 2.5 puntos
        "cristal": 0.0008,    # 5000 cristal = 4 puntos
        "deuterio": 0.001,    # 3000 deuterio = 3 puntos
        "materia_oscura": 5   # 1 MO = 5 puntos
    }
}

# ================= FUNCIONES DE CÁLCULO =================

def obtener_nivel_edificio(user_id: int, edificio: str) -> int:
    """📊 Obtiene nivel de edificio de edificios_usuario.json"""
    user_id_str = str(user_id)
    data = load_json(EDIFICIOS_USUARIO_FILE) or {}
    usuario = data.get(user_id_str, {})
    
    nivel_data = usuario.get(edificio, 0)
    if isinstance(nivel_data, dict):
        return nivel_data.get("nivel", 0)
    return int(nivel_data) if isinstance(nivel_data, (int, float)) else 0

def obtener_cantidad_flota(user_id: int, nave: str) -> int:
    """🚀 Obtiene cantidad de naves de flota_usuario.json"""
    user_id_str = str(user_id)
    data = load_json(FLOTA_USUARIO_FILE) or {}
    usuario = data.get(user_id_str, {})
    return usuario.get(nave, 0)

def obtener_cantidad_defensa(user_id: int, defensa: str) -> int:
    """🛡️ Obtiene cantidad de defensas de defensa_usuario.json"""
    user_id_str = str(user_id)
    data = load_json(DEFENSA_USUARIO_FILE) or {}
    usuario = data.get(user_id_str, {})
    return usuario.get(defensa, 0)

def obtener_nivel_investigacion(user_id: int) -> int:
    """🔬 Obtiene nivel total de investigaciones"""
    user_id_str = str(user_id)
    data = load_json(INVESTIGACIONES_USUARIO_FILE) or {}
    usuario = data.get(user_id_str, {})
    
    total = 0
    for nivel in usuario.values():
        if isinstance(nivel, dict):
            total += nivel.get("nivel", 0)
        elif isinstance(nivel, (int, float)):
            total += int(nivel)
    return total

def obtener_recursos(user_id: int) -> dict:
    """💰 Obtiene recursos del usuario"""
    user_id_str = str(user_id)
    data = load_json(RECURSOS_FILE) or {}
    return data.get(user_id_str, {
        "metal": 0,
        "cristal": 0,
        "deuterio": 0,
        "materia_oscura": 0
    })

def obtener_alianza_usuario(user_id: int) -> str:
    """🌍 Obtiene el nombre de la alianza del usuario"""
    user_id_str = str(user_id)
    
    # Buscar en miembros
    miembros = load_json(ALIANZA_MIEMBROS_FILE) or {}
    for alianza_id, miembros_alianza in miembros.items():
        if user_id_str in miembros_alianza:
            # Obtener nombre de la alianza
            datos = load_json(ALIANZA_DATOS_FILE) or {}
            alianza = datos.get(alianza_id, {})
            return alianza.get("nombre", "Sin alianza")
    
    return "Sin alianza"

# ================= CALCULAR PUNTUACIÓN TOTAL =================

def calcular_puntuacion_total(user_id: int) -> dict:
    """
    🏆 CALCULA LA PUNTUACIÓN EN TIEMPO REAL
    Lee TODOS los JSON y aplica los pesos
    """
    puntos = {
        "total": 0,
        "edificios": 0,
        "investigacion": 0,
        "flota": 0,
        "defensa": 0,
        "recursos": 0,
        "desglose": {}
    }
    
    # ========== 1. EDIFICIOS (sin minas) ==========
    for edificio, peso in PESOS["edificios"].items():
        nivel = obtener_nivel_edificio(user_id, edificio)
        puntos_edificio = nivel * peso
        puntos["edificios"] += puntos_edificio
        puntos["desglose"][f"edf_{edificio}"] = puntos_edificio
    
    # ========== 2. INVESTIGACIONES ==========
    nivel_total_inv = obtener_nivel_investigacion(user_id)
    puntos["investigacion"] = nivel_total_inv * PESOS["investigaciones"]["base"]
    puntos["desglose"]["investigacion"] = puntos["investigacion"]
    
    # ========== 3. FLOTA ==========
    for nave, peso in PESOS["flota"].items():
        cantidad = obtener_cantidad_flota(user_id, nave)
        puntos_nave = cantidad * peso
        puntos["flota"] += puntos_nave
        if cantidad > 0:
            puntos["desglose"][f"flt_{nave}"] = puntos_nave
    
    # ========== 4. DEFENSA ==========
    for defensa, peso in PESOS["defensa"].items():
        cantidad = obtener_cantidad_defensa(user_id, defensa)
        puntos_defensa = cantidad * peso
        puntos["defensa"] += puntos_defensa
        if cantidad > 0:
            puntos["desglose"][f"def_{defensa}"] = puntos_defensa
    
    # ========== 5. RECURSOS (BONUS) ==========
    recursos = obtener_recursos(user_id)
    puntos["recursos"] += int(recursos.get("metal", 0) * PESOS["recursos"]["metal"])
    puntos["recursos"] += int(recursos.get("cristal", 0) * PESOS["recursos"]["cristal"])
    puntos["recursos"] += int(recursos.get("deuterio", 0) * PESOS["recursos"]["deuterio"])
    puntos["recursos"] += int(recursos.get("materia_oscura", 0) * PESOS["recursos"]["materia_oscura"])
    puntos["desglose"]["recursos"] = puntos["recursos"]
    
    # ========== 6. TOTAL ==========
    puntos["total"] = (puntos["edificios"] + 
                      puntos["investigacion"] + 
                      puntos["flota"] + 
                      puntos["defensa"] + 
                      puntos["recursos"])
    
    return puntos

# ================= OBTENER RANKING COMPLETO =================

def obtener_ranking() -> list:
    """
    🏆 Obtiene ranking de TODOS los usuarios autorizados
    """
    ranking = []
    
    # Obtener todos los usuarios autorizados
    from login import AuthSystem
    autorizados = load_json(os.path.join(DATA_DIR, "authorized_users.json")) or []
    
    for user_id in autorizados:
        try:
            # Calcular puntuación
            puntos = calcular_puntuacion_total(user_id)
            
            # Obtener username
            username = AuthSystem.obtener_username(user_id)
            if username.startswith('@'):
                username = username[1:]  # Quitar @ para la tabla
            
            # Obtener alianza
            alianza = obtener_alianza_usuario(user_id)
            
            ranking.append({
                "user_id": user_id,
                "nombre": username,
                "usuario": username,
                "alianza": alianza[:15],  # Limitar a 15 caracteres
                "puntos": puntos["total"]
            })
        except Exception as e:
            logger.error(f"Error calculando ranking para {user_id}: {e}")
            continue
    
    # Ordenar por puntos (mayor a menor)
    ranking.sort(key=lambda x: x["puntos"], reverse=True)
    
    return ranking

# ================= MENÚ PRINCIPAL DE PUNTUACIÓN =================

@requiere_login
async def menu_puntuacion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🏠 Menú principal de puntuación"""
    query = update.callback_query
    if not query:
        logger.error("❌ menu_puntuacion sin callback_query")
        return
    
    await query.answer()
    user_id = query.from_user.id
    username_tag = AuthSystem.obtener_username(user_id)
    
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"🏆 <b>SISTEMA DE PUNTUACIÓN</b> - {username_tag}\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"Selecciona una opción:\n\n"
        f"📊 <b>MIS ESTADÍSTICAS</b> - Ver tu puntuación detallada\n"
        f"🏆 <b>RANKING GLOBAL</b> - Compara tu progreso con otros comandantes\n\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("📊 MIS ESTADÍSTICAS", callback_data="puntuacion_mis_estadisticas"),
            InlineKeyboardButton("🏆 RANKING GLOBAL", callback_data="ranking_1")
        ],
        [InlineKeyboardButton("◀️ VOLVER", callback_data="menu_principal")]
    ]
    
    await query.edit_message_text(
        text=mensaje,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

# ================= MIS ESTADÍSTICAS =================

@requiere_login
async def mis_estadisticas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📊 Muestra estadísticas detalladas del usuario"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    username_tag = AuthSystem.obtener_username(user_id)
    
    # CALCULAR EN TIEMPO REAL
    puntos = calcular_puntuacion_total(user_id)
    alianza = obtener_alianza_usuario(user_id)
    
    # Obtener posición en el ranking
    ranking = obtener_ranking()
    posicion = 1
    for i, jugador in enumerate(ranking, 1):
        if jugador["user_id"] == user_id:
            posicion = i
            break
    
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"📊 <b>ESTADÍSTICAS DE {username_tag}</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"🌍 Alianza: {alianza}\n"
        f"🏆 Posición: #{posicion} de {len(ranking)}\n"
        f"⭐ Puntuación total: <b>{abreviar_numero(puntos['total'])}</b>\n\n"
        f"📋 <b>DESGLOSE POR CATEGORÍAS:</b>\n"
        f"🏢 Edificios: {abreviar_numero(puntos['edificios'])}\n"
        f"🔬 Investigación: {abreviar_numero(puntos['investigacion'])}\n"
        f"🚀 Flota: {abreviar_numero(puntos['flota'])}\n"
        f"🛡️ Defensa: {abreviar_numero(puntos['defensa'])}\n"
        f"💰 Bonus recursos: +{abreviar_numero(puntos['recursos'])}\n\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("🔄 ACTUALIZAR", callback_data="puntuacion_mis_estadisticas"),
            InlineKeyboardButton("🏆 RANKING", callback_data="ranking_1")
        ],
        [InlineKeyboardButton("◀️ VOLVER", callback_data="menu_puntuacion")]
    ]
    
    await query.edit_message_text(
        text=mensaje,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

# ================= RANKING GLOBAL CON PAGINACIÓN =================

@requiere_login
async def mostrar_ranking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🏆 Muestra tabla de ranking con paginación"""
    query = update.callback_query
    await query.answer()
    
    # Obtener página
    data = query.data
    if data.startswith("ranking_"):
        try:
            pagina = int(data.split("_")[1])
        except:
            pagina = 1
    else:
        pagina = 1
    
    # CALCULAR RANKING EN TIEMPO REAL
    ranking = obtener_ranking()
    
    # Configurar paginación (20 por página)
    ITEMS_POR_PAGINA = 20
    total_paginas = (len(ranking) + ITEMS_POR_PAGINA - 1) // ITEMS_POR_PAGINA
    pagina = max(1, min(pagina, total_paginas))
    
    inicio = (pagina - 1) * ITEMS_POR_PAGINA
    fin = inicio + ITEMS_POR_PAGINA
    jugadores_pagina = ranking[inicio:fin]
    
    # Construir mensaje
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"🏆 <b>RANKING GLOBAL DE COMANDANTES</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"Página {pagina}/{total_paginas if total_paginas > 0 else 1}\n\n"
    )
    
    if not jugadores_pagina:
        mensaje += "❌ No hay jugadores registrados.\n\n"
        mensaje += f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    else:
        # Cabecera de la tabla
        mensaje += f"<pre>"
        mensaje += f"{'':<4} {'Jugador':<20} {'Alianza':<15} {'Puntos':>10}\n"
        mensaje += f"{'─'*4} {'─'*20} {'─'*15} {'─'*10}\n"
        
        # Datos de los jugadores
        for i, jugador in enumerate(jugadores_pagina, inicio + 1):
            # Medallitas para top 3
            if i == 1:
                puesto = "🥇"
            elif i == 2:
                puesto = "🥈"
            elif i == 3:
                puesto = "🥉"
            else:
                puesto = f"{i:<4}"
            
            nombre = jugador['nombre'][:18] + ".." if len(jugador['nombre']) > 18 else jugador['nombre']
            alianza = jugador['alianza'][:13] + ".." if len(jugador['alianza']) > 13 else jugador['alianza']
            puntos = f"{jugador['puntos']:,}".replace(",", ".")
            
            mensaje += f"{puesto:<4} @{nombre:<18} {alianza:<15} {puntos:>10}\n"
        
        mensaje += f"</pre>\n"
        mensaje += f"\n📊 Total comandantes: {len(ranking)}\n\n"
        mensaje += f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    
    # Botones de navegación
    keyboard = []
    
    # Fila de navegación de páginas
    nav_fila = []
    if pagina > 1:
        nav_fila.append(InlineKeyboardButton("◀️ Anterior", callback_data=f"ranking_{pagina-1}"))
    if pagina < total_paginas:
        nav_fila.append(InlineKeyboardButton("Siguiente ▶️", callback_data=f"ranking_{pagina+1}"))
    
    if nav_fila:
        keyboard.append(nav_fila)
    
    # Botones de acción
    keyboard.append([
        InlineKeyboardButton("📊 MIS ESTADÍSTICAS", callback_data="puntuacion_mis_estadisticas"),
        InlineKeyboardButton("🔄 ACTUALIZAR", callback_data=f"ranking_{pagina}")
    ])
    keyboard.append([InlineKeyboardButton("◀️ VOLVER", callback_data="menu_puntuacion")])
    
    await query.edit_message_text(
        text=mensaje,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

# ================= CALLBACK HANDLER PRINCIPAL =================

async def puntuacion_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🎯 Handler para todos los callbacks de puntuación"""
    query = update.callback_query
    data = query.data
    
    if data == "menu_puntuacion":
        await menu_puntuacion(update, context)
    
    elif data == "puntuacion_mis_estadisticas":
        await mis_estadisticas(update, context)
    
    elif data.startswith("ranking_"):
        await mostrar_ranking(update, context)
    
    return

# ================= EXPORTAR =================

__all__ = [
    'menu_puntuacion',
    'puntuacion_callback_handler',
    'calcular_puntuacion_total',
    'obtener_ranking'
]
