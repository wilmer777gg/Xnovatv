#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#██████╗ ███████╗████████╗██████╗  █████╗ ██╗     ███████╗
#██╔══██╗██╔════╝╚══██╔══╝██╔══██╗██╔══██╗██║     ██╔════╝
#██████╔╝███████╗   ██║   ██████╔╝███████║██║     ███████╗
#██╔══██╗╚════██║   ██║   ██╔══██╗██╔══██║██║     ╚════██║
#██║  ██║███████║   ██║   ██║  ██║██║  ██║███████╗███████║
#╚═╝  ╚═╝╚══════╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚══════╝

#🚀 ASTRO.IO v2.4.0 🚀
#🚀 flota.py - SISTEMA DE CONSTRUCCIÓN DE NAVES CON COLAS EN TIEMPO REAL
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
from edificios import obtener_nivel

logger = logging.getLogger(__name__)

# ================= CONSTANTES =================
DATA_DIR = "data"
RECURSOS_FILE = os.path.join(DATA_DIR, "recursos.json")
FLOTA_USUARIO_FILE = os.path.join(DATA_DIR, "flota_usuario.json")
COLAS_FLOTA_FILE = os.path.join(DATA_DIR, "colas_flota.json")

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

# ================= CONFIGURACIÓN DE NAVES =================
CONFIG_NAVES = {
    # ================= NAVES DE COMBATE =================
    "cazador_ligero": {
        "nombre": "Cazador Ligero",
        "tipo": "combate",
        "icono": "🚀",
        "icono_corto": "🚀",
        "descripcion": "Nave rápida y económica. Ideal para incursiones iniciales.",
        "costo": {"metal": 3000, "cristal": 1000},
        "ataque": 50,
        "escudo": 10,
        "capacidad": 5000,
        "velocidad": 100,
        "tiempo_base": 180,
        "requisitos": {"hangar": 1}
    },
    "cazador_pesado": {
        "nombre": "Cazador Pesado",
        "tipo": "combate",
        "icono": "⚔️",
        "icono_corto": "⚔️",
        "descripcion": "Versión mejorada del cazador ligero.",
        "costo": {"metal": 6000, "cristal": 4000},
        "ataque": 150,
        "escudo": 25,
        "capacidad": 10000,
        "velocidad": 80,
        "tiempo_base": 360,
        "requisitos": {"hangar": 3}
    },
    "crucero": {
        "nombre": "Crucero",
        "tipo": "combate",
        "icono": "⚡",
        "icono_corto": "⚡",
        "descripcion": "Equilibrio perfecto entre velocidad y potencia.",
        "costo": {"metal": 20000, "cristal": 7000, "deuterio": 2000},
        "ataque": 250,
        "escudo": 50,
        "capacidad": 15000,
        "velocidad": 90,
        "tiempo_base": 540,
        "requisitos": {"hangar": 5}
    },
    "nave_batalla": {
        "nombre": "Nave de Batalla",
        "tipo": "combate",
        "icono": "💥",
        "icono_corto": "💥",
        "descripcion": "El núcleo de cualquier flota de combate seria.",
        "costo": {"metal": 45000, "cristal": 15000},
        "ataque": 1000,
        "escudo": 200,
        "capacidad": 75000,
        "velocidad": 70,
        "tiempo_base": 900,
        "requisitos": {"hangar": 7}
    },
    "acorazado": {
        "nombre": "Acorazado",
        "tipo": "combate",
        "icono": "🛡️",
        "icono_corto": "🛡️",
        "descripcion": "Buque de guerra pesado con blindaje reforzado.",
        "costo": {"metal": 60000, "cristal": 20000, "deuterio": 15000},
        "ataque": 700,
        "escudo": 400,
        "capacidad": 100000,
        "velocidad": 50,
        "tiempo_base": 1500,
        "requisitos": {"hangar": 8}
    },
    "destructor": {
        "nombre": "Destructor",
        "tipo": "combate",
        "icono": "💀",
        "icono_corto": "💀",
        "descripcion": "La pesadilla de cualquier defensa.",
        "costo": {"metal": 100000, "cristal": 50000, "deuterio": 30000},
        "ataque": 2000,
        "escudo": 500,
        "capacidad": 150000,
        "velocidad": 40,
        "tiempo_base": 2400,
        "requisitos": {"hangar": 9}
    },
    "estrella_muerte": {
        "nombre": "Estrella de la Muerte",
        "tipo": "combate",
        "icono": "💫",
        "icono_corto": "💫",
        "descripcion": "La nave definitiva. Poder absoluto.",
        "costo": {"metal": 5000000, "cristal": 4000000, "deuterio": 1000000},
        "ataque": 10000,
        "escudo": 5000,
        "capacidad": 1000000,
        "velocidad": 30,
        "tiempo_base": 14400,
        "requisitos": {"hangar": 12}
    },
    # ================= NAVES CIVILES =================
    "nave_carga_pequena": {
        "nombre": "Nave de Carga Pequeña",
        "tipo": "civil",
        "icono": "📦",
        "icono_corto": "📦",
        "descripcion": "Transporte ligero para recursos.",
        "costo": {"metal": 2000, "cristal": 2000},
        "ataque": 5,
        "escudo": 10,
        "capacidad": 5000,
        "velocidad": 120,
        "tiempo_base": 120,
        "requisitos": {"hangar": 2}
    },
    "nave_carga_grande": {
        "nombre": "Nave de Carga Grande",
        "tipo": "civil",
        "icono": "🚛",
        "icono_corto": "🚛",
        "descripcion": "Transporte pesado para grandes volúmenes.",
        "costo": {"metal": 6000, "cristal": 6000, "deuterio": 2000},
        "ataque": 5,
        "escudo": 25,
        "capacidad": 25000,
        "velocidad": 80,
        "tiempo_base": 360,
        "requisitos": {"hangar": 4}
    },
    "reciclador": {
        "nombre": "Reciclador",
        "tipo": "civil",
        "icono": "♻️",
        "icono_corto": "♻️",
        "descripcion": "Recupera escombros de batallas.",
        "costo": {"metal": 10000, "cristal": 6000, "deuterio": 2000},
        "ataque": 1,
        "escudo": 10,
        "capacidad": 20000,
        "velocidad": 20,
        "tiempo_base": 600,
        "requisitos": {"hangar": 4}
    },
    "sonda_espionaje": {
        "nombre": "Sonda de Espionaje",
        "tipo": "civil",
        "icono": "🛸",
        "icono_corto": "🛸",
        "descripcion": "Nave no tripulada para reconocimiento.",
        "costo": {"metal": 0, "cristal": 1000},
        "ataque": 0,
        "escudo": 0,
        "capacidad": 0,
        "velocidad": 200,
        "tiempo_base": 30,
        "requisitos": {"hangar": 3}
    },
    "satelite_solar": {
        "nombre": "Satélite Solar",
        "tipo": "civil",
        "icono": "☀️",
        "icono_corto": "☀️",
        "descripcion": "Genera energía en órbita.",
        "costo": {"metal": 0, "cristal": 2000},
        "ataque": 1,
        "escudo": 1,
        "capacidad": 0,
        "velocidad": 0,
        "produccion_energia": 50,
        "tiempo_base": 60,
        "requisitos": {"hangar": 2}
    }
}

# ================= FUNCIONES DE LECTURA =================

def obtener_flota(user_id: int) -> dict:
    user_id_str = str(user_id)
    data = load_json(FLOTA_USUARIO_FILE) or {}
    return data.get(user_id_str, {})

def guardar_flota(user_id: int, flota: dict) -> bool:
    user_id_str = str(user_id)
    data = load_json(FLOTA_USUARIO_FILE) or {}
    data[user_id_str] = flota
    return save_json(FLOTA_USUARIO_FILE, data)

def obtener_recursos(user_id: int) -> dict:
    user_id_str = str(user_id)
    data = load_json(RECURSOS_FILE) or {}
    return data.get(user_id_str, {})

def guardar_recursos(user_id: int, recursos: dict) -> bool:
    user_id_str = str(user_id)
    data = load_json(RECURSOS_FILE) or {}
    data[user_id_str] = recursos
    return save_json(RECURSOS_FILE, data)

def verificar_requisitos(user_id: int, tipo_nave: str) -> tuple:
    if tipo_nave not in CONFIG_NAVES:
        return False, "❌ Nave no válida"
    
    config = CONFIG_NAVES[tipo_nave]
    nivel_hangar = obtener_nivel(user_id, "hangar")
    nivel_requerido = config["requisitos"]["hangar"]
    
    if nivel_hangar < nivel_requerido:
        return False, f"❌ Requiere Hangar nivel {nivel_requerido} (tienes: {nivel_hangar})"
    
    return True, "✅ Requisitos cumplidos"

def verificar_recursos_suficientes(user_id: int, tipo_nave: str, cantidad: int) -> tuple:
    recursos = obtener_recursos(user_id)
    config = CONFIG_NAVES[tipo_nave]
    
    faltantes = []
    for recurso, costo_unitario in config["costo"].items():
        if costo_unitario > 0:
            necesario = costo_unitario * cantidad
            disponible = recursos.get(recurso, 0)
            if disponible < necesario:
                icono = "🔩" if recurso == "metal" else "💎" if recurso == "cristal" else "🧪"
                faltantes.append(f"{icono} {recurso.capitalize()}: {abreviar_numero(disponible)}/{abreviar_numero(necesario)}")
    
    if faltantes:
        return False, "❌ Recursos insuficientes:\n" + "\n".join(faltantes)
    
    return True, "✅ Recursos suficientes"

def calcular_tiempo_construccion(user_id: int, tipo_nave: str, cantidad: int = 1) -> int:
    config = CONFIG_NAVES[tipo_nave]
    tiempo_base = config["tiempo_base"]
    nivel_hangar = obtener_nivel(user_id, "hangar")
    
    # Reducción por nivel de hangar (5% por nivel)
    factor = 1 + (nivel_hangar * 0.05)
    tiempo_unitario = int(tiempo_base / factor)
    
    return max(10, tiempo_unitario) * cantidad

# ================= 📋 FUNCIONES DE COLA =================

def obtener_cola(user_id: int) -> list:
    user_id_str = str(user_id)
    data = load_json(COLAS_FLOTA_FILE) or {}
    return data.get(user_id_str, [])

def guardar_cola(user_id: int, cola: list) -> bool:
    user_id_str = str(user_id)
    data = load_json(COLAS_FLOTA_FILE) or {}
    data[user_id_str] = cola
    return save_json(COLAS_FLOTA_FILE, data)

def agregar_a_cola(user_id: int, tipo_nave: str, cantidad: int, costo: dict, tiempo: int) -> tuple:
    cola = obtener_cola(user_id)
    
    if len(cola) >= MAX_COLA_SIZE:
        return False, f"❌ Límite de {MAX_COLA_SIZE} construcciones alcanzado"
    
    ahora = datetime.now()
    fin = ahora + timedelta(seconds=tiempo)
    
    nueva = {
        "tipo": "flota",
        "nave": tipo_nave,
        "cantidad": cantidad,
        "inicio": ahora.strftime("%Y-%m-%d %H:%M:%S"),
        "fin": fin.strftime("%Y-%m-%d %H:%M:%S"),
        "tiempo_total": tiempo,
        "tiempo_restante": tiempo,
        "progreso": 0,
        "costo": costo
    }
    
    cola.append(nueva)
    guardar_cola(user_id, cola)
    return True, f"✅ Construcción añadida a la cola"

def procesar_cola(user_id: int) -> list:
    cola = obtener_cola(user_id)
    if not cola:
        return []
    
    ahora = datetime.now()
    completadas = []
    cola_restante = []
    
    for item in cola:
        try:
            if item.get("tipo") != "flota":
                cola_restante.append(item)
                continue
            
            fin = datetime.strptime(item["fin"], "%Y-%m-%d %H:%M:%S")
            
            if ahora >= fin:
                tipo_nave = item["nave"]
                cantidad = item["cantidad"]
                
                flota = obtener_flota(user_id)
                flota[tipo_nave] = flota.get(tipo_nave, 0) + cantidad
                guardar_flota(user_id, flota)
                
                completadas.append(item)
                logger.info(f"✅ Construcción completada: {cantidad}x {tipo_nave} para {AuthSystem.obtener_username(user_id)}")
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
    
    if "costo" in item:
        for recurso, cantidad in item["costo"].items():
            reembolso[recurso] = int(cantidad * 0.5)
    
    if reembolso:
        recursos = obtener_recursos(user_id)
        for recurso, cantidad in reembolso.items():
            recursos[recurso] = recursos.get(recurso, 0) + cantidad
        guardar_recursos(user_id, recursos)
    
    guardar_cola(user_id, cola)
    return True, f"✅ Construcción cancelada. 50% reembolsado.", reembolso

# ================= 🚀 INICIAR CONSTRUCCIÓN =================

def construir_naves(user_id: int, tipo_nave: str, cantidad: int = 1) -> tuple:
    if tipo_nave not in CONFIG_NAVES:
        return False, "❌ Nave no válida"
    
    if cantidad <= 0 or cantidad > 10000:
        return False, "❌ Cantidad debe ser entre 1 y 10.000"
    
    config = CONFIG_NAVES[tipo_nave]
    
    # Verificar requisitos
    cumple_req, msg_req = verificar_requisitos(user_id, tipo_nave)
    if not cumple_req:
        return False, msg_req
    
    # Verificar recursos
    cumple_rec, msg_rec = verificar_recursos_suficientes(user_id, tipo_nave, cantidad)
    if not cumple_rec:
        return False, msg_rec
    
    # Verificar cola
    cola = obtener_cola(user_id)
    if len(cola) >= MAX_COLA_SIZE:
        return False, f"❌ Límite de {MAX_COLA_SIZE} construcciones alcanzado"
    
    # Calcular costo y tiempo
    costo_total = {}
    for recurso, valor in config["costo"].items():
        if valor > 0:
            costo_total[recurso] = valor * cantidad
    
    tiempo = calcular_tiempo_construccion(user_id, tipo_nave, cantidad)
    
    # Descontar recursos
    recursos = obtener_recursos(user_id)
    for recurso, cantidad_req in costo_total.items():
        recursos[recurso] = recursos.get(recurso, 0) - cantidad_req
    guardar_recursos(user_id, recursos)
    
    # Agregar a cola
    exito, msg_cola = agregar_a_cola(user_id, tipo_nave, cantidad, costo_total, tiempo)
    if not exito:
        # Reembolsar si falla
        for recurso, cantidad_req in costo_total.items():
            recursos[recurso] = recursos.get(recurso, 0) + cantidad_req
        guardar_recursos(user_id, recursos)
        return False, msg_cola
    
    username = AuthSystem.obtener_username(user_id)
    logger.info(f"🚀 {username} inició construcción de {cantidad}x {config['nombre']} - {formatear_tiempo_corto(tiempo)}")
    
    tiempo_str = formatear_tiempo_corto(tiempo)
    
    cola = obtener_cola(user_id)
    
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"🚀 <b>CONSTRUCCIÓN INICIADA</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"{config['icono']} {config['nombre']}\n"
        f"├ Cantidad: {cantidad}\n"
        f"├ Tiempo: {tiempo_str}\n"
        f"└ Posición en cola: {len(cola)}\n\n"
        f"💰 Recursos descontados correctamente.\n\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    )
    
    return True, mensaje

# ================= 🚀 HANDLERS =================

@requiere_login
async def menu_flota_principal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        logger.error("❌ menu_flota_principal sin callback_query")
        return
    
    await query.answer()
    user_id = query.from_user.id
    
    procesar_cola(user_id)
    
    recursos = obtener_recursos(user_id)
    flota = obtener_flota(user_id)
    cola = obtener_cola(user_id)
    username_tag = AuthSystem.obtener_username(user_id)
    
    total_naves = sum(flota.values())
    
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"🚀 <b>COMANDO DE FLOTA</b> - {username_tag}\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"💰 <b>RECURSOS:</b>\n"
        f"🔩 Metal: {abreviar_numero(recursos.get('metal', 0))}\n"
        f"💎 Cristal: {abreviar_numero(recursos.get('cristal', 0))}\n"
        f"🧪 Deuterio: {abreviar_numero(recursos.get('deuterio', 0))}\n\n"
        f"📋 <b>COLA:</b> {len(cola)}/{MAX_COLA_SIZE}\n"
        f"📊 <b>FLOTA EN BASE:</b> {abreviar_numero(total_naves)} naves\n\n"
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
            config = CONFIG_NAVES.get(item["nave"], {})
            icono = config.get("icono", "🚀")
            nombre = config.get("nombre", item["nave"])
            cantidad = item["cantidad"]
            mensaje += f"   {idx}. {icono} {nombre} x{cantidad}\n"
            mensaje += f"      {barra} {tiempo}\n"
        mensaje += "\n"
    
    naves_activas = {k: v for k, v in flota.items() if v > 0}
    if naves_activas:
        mensaje += f"<b>TUS NAVES:</b>\n"
        for nave_id, cantidad in list(naves_activas.items())[:8]:
            config = CONFIG_NAVES.get(nave_id, {})
            icono = config.get("icono", "🚀")
            nombre = config.get("nombre", nave_id)
            mensaje += f"   {icono} {nombre}: {abreviar_numero(cantidad)}\n"
        if len(naves_activas) > 8:
            mensaje += f"   ... y {len(naves_activas) - 8} tipos más\n"
        mensaje += "\n"
    
    mensaje += f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
    mensaje += f"<i>Selecciona una nave:</i>"
    
    keyboard = [
        [InlineKeyboardButton("⚔️ NAVES DE COMBATE", callback_data="noop")],
        [
            InlineKeyboardButton("🚀 Cazador Ligero", callback_data="nave_cazador_ligero"),
            InlineKeyboardButton("⚔️ Cazador Pesado", callback_data="nave_cazador_pesado")
        ],
        [
            InlineKeyboardButton("⚡ Crucero", callback_data="nave_crucero"),
            InlineKeyboardButton("💥 Nave Batalla", callback_data="nave_nave_batalla")
        ],
        [
            InlineKeyboardButton("🛡️ Acorazado", callback_data="nave_acorazado"),
            InlineKeyboardButton("💀 Destructor", callback_data="nave_destructor")
        ],
        [InlineKeyboardButton("💫 Estrella Muerte", callback_data="nave_estrella_muerte")],
        [InlineKeyboardButton("📦 NAVES CIVILES", callback_data="noop")],
        [
            InlineKeyboardButton("📦 Carga Pequeña", callback_data="nave_nave_carga_pequena"),
            InlineKeyboardButton("🚛 Carga Grande", callback_data="nave_nave_carga_grande")
        ],
        [
            InlineKeyboardButton("♻️ Reciclador", callback_data="nave_reciclador"),
            InlineKeyboardButton("🛸 Sonda", callback_data="nave_sonda_espionaje")
        ],
        [InlineKeyboardButton("☀️ Satélite Solar", callback_data="nave_satelite_solar")],
        [InlineKeyboardButton("📋 VER COLA", callback_data="flota_cola")],
        [InlineKeyboardButton("◀️ VOLVER", callback_data="menu_principal")]
    ]
    
    if cola:
        cancel_fila = []
        for i in range(1, min(len(cola) + 1, 4)):
            cancel_fila.append(InlineKeyboardButton(f"❌ Cancelar {i}", callback_data=f"flota_cancelar_{i-1}"))
        keyboard.insert(-2, cancel_fila)
    
    await query.edit_message_text(
        text=mensaje,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

@requiere_login
async def submenu_nave(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    tipo_nave = query.data.replace("nave_", "")
    
    if tipo_nave not in CONFIG_NAVES:
        await query.edit_message_text("❌ Nave no encontrada")
        return
    
    config = CONFIG_NAVES[tipo_nave]
    
    recursos = obtener_recursos(user_id)
    flota = obtener_flota(user_id)
    cola = obtener_cola(user_id)
    cantidad_actual = flota.get(tipo_nave, 0)
    nivel_hangar = obtener_nivel(user_id, "hangar")
    username_tag = AuthSystem.obtener_username(user_id)
    
    tiempo_unitario = calcular_tiempo_construccion(user_id, tipo_nave, 1)
    tiempo_10 = tiempo_unitario * 10
    
    cumple_requisitos, msg_req = verificar_requisitos(user_id, tipo_nave)
    puede_1, _ = verificar_recursos_suficientes(user_id, tipo_nave, 1) if cumple_requisitos else (False, "")
    tiene_slot = len(cola) < MAX_COLA_SIZE
    
    tiempo_str = formatear_tiempo_corto(tiempo_unitario)
    tiempo_10_str = formatear_tiempo_corto(tiempo_10)
    
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"{config['icono']} <b>{config['nombre']}</b> - {username_tag}\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"💰 <b>RECURSOS:</b>\n"
        f"🔩 Metal: {abreviar_numero(recursos.get('metal', 0))}\n"
        f"💎 Cristal: {abreviar_numero(recursos.get('cristal', 0))}\n"
        f"🧪 Deuterio: {abreviar_numero(recursos.get('deuterio', 0))}\n\n"
        f"📊 <b>CANTIDAD ACTUAL:</b> {abreviar_numero(cantidad_actual)}\n"
        f"📋 <b>COLA:</b> {len(cola)}/{MAX_COLA_SIZE}\n\n"
        f"⚙️ <b>ESPECIFICACIONES:</b>\n"
        f"├ ⚔️ Ataque: {config['ataque']}\n"
        f"├ 🛡️ Escudo: {config['escudo']}\n"
        f"├ 📦 Capacidad: {abreviar_numero(config['capacidad'])}\n"
        f"├ ⚡ Velocidad: {config['velocidad']}\n"
        f"└ 🏭 Requiere Hangar: Nivel {config['requisitos']['hangar']} (tienes: {nivel_hangar})\n\n"
        f"💰 <b>COSTO POR UNIDAD:</b>\n"
    )
    
    for recurso, costo in config["costo"].items():
        if costo > 0:
            icono = "🔩" if recurso == "metal" else "💎" if recurso == "cristal" else "🧪"
            mensaje += f"   {icono} {recurso.capitalize()}: {abreviar_numero(costo)}\n"
    
    mensaje += f"\n⏱️ <b>TIEMPO:</b>\n"
    mensaje += f"   ├ 1 unidad: {tiempo_str}\n"
    mensaje += f"   └ 10 unidades: {tiempo_10_str}\n\n"
    
    mensaje += f"📖 <b>DESCRIPCIÓN:</b>\n{config['descripcion']}\n"
    mensaje += f"\n🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    
    if not cumple_requisitos:
        mensaje += f"\n\n❌ {msg_req}"
    elif not tiene_slot:
        mensaje += f"\n\n❌ Cola llena ({len(cola)}/{MAX_COLA_SIZE})"
    
    keyboard = []
    
    if cumple_requisitos and tiene_slot:
        fila_botones = []
        
        if puede_1:
            fila_botones.append(InlineKeyboardButton("1️⃣ 1", callback_data=f"confirmar_{tipo_nave}_1"))
        else:
            fila_botones.append(InlineKeyboardButton("1️⃣ 🔒", callback_data="noop"))
        
        fila_botones.append(InlineKeyboardButton("5️⃣ 5", callback_data=f"confirmar_{tipo_nave}_5"))
        fila_botones.append(InlineKeyboardButton("🔟 10", callback_data=f"confirmar_{tipo_nave}_10"))
        keyboard.append(fila_botones)
        
        keyboard.append([
            InlineKeyboardButton("✏️ CANTIDAD PERSONALIZADA", callback_data=f"personalizar_{tipo_nave}")
        ])
    else:
        razones = []
        if not cumple_requisitos:
            razones.append("REQUISITOS")
        if not tiene_slot:
            razones.append("COLA LLENA")
        keyboard.append([
            InlineKeyboardButton(f"🔒 {', '.join(razones)}", callback_data="noop")
        ])
    
    keyboard.append([
        InlineKeyboardButton("◀️ VOLVER", callback_data="menu_flota"),
        InlineKeyboardButton("🏠 MENÚ", callback_data="menu_principal")
    ])
    
    await query.edit_message_text(
        text=mensaje,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

@requiere_login
async def confirmar_construccion_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    partes = query.data.split("_")
    tipo_nave = "_".join(partes[1:-1])
    cantidad = int(partes[-1])
    
    if tipo_nave not in CONFIG_NAVES:
        await query.edit_message_text("❌ Nave no encontrada")
        return
    
    config = CONFIG_NAVES[tipo_nave]
    cola = obtener_cola(user_id)
    
    cumple_req, msg_req = verificar_requisitos(user_id, tipo_nave)
    if not cumple_req:
        keyboard = [[InlineKeyboardButton("◀️ VOLVER", callback_data=f"nave_{tipo_nave}")]]
        await query.edit_message_text(
            text=f"❌ {msg_req}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    if len(cola) >= MAX_COLA_SIZE:
        keyboard = [[InlineKeyboardButton("◀️ VOLVER", callback_data=f"nave_{tipo_nave}")]]
        await query.edit_message_text(
            text=f"❌ Cola llena ({len(cola)}/{MAX_COLA_SIZE})",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    cumple_rec, msg_rec = verificar_recursos_suficientes(user_id, tipo_nave, cantidad)
    tiempo = calcular_tiempo_construccion(user_id, tipo_nave, cantidad)
    
    costo_total = {}
    for recurso, valor in config["costo"].items():
        if valor > 0:
            costo_total[recurso] = valor * cantidad
    
    tiempo_str = formatear_tiempo_corto(tiempo)
    
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"🔨 <b>CONFIRMAR CONSTRUCCIÓN</b> - {AuthSystem.obtener_username(user_id)}\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"{config['icono']} {config['nombre']}\n"
        f"Cantidad: <b>{cantidad}</b>\n\n"
        f"💰 <b>COSTO TOTAL:</b>\n"
    )
    
    for recurso, total in costo_total.items():
        icono = "🔩" if recurso == "metal" else "💎" if recurso == "cristal" else "🧪"
        mensaje += f"   {icono} {recurso.capitalize()}: {abreviar_numero(total)}\n"
    
    mensaje += f"\n⏱️ <b>TIEMPO TOTAL:</b> {tiempo_str}\n"
    mensaje += f"📋 <b>COLA:</b> {len(cola)}/{MAX_COLA_SIZE}\n\n"
    
    if not cumple_rec:
        mensaje += f"❌ {msg_rec}\n"
    
    mensaje += f"\n🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    
    keyboard = []
    if cumple_rec:
        keyboard.append([
            InlineKeyboardButton(
                f"✅ CONFIRMAR {cantidad}",
                callback_data=f"comprar_{tipo_nave}_{cantidad}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton("◀️ CAMBIAR CANTIDAD", callback_data=f"nave_{tipo_nave}")
    ])
    
    await query.edit_message_text(
        text=mensaje,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

@requiere_login
async def comprar_nave_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    partes = query.data.split("_")
    tipo_nave = "_".join(partes[1:-1])
    cantidad = int(partes[-1])
    
    exito, mensaje = construir_naves(user_id, tipo_nave, cantidad)
    
    if exito:
        keyboard = [
            [InlineKeyboardButton("📋 VER COLA", callback_data="menu_flota")],
            [InlineKeyboardButton(f"➕ CONSTRUIR MÁS", callback_data=f"nave_{tipo_nave}")],
            [InlineKeyboardButton("🏠 MENÚ PRINCIPAL", callback_data="menu_principal")]
        ]
        await query.edit_message_text(
            text=mensaje,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
    else:
        keyboard = [
            [InlineKeyboardButton("🔄 REINTENTAR", callback_data=f"nave_{tipo_nave}")],
            [InlineKeyboardButton("🚀 VOLVER A FLOTA", callback_data="menu_flota")]
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
            [InlineKeyboardButton("🚀 CONSTRUIR", callback_data="menu_flota")],
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
            config = CONFIG_NAVES.get(item["nave"], {})
            icono = config.get("icono", "🚀")
            nombre = config.get("nombre", item["nave"])
            cantidad = item["cantidad"]
            mensaje += f"{idx}. {icono} <b>{nombre}</b> x{cantidad}\n"
            mensaje += f"   └ {barra} {tiempo}\n\n"
        
        mensaje += f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
        
        keyboard = [
            [InlineKeyboardButton("🔄 ACTUALIZAR", callback_data="flota_cola")],
            [InlineKeyboardButton("🚀 CONSTRUIR", callback_data="menu_flota")],
            [InlineKeyboardButton("◀️ VOLVER", callback_data="menu_principal")]
        ]
        
        cancel_fila = []
        for i in range(1, min(len(cola) + 1, 4)):
            cancel_fila.append(InlineKeyboardButton(f"❌ Cancelar {i}", callback_data=f"flota_cancelar_{i-1}"))
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
            [InlineKeyboardButton("📋 VER COLA", callback_data="flota_cola")],
            [InlineKeyboardButton("🚀 CONSTRUIR", callback_data="menu_flota")],
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
                InlineKeyboardButton("◀️ VOLVER", callback_data="flota_cola")
            ]]),
            parse_mode="HTML"
        )

@requiere_login
async def personalizar_cantidad_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    tipo_nave = query.data.replace("personalizar_", "")
    
    context.user_data['esperando_cantidad'] = tipo_nave
    
    config = CONFIG_NAVES[tipo_nave]
    
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"✏️ <b>CANTIDAD PERSONALIZADA</b> - {AuthSystem.obtener_username(user_id)}\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"{config['icono']} {config['nombre']}\n\n"
        f"💰 Costo por unidad:\n"
    )
    
    for recurso, costo in config["costo"].items():
        if costo > 0:
            icono = "🔩" if recurso == "metal" else "💎" if recurso == "cristal" else "🧪"
            mensaje += f"   {icono} {recurso.capitalize()}: {abreviar_numero(costo)}\n"
    
    mensaje += f"\n<b>Escribe la cantidad (1-10.000):</b>\n\n"
    mensaje += f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    
    keyboard = [[InlineKeyboardButton("◀️ CANCELAR", callback_data=f"nave_{tipo_nave}")]]
    
    await query.edit_message_text(
        text=mensaje,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

@requiere_login
async def recibir_cantidad_personalizada(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if 'esperando_cantidad' not in context.user_data:
        return
    
    tipo_nave = context.user_data['esperando_cantidad']
    texto = update.message.text.strip()
    
    del context.user_data['esperando_cantidad']
    
    try:
        cantidad = int(texto)
    except ValueError:
        await update.message.reply_text("❌ Por favor, ingresa un número válido.")
        return
    
    if cantidad <= 0 or cantidad > 10000:
        await update.message.reply_text("❌ La cantidad debe ser entre 1 y 10.000.")
        return
    
    cumple_req, msg_req = verificar_requisitos(user_id, tipo_nave)
    if not cumple_req:
        await update.message.reply_text(f"❌ {msg_req}")
        return
    
    cola = obtener_cola(user_id)
    if len(cola) >= MAX_COLA_SIZE:
        await update.message.reply_text(f"❌ Cola llena ({len(cola)}/{MAX_COLA_SIZE})")
        return
    
    cumple_rec, msg_rec = verificar_recursos_suficientes(user_id, tipo_nave, cantidad)
    if not cumple_rec:
        await update.message.reply_text(f"❌ {msg_rec}")
        return
    
    exito, mensaje = construir_naves(user_id, tipo_nave, cantidad)
    
    if exito:
        await update.message.reply_text(mensaje, parse_mode="HTML")
    else:
        await update.message.reply_text(f"❌ {mensaje}")

# ================= 🕐 TAREA PROGRAMADA =================

async def procesar_colas_background(context: ContextTypes.DEFAULT_TYPE):
    logger.info("🔄 Procesando colas de flota...")
    colas_data = load_json(COLAS_FLOTA_FILE) or {}
    for user_id_str in colas_data.keys():
        try:
            user_id = int(user_id_str)
            procesar_cola(user_id)
        except Exception as e:
            logger.error(f"❌ Error procesando cola de {user_id_str}: {e}")
    logger.info("✅ Colas de flota procesadas")

# ================= EXPORTAR =================

__all__ = [
    'menu_flota_principal',
    'submenu_nave',
    'confirmar_construccion_handler',
    'comprar_nave_handler',
    'ver_cola_handler',
    'cancelar_construccion_handler',
    'personalizar_cantidad_handler',
    'recibir_cantidad_personalizada',
    'procesar_colas_background',
    'CONFIG_NAVES',
    'obtener_flota'
]
