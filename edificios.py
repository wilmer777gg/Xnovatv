#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#██████╗ ███████╗████████╗██████╗  █████╗ ██╗     ███████╗
#██╔══██╗██╔════╝╚══██╔══╝██╔══██╗██╔══██╗██║     ██╔════╝
#██████╔╝███████╗   ██║   ██████╔╝███████║██║     ███████╗
#██╔══██╗╚════██║   ██║   ██╔══██╗██╔══██║██║     ╚════██║
#██║  ██║███████║   ██║   ██║  ██║██║  ██║███████╗███████║
#╚═╝  ╚═╝╚══════╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚══════╝

#🚀 ASTRO.IO v2.4.5 🚀
#🏗️ edificios.py - SISTEMA DE CONSTRUCCIÓN CON COLAS EN TIEMPO REAL
#===========================================================
#✅ MISMO ESTILO que menú principal
#✅ Barras de progreso [██░] 3 caracteres
#✅ Formato de tiempo corto: 45m, 2h, 1h 30m
#✅ Diseño con separadores 🌀
#===========================================================

import os
import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from login import AuthSystem, requiere_login
from database import load_json, save_json
from utils import abreviar_numero

logger = logging.getLogger(__name__)

# ================= CONSTANTES =================
DATA_DIR = "data"
RECURSOS_FILE = os.path.join(DATA_DIR, "recursos.json")
MINAS_FILE = os.path.join(DATA_DIR, "minas.json")
EDIFICIOS_USUARIO_FILE = os.path.join(DATA_DIR, "edificios_usuario.json")
CAMPOS_FILE = os.path.join(DATA_DIR, "campos.json")
COLAS_EDIFICIOS_FILE = os.path.join(DATA_DIR, "colas_edificios.json")
DATA_FILE = os.path.join(DATA_DIR, "data.json")

CAMPO_BASE_PLANETA = 163
MAX_COLA_SIZE = 3

# ================= 🎨 FUNCIONES VISUALES (MISMO ESTILO QUE MENÚ PRINCIPAL) =================

def barra_progreso_3c(actual: int, total: int) -> str:
    """📊 Barra de progreso de SOLO 3 caracteres [██░]"""
    if total <= 0:
        return "[░░░]"
    porcentaje = min(1.0, actual / total)
    llenos = int(porcentaje * 3)
    return "[" + "█" * llenos + "░" * (3 - llenos) + "]"

def formatear_tiempo_corto(segundos: int) -> str:
    """⏱️ Formatea tiempo en formato corto: 45s, 23m, 2h, 1h 30m"""
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

# ================= CONFIGURACIÓN DE CONSTRUCCIONES =================
CONSTRUCCIONES = {
    # ================= MINAS =================
    "metal": {
        "nombre": "Mina de Metal",
        "tipo": "mina",
        "icono": "🔩",
        "icono_corto": "🪙",
        "descripcion": "Extrae metal de los asteroides cercanos.",
        "costo_base": {"metal": 60, "cristal": 15},
        "produccion_base": 30,
        "consumo_energia": 5,
        "campos": 1,
        "max_nivel": 100,
        "tiempo_base": 60,
        "factor_costo": 1.3,
        "factor_tiempo": 1.2,
        "factor_produccion": 1.1
    },
    "cristal": {
        "nombre": "Mina de Cristal",
        "tipo": "mina",
        "icono": "💎",
        "icono_corto": "💎",
        "descripcion": "Extrae cristales lunares.",
        "costo_base": {"metal": 48, "cristal": 24},
        "produccion_base": 20,
        "consumo_energia": 5,
        "campos": 1,
        "max_nivel": 100,
        "tiempo_base": 60,
        "factor_costo": 1.3,
        "factor_tiempo": 1.2,
        "factor_produccion": 1.1
    },
    "deuterio": {
        "nombre": "Sintetizador de Deuterio",
        "tipo": "mina",
        "icono": "🧪",
        "icono_corto": "⚛️",
        "descripcion": "Procesa deuterio de los océanos planetarios.",
        "costo_base": {"metal": 225, "cristal": 75, "deuterio": 30},
        "produccion_base": 15,
        "consumo_energia": 10,
        "campos": 1,
        "max_nivel": 100,
        "tiempo_base": 60,
        "factor_costo": 1.3,
        "factor_tiempo": 1.2,
        "factor_produccion": 1.1
    },
    # ================= EDIFICIOS =================
    "energia": {
        "nombre": "Planta de Energía",
        "tipo": "edificio",
        "icono": "⚡",
        "icono_corto": "⚡",
        "descripcion": "Genera energía para todas tus estructuras.",
        "costo_base": {"metal": 150, "cristal": 50},
        "produccion_base": 100,
        "consumo_energia": 0,
        "campos": 1,
        "max_nivel": 100,
        "tiempo_base": 60,
        "factor_costo": 1.3,
        "factor_tiempo": 1.2,
        "factor_produccion": 1.1
    },
    "laboratorio": {
        "nombre": "Laboratorio de Investigación",
        "tipo": "edificio",
        "icono": "🔬",
        "icono_corto": "🔬",
        "descripcion": "Desarrolla nuevas tecnologías. Requiere deuterio.",
        "costo_base": {"metal": 200, "cristal": 100, "deuterio": 30},
        "produccion_base": 0,
        "consumo_energia": 20,
        "campos": 2,
        "max_nivel": 30,
        "tiempo_base": 90,
        "factor_costo": 1.5,
        "factor_tiempo": 1.3,
        "factor_produccion": 1.0
    },
    "hangar": {
        "nombre": "Hangar Espacial",
        "tipo": "edificio",
        "icono": "🚀",
        "icono_corto": "✈️",
        "descripcion": "Construye y almacena naves espaciales.",
        "costo_base": {"metal": 300, "cristal": 150, "deuterio": 50},
        "produccion_base": 0,
        "consumo_energia": 30,
        "campos": 3,
        "max_nivel": 20,
        "tiempo_base": 120,
        "requisitos": {"laboratorio": 1, "energia": 3},
        "factor_costo": 1.6,
        "factor_tiempo": 1.4,
        "factor_produccion": 1.0
    },
    "terraformer": {
        "nombre": "Terraformer",
        "tipo": "edificio",
        "icono": "🌍",
        "icono_corto": "🌍",
        "descripcion": "Expande el terreno disponible. +5 campos por nivel.",
        "costo_base": {"metal": 750, "cristal": 500, "deuterio": 250},
        "produccion_base": 0,
        "consumo_energia": 50,
        "campos": 5,
        "max_nivel": 10,
        "tiempo_base": 180,
        "requisitos": {"laboratorio": 5, "hangar": 3, "energia": 8},
        "factor_costo": 2.0,
        "factor_tiempo": 1.5,
        "factor_produccion": 1.0
    }
}

# ================= FUNCIONES DE LECTURA =================

def obtener_nivel(user_id: int, tipo: str) -> int:
    user_id_str = str(user_id)
    if tipo in ["metal", "cristal", "deuterio"]:
        data = load_json(MINAS_FILE) or {}
        usuario = data.get(user_id_str, {})
        nivel_data = usuario.get(tipo, 0)
    else:
        data = load_json(EDIFICIOS_USUARIO_FILE) or {}
        usuario = data.get(user_id_str, {})
        nivel_data = usuario.get(tipo, 0)
    
    if isinstance(nivel_data, dict):
        return nivel_data.get("nivel", 0)
    return int(nivel_data) if isinstance(nivel_data, (int, float)) else 0

def obtener_campos(user_id: int) -> dict:
    user_id_str = str(user_id)
    campos_data = load_json(CAMPOS_FILE) or {}
    return campos_data.get(user_id_str, {
        "total": CAMPO_BASE_PLANETA,
        "usados": 0,
        "adicionales": 0
    })

def calcular_campos_usados(user_id: int) -> int:
    user_id_str = str(user_id)
    minas_data = load_json(MINAS_FILE) or {}
    minas = minas_data.get(user_id_str, {})
    edificios_data = load_json(EDIFICIOS_USUARIO_FILE) or {}
    edificios = edificios_data.get(user_id_str, {})
    
    total = 0
    for mina in ["metal", "cristal", "deuterio"]:
        nivel = minas.get(mina, 0)
        if isinstance(nivel, dict):
            nivel = nivel.get("nivel", 0)
        total += int(nivel) * 1
    
    for edificio, nivel in edificios.items():
        if isinstance(nivel, dict):
            nivel = nivel.get("nivel", 0)
        nivel = int(nivel)
        if edificio == "energia":
            total += nivel * 1
        elif edificio == "laboratorio":
            total += nivel * 2
        elif edificio == "hangar":
            total += nivel * 3
        elif edificio == "terraformer":
            total += nivel * 5
    
    return total

def actualizar_campos(user_id: int) -> dict:
    user_id_str = str(user_id)
    campos = obtener_campos(user_id)
    campos_usados = calcular_campos_usados(user_id)
    
    if campos.get("usados", 0) != campos_usados:
        campos["usados"] = campos_usados
        campos_data = load_json(CAMPOS_FILE) or {}
        campos_data[user_id_str] = campos
        save_json(CAMPOS_FILE, campos_data)
    
    return campos

def calcular_costo(tipo: str, nivel_actual: int) -> dict:
    if tipo not in CONSTRUCCIONES:
        return {}
    config = CONSTRUCCIONES[tipo]
    costo = {}
    for recurso, base in config["costo_base"].items():
        costo[recurso] = int(base * (config["factor_costo"] ** nivel_actual))
    return costo

def calcular_tiempo(tipo: str, nivel_actual: int) -> int:
    if tipo not in CONSTRUCCIONES:
        return 0
    config = CONSTRUCCIONES[tipo]
    tiempo = int(config["tiempo_base"] * (config["factor_tiempo"] ** nivel_actual))
    return max(30, tiempo)

def calcular_produccion(tipo: str, nivel: int) -> int:
    if tipo not in CONSTRUCCIONES:
        return 0
    config = CONSTRUCCIONES[tipo]
    if nivel <= 0:
        return 0
    return int(config["produccion_base"] * (config["factor_produccion"] ** nivel))

def verificar_requisitos(user_id: int, tipo: str) -> tuple:
    if tipo not in CONSTRUCCIONES:
        return False, "❌ Construcción no válida"
    config = CONSTRUCCIONES[tipo]
    requisitos = config.get("requisitos", {})
    if not requisitos:
        return True, "✅ Requisitos cumplidos"
    
    faltantes = []
    for req_tipo, req_nivel in requisitos.items():
        nivel_actual = obtener_nivel(user_id, req_tipo)
        if nivel_actual < req_nivel:
            req_nombre = CONSTRUCCIONES.get(req_tipo, {}).get("nombre", req_tipo)
            faltantes.append(f"• {req_nombre}: Nivel {req_nivel} (tienes: {nivel_actual})")
    
    if faltantes:
        return False, "❌ Requisitos no cumplidos:\n" + "\n".join(faltantes)
    return True, "✅ Requisitos cumplidos"

def verificar_recursos(user_id: int, tipo: str, nivel_actual: int) -> tuple:
    user_id_str = str(user_id)
    recursos_data = load_json(RECURSOS_FILE) or {}
    recursos = recursos_data.get(user_id_str, {})
    costo = calcular_costo(tipo, nivel_actual)
    
    faltantes = []
    for recurso, cantidad in costo.items():
        disponible = recursos.get(recurso, 0)
        if disponible < cantidad:
            icono = "🔩" if recurso == "metal" else "💎" if recurso == "cristal" else "🧪"
            faltantes.append(f"{icono} {recurso.capitalize()}: {abreviar_numero(disponible)}/{abreviar_numero(cantidad)}")
    
    if faltantes:
        return False, "❌ Recursos insuficientes:\n" + "\n".join(faltantes)
    return True, "✅ Recursos suficientes"

def verificar_campos(user_id: int, tipo: str) -> tuple:
    config = CONSTRUCCIONES[tipo]
    campos = actualizar_campos(user_id)
    campos_libres = campos.get("total", CAMPO_BASE_PLANETA) - campos.get("usados", 0)
    if campos_libres < config["campos"]:
        return False, f"❌ Espacio insuficiente. Necesitas {config['campos']} campos (libres: {campos_libres})"
    return True, "✅ Campos suficientes"

# ================= 📋 FUNCIONES DE COLA =================

def obtener_cola(user_id: int) -> list:
    user_id_str = str(user_id)
    data = load_json(COLAS_EDIFICIOS_FILE) or {}
    return data.get(user_id_str, [])

def guardar_cola(user_id: int, cola: list) -> bool:
    user_id_str = str(user_id)
    data = load_json(COLAS_EDIFICIOS_FILE) or {}
    data[user_id_str] = cola
    return save_json(COLAS_EDIFICIOS_FILE, data)

def agregar_a_cola(user_id: int, tipo: str, nivel_objetivo: int, costo: dict) -> tuple:
    cola = obtener_cola(user_id)
    if len(cola) >= MAX_COLA_SIZE:
        return False, f"❌ Límite de {MAX_COLA_SIZE} construcciones alcanzado", 0
    
    nivel_actual = obtener_nivel(user_id, tipo)
    tiempo = calcular_tiempo(tipo, nivel_actual)
    ahora = datetime.now()
    fin = ahora + timedelta(seconds=tiempo)
    
    nueva = {
        "tipo": tipo,
        "nivel_actual": nivel_actual,
        "nivel_objetivo": nivel_objetivo,
        "inicio": ahora.strftime("%Y-%m-%d %H:%M:%S"),
        "fin": fin.strftime("%Y-%m-%d %H:%M:%S"),
        "tiempo_total": tiempo,
        "tiempo_restante": tiempo,
        "progreso": 0,
        "costo": costo
    }
    
    cola.append(nueva)
    guardar_cola(user_id, cola)
    return True, f"✅ Construcción añadida a la cola", tiempo

def procesar_cola(user_id: int) -> list:
    cola = obtener_cola(user_id)
    if not cola:
        return []
    
    ahora = datetime.now()
    completadas = []
    cola_restante = []
    
    for item in cola:
        try:
            fin = datetime.strptime(item["fin"], "%Y-%m-%d %H:%M:%S")
            if ahora >= fin:
                tipo = item["tipo"]
                nivel = item["nivel_objetivo"]
                
                if tipo in ["metal", "cristal", "deuterio"]:
                    minas_data = load_json(MINAS_FILE) or {}
                    minas_usuario = minas_data.get(str(user_id), {})
                    minas_usuario[tipo] = nivel
                    minas_data[str(user_id)] = minas_usuario
                    save_json(MINAS_FILE, minas_data)
                else:
                    edificios_data = load_json(EDIFICIOS_USUARIO_FILE) or {}
                    edificios_usuario = edificios_data.get(str(user_id), {})
                    edificios_usuario[tipo] = nivel
                    edificios_data[str(user_id)] = edificios_usuario
                    save_json(EDIFICIOS_USUARIO_FILE, edificios_data)
                
                if tipo == "terraformer":
                    campos_data = load_json(CAMPOS_FILE) or {}
                    campos = campos_data.get(str(user_id), {
                        "total": CAMPO_BASE_PLANETA,
                        "usados": 0,
                        "adicionales": 0
                    })
                    campos_adicionales = nivel * 5
                    campos["adicionales"] = campos_adicionales
                    campos["total"] = CAMPO_BASE_PLANETA + campos_adicionales
                    campos["usados"] = calcular_campos_usados(user_id)
                    campos_data[str(user_id)] = campos
                    save_json(CAMPOS_FILE, campos_data)
                else:
                    actualizar_campos(user_id)
                
                completadas.append(item)
                logger.info(f"✅ Construcción completada: {tipo} nivel {nivel} para {AuthSystem.obtener_username(user_id)}")
            else:
                tiempo_transcurrido = item["tiempo_total"] - (fin - ahora).total_seconds()
                item["tiempo_restante"] = max(0, (fin - ahora).total_seconds())
                item["progreso"] = max(0, tiempo_transcurrido)
                cola_restante.append(item)
        except Exception as e:
            logger.error(f"❌ Error: {e}")
            cola_restante.append(item)
    
    guardar_cola(user_id, cola_restante)
    return completadas

def cancelar_construccion(user_id: int, posicion: int) -> tuple:
    cola = obtener_cola(user_id)
    if posicion < 0 or posicion >= len(cola):
        return False, "❌ Posición inválida", {}
    
    item = cola.pop(posicion)
    reembolso = {}
    for recurso, cantidad in item["costo"].items():
        reembolso[recurso] = int(cantidad * 0.5)
    
    if reembolso:
        recursos_data = load_json(RECURSOS_FILE) or {}
        recursos = recursos_data.get(str(user_id), {})
        for recurso, cantidad in reembolso.items():
            recursos[recurso] = recursos.get(recurso, 0) + cantidad
        recursos_data[str(user_id)] = recursos
        save_json(RECURSOS_FILE, recursos_data)
    
    guardar_cola(user_id, cola)
    return True, f"✅ Construcción cancelada. 50% reembolsado.", reembolso

# ================= 🏗️ INICIAR CONSTRUCCIÓN =================

def iniciar_construccion(user_id: int, tipo: str) -> tuple:
    if tipo not in CONSTRUCCIONES:
        return False, "❌ Construcción no válida"
    
    config = CONSTRUCCIONES[tipo]
    nivel_actual = obtener_nivel(user_id, tipo)
    
    if nivel_actual >= config["max_nivel"]:
        return False, f"🏆 Nivel máximo ({config['max_nivel']}) alcanzado"
    
    cumple_req, msg_req = verificar_requisitos(user_id, tipo)
    if not cumple_req:
        return False, msg_req
    
    cumple_rec, msg_rec = verificar_recursos(user_id, tipo, nivel_actual)
    if not cumple_rec:
        return False, msg_rec
    
    cumple_cam, msg_cam = verificar_campos(user_id, tipo)
    if not cumple_cam:
        return False, msg_cam
    
    costo = calcular_costo(tipo, nivel_actual)
    
    # Descontar recursos
    recursos_data = load_json(RECURSOS_FILE) or {}
    recursos = recursos_data.get(str(user_id), {})
    for recurso, cantidad in costo.items():
        recursos[recurso] = recursos.get(recurso, 0) - cantidad
    recursos_data[str(user_id)] = recursos
    save_json(RECURSOS_FILE, recursos_data)
    
    # Agregar a cola
    exito, msg_cola, tiempo = agregar_a_cola(user_id, tipo, nivel_actual + 1, costo)
    if not exito:
        for recurso, cantidad in costo.items():
            recursos[recurso] = recursos.get(recurso, 0) + cantidad
        recursos_data[str(user_id)] = recursos
        save_json(RECURSOS_FILE, recursos_data)
        return False, msg_cola
    
    cola = obtener_cola(user_id)
    username = AuthSystem.obtener_username(user_id)
    logger.info(f"🏗️ {username} inició {config['nombre']} nivel {nivel_actual + 1} - {formatear_tiempo_corto(tiempo)}")
    
    tiempo_str = formatear_tiempo_corto(tiempo)
    
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"🏗️ <b>CONSTRUCCIÓN INICIADA</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"{config['icono']} {config['nombre']}\n"
        f"├ Nivel actual: {nivel_actual}\n"
        f"├ Nivel objetivo: <b>{nivel_actual + 1}</b>\n"
        f"├ Tiempo: {tiempo_str}\n"
        f"└ Posición en cola: {len(cola)}\n\n"
        f"💰 Recursos descontados correctamente.\n\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    )
    
    return True, mensaje

# ================= 🏗️ HANDLERS =================

@requiere_login
async def menu_edificios_principal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    
    await query.answer()
    user_id = query.from_user.id
    
    procesar_cola(user_id)
    
    recursos_data = load_json(RECURSOS_FILE) or {}
    recursos = recursos_data.get(str(user_id), {})
    campos = actualizar_campos(user_id)
    cola = obtener_cola(user_id)
    username_tag = AuthSystem.obtener_username(user_id)
    
    niveles = {tipo: obtener_nivel(user_id, tipo) for tipo in CONSTRUCCIONES}
    
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"🏗️ <b>CENTRO DE CONSTRUCCIÓN</b> - {username_tag}\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"💰 <b>RECURSOS:</b>\n"
        f"🔩 Metal: {abreviar_numero(recursos.get('metal', 0))}\n"
        f"💎 Cristal: {abreviar_numero(recursos.get('cristal', 0))}\n"
        f"🧪 Deuterio: {abreviar_numero(recursos.get('deuterio', 0))}\n"
        f"⚡ Energía: {abreviar_numero(recursos.get('energia', 0))}\n\n"
        f"📋 <b>COLA:</b> {len(cola)}/{MAX_COLA_SIZE}\n"
        f"🌍 <b>CAMPOS:</b> {campos.get('usados', 0)}/{campos.get('total', CAMPO_BASE_PLANETA)}\n\n"
    )
    
    if cola:
        mensaje += f"⏳ <b>EN CONSTRUCCIÓN:</b>\n"
        ahora = datetime.now()
        for idx, item in enumerate(cola[:3], 1):
            fin = datetime.strptime(item["fin"], "%Y-%m-%d %H:%M:%S")
            segundos = max(0, (fin - ahora).total_seconds())
            tiempo = formatear_tiempo_corto(int(segundos))
            progreso = item["tiempo_total"] - item["tiempo_restante"]
            barra = barra_progreso_3c(progreso, item["tiempo_total"])
            config = CONSTRUCCIONES.get(item["tipo"], {})
            icono = config.get("icono", "🏗️")
            nombre = config.get("nombre", item["tipo"])
            mensaje += f"   {idx}. {icono} {nombre}\n"
            mensaje += f"      {barra} {tiempo} → N.{item['nivel_objetivo']}\n"
        mensaje += "\n"
    
    mensaje += f"📊 <b>TUS CONSTRUCCIONES:</b>\n\n"
    mensaje += f"⛏️ <b>MINAS:</b>\n"
    for tipo in ["metal", "cristal", "deuterio"]:
        nivel = niveles.get(tipo, 0)
        config = CONSTRUCCIONES[tipo]
        prod = calcular_produccion(tipo, nivel)
        mensaje += f"   {config['icono']} {config['nombre']}: N.{nivel} (+{abreviar_numero(prod)}/h)\n"
    
    mensaje += f"\n🏢 <b>EDIFICIOS:</b>\n"
    for tipo in ["energia", "laboratorio", "hangar", "terraformer"]:
        nivel = niveles.get(tipo, 0)
        config = CONSTRUCCIONES[tipo]
        if tipo == "energia":
            prod = calcular_produccion(tipo, nivel)
            mensaje += f"   {config['icono']} {config['nombre']}: N.{nivel} (+{abreviar_numero(prod)}/h)\n"
        else:
            mensaje += f"   {config['icono']} {config['nombre']}: N.{nivel}\n"
    
    mensaje += f"\n🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
    mensaje += f"<i>Selecciona una construcción:</i>"
    
    keyboard = [
        [
            InlineKeyboardButton("🔩 Metal", callback_data="edificio_metal"),
            InlineKeyboardButton("💎 Cristal", callback_data="edificio_cristal"),
            InlineKeyboardButton("🧪 Deuterio", callback_data="edificio_deuterio")
        ],
        [
            InlineKeyboardButton("⚡ Energía", callback_data="edificio_energia"),
            InlineKeyboardButton("🔬 Laboratorio", callback_data="edificio_laboratorio")
        ],
        [
            InlineKeyboardButton("🚀 Hangar", callback_data="edificio_hangar"),
            InlineKeyboardButton("🌍 Terraformer", callback_data="edificio_terraformer")
        ],
        [InlineKeyboardButton("📋 VER COLA", callback_data="edificios_cola")],
        [InlineKeyboardButton("◀️ VOLVER", callback_data="menu_principal")]
    ]
    
    if cola:
        cancel_fila = []
        for i in range(1, min(len(cola) + 1, 4)):
            cancel_fila.append(InlineKeyboardButton(f"❌ Cancelar {i}", callback_data=f"edificios_cancelar_{i-1}"))
        keyboard.insert(-1, cancel_fila)
    
    await query.edit_message_text(
        text=mensaje,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

@requiere_login
async def submenu_edificio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    tipo = query.data.replace("edificio_", "")
    
    if tipo not in CONSTRUCCIONES:
        await query.edit_message_text("❌ Edificio no encontrado")
        return
    
    config = CONSTRUCCIONES[tipo]
    nivel_actual = obtener_nivel(user_id, tipo)
    recursos_data = load_json(RECURSOS_FILE) or {}
    recursos = recursos_data.get(str(user_id), {})
    username_tag = AuthSystem.obtener_username(user_id)
    cola = obtener_cola(user_id)
    
    costo_proximo = calcular_costo(tipo, nivel_actual) if nivel_actual < config["max_nivel"] else {}
    tiempo_proximo = calcular_tiempo(tipo, nivel_actual) if nivel_actual < config["max_nivel"] else 0
    produccion_actual = calcular_produccion(tipo, nivel_actual)
    produccion_proximo = calcular_produccion(tipo, nivel_actual + 1) if nivel_actual < config["max_nivel"] else 0
    
    cumple_requisitos, msg_req = verificar_requisitos(user_id, tipo)
    cumple_recursos, msg_rec = verificar_recursos(user_id, tipo, nivel_actual) if nivel_actual < config["max_nivel"] else (False, "")
    cumple_campos, msg_cam = verificar_campos(user_id, tipo) if nivel_actual < config["max_nivel"] else (False, "")
    tiene_slot = len(cola) < MAX_COLA_SIZE if nivel_actual < config["max_nivel"] else False
    
    puede_construir = (
        nivel_actual < config["max_nivel"] and
        cumple_requisitos and
        cumple_recursos and
        cumple_campos and
        tiene_slot
    )
    
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"{config['icono']} <b>{config['nombre']}</b> - {username_tag}\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"📊 <b>NIVEL ACTUAL:</b> {nivel_actual}\n"
    )
    
    if config["tipo"] == "mina":
        mensaje += f"   ⛏️ Producción: +{abreviar_numero(produccion_actual)}/h\n"
        mensaje += f"   ⚡ Consumo: {config['consumo_energia'] * nivel_actual}/h\n"
    elif tipo == "energia":
        mensaje += f"   ⚡ Generación: +{abreviar_numero(produccion_actual)}/h\n"
    else:
        mensaje += f"   ⚡ Consumo: {config['consumo_energia'] * nivel_actual}/h\n"
    
    mensaje += f"   🌍 Campos: {config['campos']}\n\n"
    
    if nivel_actual < config["max_nivel"]:
        tiempo_str = formatear_tiempo_corto(tiempo_proximo)
        
        mensaje += f"📈 <b>PRÓXIMO NIVEL ({nivel_actual + 1}):</b>\n"
        
        if config["tipo"] == "mina" or tipo == "energia":
            mensaje += f"   ├ Producción: +{abreviar_numero(produccion_proximo)}/h "
            mensaje += f"(+{abreviar_numero(produccion_proximo - produccion_actual)})\n"
        
        mensaje += f"   ├ Tiempo: {tiempo_str}\n"
        mensaje += f"   ├ Costo:\n"
        for recurso, cantidad in costo_proximo.items():
            icono = "🔩" if recurso == "metal" else "💎" if recurso == "cristal" else "🧪"
            disponible = recursos.get(recurso, 0)
            check = "✅" if disponible >= cantidad else "❌"
            mensaje += f"   │  {icono} {recurso.capitalize()}: {abreviar_numero(cantidad)} {check}\n"
        
        mensaje += f"   └ Campos necesarios: {config['campos']}\n\n"
    else:
        mensaje += f"🏆 <b>¡NIVEL MÁXIMO ALCANZADO!</b>\n\n"
    
    mensaje += f"📋 <b>COLA:</b> {len(cola)}/{MAX_COLA_SIZE}\n\n"
    mensaje += f"📖 <b>DESCRIPCIÓN:</b>\n{config['descripcion']}\n\n"
    mensaje += f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    
    keyboard = []
    if nivel_actual < config["max_nivel"]:
        if puede_construir:
            keyboard.append([
                InlineKeyboardButton(
                    f"🏗️ CONSTRUIR NIVEL {nivel_actual + 1}",
                    callback_data=f"construir_{tipo}"
                )
            ])
        else:
            razones = []
            if not cumple_requisitos:
                razones.append("REQUISITOS")
            if not cumple_recursos:
                razones.append("RECURSOS")
            if not cumple_campos:
                razones.append("CAMPOS")
            if not tiene_slot:
                razones.append("COLA LLENA")
            keyboard.append([
                InlineKeyboardButton(f"🔒 {', '.join(razones)}", callback_data="noop")
            ])
    
    keyboard.append([
        InlineKeyboardButton("◀️ VOLVER", callback_data="menu_edificios"),
        InlineKeyboardButton("🏠 MENÚ", callback_data="menu_principal")
    ])
    
    await query.edit_message_text(
        text=mensaje,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

@requiere_login
async def construir_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    tipo = query.data.replace("construir_", "")
    
    exito, mensaje = iniciar_construccion(user_id, tipo)
    
    if exito:
        keyboard = [
            [InlineKeyboardButton("📋 VER COLA", callback_data="menu_edificios")],
            [InlineKeyboardButton("🔄 VER ESTADO", callback_data=f"edificio_{tipo}")],
            [InlineKeyboardButton("🏠 MENÚ PRINCIPAL", callback_data="menu_principal")]
        ]
        await query.edit_message_text(
            text=mensaje,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
    else:
        keyboard = [
            [InlineKeyboardButton("🔄 REINTENTAR", callback_data=f"edificio_{tipo}")],
            [InlineKeyboardButton("◀️ VOLVER", callback_data="menu_edificios")]
        ]
        await query.edit_message_text(
            text=f"❌ <b>ERROR</b>\n\n{mensaje}",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )

@requiere_login
async def ver_cola_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    username_tag = AuthSystem.obtener_username(user_id)
    
    procesar_cola(user_id)
    cola = obtener_cola(user_id)
    
    if not cola:
        mensaje = (
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
            f"📋 <b>COLA DE CONSTRUCCIÓN</b> - {username_tag}\n"
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
            f"📭 No hay construcciones en cola.\n\n"
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
        )
        keyboard = [
            [InlineKeyboardButton("🏗️ CONSTRUIR", callback_data="menu_edificios")],
            [InlineKeyboardButton("◀️ VOLVER", callback_data="menu_principal")]
        ]
    else:
        ahora = datetime.now()
        mensaje = (
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
            f"📋 <b>COLA DE CONSTRUCCIÓN</b> - {username_tag}\n"
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
            f"📊 {len(cola)}/{MAX_COLA_SIZE} construcciones\n\n"
        )
        
        for idx, item in enumerate(cola, 1):
            fin = datetime.strptime(item["fin"], "%Y-%m-%d %H:%M:%S")
            segundos = max(0, (fin - ahora).total_seconds())
            tiempo = formatear_tiempo_corto(int(segundos))
            progreso = item["tiempo_total"] - item["tiempo_restante"]
            barra = barra_progreso_3c(progreso, item["tiempo_total"])
            config = CONSTRUCCIONES.get(item["tipo"], {})
            icono = config.get("icono", "🏗️")
            nombre = config.get("nombre", item["tipo"])
            mensaje += f"{idx}. {icono} <b>{nombre}</b>\n"
            mensaje += f"   ├ Nivel: {item['nivel_actual']} → {item['nivel_objetivo']}\n"
            mensaje += f"   └ {barra} {tiempo}\n\n"
        
        mensaje += f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
        
        keyboard = [
            [InlineKeyboardButton("🔄 ACTUALIZAR", callback_data="edificios_cola")],
            [InlineKeyboardButton("🏗️ CONSTRUIR", callback_data="menu_edificios")],
            [InlineKeyboardButton("◀️ VOLVER", callback_data="menu_principal")]
        ]
        
        cancel_fila = []
        for i in range(1, min(len(cola) + 1, 4)):
            cancel_fila.append(InlineKeyboardButton(f"❌ Cancelar {i}", callback_data=f"edificios_cancelar_{i-1}"))
        if cancel_fila:
            keyboard.insert(0, cancel_fila)
    
    await query.edit_message_text(
        text=mensaje,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

@requiere_login
async def cancelar_construccion_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    posicion = int(query.data.split("_")[2])
    
    exito, mensaje, reembolso = cancelar_construccion(user_id, posicion)
    
    if exito:
        texto = (
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
            f"✅ <b>CONSTRUCCIÓN CANCELADA</b>\n"
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
            f"{mensaje}"
        )
        if reembolso:
            texto += f"\n\n💰 <b>REEMBOLSO:</b>\n"
            for recurso, cantidad in reembolso.items():
                icono = "🔩" if recurso == "metal" else "💎" if recurso == "cristal" else "🧪"
                texto += f"{icono} {recurso.capitalize()}: {abreviar_numero(cantidad)}\n"
        
        texto += f"\n🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
        
        keyboard = [
            [InlineKeyboardButton("📋 VER COLA", callback_data="edificios_cola")],
            [InlineKeyboardButton("🏗️ CONSTRUIR", callback_data="menu_edificios")],
            [InlineKeyboardButton("🏠 MENÚ", callback_data="menu_principal")]
        ]
        await query.edit_message_text(
            text=texto,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
    else:
        await query.edit_message_text(
            text=f"❌ <b>ERROR</b>\n\n{mensaje}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ VOLVER", callback_data="edificios_cola")
            ]]),
            parse_mode="HTML"
        )

# ================= 🕐 TAREA PROGRAMADA =================

async def procesar_colas_background(context: ContextTypes.DEFAULT_TYPE):
    logger.info("🔄 Procesando colas de construcción...")
    colas_data = load_json(COLAS_EDIFICIOS_FILE) or {}
    for user_id_str in colas_data.keys():
        try:
            user_id = int(user_id_str)
            procesar_cola(user_id)
        except Exception as e:
            logger.error(f"❌ Error procesando cola de {user_id_str}: {e}")
    logger.info("✅ Colas de construcción procesadas")

# ================= EXPORTAR =================

__all__ = [
    'menu_edificios_principal',
    'submenu_edificio',
    'construir_handler',
    'ver_cola_handler',
    'cancelar_construccion_handler',
    'procesar_colas_background',
    'CONSTRUCCIONES',
    'obtener_nivel',
    'calcular_produccion',
    'actualizar_campos'
]
