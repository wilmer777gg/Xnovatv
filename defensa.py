#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#██████╗ ███████╗████████╗██████╗  █████╗ ██╗     ███████╗
#██╔══██╗██╔════╝╚══██╔══╝██╔══██╗██╔══██╗██║     ██╔════╝
#██████╔╝███████╗   ██║   ██████╔╝███████║██║     ███████╗
#██╔══██╗╚════██║   ██║   ██╔══██╗██╔══██║██║     ╚════██║
#██║  ██║███████║   ██║   ██║  ██║██║  ██║███████╗███████║
#╚═╝  ╚═╝╚══════╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚══════╝

#🚀 ASTRO.IO v2.4.0 🚀
#🛡️ defensa.py - SISTEMA DE CONSTRUCCIÓN DE DEFENSAS CON COLAS EN TIEMPO REAL
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
DEFENSA_USUARIO_FILE = os.path.join(DATA_DIR, "defensa_usuario.json")
COLAS_DEFENSA_FILE = os.path.join(DATA_DIR, "colas_defensa.json")

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

# ================= CONFIGURACIÓN DE DEFENSAS =================
CONFIG_DEFENSAS = {
    # ================= DEFENSAS LIGERAS =================
    "lanza_misiles": {
        "nombre": "Lanzador de Misiles",
        "tipo": "ligera",
        "icono": "🚀",
        "icono_corto": "🚀",
        "descripcion": "Defensa básica y económica. Ideal para protección inicial.",
        "costo": {"metal": 2000, "cristal": 0},
        "ataque": 80,
        "escudo": 20,
        "tiempo_base": 30,
        "requisitos": {"hangar": 1}
    },
    "laser_ligero": {
        "nombre": "Láser Ligero",
        "tipo": "ligera",
        "icono": "🔫",
        "icono_corto": "🔫",
        "descripcion": "Cañón láser de baja potencia. Efectivo contra naves ligeras.",
        "costo": {"metal": 1500, "cristal": 500},
        "ataque": 100,
        "escudo": 25,
        "tiempo_base": 45,
        "requisitos": {"hangar": 2}
    },
    "laser_pesado": {
        "nombre": "Láser Pesado",
        "tipo": "ligera",
        "icono": "🔫🔫",
        "icono_corto": "🔫🔫",
        "descripcion": "Cañón láser mejorado. Bueno contra naves medianas.",
        "costo": {"metal": 6000, "cristal": 2000},
        "ataque": 250,
        "escudo": 100,
        "tiempo_base": 90,
        "requisitos": {"hangar": 4}
    },
    # ================= DEFENSAS MEDIAS =================
    "canion_ionico": {
        "nombre": "Cañón Iónico",
        "tipo": "media",
        "icono": "⚡",
        "icono_corto": "⚡",
        "descripcion": "Ataque de iones. Muy efectivo contra escudos.",
        "costo": {"metal": 2000, "cristal": 6000},
        "ataque": 150,
        "escudo": 500,
        "tiempo_base": 180,
        "requisitos": {"hangar": 4}
    },
    "canion_gauss": {
        "nombre": "Cañón Gauss",
        "tipo": "media",
        "icono": "🧲",
        "icono_corto": "🧲",
        "descripcion": "Cañón electromagnético. Alta penetración de blindaje.",
        "costo": {"metal": 20000, "cristal": 15000, "deuterio": 2000},
        "ataque": 1100,
        "escudo": 200,
        "tiempo_base": 300,
        "requisitos": {"hangar": 6}
    },
    # ================= DEFENSAS PESADAS =================
    "canion_plasma": {
        "nombre": "Cañón de Plasma",
        "tipo": "pesada",
        "icono": "☢️",
        "icono_corto": "☢️",
        "descripcion": "Defensa pesada de plasma. Devastador contra flotas grandes.",
        "costo": {"metal": 50000, "cristal": 50000, "deuterio": 30000},
        "ataque": 3000,
        "escudo": 300,
        "tiempo_base": 600,
        "requisitos": {"hangar": 8}
    },
    "escudo_pequeno": {
        "nombre": "Cúpula Escudo Pequeña",
        "tipo": "escudo",
        "icono": "🛡️",
        "icono_corto": "🛡️",
        "descripcion": "Genera un campo de fuerza protector. Reduce daño entrante.",
        "costo": {"metal": 10000, "cristal": 10000},
        "ataque": 1,
        "escudo": 2000,
        "tiempo_base": 300,
        "requisitos": {"hangar": 3}
    },
    "escudo_grande": {
        "nombre": "Cúpula Escudo Grande",
        "tipo": "escudo",
        "icono": "🛡️🛡️",
        "icono_corto": "🛡️🛡️",
        "descripcion": "Escudo planetario avanzado. Protección superior.",
        "costo": {"metal": 50000, "cristal": 50000},
        "ataque": 1,
        "escudo": 10000,
        "tiempo_base": 900,
        "requisitos": {"hangar": 6, "escudo_pequeno": 1}
    },
    # ================= MISILES =================
    "misil_interceptor": {
        "nombre": "Misil Interceptor",
        "tipo": "misil",
        "icono": "🎯",
        "icono_corto": "🎯",
        "descripcion": "Destruye misiles enemigos. Defensa anti-balística.",
        "costo": {"metal": 8000, "deuterio": 2000},
        "ataque": 1,
        "escudo": 1,
        "tiempo_base": 30,
        "requisitos": {"hangar": 2}
    },
    "misil_interplanetario": {
        "nombre": "Misil Interplanetario",
        "tipo": "misil",
        "icono": "💥",
        "icono_corto": "💥",
        "descripcion": "Ataca otros planetas. Puede destruir defensas enemigas.",
        "costo": {"metal": 12500, "cristal": 2500, "deuterio": 10000},
        "ataque": 12000,
        "escudo": 1,
        "tiempo_base": 600,
        "requisitos": {"hangar": 4}
    }
}

# ================= FUNCIONES DE LECTURA =================

def obtener_defensas(user_id: int) -> dict:
    user_id_str = str(user_id)
    data = load_json(DEFENSA_USUARIO_FILE) or {}
    return data.get(user_id_str, {})

def guardar_defensas(user_id: int, defensas: dict) -> bool:
    user_id_str = str(user_id)
    data = load_json(DEFENSA_USUARIO_FILE) or {}
    data[user_id_str] = defensas
    return save_json(DEFENSA_USUARIO_FILE, data)

def obtener_recursos(user_id: int) -> dict:
    user_id_str = str(user_id)
    data = load_json(RECURSOS_FILE) or {}
    return data.get(user_id_str, {})

def guardar_recursos(user_id: int, recursos: dict) -> bool:
    user_id_str = str(user_id)
    data = load_json(RECURSOS_FILE) or {}
    data[user_id_str] = recursos
    return save_json(RECURSOS_FILE, data)

def obtener_cantidad_defensa(user_id: int, tipo_defensa: str) -> int:
    defensas = obtener_defensas(user_id)
    return defensas.get(tipo_defensa, 0)

def verificar_requisitos(user_id: int, tipo_defensa: str) -> tuple:
    if tipo_defensa not in CONFIG_DEFENSAS:
        return False, "❌ Defensa no válida"
    
    config = CONFIG_DEFENSAS[tipo_defensa]
    errores = []
    
    if "hangar" in config["requisitos"]:
        nivel_hangar = obtener_nivel(user_id, "hangar")
        nivel_requerido = config["requisitos"]["hangar"]
        if nivel_hangar < nivel_requerido:
            errores.append(f"• Hangar: Nivel {nivel_requerido} (tienes: {nivel_hangar})")
    
    for req_def, cantidad_req in config["requisitos"].items():
        if req_def != "hangar":
            cantidad_actual = obtener_cantidad_defensa(user_id, req_def)
            if cantidad_actual < cantidad_req:
                nombre_def = CONFIG_DEFENSAS.get(req_def, {}).get("nombre", req_def)
                errores.append(f"• {nombre_def}: {cantidad_req} unidad(es) (tienes: {cantidad_actual})")
    
    if errores:
        return False, "❌ Requisitos no cumplidos:\n" + "\n".join(errores)
    
    return True, "✅ Requisitos cumplidos"

def verificar_recursos_suficientes(user_id: int, tipo_defensa: str, cantidad: int) -> tuple:
    recursos = obtener_recursos(user_id)
    config = CONFIG_DEFENSAS[tipo_defensa]
    
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

def calcular_tiempo_construccion(user_id: int, tipo_defensa: str, cantidad: int = 1) -> int:
    config = CONFIG_DEFENSAS[tipo_defensa]
    tiempo_base = config["tiempo_base"]
    nivel_hangar = obtener_nivel(user_id, "hangar")
    
    # Reducción por nivel de hangar (5% por nivel)
    factor = 1 + (nivel_hangar * 0.05)
    tiempo_unitario = int(tiempo_base / factor)
    
    return max(5, tiempo_unitario) * cantidad

# ================= 📋 FUNCIONES DE COLA =================

def obtener_cola(user_id: int) -> list:
    user_id_str = str(user_id)
    data = load_json(COLAS_DEFENSA_FILE) or {}
    return data.get(user_id_str, [])

def guardar_cola(user_id: int, cola: list) -> bool:
    user_id_str = str(user_id)
    data = load_json(COLAS_DEFENSA_FILE) or {}
    data[user_id_str] = cola
    return save_json(COLAS_DEFENSA_FILE, data)

def agregar_a_cola(user_id: int, tipo_defensa: str, cantidad: int, costo: dict, tiempo: int) -> tuple:
    cola = obtener_cola(user_id)
    
    if len(cola) >= MAX_COLA_SIZE:
        return False, f"❌ Límite de {MAX_COLA_SIZE} construcciones alcanzado"
    
    ahora = datetime.now()
    fin = ahora + timedelta(seconds=tiempo)
    
    nueva = {
        "tipo": "defensa",
        "defensa": tipo_defensa,
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
            if item.get("tipo") != "defensa":
                cola_restante.append(item)
                continue
            
            fin = datetime.strptime(item["fin"], "%Y-%m-%d %H:%M:%S")
            
            if ahora >= fin:
                tipo_defensa = item["defensa"]
                cantidad = item["cantidad"]
                
                defensas = obtener_defensas(user_id)
                defensas[tipo_defensa] = defensas.get(tipo_defensa, 0) + cantidad
                guardar_defensas(user_id, defensas)
                
                completadas.append(item)
                logger.info(f"✅ Construcción completada: {cantidad}x {tipo_defensa} para {AuthSystem.obtener_username(user_id)}")
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

# ================= 🛡️ INICIAR CONSTRUCCIÓN =================

def construir_defensas(user_id: int, tipo_defensa: str, cantidad: int = 1) -> tuple:
    if tipo_defensa not in CONFIG_DEFENSAS:
        return False, "❌ Defensa no válida"
    
    if cantidad <= 0 or cantidad > 10000:
        return False, "❌ Cantidad debe ser entre 1 y 10.000"
    
    config = CONFIG_DEFENSAS[tipo_defensa]
    
    # Verificar requisitos
    cumple_req, msg_req = verificar_requisitos(user_id, tipo_defensa)
    if not cumple_req:
        return False, msg_req
    
    # Verificar recursos
    cumple_rec, msg_rec = verificar_recursos_suficientes(user_id, tipo_defensa, cantidad)
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
    
    tiempo = calcular_tiempo_construccion(user_id, tipo_defensa, cantidad)
    
    # Descontar recursos
    recursos = obtener_recursos(user_id)
    for recurso, cantidad_req in costo_total.items():
        recursos[recurso] = recursos.get(recurso, 0) - cantidad_req
    guardar_recursos(user_id, recursos)
    
    # Agregar a cola
    exito, msg_cola = agregar_a_cola(user_id, tipo_defensa, cantidad, costo_total, tiempo)
    if not exito:
        # Reembolsar si falla
        for recurso, cantidad_req in costo_total.items():
            recursos[recurso] = recursos.get(recurso, 0) + cantidad_req
        guardar_recursos(user_id, recursos)
        return False, msg_cola
    
    username = AuthSystem.obtener_username(user_id)
    logger.info(f"🛡️ {username} inició construcción de {cantidad}x {config['nombre']} - {formatear_tiempo_corto(tiempo)}")
    
    tiempo_str = formatear_tiempo_corto(tiempo)
    
    cola = obtener_cola(user_id)
    
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"🛡️ <b>CONSTRUCCIÓN INICIADA</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"{config['icono']} {config['nombre']}\n"
        f"├ Cantidad: {cantidad}\n"
        f"├ Tiempo: {tiempo_str}\n"
        f"└ Posición en cola: {len(cola)}\n\n"
        f"💰 Recursos descontados correctamente.\n\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    )
    
    return True, mensaje

# ================= 🛡️ HANDLERS =================

@requiere_login
async def menu_defensa_principal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        logger.error("❌ menu_defensa_principal sin callback_query")
        return
    
    await query.answer()
    user_id = query.from_user.id
    
    procesar_cola(user_id)
    
    recursos = obtener_recursos(user_id)
    defensas = obtener_defensas(user_id)
    cola = obtener_cola(user_id)
    username_tag = AuthSystem.obtener_username(user_id)
    
    total_defensas = sum(defensas.values())
    
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"🛡️ <b>COMANDO DE DEFENSAS</b> - {username_tag}\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"💰 <b>RECURSOS:</b>\n"
        f"🔩 Metal: {abreviar_numero(recursos.get('metal', 0))}\n"
        f"💎 Cristal: {abreviar_numero(recursos.get('cristal', 0))}\n"
        f"🧪 Deuterio: {abreviar_numero(recursos.get('deuterio', 0))}\n\n"
        f"📋 <b>COLA:</b> {len(cola)}/{MAX_COLA_SIZE}\n"
        f"📊 <b>DEFENSAS TOTALES:</b> {abreviar_numero(total_defensas)} unidades\n\n"
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
            config = CONFIG_DEFENSAS.get(item["defensa"], {})
            icono = config.get("icono", "🛡️")
            nombre = config.get("nombre", item["defensa"])
            cantidad = item["cantidad"]
            mensaje += f"   {idx}. {icono} {nombre} x{cantidad}\n"
            mensaje += f"      {barra} {tiempo}\n"
        mensaje += "\n"
    
    defensas_activas = {k: v for k, v in defensas.items() if v > 0}
    if defensas_activas:
        mensaje += f"<b>TUS DEFENSAS:</b>\n"
        for def_id, cantidad in list(defensas_activas.items())[:8]:
            config = CONFIG_DEFENSAS.get(def_id, {})
            icono = config.get("icono", "🛡️")
            nombre = config.get("nombre", def_id)
            mensaje += f"   {icono} {nombre}: {abreviar_numero(cantidad)}\n"
        if len(defensas_activas) > 8:
            mensaje += f"   ... y {len(defensas_activas) - 8} tipos más\n"
        mensaje += "\n"
    
    mensaje += f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
    mensaje += f"<i>Selecciona una defensa:</i>"
    
    keyboard = [
        [InlineKeyboardButton("🚀 DEFENSAS LIGERAS", callback_data="noop")],
        [
            InlineKeyboardButton("🚀 Lanzador", callback_data="defensa_lanza_misiles"),
            InlineKeyboardButton("🔫 Láser Ligero", callback_data="defensa_laser_ligero")
        ],
        [InlineKeyboardButton("🔫🔫 Láser Pesado", callback_data="defensa_laser_pesado")],
        
        [InlineKeyboardButton("⚡ DEFENSAS MEDIAS", callback_data="noop")],
        [
            InlineKeyboardButton("⚡ Cañón Iónico", callback_data="defensa_canion_ionico"),
            InlineKeyboardButton("🧲 Cañón Gauss", callback_data="defensa_canion_gauss")
        ],
        
        [InlineKeyboardButton("☢️ DEFENSAS PESADAS", callback_data="noop")],
        [
            InlineKeyboardButton("☢️ Cañón Plasma", callback_data="defensa_canion_plasma"),
            InlineKeyboardButton("🛡️ Escudo Pequeño", callback_data="defensa_escudo_pequeno")
        ],
        [InlineKeyboardButton("🛡️🛡️ Escudo Grande", callback_data="defensa_escudo_grande")],
        
        [InlineKeyboardButton("🎯 MISILES", callback_data="noop")],
        [
            InlineKeyboardButton("🎯 Interceptor", callback_data="defensa_misil_interceptor"),
            InlineKeyboardButton("💥 Interplanetario", callback_data="defensa_misil_interplanetario")
        ],
        
        [InlineKeyboardButton("📋 VER COLA", callback_data="defensa_cola")],
        [InlineKeyboardButton("◀️ VOLVER", callback_data="menu_principal")]
    ]
    
    if cola:
        cancel_fila = []
        for i in range(1, min(len(cola) + 1, 4)):
            cancel_fila.append(InlineKeyboardButton(f"❌ Cancelar {i}", callback_data=f"defensa_cancelar_{i-1}"))
        keyboard.insert(-2, cancel_fila)
    
    await query.edit_message_text(
        text=mensaje,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

@requiere_login
async def submenu_defensa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    tipo_defensa = query.data.replace("defensa_", "")
    
    if tipo_defensa not in CONFIG_DEFENSAS:
        await query.edit_message_text("❌ Defensa no encontrada")
        return
    
    config = CONFIG_DEFENSAS[tipo_defensa]
    
    recursos = obtener_recursos(user_id)
    defensas = obtener_defensas(user_id)
    cola = obtener_cola(user_id)
    cantidad_actual = defensas.get(tipo_defensa, 0)
    nivel_hangar = obtener_nivel(user_id, "hangar")
    username_tag = AuthSystem.obtener_username(user_id)
    
    tiempo_unitario = calcular_tiempo_construccion(user_id, tipo_defensa, 1)
    tiempo_10 = tiempo_unitario * 10
    
    cumple_requisitos, msg_req = verificar_requisitos(user_id, tipo_defensa)
    puede_1, _ = verificar_recursos_suficientes(user_id, tipo_defensa, 1) if cumple_requisitos else (False, "")
    tiene_slot = len(cola) < MAX_COLA_SIZE
    
    tiempo_str = formatear_tiempo_corto(tiempo_unitario)
    tiempo_10_str = formatear_tiempo_corto(tiempo_10)
    
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"{config['icono']} <b>{config['nombre']}</b> - {username_tag}\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"💰 <b>TUS RECURSOS:</b>\n"
        f"🔩 Metal: {abreviar_numero(recursos.get('metal', 0))}\n"
        f"💎 Cristal: {abreviar_numero(recursos.get('cristal', 0))}\n"
        f"🧪 Deuterio: {abreviar_numero(recursos.get('deuterio', 0))}\n\n"
        f"📊 <b>CANTIDAD ACTUAL:</b> {abreviar_numero(cantidad_actual)}\n"
        f"📋 <b>COLA:</b> {len(cola)}/{MAX_COLA_SIZE}\n\n"
        f"⚙️ <b>ESPECIFICACIONES:</b>\n"
        f"├ ⚔️ Ataque: {config['ataque']}\n"
        f"├ 🛡️ Escudo: {config['escudo']}\n"
        f"└ 🏭 Tipo: {config['tipo'].capitalize()}\n\n"
        f"💰 <b>COSTO POR UNIDAD:</b>\n"
    )
    
    for recurso, costo in config["costo"].items():
        if costo > 0:
            icono = "🔩" if recurso == "metal" else "💎" if recurso == "cristal" else "🧪"
            mensaje += f"   {icono} {recurso.capitalize()}: {abreviar_numero(costo)}\n"
    
    mensaje += f"\n⏱️ <b>TIEMPO:</b>\n"
    mensaje += f"   ├ 1 unidad: {tiempo_str}\n"
    mensaje += f"   └ 10 unidades: {tiempo_10_str}\n\n"
    
    mensaje += f"📋 <b>REQUISITOS:</b>\n"
    
    if "hangar" in config["requisitos"]:
        nivel_req = config["requisitos"]["hangar"]
        estado = "✅" if nivel_hangar >= nivel_req else "❌"
        mensaje += f"   {estado} Hangar: Nivel {nivel_req} (tienes: {nivel_hangar})\n"
    
    for req_def, cantidad_req in config["requisitos"].items():
        if req_def != "hangar":
            cant_actual = obtener_cantidad_defensa(user_id, req_def)
            estado = "✅" if cant_actual >= cantidad_req else "❌"
            nombre_def = CONFIG_DEFENSAS.get(req_def, {}).get("nombre", req_def)
            mensaje += f"   {estado} {nombre_def}: {cantidad_req} (tienes: {cant_actual})\n"
    
    mensaje += f"\n📖 <b>DESCRIPCIÓN:</b>\n{config['descripcion']}\n"
    mensaje += f"\n🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    
    if not cumple_requisitos:
        mensaje += f"\n\n❌ {msg_req}"
    elif not tiene_slot:
        mensaje += f"\n\n❌ Cola llena ({len(cola)}/{MAX_COLA_SIZE})"
    
    keyboard = []
    
    if cumple_requisitos and tiene_slot:
        fila_botones = []
        
        if puede_1:
            fila_botones.append(InlineKeyboardButton("1️⃣ 1", callback_data=f"confirmar_defensa_{tipo_defensa}_1"))
        else:
            fila_botones.append(InlineKeyboardButton("1️⃣ 🔒", callback_data="noop"))
        
        fila_botones.append(InlineKeyboardButton("5️⃣ 5", callback_data=f"confirmar_defensa_{tipo_defensa}_5"))
        fila_botones.append(InlineKeyboardButton("🔟 10", callback_data=f"confirmar_defensa_{tipo_defensa}_10"))
        keyboard.append(fila_botones)
        
        keyboard.append([
            InlineKeyboardButton("✏️ CANTIDAD PERSONALIZADA", callback_data=f"personalizar_defensa_{tipo_defensa}")
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
        InlineKeyboardButton("◀️ VOLVER", callback_data="menu_defensa"),
        InlineKeyboardButton("🏠 MENÚ", callback_data="menu_principal")
    ])
    
    await query.edit_message_text(
        text=mensaje,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

@requiere_login
async def confirmar_construccion_defensa_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    partes = query.data.split("_")
    tipo_defensa = "_".join(partes[2:-1])
    cantidad = int(partes[-1])
    
    if tipo_defensa not in CONFIG_DEFENSAS:
        await query.edit_message_text("❌ Defensa no encontrada")
        return
    
    config = CONFIG_DEFENSAS[tipo_defensa]
    cola = obtener_cola(user_id)
    
    cumple_req, msg_req = verificar_requisitos(user_id, tipo_defensa)
    if not cumple_req:
        keyboard = [[InlineKeyboardButton("◀️ VOLVER", callback_data=f"defensa_{tipo_defensa}")]]
        await query.edit_message_text(
            text=f"❌ {msg_req}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    if len(cola) >= MAX_COLA_SIZE:
        keyboard = [[InlineKeyboardButton("◀️ VOLVER", callback_data=f"defensa_{tipo_defensa}")]]
        await query.edit_message_text(
            text=f"❌ Cola llena ({len(cola)}/{MAX_COLA_SIZE})",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    cumple_rec, msg_rec = verificar_recursos_suficientes(user_id, tipo_defensa, cantidad)
    tiempo = calcular_tiempo_construccion(user_id, tipo_defensa, cantidad)
    
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
                callback_data=f"comprar_defensa_{tipo_defensa}_{cantidad}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton("◀️ CAMBIAR CANTIDAD", callback_data=f"defensa_{tipo_defensa}")
    ])
    
    await query.edit_message_text(
        text=mensaje,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

@requiere_login
async def comprar_defensa_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    partes = query.data.split("_")
    tipo_defensa = "_".join(partes[2:-1])
    cantidad = int(partes[-1])
    
    exito, mensaje = construir_defensas(user_id, tipo_defensa, cantidad)
    
    if exito:
        keyboard = [
            [InlineKeyboardButton("📋 VER COLA", callback_data="menu_defensa")],
            [InlineKeyboardButton(f"➕ CONSTRUIR MÁS", callback_data=f"defensa_{tipo_defensa}")],
            [InlineKeyboardButton("🏠 MENÚ PRINCIPAL", callback_data="menu_principal")]
        ]
        await query.edit_message_text(
            text=mensaje,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
    else:
        keyboard = [
            [InlineKeyboardButton("🔄 REINTENTAR", callback_data=f"defensa_{tipo_defensa}")],
            [InlineKeyboardButton("🛡️ VOLVER A DEFENSAS", callback_data="menu_defensa")]
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
            [InlineKeyboardButton("🛡️ CONSTRUIR", callback_data="menu_defensa")],
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
            config = CONFIG_DEFENSAS.get(item["defensa"], {})
            icono = config.get("icono", "🛡️")
            nombre = config.get("nombre", item["defensa"])
            cantidad = item["cantidad"]
            mensaje += f"{idx}. {icono} <b>{nombre}</b> x{cantidad}\n"
            mensaje += f"   └ {barra} {tiempo}\n\n"
        
        mensaje += f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
        
        keyboard = [
            [InlineKeyboardButton("🔄 ACTUALIZAR", callback_data="defensa_cola")],
            [InlineKeyboardButton("🛡️ CONSTRUIR", callback_data="menu_defensa")],
            [InlineKeyboardButton("◀️ VOLVER", callback_data="menu_principal")]
        ]
        
        cancel_fila = []
        for i in range(1, min(len(cola) + 1, 4)):
            cancel_fila.append(InlineKeyboardButton(f"❌ Cancelar {i}", callback_data=f"defensa_cancelar_{i-1}"))
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
            [InlineKeyboardButton("📋 VER COLA", callback_data="defensa_cola")],
            [InlineKeyboardButton("🛡️ CONSTRUIR", callback_data="menu_defensa")],
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
                InlineKeyboardButton("◀️ VOLVER", callback_data="defensa_cola")
            ]]),
            parse_mode="HTML"
        )

@requiere_login
async def personalizar_cantidad_defensa_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    tipo_defensa = query.data.replace("personalizar_defensa_", "")
    
    context.user_data['esperando_cantidad_defensa'] = tipo_defensa
    
    config = CONFIG_DEFENSAS[tipo_defensa]
    
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
    
    keyboard = [[InlineKeyboardButton("◀️ CANCELAR", callback_data=f"defensa_{tipo_defensa}")]]
    
    await query.edit_message_text(
        text=mensaje,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

@requiere_login
async def recibir_cantidad_personalizada_defensa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if 'esperando_cantidad_defensa' not in context.user_data:
        return
    
    tipo_defensa = context.user_data['esperando_cantidad_defensa']
    texto = update.message.text.strip()
    
    del context.user_data['esperando_cantidad_defensa']
    
    try:
        cantidad = int(texto)
    except ValueError:
        await update.message.reply_text("❌ Por favor, ingresa un número válido.")
        return
    
    if cantidad <= 0 or cantidad > 10000:
        await update.message.reply_text("❌ La cantidad debe ser entre 1 y 10.000.")
        return
    
    cumple_req, msg_req = verificar_requisitos(user_id, tipo_defensa)
    if not cumple_req:
        await update.message.reply_text(f"❌ {msg_req}")
        return
    
    cola = obtener_cola(user_id)
    if len(cola) >= MAX_COLA_SIZE:
        await update.message.reply_text(f"❌ Cola llena ({len(cola)}/{MAX_COLA_SIZE})")
        return
    
    cumple_rec, msg_rec = verificar_recursos_suficientes(user_id, tipo_defensa, cantidad)
    if not cumple_rec:
        await update.message.reply_text(f"❌ {msg_rec}")
        return
    
    exito, mensaje = construir_defensas(user_id, tipo_defensa, cantidad)
    
    if exito:
        await update.message.reply_text(mensaje, parse_mode="HTML")
    else:
        await update.message.reply_text(f"❌ {mensaje}")

# ================= 🕐 TAREA PROGRAMADA =================

async def procesar_colas_background(context: ContextTypes.DEFAULT_TYPE):
    logger.info("🔄 Procesando colas de defensa...")
    colas_data = load_json(COLAS_DEFENSA_FILE) or {}
    for user_id_str in colas_data.keys():
        try:
            user_id = int(user_id_str)
            procesar_cola(user_id)
        except Exception as e:
            logger.error(f"❌ Error procesando cola de {user_id_str}: {e}")
    logger.info("✅ Colas de defensa procesadas")

# ================= EXPORTAR =================

__all__ = [
    'menu_defensa_principal',
    'submenu_defensa',
    'confirmar_construccion_defensa_handler',
    'comprar_defensa_handler',
    'ver_cola_handler',
    'cancelar_construccion_handler',
    'personalizar_cantidad_defensa_handler',
    'recibir_cantidad_personalizada_defensa',
    'procesar_colas_background',
    'CONFIG_DEFENSAS',
    'obtener_defensas'
]
