#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#█████╗ ███████╗████████╗██████╗  █████╗ ██╗     ███████╗
#██╔══██╗██╔════╝╚══██╔══╝██╔══██╗██╔══██╗██║     ██╔════╝
#███████║███████╗   ██║   ██████╔╝███████║██║     █████╗  
#██╔══██║╚════██║   ██║   ██╔═══╝ ██╔══██║██║     ██╔══╝  
#██║  ██║███████║   ██║   ██║     ██║  ██║███████╗███████╗
#╚═╝  ╚═╝╚══════╝   ╚═╝   ╚═╝     ╚═╝  ╚═╝╚══════╝╚══════╝

#🚀 ASTRO.IO v2.4.5 🚀
#🎯 menú_principal.py - INTERFAZ GALÁCTICA DEFINITIVA
#✅ Datos 100% reales desde JSON
#✅ Barras de progreso [██░] 3 caracteres
#✅ COLAS DINÁMICAS - Solo muestran lo que hay en cola
#✅ TIEMPOS CORREGIDOS - Formato legible (18s, 2m, 1h 30m)
#✅ MERCADO NEGRO - Botón para acceder al sistema de mercado
#===============================================================

import os
import logging
import random
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import BadRequest

from login import AuthSystem, VERSION
from database import load_json, save_json
from utils import abreviar_numero, formatear_tiempo_corto

logger = logging.getLogger(__name__)

# ================= CONSTANTES =================
DATA_DIR = "data"
RECURSOS_FILE = os.path.join(DATA_DIR, "recursos.json")
MINAS_FILE = os.path.join(DATA_DIR, "minas.json")
EDIFICIOS_USUARIO_FILE = os.path.join(DATA_DIR, "edificios_usuario.json")
CAMPOS_FILE = os.path.join(DATA_DIR, "campos.json")
AUTHORIZED_USERS_FILE = os.path.join(DATA_DIR, "authorized_users.json")
USUARIOS_FILE = os.path.join(DATA_DIR, "usuarios.json")
COLAS_EDIFICIOS_FILE = os.path.join(DATA_DIR, "colas_edificios.json")
COLAS_INVESTIGACION_FILE = os.path.join(DATA_DIR, "investigaciones.json")

# ================= FUNCIONES DE DATOS REALES =================

def obtener_coordenadas_reales(user_id: int) -> dict:
    """🪐 Obtiene coordenadas REALES del usuario desde usuarios.json"""
    user_id_str = str(user_id)
    usuarios_data = load_json(USUARIOS_FILE) or {}
    
    if user_id_str not in usuarios_data:
        # Generar coordenadas aleatorias para usuario nuevo
        galaxia = 1
        sistema = random.randint(1, 100)
        planeta = random.randint(1, 15)
        usuarios_data[user_id_str] = {
            "galaxia": galaxia,
            "sistema": sistema,
            "planeta": planeta,
            "registro": datetime.now().isoformat()
        }
        save_json(USUARIOS_FILE, usuarios_data)
        logger.info(f"🪐 Coordenadas generadas para {AuthSystem.obtener_username(user_id)}: {galaxia}:{sistema}:{planeta}")
    
    return usuarios_data.get(user_id_str, {
        "galaxia": 1,
        "sistema": random.randint(1, 100),
        "planeta": random.randint(1, 15)
    })

def obtener_total_usuarios_real() -> int:
    """👥 Obtiene número REAL de usuarios autorizados"""
    autorizados = load_json(AUTHORIZED_USERS_FILE) or []
    return len(autorizados)

def obtener_recursos_reales(user_id: int) -> dict:
    """💰 Obtiene recursos REALES desde recursos.json"""
    user_id_str = str(user_id)
    recursos_data = load_json(RECURSOS_FILE) or {}
    
    return recursos_data.get(user_id_str, {
        "metal": 200,
        "cristal": 100,
        "deuterio": 0,
        "energia": 0,
        "materia_oscura": 0,
        "nxt20": 0
    })

def obtener_colas_edificios_reales(user_id: int) -> list:
    """🏗️ Obtiene colas de edificios REALES"""
    user_id_str = str(user_id)
    colas_data = load_json(COLAS_EDIFICIOS_FILE) or {}
    return colas_data.get(user_id_str, [])

def obtener_colas_investigacion_reales(user_id: int) -> list:
    """🔬 Obtiene colas de investigación REALES"""
    user_id_str = str(user_id)
    colas_data = load_json(COLAS_INVESTIGACION_FILE) or {}
    return colas_data.get(user_id_str, [])

def calcular_campos_usados_real(user_id: int) -> int:
    """📐 Calcula campos usados en tiempo REAL"""
    user_id_str = str(user_id)
    
    minas_data = load_json(MINAS_FILE) or {}
    minas = minas_data.get(user_id_str, {"metal": 0, "cristal": 0, "deuterio": 0})
    
    edificios_data = load_json(EDIFICIOS_USUARIO_FILE) or {}
    edificios = edificios_data.get(user_id_str, {
        "energia": 0, "laboratorio": 0, "hangar": 0, "terraformer": 0
    })
    
    campos_usados = 0
    
    for mina, nivel in minas.items():
        if isinstance(nivel, dict):
            nivel = nivel.get("nivel", 0)
        campos_usados += int(nivel) * 1
    
    for edificio, nivel in edificios.items():
        if isinstance(nivel, dict):
            nivel = nivel.get("nivel", 0)
        nivel = int(nivel)
        
        if edificio == "energia":
            campos_usados += nivel * 1
        elif edificio == "laboratorio":
            campos_usados += nivel * 2
        elif edificio == "hangar":
            campos_usados += nivel * 3
        elif edificio == "terraformer":
            campos_usados += nivel * 5
    
    return campos_usados

def obtener_campos_reales(user_id: int) -> dict:
    """🌍 Obtiene campos del planeta ACTUALIZADOS"""
    user_id_str = str(user_id)
    
    campos_data = load_json(CAMPOS_FILE) or {}
    campos = campos_data.get(user_id_str, {
        "total": 163,
        "usados": 0,
        "adicionales": 0
    })
    
    campos_usados = calcular_campos_usados_real(user_id)
    
    if campos.get("usados", 0) != campos_usados:
        campos["usados"] = campos_usados
        campos_data[user_id_str] = campos
        save_json(CAMPOS_FILE, campos_data)
    
    return campos

def barra_progreso_corta(actual: int, total: int) -> str:
    """📊 Barra de progreso de SOLO 3 caracteres"""
    if total <= 0:
        return "[░░░]"
    porcentaje = actual / total
    llenos = int(porcentaje * 3)
    return "[" + "█" * llenos + "░" * (3 - llenos) + "]"

# ================= 🔧 FUNCIÓN CORREGIDA - TIEMPOS DE COLA =================

def formatear_tiempo_cola(segundos_restantes: float) -> str:
    """
    ⏱️ Formatea tiempo en formato legible:
    - Menos de 60s: 45s
    - Menos de 1h: 23m, 45m
    - Más de 1h: 1h, 2h, 1h 30m
    """
    segundos = int(segundos_restantes)  # 👈 CONVERTIR A ENTERO
    
    if segundos < 60:
        return f"{segundos}s"
    elif segundos < 3600:
        minutos = segundos // 60
        return f"{minutos}m"
    else:
        horas = segundos // 3600
        minutos = (segundos % 3600) // 60
        if minutos == 0:
            return f"{horas}h"
        else:
            return f"{horas}h {minutos}m"

def procesar_cola_edificio(cola: dict) -> tuple:
    """Procesa una cola de edificio y devuelve (texto, barra, tiempo, tipo, nivel)"""
    tipo = cola.get("tipo", "")
    nivel = cola.get("nivel_objetivo", 1)
    tiempo_restante = cola.get("tiempo_restante", 0)
    tiempo_total = cola.get("tiempo_total", 1)
    
    # Mapeo de tipos a nombres mostrados
    if tipo == "metal":
        nombre = "M.Metal"
    elif tipo == "cristal":
        nombre = "M.Cristal"
    elif tipo == "deuterio":
        nombre = "M.Deuterio"
    elif tipo == "energia":
        nombre = "Planta"
    elif tipo == "laboratorio":
        nombre = "Laboratorio"
    elif tipo == "hangar":
        nombre = "Hangar"
    elif tipo == "terraformer":
        nombre = "Terraformer"
    else:
        nombre = tipo.capitalize()
    
    progreso = max(0, tiempo_total - tiempo_restante)
    barra = barra_progreso_corta(progreso, tiempo_total)
    tiempo = formatear_tiempo_cola(tiempo_restante)  # 👈 AHORA USA FUNCIÓN CORREGIDA
    
    return (nombre, barra, tiempo, tipo, nivel)

def procesar_cola_investigacion(cola: dict) -> tuple:
    """Procesa una cola de investigación y devuelve (texto, barra, tiempo, tecnologia, nivel)"""
    tecnologia = cola.get("tecnologia", "")
    nivel = cola.get("nivel_objetivo", 1)
    tiempo_restante = cola.get("tiempo_restante", 0)
    tiempo_total = cola.get("tiempo_total", 1)
    
    # Mapeo de tecnologías a nombres cortos
    if "espion" in tecnologia.lower():
        nombre = "T.Espionaje"
    elif "combust" in tecnologia.lower():
        nombre = "T.Combustión"
    elif "escudo" in tecnologia.lower():
        nombre = "T.Escudos"
    elif "protec" in tecnologia.lower():
        nombre = "T.Protección"
    elif "nave" in tecnologia.lower():
        nombre = "T.Naves"
    elif "energ" in tecnologia.lower():
        nombre = "T.Energía"
    elif "laser" in tecnologia.lower():
        nombre = "T.Láser"
    elif "plasma" in tecnologia.lower():
        nombre = "T.Plasma"
    elif "hiper" in tecnologia.lower():
        nombre = "T.Hiperespacio"
    else:
        nombre = tecnologia[:12]
    
    progreso = max(0, tiempo_total - tiempo_restante)
    barra = barra_progreso_corta(progreso, tiempo_total)
    tiempo = formatear_tiempo_cola(tiempo_restante)  # 👈 MISMA FUNCIÓN CORREGIDA
    
    return (nombre, barra, tiempo, tecnologia, nivel)

# ================= MENÚ PRINCIPAL v2.4.0 - COLAS DINÁMICAS =================

async def menu_principal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    🏠 MENÚ PRINCIPAL - INTERFAZ GALÁCTICA DEFINITIVA
    ✅ COLAS DINÁMICAS - Solo muestra lo que hay en cola
    ✅ MERCADO NEGRO - Botón añadido
    """
    query = update.callback_query
    if not query:
        logger.error("❌ menu_principal llamado sin callback_query")
        return
    
    await query.answer()
    
    # ========== DATOS 100% REALES ==========
    user_id = query.from_user.id
    username_tag = AuthSystem.formatear_username(user_id, query.from_user.first_name)
    
    # Coordenadas reales
    coords = obtener_coordenadas_reales(user_id)
    galaxia = coords.get("galaxia", 1)
    sistema = coords.get("sistema", 1)
    planeta = coords.get("planeta", 1)
    
    # Total usuarios real
    total_usuarios = obtener_total_usuarios_real()
    
    # Recursos reales
    recursos = obtener_recursos_reales(user_id)
    metal = abreviar_numero(recursos.get("metal", 200))
    cristal = abreviar_numero(recursos.get("cristal", 100))
    deuterio = abreviar_numero(recursos.get("deuterio", 0))
    energia = abreviar_numero(recursos.get("energia", 0))
    materia = abreviar_numero(recursos.get("materia_oscura", 0))
    nxt = abreviar_numero(recursos.get("nxt20", 0))
    
    # Campos reales
    campos = obtener_campos_reales(user_id)
    campos_usados = campos.get("usados", 0)
    campos_totales = campos.get("total", 163)
    barra_campos = barra_progreso_corta(campos_usados, campos_totales)
    
    # ========== 🔥 COLAS DINÁMICAS - SOLO LO QUE HAY ==========
    colas_edificios = obtener_colas_edificios_reales(user_id)
    colas_investigacion = obtener_colas_investigacion_reales(user_id)
    
    # Procesar todas las colas
    edificios_procesados = []
    for cola in colas_edificios:
        nombre, barra, tiempo, tipo, nivel = procesar_cola_edificio(cola)
        edificios_procesados.append((nombre, barra, tiempo, tipo, nivel))
    
    investigaciones_procesadas = []
    for cola in colas_investigacion:
        nombre, barra, tiempo, tecnologia, nivel = procesar_cola_investigacion(cola)
        investigaciones_procesadas.append((nombre, barra, tiempo, tecnologia, nivel))
    
    # ========== CONSTRUIR MENSAJE CON COLAS DINÁMICAS ==========
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"\n"
        f"🚀 ASTRO.IO v2.4.5\n"
        f"\n"
        f"👤 {username_tag}  • 🌐 ONLINE \n"
        f"🪐 {galaxia}:{sistema}:{planeta}   • 👥 {total_usuarios}     \n"
        f"⚔️ 🕊️ PAZ\n"
        f"\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"\n"
        f"🔩 {metal}  💎 {cristal}  🧪 {deuterio}\n"
        f"⚡ {energia}   🌑 {materia}  🪙 {nxt}\n"
        f"\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"\n"
    )
    
    # ========== 🔥 SECCIÓN DE COLAS - DINÁMICA ==========
    hay_colas = False
    
    # Mostrar hasta 3 construcciones (edificios primero)
    cola_idx = 0
    for edificio in edificios_procesados[:2]:  # Máximo 2 edificios
        nombre, barra, tiempo, tipo, nivel = edificio
        mensaje += f"🔨 {nombre}:    {barra} {tiempo} (N.{nivel})\n"
        hay_colas = True
        cola_idx += 1
    
    # Si hay espacio, mostrar investigaciones
    if cola_idx < 3 and investigaciones_procesadas:
        for investigacion in investigaciones_procesadas[:3 - cola_idx]:
            nombre, barra, tiempo, tecnologia, nivel = investigacion
            mensaje += f"🔬 {nombre}: {barra} {tiempo} (N.{nivel})\n"
            hay_colas = True
            cola_idx += 1
    
    # Si no hay nada en cola, mostrar mensaje
    if not hay_colas:
        mensaje += f"🏗️ Sin construcciones en cola\n"
        mensaje += f"🔬 Sin investigaciones en cola\n"
    
    # Siempre mostrar campos
    mensaje += f"🌍 Compos:     {barra_campos} {campos_usados}/{campos_totales}\n"
    mensaje += f"\n"
    mensaje += f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    
    # ========== CONSTRUIR TECLADO CON BOTÓN DE MERCADO ==========
    es_admin = AuthSystem.es_admin(user_id)
    
    keyboard = [
        [InlineKeyboardButton("💰 RECURSOS", callback_data="menu_recursos")],
        [
            InlineKeyboardButton("🏗️ EDIFICIOS", callback_data="menu_edificios"),
            InlineKeyboardButton("🔬 INVESTIGACIÓN", callback_data="menu_investigaciones")
        ],
        [
            InlineKeyboardButton("🚀 FLOTA", callback_data="menu_flota"),
            InlineKeyboardButton("🛡️ DEFENSA", callback_data="menu_defensa")
        ],
        [
            InlineKeyboardButton("✈️ BASE FLOTAS", callback_data="menu_base_flotas"),
            InlineKeyboardButton("🌍 ALIANZA", callback_data="menu_alianza")
        ],
        [
            InlineKeyboardButton("📖 GUÍA", callback_data="guia_desbloqueo"),
            InlineKeyboardButton("🏆 PUNTUACIÓN", callback_data="menu_puntuacion")
        ],
        [InlineKeyboardButton("💰 MERCADO NEGRO", callback_data="mercado_principal")],  # 👈 NUEVO BOTÓN
    ]
    
    # Si hay colas, agregar botón para ver cola completa
    if hay_colas:
        keyboard.insert(0, [InlineKeyboardButton("📋 VER COLA COMPLETA", callback_data="edificios_cola")])
    
    if es_admin:
        keyboard.append([InlineKeyboardButton("👑 ADMINISTRADOR", callback_data="menu_admin")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # ========== EDITAR MENSAJE ==========
    try:
        await query.edit_message_text(
            text=mensaje,
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
        logger.info(f"✅ Menú principal v2.4.0 actualizado para {username_tag}")
        
    except BadRequest as e:
        if "Message is not modified" in str(e):
            await query.answer("✅ Menú ya actualizado")
        else:
            logger.error(f"❌ Error editando menú principal: {e}")
            await query.answer(f"❌ Error", show_alert=True)
    except Exception as e:
        logger.error(f"❌ Error editando menú principal: {e}")
        await query.answer(f"❌ Error", show_alert=True)

# ================= BIENVENIDA PARA USUARIOS NUEVOS =================

async def menu_bienvenida(context, user_id: int, username: str = None):
    """🎉 BIENVENIDA - Mismo estilo que menú principal con botón de mercado"""
    username_tag = AuthSystem.formatear_username(user_id, username)
    
    # Generar coordenadas
    coords = obtener_coordenadas_reales(user_id)
    galaxia = coords.get("galaxia", 1)
    sistema = coords.get("sistema", 1)
    planeta = coords.get("planeta", 1)
    
    total_usuarios = obtener_total_usuarios_real()
    es_admin = AuthSystem.es_admin(user_id)
    
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"\n"
        f"🚀 ASTRO.IO v2.4.5\n"
        f"\n"
        f"👤 {username_tag}  • 🌐 ONLINE \n"
        f"🪐 {galaxia}:{sistema}:{planeta}   • 👥 {total_usuarios}     \n"
        f"⚔️ 🕊️ PAZ\n"
        f"\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"\n"
        f"🔩 200  💎 100  🧪 0\n"
        f"⚡ 0   🌑 0  🪙 0\n"
        f"\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"\n"
        f"🏗️ Sin construcciones en cola\n"
        f"🔬 Sin investigaciones en cola\n"
        f"🌍 Compos:     [░░░] 0/163\n"
        f"\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    )
    
    keyboard = [
        [InlineKeyboardButton("💰 RECURSOS", callback_data="menu_recursos")],
        [
            InlineKeyboardButton("🏗️ EDIFICIOS", callback_data="menu_edificios"),
            InlineKeyboardButton("🔬 INVESTIGACIÓN", callback_data="menu_investigaciones")
        ],
        [
            InlineKeyboardButton("🚀 FLOTA", callback_data="menu_flota"),
            InlineKeyboardButton("🛡️ DEFENSA", callback_data="menu_defensa")
        ],
        [
            InlineKeyboardButton("✈️ BASE FLOTAS", callback_data="menu_base_flotas"),
            InlineKeyboardButton("🌍 ALIANZA", callback_data="menu_alianza")
        ],
        [
            InlineKeyboardButton("📖 GUÍA", callback_data="guia_desbloqueo"),
            InlineKeyboardButton("🏆 PUNTUACIÓN", callback_data="menu_puntuacion")
        ],
        [InlineKeyboardButton("💰 MERCADO NEGRO", callback_data="mercado_principal")],  # 👈 NUEVO BOTÓN
    ]
    
    if es_admin:
        keyboard.append([InlineKeyboardButton("👑 ADMINISTRADOR", callback_data="menu_admin")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=mensaje,
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
        logger.info(f"✅ Bienvenida v2.4.0 enviada a {username_tag}")
        return True
    except Exception as e:
        logger.error(f"❌ Error enviando bienvenida a {username_tag}: {e}")
        return False

# ================= EXPORTAR =================

__all__ = [
    'menu_principal',
    'menu_bienvenida',
    'obtener_coordenadas_reales',
    'obtener_recursos_reales',
    'obtener_campos_reales',
    'barra_progreso_corta'
]
