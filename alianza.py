#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#██████╗ ███████╗████████╗██████╗  █████╗ ██╗     ███████╗
#██╔══██╗██╔════╝╚══██╔══╝██╔══██╗██╔══██╗██║     ██╔════╝
#██████╔╝███████╗   ██║   ██╔══██╗███████║██║     ███████╗
#██╔══██╗╚════██║   ██║   ██╔══██╗██╔══██║██║     ╚════██║
#██║  ██║███████║   ██║   ██║  ██║██║  ██║███████╗███████║
#╚═╝  ╚═╝╚══════╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚══════╝

#🚀 ASTRO.IO v2.4.5 🚀
#🌍 alianza.py - SISTEMA COMPLETO DE ALIANZAS
#================================================
#✅ Donaciones con 0 para omitir recursos
#✅ Niveles de banco (1-25) con capacidad = 10k * nivel
#✅ Mejora lineal: costo = 10 * nivel_actual (en NXT-20)
#✅ Chat interno con máximo 20 mensajes (FIFO)
#✅ Gestión de solicitudes, expulsión, descripción y disolución
#================================================

import os
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler, 
    MessageHandler, filters, CallbackQueryHandler
)

from login import AuthSystem, requiere_login
from database import load_json, save_json
from utils import abreviar_numero

logger = logging.getLogger(__name__)

# ================= CONSTANTES =================
DATA_DIR = "data"
RECURSOS_FILE = os.path.join(DATA_DIR, "recursos.json")

# Archivos de alianza
ALIANZA_DATOS_FILE = os.path.join(DATA_DIR, "alianza_datos.json")
ALIANZA_MIEMBROS_FILE = os.path.join(DATA_DIR, "alianza_miembros.json")
ALIANZA_BANCO_FILE = os.path.join(DATA_DIR, "alianza_banco.json")
ALIANZA_PERMISOS_FILE = os.path.join(DATA_DIR, "alianza_permisos.json")
ALIANZA_MENSAJES_FILE = os.path.join(DATA_DIR, "alianza_mensajes.json")
ALIANZA_SOLICITUDES_FILE = os.path.join(DATA_DIR, "alianza_solicitudes.json")

# Estados para ConversationHandler
NOMBRE_ALIANZA, ETIQUETA_ALIANZA = range(2)
BUSCAR_NOMBRE, BUSCAR_ETIQUETA = range(2, 4)
DONACION_METAL, DONACION_CRISTAL, DONACION_DEUTERIO = range(4, 7)
RETIRO_METAL, RETIRO_CRISTAL, RETIRO_DEUTERIO = range(7, 10)
MEJORAR_BANCO_CONFIRMAR = 10
MENSAJE_TEXTO = 11
EDITAR_DESCRIPCION = 12
DISOLVER_CONFIRMAR = 13

# Configuración del banco
BANCO_NIVEL_MAX = 25
BANCO_CAPACIDAD_BASE = 10000          # 10k por nivel
COSTO_MEJORA_BASE = 10                 # costo = base * nivel_actual

def calcular_capacidad_banco(nivel: int) -> int:
    return BANCO_CAPACIDAD_BASE * nivel

def calcular_costo_mejora_banco(nivel_actual: int) -> int:
    return COSTO_MEJORA_BASE * nivel_actual   # 10, 20, 30, ...

# ================= FUNCIONES DE INICIALIZACIÓN =================

def inicializar_archivos_alianza():
    os.makedirs(DATA_DIR, exist_ok=True)
    archivos = [
        ALIANZA_DATOS_FILE,
        ALIANZA_MIEMBROS_FILE,
        ALIANZA_BANCO_FILE,
        ALIANZA_PERMISOS_FILE,
        ALIANZA_MENSAJES_FILE,
        ALIANZA_SOLICITUDES_FILE
    ]
    for archivo in archivos:
        if not os.path.exists(archivo):
            save_json(archivo, {})

inicializar_archivos_alianza()

# ================= FUNCIONES AUXILIARES =================

def generar_id_alianza(etiqueta: str) -> str:
    return etiqueta.upper().replace(" ", "")[:10]

def obtener_alianza_usuario(user_id: int) -> tuple:
    user_id_str = str(user_id)
    miembros_data = load_json(ALIANZA_MIEMBROS_FILE) or {}
    for alianza_id, miembros in miembros_data.items():
        if user_id_str in miembros:
            datos = load_json(ALIANZA_DATOS_FILE) or {}
            return alianza_id, datos.get(alianza_id, {})
    return None, None

def es_fundador_alianza(user_id: int, alianza_id: str) -> bool:
    datos = load_json(ALIANZA_DATOS_FILE) or {}
    alianza = datos.get(alianza_id, {})
    return alianza.get("fundador") == user_id

def es_admin_alianza(user_id: int, alianza_id: str) -> bool:
    if es_fundador_alianza(user_id, alianza_id):
        return True
    miembros = load_json(ALIANZA_MIEMBROS_FILE) or {}
    alianza_miembros = miembros.get(alianza_id, {})
    miembro = alianza_miembros.get(str(user_id), {})
    return miembro.get("rango") == "admin"

def puede_retirar(user_id: int, alianza_id: str) -> bool:
    permisos = load_json(ALIANZA_PERMISOS_FILE) or {}
    alianza_permisos = permisos.get(alianza_id, {})
    return user_id in alianza_permisos.get("retiro", [])

def obtener_banco(alianza_id: str) -> dict:
    banco_data = load_json(ALIANZA_BANCO_FILE) or {}
    banco = banco_data.get(alianza_id, {"metal": 0, "cristal": 0, "deuterio": 0})
    datos = load_json(ALIANZA_DATOS_FILE) or {}
    alianza = datos.get(alianza_id, {})
    nivel = alianza.get("banco_nivel", 1)
    return {
        "metal": banco.get("metal", 0),
        "cristal": banco.get("cristal", 0),
        "deuterio": banco.get("deuterio", 0),
        "nivel": nivel
    }

def guardar_banco(alianza_id: str, metal: int, cristal: int, deuterio: int):
    banco_data = load_json(ALIANZA_BANCO_FILE) or {}
    banco_data[alianza_id] = {"metal": metal, "cristal": cristal, "deuterio": deuterio}
    save_json(ALIANZA_BANCO_FILE, banco_data)

def verificar_capacidad_banco(alianza_id: str, metal: int, cristal: int, deuterio: int) -> tuple:
    banco = obtener_banco(alianza_id)
    nivel = banco["nivel"]
    capacidad = calcular_capacidad_banco(nivel)
    if banco["metal"] + metal > capacidad:
        return False, f"🔩 Metal excede capacidad ({abreviar_numero(capacidad)})"
    if banco["cristal"] + cristal > capacidad:
        return False, f"💎 Cristal excede capacidad ({abreviar_numero(capacidad)})"
    if banco["deuterio"] + deuterio > capacidad:
        return False, f"🧪 Deuterio excede capacidad ({abreviar_numero(capacidad)})"
    return True, ""

# ================= MENÚ PRINCIPAL DE ALIANZA =================

@requiere_login
async def menu_alianza_principal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        logger.error("❌ menu_alianza_principal sin callback_query")
        return
    await query.answer()
    user_id = query.from_user.id
    alianza_id, alianza_datos = obtener_alianza_usuario(user_id)
    if alianza_id:
        await menu_alianza_interno(update, context, alianza_id, alianza_datos)
    else:
        await menu_sin_alianza(update, context)

async def menu_sin_alianza(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    username_tag = AuthSystem.obtener_username(user_id)
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"🌍 <b>SISTEMA DE ALIANZAS</b> - {username_tag}\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"No perteneces a ninguna alianza.\n\n"
        f"📌 <b>CREAR ALIANZA</b>\n"
        f"   Crea tu propia alianza y conviértete en fundador.\n\n"
        f"🔍 <b>BUSCAR ALIANZA</b>\n"
        f"   Busca una alianza existente y envía solicitud.\n\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"<i>Selecciona una opción:</i>"
    )
    keyboard = [
        [InlineKeyboardButton("📌 CREAR ALIANZA", callback_data="alianza_crear"),
         InlineKeyboardButton("🔍 BUSCAR ALIANZA", callback_data="alianza_buscar")],
        [InlineKeyboardButton("◀️ VOLVER", callback_data="menu_principal")]
    ]
    await query.edit_message_text(text=mensaje, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

async def menu_alianza_interno(update: Update, context: ContextTypes.DEFAULT_TYPE, alianza_id: str, alianza_datos: dict):
    query = update.callback_query
    user_id = query.from_user.id
    username_tag = AuthSystem.obtener_username(user_id)
    banco_info = obtener_banco(alianza_id)
    metal = banco_info["metal"]
    cristal = banco_info["cristal"]
    deuterio = banco_info["deuterio"]
    nivel_banco = banco_info["nivel"]
    capacidad = calcular_capacidad_banco(nivel_banco)
    miembros = load_json(ALIANZA_MIEMBROS_FILE) or {}
    alianza_miembros = miembros.get(alianza_id, {})
    total_miembros = len(alianza_miembros)
    es_fundador = es_fundador_alianza(user_id, alianza_id)
    es_admin = es_admin_alianza(user_id, alianza_id)
    descripcion = alianza_datos.get("descripcion", "Sin descripción.")
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"🌍 <b>{alianza_datos.get('nombre', 'ALIANZA')}</b> [{alianza_datos.get('etiqueta', '???')}]\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"📝 {descripcion}\n\n"
        f"👑 Fundador: {alianza_datos.get('fundador_username', '@Desconocido')}\n"
        f"👥 Miembros: {total_miembros}\n"
        f"📅 Fundación: {alianza_datos.get('fecha_creacion', 'Desconocida')[:10]}\n\n"
        f"💰 <b>BANCO DE LA ALIANZA</b> (Nivel {nivel_banco}/{BANCO_NIVEL_MAX})\n"
        f"📦 Capacidad: {abreviar_numero(capacidad)} por recurso\n"
        f"🔩 Metal: {abreviar_numero(metal)}/{abreviar_numero(capacidad)}\n"
        f"💎 Cristal: {abreviar_numero(cristal)}/{abreviar_numero(capacidad)}\n"
        f"🧪 Deuterio: {abreviar_numero(deuterio)}/{abreviar_numero(capacidad)}\n\n"
        f"📋 <b>TU RANGO:</b> "
    )
    if es_fundador:
        mensaje += "👑 Fundador\n"
    elif es_admin:
        mensaje += "🔰 Administrador\n"
    else:
        mensaje += "👤 Miembro\n"
    mensaje += f"\n🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
    mensaje += f"<i>Selecciona una opción:</i>"

    keyboard = [
        [InlineKeyboardButton("💰 DONAR", callback_data=f"alianza_donar_{alianza_id}"),
         InlineKeyboardButton("💸 RETIRAR", callback_data=f"alianza_retirar_{alianza_id}")],
        [InlineKeyboardButton("📋 MIEMBROS", callback_data=f"alianza_miembros_{alianza_id}"),
         InlineKeyboardButton("💬 CHAT", callback_data=f"alianza_chat_{alianza_id}")],
        [InlineKeyboardButton("📊 ESTADÍSTICAS", callback_data=f"alianza_stats_{alianza_id}")]
    ]
    if es_fundador or es_admin:
        admin_row = [
            InlineKeyboardButton("🔑 PERMISOS", callback_data=f"alianza_permisos_{alianza_id}"),
            InlineKeyboardButton("⚙️ ADMIN", callback_data=f"alianza_admin_{alianza_id}")
        ]
        if nivel_banco < BANCO_NIVEL_MAX:
            admin_row.append(InlineKeyboardButton("🏦 MEJORAR BANCO", callback_data=f"alianza_mejorar_banco_{alianza_id}"))
        keyboard.append(admin_row)
    if not es_fundador:
        keyboard.append([InlineKeyboardButton("🚪 SALIR DE ALIANZA", callback_data=f"alianza_salir_{alianza_id}")])
    keyboard.append([InlineKeyboardButton("◀️ VOLVER", callback_data="menu_principal")])

    await query.edit_message_text(text=mensaje, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

# ================= CREACIÓN DE ALIANZA =================

@requiere_login
async def iniciar_creacion_alianza(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    username_tag = AuthSystem.obtener_username(user_id)
    alianza_id, _ = obtener_alianza_usuario(user_id)
    if alianza_id:
        await query.edit_message_text(
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
            f"❌ <b>YA PERTENECES A UNA ALIANZA</b>\n"
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
            f"Debes salir de tu alianza actual antes de crear una nueva.\n\n"
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ VOLVER", callback_data="menu_alianza")
            ]])
        )
        return ConversationHandler.END
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"📌 <b>CREAR NUEVA ALIANZA</b> - {username_tag}\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"Paso 1/2: <b>Nombre de la alianza</b>\n\n"
        f"Escribe el nombre que tendrá tu alianza.\n"
        f"• Mínimo 3 caracteres\n"
        f"• Máximo 30 caracteres\n"
        f"• No puede estar ya en uso\n\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"<i>Escribe el nombre o envía /cancelar para abortar:</i>"
    )
    await query.edit_message_text(
        text=mensaje,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ CANCELAR", callback_data="menu_alianza")
        ]])
    )
    return NOMBRE_ALIANZA

async def recibir_nombre_alianza(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username_tag = AuthSystem.obtener_username(user_id)
    nombre = update.message.text.strip()
    if len(nombre) < 3 or len(nombre) > 30:
        await update.message.reply_text(
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
            f"❌ <b>NOMBRE INVÁLIDO</b>\n"
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
            f"El nombre debe tener entre 3 y 30 caracteres.\n\n"
            f"<i>Escribe otro nombre o envía /cancelar:</i>",
            parse_mode="HTML"
        )
        return NOMBRE_ALIANZA
    datos = load_json(ALIANZA_DATOS_FILE) or {}
    nombre_existe = False
    for alianza in datos.values():
        if alianza.get("nombre", "").lower() == nombre.lower():
            nombre_existe = True
            break
    if nombre_existe:
        await update.message.reply_text(
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
            f"❌ <b>NOMBRE NO DISPONIBLE</b>\n"
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
            f"El nombre '{nombre}' ya está siendo usado.\n\n"
            f"<i>Escribe otro nombre o envía /cancelar:</i>",
            parse_mode="HTML"
        )
        return NOMBRE_ALIANZA
    context.user_data['alianza_nombre'] = nombre
    await update.message.reply_text(
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"📌 <b>CREAR NUEVA ALIANZA</b> - {username_tag}\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"Paso 2/2: <b>Etiqueta de la alianza</b>\n\n"
        f"Escribe la etiqueta (tag) de tu alianza.\n"
        f"• 2-5 caracteres\n"
        f"• Solo letras mayúsculas\n"
        f"• No puede estar ya en uso\n\n"
        f"Ejemplo: IG, AE, COSMO\n\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"<i>Escribe la etiqueta o envía /cancelar:</i>",
        parse_mode="HTML"
    )
    return ETIQUETA_ALIANZA

async def recibir_etiqueta_alianza(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username_tag = AuthSystem.obtener_username(user_id)
    etiqueta = update.message.text.strip().upper()
    if len(etiqueta) < 2 or len(etiqueta) > 5:
        await update.message.reply_text(
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
            f"❌ <b>ETIQUETA INVÁLIDA</b>\n"
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
            f"La etiqueta debe tener entre 2 y 5 caracteres.\n\n"
            f"<i>Escribe otra etiqueta o envía /cancelar:</i>",
            parse_mode="HTML"
        )
        return ETIQUETA_ALIANZA
    if not etiqueta.isalpha():
        await update.message.reply_text(
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
            f"❌ <b>ETIQUETA INVÁLIDA</b>\n"
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
            f"Solo se permiten letras (A-Z).\n\n"
            f"<i>Escribe otra etiqueta o envía /cancelar:</i>",
            parse_mode="HTML"
        )
        return ETIQUETA_ALIANZA
    datos = load_json(ALIANZA_DATOS_FILE) or {}
    if etiqueta in datos:
        await update.message.reply_text(
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
            f"❌ <b>ETIQUETA NO DISPONIBLE</b>\n"
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
            f"La etiqueta '{etiqueta}' ya está en uso.\n\n"
            f"<i>Escribe otra etiqueta o envía /cancelar:</i>",
            parse_mode="HTML"
        )
        return ETIQUETA_ALIANZA
    nombre = context.user_data.get('alianza_nombre', 'Alianza sin nombre')
    alianza_id = etiqueta
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    datos[alianza_id] = {
        "id": alianza_id,
        "nombre": nombre,
        "etiqueta": etiqueta,
        "fundador": user_id,
        "fundador_username": username_tag,
        "fecha_creacion": ahora,
        "descripcion": "",
        "banco_nivel": 1
    }
    save_json(ALIANZA_DATOS_FILE, datos)
    miembros = load_json(ALIANZA_MIEMBROS_FILE) or {}
    if alianza_id not in miembros:
        miembros[alianza_id] = {}
    miembros[alianza_id][str(user_id)] = {
        "user_id": user_id,
        "username": username_tag,
        "rango": "fundador",
        "fecha_ingreso": ahora
    }
    save_json(ALIANZA_MIEMBROS_FILE, miembros)
    banco = load_json(ALIANZA_BANCO_FILE) or {}
    banco[alianza_id] = {"metal": 0, "cristal": 0, "deuterio": 0}
    save_json(ALIANZA_BANCO_FILE, banco)
    permisos = load_json(ALIANZA_PERMISOS_FILE) or {}
    permisos[alianza_id] = {"retiro": [user_id]}
    save_json(ALIANZA_PERMISOS_FILE, permisos)
    del context.user_data['alianza_nombre']
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"✅ <b>¡ALIANZA CREADA CON ÉXITO!</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"📌 <b>{nombre}</b> [{etiqueta}]\n\n"
        f"👑 Fundador: {username_tag}\n"
        f"📅 Fecha: {ahora[:10]}\n\n"
        f"Ya puedes invitar miembros y gestionar tu alianza.\n\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    )
    keyboard = [
        [InlineKeyboardButton("🌍 IR A MI ALIANZA", callback_data="menu_alianza")],
        [InlineKeyboardButton("🏠 MENÚ PRINCIPAL", callback_data="menu_principal")]
    ]
    await update.message.reply_text(text=mensaje, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    logger.info(f"✅ Alianza creada: {nombre} [{etiqueta}] por {username_tag}")
    return ConversationHandler.END

# ================= BÚSQUEDA DE ALIANZA =================
@requiere_login
async def iniciar_busqueda_alianza(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    username_tag = AuthSystem.obtener_username(user_id)
    alianza_id, _ = obtener_alianza_usuario(user_id)
    if alianza_id:
        await query.edit_message_text(
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
            f"❌ <b>YA PERTENECES A UNA ALIANZA</b>\n"
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
            f"Debes salir de tu alianza actual antes de buscar otra.\n\n"
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ VOLVER", callback_data="menu_alianza")
            ]])
        )
        return ConversationHandler.END
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"🔍 <b>BUSCAR ALIANZA</b> - {username_tag}\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"Escribe el <b>nombre</b> o la <b>etiqueta</b> de la alianza que buscas.\n\n"
        f"Ejemplo: 'Imperio Galáctico' o 'IG'\n\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"<i>Escribe el nombre/etiqueta o envía /cancelar:</i>"
    )
    await query.edit_message_text(text=mensaje, parse_mode="HTML", reply_markup=InlineKeyboardMarkup([[
        InlineKeyboardButton("❌ CANCELAR", callback_data="menu_alianza")
    ]]))
    return BUSCAR_NOMBRE

async def recibir_busqueda_alianza(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username_tag = AuthSystem.obtener_username(user_id)
    busqueda = update.message.text.strip()
    datos = load_json(ALIANZA_DATOS_FILE) or {}
    alianza_encontrada = None
    alianza_id = None
    if busqueda.upper() in datos:
        alianza_id = busqueda.upper()
        alianza_encontrada = datos[alianza_id]
    else:
        for aid, alianza in datos.items():
            if alianza.get("nombre", "").lower() == busqueda.lower():
                alianza_id = aid
                alianza_encontrada = alianza
                break
    if not alianza_encontrada:
        await update.message.reply_text(
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
            f"❌ <b>ALIANZA NO ENCONTRADA</b>\n"
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
            f"No se encontró ninguna alianza con '{busqueda}'.\n\n"
            f"<i>Escribe otro nombre/etiqueta o envía /cancelar:</i>",
            parse_mode="HTML"
        )
        return BUSCAR_NOMBRE
    miembros = load_json(ALIANZA_MIEMBROS_FILE) or {}
    total_miembros = len(miembros.get(alianza_id, {}))
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"🔍 <b>ALIANZA ENCONTRADA</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"📌 <b>{alianza_encontrada.get('nombre')}</b> [{alianza_id}]\n"
        f"👑 Fundador: {alianza_encontrada.get('fundador_username')}\n"
        f"👥 Miembros: {total_miembros}\n"
        f"📅 Fundación: {alianza_encontrada.get('fecha_creacion', 'Desconocida')[:10]}\n\n"
        f"¿Deseas enviar una solicitud para unirte?\n\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    )
    keyboard = [
        [InlineKeyboardButton("✅ ENVIAR SOLICITUD", callback_data=f"alianza_solicitar_{alianza_id}"),
         InlineKeyboardButton("❌ CANCELAR", callback_data="menu_alianza")]
    ]
    await update.message.reply_text(text=mensaje, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    return ConversationHandler.END

# ================= SOLICITUDES DE ALIANZA (ahora guardadas en archivo) =================

@requiere_login
async def enviar_solicitud_alianza(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    username_tag = AuthSystem.obtener_username(user_id)
    alianza_id = query.data.replace("alianza_solicitar_", "")
    alianza_actual, _ = obtener_alianza_usuario(user_id)
    if alianza_actual:
        await query.edit_message_text(
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
            f"❌ <b>YA PERTENECES A UNA ALIANZA</b>\n"
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
            f"Debes salir de tu alianza actual antes de solicitar ingreso.\n\n"
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ VOLVER", callback_data="menu_alianza")
            ]])
        )
        return
    datos = load_json(ALIANZA_DATOS_FILE) or {}
    alianza = datos.get(alianza_id, {})
    if not alianza:
        await query.edit_message_text(
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
            f"❌ <b>ALIANZA NO EXISTE</b>\n"
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
            f"La alianza que buscas ya no está disponible.\n\n"
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ VOLVER", callback_data="menu_alianza")
            ]])
        )
        return

    # Guardar solicitud en archivo
    solicitudes_data = load_json(ALIANZA_SOLICITUDES_FILE) or {}
    if alianza_id not in solicitudes_data:
        solicitudes_data[alianza_id] = []
    # Evitar duplicados
    for s in solicitudes_data[alianza_id]:
        if s["user_id"] == user_id:
            await query.edit_message_text(
                f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
                f"❌ <b>YA ENVIASTE SOLICITUD</b>\n"
                f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
                f"Ya tienes una solicitud pendiente para esta alianza.",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("◀️ VOLVER", callback_data="menu_alianza")
                ]])
            )
            return
    solicitudes_data[alianza_id].append({
        "user_id": user_id,
        "username": username_tag,
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    save_json(ALIANZA_SOLICITUDES_FILE, solicitudes_data)

    # Notificar a los administradores (opcional, pero se puede hacer)
    miembros = load_json(ALIANZA_MIEMBROS_FILE) or {}
    miembros_alianza = miembros.get(alianza_id, {})
    for uid_str in miembros_alianza.keys():
        if es_admin_alianza(int(uid_str), alianza_id):
            try:
                await context.bot.send_message(
                    chat_id=int(uid_str),
                    text=f"📨 Nueva solicitud de {username_tag} para unirse a la alianza.",
                    parse_mode="HTML"
                )
            except:
                pass

    await query.edit_message_text(
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"✅ <b>SOLICITUD ENVIADA</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"Tu solicitud ha sido enviada a los administradores de {alianza.get('nombre')}.\n"
        f"Recibirás una notificación cuando sea respondida.\n\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("◀️ VOLVER", callback_data="menu_alianza")
        ]])
    )
    logger.info(f"📨 Solicitud de {username_tag} para unirse a {alianza_id}")

# Funciones para aceptar/rechazar desde el panel de administración (ya definidas más abajo)

# ================= DONACIONES MODIFICADAS (aceptar 0) =================

@requiere_login
async def iniciar_donacion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    alianza_id = query.data.replace("alianza_donar_", "")
    alianza_actual, _ = obtener_alianza_usuario(user_id)
    if alianza_actual != alianza_id:
        await query.answer("❌ No perteneces a esta alianza", show_alert=True)
        return
    context.user_data['donacion_alianza'] = alianza_id
    context.user_data['donacion_metal'] = 0
    context.user_data['donacion_cristal'] = 0
    context.user_data['donacion_deuterio'] = 0
    recursos_data = load_json(RECURSOS_FILE) or {}
    recursos = recursos_data.get(str(user_id), {"metal": 0, "cristal": 0, "deuterio": 0})
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"💰 <b>DONAR METAL</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"Tus recursos disponibles: 🔩 {abreviar_numero(recursos.get('metal', 0))}\n\n"
        f"Escribe la cantidad de metal que deseas donar (0 para omitir):\n\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    )
    await query.edit_message_text(
        text=mensaje,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ CANCELAR", callback_data="menu_alianza")
        ]])
    )
    return DONACION_METAL

async def recibir_donacion_metal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    alianza_id = context.user_data.get('donacion_alianza')
    if not alianza_id:
        await update.message.reply_text("❌ Sesión de donación expirada")
        return ConversationHandler.END
    try:
        cantidad = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text(
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
            f"❌ <b>ERROR</b>\n"
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
            f"Por favor, ingresa un número válido.\n\n"
            f"<i>Escribe la cantidad o envía /cancelar:</i>",
            parse_mode="HTML"
        )
        return DONACION_METAL
    if cantidad < 0:
        await update.message.reply_text(
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
            f"❌ <b>ERROR</b>\n"
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
            f"La cantidad no puede ser negativa.\n\n"
            f"<i>Escribe la cantidad o envía /cancelar:</i>",
            parse_mode="HTML"
        )
        return DONACION_METAL
    if cantidad > 0:
        recursos_data = load_json(RECURSOS_FILE) or {}
        recursos = recursos_data.get(str(user_id), {})
        if recursos.get('metal', 0) < cantidad:
            await update.message.reply_text(
                f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
                f"❌ <b>RECURSOS INSUFICIENTES</b>\n"
                f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
                f"No tienes suficiente metal.\n"
                f"Disponible: 🔩 {abreviar_numero(recursos.get('metal', 0))}\n\n"
                f"<i>Escribe otra cantidad o envía /cancelar:</i>",
                parse_mode="HTML"
            )
            return DONACION_METAL
    context.user_data['donacion_metal'] = cantidad
    recursos_data = load_json(RECURSOS_FILE) or {}
    recursos = recursos_data.get(str(user_id), {})
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"💰 <b>DONAR CRISTAL</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"Tus recursos disponibles: 💎 {abreviar_numero(recursos.get('cristal', 0))}\n\n"
        f"Escribe la cantidad de cristal que deseas donar (0 para omitir):\n\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    )
    await update.message.reply_text(text=mensaje, parse_mode="HTML")
    return DONACION_CRISTAL

async def recibir_donacion_cristal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    alianza_id = context.user_data.get('donacion_alianza')
    if not alianza_id:
        await update.message.reply_text("❌ Sesión de donación expirada")
        return ConversationHandler.END
    try:
        cantidad = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text(
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
            f"❌ <b>ERROR</b>\n"
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
            f"Por favor, ingresa un número válido.\n\n"
            f"<i>Escribe la cantidad o envía /cancelar:</i>",
            parse_mode="HTML"
        )
        return DONACION_CRISTAL
    if cantidad < 0:
        await update.message.reply_text(
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
            f"❌ <b>ERROR</b>\n"
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
            f"La cantidad no puede ser negativa.\n\n"
            f"<i>Escribe la cantidad o envía /cancelar:</i>",
            parse_mode="HTML"
        )
        return DONACION_CRISTAL
    if cantidad > 0:
        recursos_data = load_json(RECURSOS_FILE) or {}
        recursos = recursos_data.get(str(user_id), {})
        if recursos.get('cristal', 0) < cantidad:
            await update.message.reply_text(
                f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
                f"❌ <b>RECURSOS INSUFICIENTES</b>\n"
                f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
                f"No tienes suficiente cristal.\n"
                f"Disponible: 💎 {abreviar_numero(recursos.get('cristal', 0))}\n\n"
                f"<i>Escribe otra cantidad o envía /cancelar:</i>",
                parse_mode="HTML"
            )
            return DONACION_CRISTAL
    context.user_data['donacion_cristal'] = cantidad
    recursos_data = load_json(RECURSOS_FILE) or {}
    recursos = recursos_data.get(str(user_id), {})
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"💰 <b>DONAR DEUTERIO</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"Tus recursos disponibles: 🧪 {abreviar_numero(recursos.get('deuterio', 0))}\n\n"
        f"Escribe la cantidad de deuterio que deseas donar (0 para omitir):\n\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    )
    await update.message.reply_text(text=mensaje, parse_mode="HTML")
    return DONACION_DEUTERIO

async def recibir_donacion_deuterio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username_tag = AuthSystem.obtener_username(user_id)
    alianza_id = context.user_data.get('donacion_alianza')
    if not alianza_id:
        await update.message.reply_text("❌ Sesión de donación expirada")
        return ConversationHandler.END
    try:
        cantidad = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text(
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
            f"❌ <b>ERROR</b>\n"
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
            f"Por favor, ingresa un número válido.\n\n"
            f"<i>Escribe la cantidad o envía /cancelar:</i>",
            parse_mode="HTML"
        )
        return DONACION_DEUTERIO
    if cantidad < 0:
        await update.message.reply_text(
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
            f"❌ <b>ERROR</b>\n"
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
            f"La cantidad no puede ser negativa.\n\n"
            f"<i>Escribe la cantidad o envía /cancelar:</i>",
            parse_mode="HTML"
        )
        return DONACION_DEUTERIO
    if cantidad > 0:
        recursos_data = load_json(RECURSOS_FILE) or {}
        recursos = recursos_data.get(str(user_id), {})
        if recursos.get('deuterio', 0) < cantidad:
            await update.message.reply_text(
                f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
                f"❌ <b>RECURSOS INSUFICIENTES</b>\n"
                f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
                f"No tienes suficiente deuterio.\n"
                f"Disponible: 🧪 {abreviar_numero(recursos.get('deuterio', 0))}\n\n"
                f"<i>Escribe otra cantidad o envía /cancelar:</i>",
                parse_mode="HTML"
            )
            return DONACION_DEUTERIO
    metal = context.user_data.get('donacion_metal', 0)
    cristal = context.user_data.get('donacion_cristal', 0)
    deuterio = cantidad
    if metal == 0 and cristal == 0 and deuterio == 0:
        await update.message.reply_text(
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
            f"❌ <b>DONACIÓN CANCELADA</b>\n"
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
            f"No has donado ningún recurso.\n\n",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🌍 VOLVER A ALIANZA", callback_data="menu_alianza")
            ]])
        )
        for key in ['donacion_alianza', 'donacion_metal', 'donacion_cristal']:
            context.user_data.pop(key, None)
        return ConversationHandler.END
    ok, msg = verificar_capacidad_banco(alianza_id, metal, cristal, deuterio)
    if not ok:
        await update.message.reply_text(
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
            f"❌ <b>CAPACIDAD INSUFICIENTE</b>\n"
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
            f"{msg}\n\n"
            f"<i>La donación no puede completarse.</i>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 VOLVER", callback_data="menu_alianza")
            ]])
        )
        return ConversationHandler.END
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"✅ <b>CONFIRMAR DONACIÓN</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"Vas a donar a la alianza:\n\n"
        f"🔩 Metal: {abreviar_numero(metal) if metal > 0 else '0 (omitido)'}\n"
        f"💎 Cristal: {abreviar_numero(cristal) if cristal > 0 else '0 (omitido)'}\n"
        f"🧪 Deuterio: {abreviar_numero(deuterio) if deuterio > 0 else '0 (omitido)'}\n\n"
        f"¿Confirmas esta donación?\n\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    )
    keyboard = [
        [InlineKeyboardButton("✅ CONFIRMAR", callback_data=f"alianza_confirmar_donacion_{alianza_id}_{metal}_{cristal}_{deuterio}"),
         InlineKeyboardButton("❌ CANCELAR", callback_data="menu_alianza")]
    ]
    await update.message.reply_text(text=mensaje, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    return ConversationHandler.END

@requiere_login
async def confirmar_donacion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    partes = query.data.split("_")
    alianza_id = partes[3]
    metal = int(partes[4])
    cristal = int(partes[5])
    deuterio = int(partes[6])
    user_id = query.from_user.id
    username_tag = AuthSystem.obtener_username(user_id)
    ok, msg = verificar_capacidad_banco(alianza_id, metal, cristal, deuterio)
    if not ok:
        await query.edit_message_text(
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
            f"❌ <b>ERROR</b>\n"
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
            f"{msg}\n\n"
            f"La donación no pudo completarse.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🌍 VOLVER A ALIANZA", callback_data="menu_alianza")
            ]])
        )
        return
    recursos_data = load_json(RECURSOS_FILE) or {}
    recursos = recursos_data.get(str(user_id), {})
    if metal > 0:
        recursos['metal'] = recursos.get('metal', 0) - metal
    if cristal > 0:
        recursos['cristal'] = recursos.get('cristal', 0) - cristal
    if deuterio > 0:
        recursos['deuterio'] = recursos.get('deuterio', 0) - deuterio
    recursos_data[str(user_id)] = recursos
    save_json(RECURSOS_FILE, recursos_data)
    banco_info = obtener_banco(alianza_id)
    nuevo_metal = banco_info["metal"] + metal
    nuevo_cristal = banco_info["cristal"] + cristal
    nuevo_deuterio = banco_info["deuterio"] + deuterio
    guardar_banco(alianza_id, nuevo_metal, nuevo_cristal, nuevo_deuterio)
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"✅ <b>DONACIÓN COMPLETADA</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"Has donado a la alianza:\n\n"
    )
    if metal > 0:
        mensaje += f"🔩 Metal: {abreviar_numero(metal)}\n"
    if cristal > 0:
        mensaje += f"💎 Cristal: {abreviar_numero(cristal)}\n"
    if deuterio > 0:
        mensaje += f"🧪 Deuterio: {abreviar_numero(deuterio)}\n"
    mensaje += f"\n💰 Recursos descontados de tu cuenta.\n"
    mensaje += f"🏦 Recursos añadidos al banco de la alianza.\n\n"
    mensaje += f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    keyboard = [
        [InlineKeyboardButton("🌍 VOLVER A ALIANZA", callback_data="menu_alianza")],
        [InlineKeyboardButton("🏠 MENÚ PRINCIPAL", callback_data="menu_principal")]
    ]
    await query.edit_message_text(text=mensaje, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    logger.info(f"💰 {username_tag} donó {metal}M {cristal}C {deuterio}D a {alianza_id}")

# ================= MEJORA DE BANCO =================

@requiere_login
async def iniciar_mejora_banco(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    alianza_id = query.data.replace("alianza_mejorar_banco_", "")
    if not es_admin_alianza(user_id, alianza_id):
        await query.answer("❌ No tienes permisos", show_alert=True)
        return
    banco_info = obtener_banco(alianza_id)
    nivel_actual = banco_info["nivel"]
    if nivel_actual >= BANCO_NIVEL_MAX:
        await query.edit_message_text(
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
            f"🏆 <b>BANCO AL MÁXIMO NIVEL</b>\n"
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
            f"El banco ya está en nivel máximo ({BANCO_NIVEL_MAX}).",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ VOLVER", callback_data="menu_alianza")
            ]])
        )
        return
    costo = calcular_costo_mejora_banco(nivel_actual)
    nueva_capacidad = calcular_capacidad_banco(nivel_actual + 1)
    recursos = load_json(RECURSOS_FILE) or {}
    user_recursos = recursos.get(str(user_id), {})
    nxt20_disponible = user_recursos.get("nxt20", 0)
    if nxt20_disponible < costo:
        await query.edit_message_text(
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
            f"❌ <b>NXT20 INSUFICIENTE</b>\n"
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
            f"Necesitas {abreviar_numero(costo)} NXT-20 para mejorar el banco.\n"
            f"Tienes: {abreviar_numero(nxt20_disponible)}",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ VOLVER", callback_data="menu_alianza")
            ]])
        )
        return
    context.user_data['mejora_banco_alianza'] = alianza_id
    context.user_data['mejora_banco_costo'] = costo
    context.user_data['mejora_banco_nuevo_nivel'] = nivel_actual + 1
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"🏦 <b>MEJORAR BANCO</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"Banco actual: Nivel {nivel_actual}\n"
        f"Capacidad actual: {abreviar_numero(calcular_capacidad_banco(nivel_actual))} por recurso\n\n"
        f"Banco nuevo: Nivel {nivel_actual + 1}\n"
        f"Capacidad nueva: {abreviar_numero(nueva_capacidad)} por recurso\n\n"
        f"💰 Costo: {abreviar_numero(costo)} NXT-20\n\n"
        f"¿Confirmas la mejora?\n\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    )
    keyboard = [
        [InlineKeyboardButton("✅ CONFIRMAR", callback_data="alianza_confirmar_mejora_banco"),
         InlineKeyboardButton("❌ CANCELAR", callback_data="menu_alianza")]
    ]
    await query.edit_message_text(text=mensaje, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    return MEJORAR_BANCO_CONFIRMAR

async def confirmar_mejora_banco(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    alianza_id = context.user_data.get('mejora_banco_alianza')
    costo = context.user_data.get('mejora_banco_costo')
    nuevo_nivel = context.user_data.get('mejora_banco_nuevo_nivel')
    if not alianza_id:
        await query.edit_message_text("❌ Sesión expirada")
        return ConversationHandler.END
    recursos = load_json(RECURSOS_FILE) or {}
    user_recursos = recursos.get(str(user_id), {})
    nxt20_actual = user_recursos.get("nxt20", 0)
    if nxt20_actual < costo:
        await query.edit_message_text(
            f"❌ No tienes suficiente NXT-20",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ VOLVER", callback_data="menu_alianza")
            ]])
        )
        return ConversationHandler.END
    user_recursos["nxt20"] = nxt20_actual - costo
    recursos[str(user_id)] = user_recursos
    save_json(RECURSOS_FILE, recursos)
    datos = load_json(ALIANZA_DATOS_FILE) or {}
    if alianza_id not in datos:
        datos[alianza_id] = {}
    datos[alianza_id]["banco_nivel"] = nuevo_nivel
    save_json(ALIANZA_DATOS_FILE, datos)
    await query.edit_message_text(
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"✅ <b>BANCO MEJORADO</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"¡El banco ahora es nivel {nuevo_nivel}!\n"
        f"Capacidad: {abreviar_numero(calcular_capacidad_banco(nuevo_nivel))} por recurso.\n\n"
        f"Se han descontado {abreviar_numero(costo)} NXT-20.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🌍 VOLVER A ALIANZA", callback_data="menu_alianza")
        ]])
    )
    for key in ['mejora_banco_alianza', 'mejora_banco_costo', 'mejora_banco_nuevo_nivel']:
        context.user_data.pop(key, None)
    logger.info(f"🏦 {AuthSystem.obtener_username(user_id)} mejoró banco de {alianza_id} a nivel {nuevo_nivel}")
    return ConversationHandler.END

# ================= CHAT DE ALIANZA =================

@requiere_login
async def ver_chat_alianza(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    alianza_id, alianza_datos = obtener_alianza_usuario(user_id)
    if not alianza_id:
        await query.answer("❌ No perteneces a ninguna alianza", show_alert=True)
        return
    mensajes_data = load_json(ALIANZA_MENSAJES_FILE) or {}
    mensajes = mensajes_data.get(alianza_id, [])
    mensajes = sorted(mensajes, key=lambda x: x["fecha"], reverse=True)[:20]  # Últimos 20
    texto = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"💬 <b>CHAT DE {alianza_datos.get('nombre', 'ALIANZA')}</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
    )
    if not mensajes:
        texto += "📭 No hay mensajes aún.\n\n"
    else:
        for msg in mensajes:
            fecha = msg["fecha"][:16]
            texto += f"<b>{msg['username']}</b> [{fecha}]:\n{msg['texto']}\n\n"
    texto += f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    keyboard = [
        [InlineKeyboardButton("✏️ ESCRIBIR MENSAJE", callback_data=f"alianza_escribir_chat_{alianza_id}")],
        [InlineKeyboardButton("🔄 ACTUALIZAR", callback_data=f"alianza_chat_{alianza_id}")],
        [InlineKeyboardButton("◀️ VOLVER", callback_data="menu_alianza")]
    ]
    await query.edit_message_text(text=texto, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

@requiere_login
async def iniciar_escribir_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    alianza_id, alianza_datos = obtener_alianza_usuario(user_id)
    if not alianza_id:
        await query.answer("❌ No perteneces a ninguna alianza", show_alert=True)
        return
    context.user_data['chat_alianza'] = alianza_id
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"✏️ <b>ESCRIBIR MENSAJE</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"Escribe tu mensaje. Será visible para todos los miembros.\n\n"
        f"<i>Puedes usar formato HTML: &lt;b&gt;negrita&lt;/b&gt;, etc.</i>\n\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    )
    keyboard = [[InlineKeyboardButton("❌ CANCELAR", callback_data=f"alianza_chat_{alianza_id}")]]
    await query.edit_message_text(text=mensaje, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    return MENSAJE_TEXTO

async def recibir_mensaje_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    alianza_id = context.user_data.get('chat_alianza')
    if not alianza_id:
        await update.message.reply_text("❌ Sesión expirada")
        return ConversationHandler.END
    texto = update.message.text.strip()
    if not texto:
        await update.message.reply_text("❌ El mensaje no puede estar vacío.")
        return MENSAJE_TEXTO
    username = AuthSystem.obtener_username(user_id)
    mensajes_data = load_json(ALIANZA_MENSAJES_FILE) or {}
    if alianza_id not in mensajes_data:
        mensajes_data[alianza_id] = []
    mensajes_data[alianza_id].append({
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "user_id": user_id,
        "username": username,
        "texto": texto
    })
    # Mantener solo los últimos 20 mensajes
    if len(mensajes_data[alianza_id]) > 20:
        mensajes_data[alianza_id] = mensajes_data[alianza_id][-20:]
    save_json(ALIANZA_MENSAJES_FILE, mensajes_data)
    await update.message.reply_text(
        f"✅ Mensaje enviado al chat de la alianza.",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("💬 VER CHAT", callback_data=f"alianza_chat_{alianza_id}")
        ]])
    )
    context.user_data.pop('chat_alianza', None)
    return ConversationHandler.END

# ================= LISTA DE MIEMBROS =================
@requiere_login
async def ver_miembros(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    alianza_id = query.data.replace("alianza_miembros_", "")
    alianza_actual, _ = obtener_alianza_usuario(user_id)
    if alianza_actual != alianza_id:
        await query.answer("❌ No perteneces a esta alianza", show_alert=True)
        return
    datos = load_json(ALIANZA_DATOS_FILE) or {}
    alianza = datos.get(alianza_id, {})
    miembros = load_json(ALIANZA_MIEMBROS_FILE) or {}
    alianza_miembros = miembros.get(alianza_id, {})
    if not alianza_miembros:
        await query.edit_message_text(
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
            f"❌ <b>ERROR</b>\n"
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
            f"No hay miembros registrados en esta alianza.\n\n"
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ VOLVER", callback_data="menu_alianza")
            ]])
        )
        return
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"📋 <b>MIEMBROS DE {alianza.get('nombre', 'ALIANZA')}</b> [{alianza_id}]\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
    )
    fundador = None
    admins = []
    miembros_normales = []
    for uid, miembro in alianza_miembros.items():
        rango = miembro.get("rango", "miembro")
        username = miembro.get("username", f"@{uid}")
        if rango == "fundador":
            fundador = f"👑 {username} (ID: <code>{uid}</code>)\n"
        elif rango == "admin":
            admins.append(f"🔰 {username} (ID: <code>{uid}</code>)\n")
        else:
            miembros_normales.append(f"👤 {username} (ID: <code>{uid}</code>)\n")
    if fundador:
        mensaje += f"<b>FUNDADOR:</b>\n{fundador}\n"
    if admins:
        mensaje += f"<b>ADMINISTRADORES:</b>\n"
        for admin in admins[:10]:
            mensaje += admin
        if len(admins) > 10:
            mensaje += f"   ... y {len(admins) - 10} más\n"
        mensaje += "\n"
    if miembros_normales:
        mensaje += f"<b>MIEMBROS:</b>\n"
        for miembro in miembros_normales[:15]:
            mensaje += miembro
        if len(miembros_normales) > 15:
            mensaje += f"   ... y {len(miembros_normales) - 15} más\n"
        mensaje += "\n"
    mensaje += f"📊 <b>TOTAL:</b> {len(alianza_miembros)} miembros\n\n"
    mensaje += f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    keyboard = [
        [InlineKeyboardButton("◀️ VOLVER", callback_data="menu_alianza")],
        [InlineKeyboardButton("🏠 MENÚ PRINCIPAL", callback_data="menu_principal")]
    ]
    await query.edit_message_text(text=mensaje, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

# ================= SALIR DE ALIANZA =================
@requiere_login
async def salir_alianza(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    username_tag = AuthSystem.obtener_username(user_id)
    alianza_id = query.data.replace("alianza_salir_", "")
    if es_fundador_alianza(user_id, alianza_id):
        await query.answer("❌ Los fundadores no pueden salir, deben disolver la alianza", show_alert=True)
        return
    miembros = load_json(ALIANZA_MIEMBROS_FILE) or {}
    if alianza_id in miembros and str(user_id) in miembros[alianza_id]:
        del miembros[alianza_id][str(user_id)]
        save_json(ALIANZA_MIEMBROS_FILE, miembros)
        permisos = load_json(ALIANZA_PERMISOS_FILE) or {}
        if alianza_id in permisos and user_id in permisos[alianza_id].get("retiro", []):
            permisos[alianza_id]["retiro"].remove(user_id)
            save_json(ALIANZA_PERMISOS_FILE, permisos)
        await query.edit_message_text(
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
            f"✅ <b>HAS SALIDO DE LA ALIANZA</b>\n"
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
            f"Ya no perteneces a la alianza.\n\n"
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🌍 VOLVER", callback_data="menu_alianza")
            ]])
        )
        logger.info(f"🚪 {username_tag} salió de {alianza_id}")
    else:
        await query.edit_message_text(
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
            f"❌ <b>ERROR</b>\n"
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
            f"No se pudo procesar tu solicitud.\n\n"
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ VOLVER", callback_data="menu_alianza")
            ]])
        )

# ================= PANEL DE ADMINISTRACIÓN =================

@requiere_login
async def panel_admin_alianza(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    alianza_id = query.data.replace("alianza_admin_", "")
    
    if not es_admin_alianza(user_id, alianza_id):
        await query.answer("❌ No tienes permisos de administrador", show_alert=True)
        return
    
    datos = load_json(ALIANZA_DATOS_FILE) or {}
    alianza = datos.get(alianza_id, {})
    banco_info = obtener_banco(alianza_id)
    nivel_banco = banco_info["nivel"]
    
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"⚙️ <b>ADMINISTRACIÓN DE {alianza.get('nombre', 'ALIANZA')}</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"Selecciona una opción:\n\n"
    )
    
    keyboard = [
        [InlineKeyboardButton("📥 SOLICITUDES PENDIENTES", callback_data=f"alianza_solicitudes_{alianza_id}")],
        [InlineKeyboardButton("🔑 GESTIONAR PERMISOS", callback_data=f"alianza_permisos_{alianza_id}")],
        [InlineKeyboardButton("❌ EXPULSAR MIEMBRO", callback_data=f"alianza_expulsar_{alianza_id}")],
        [InlineKeyboardButton("📝 EDITAR DESCRIPCIÓN", callback_data=f"alianza_editar_{alianza_id}")]
    ]
    
    if nivel_banco < BANCO_NIVEL_MAX:
        keyboard.append([InlineKeyboardButton("🏦 MEJORAR BANCO", callback_data=f"alianza_mejorar_banco_{alianza_id}")])
    
    if es_fundador_alianza(user_id, alianza_id):
        keyboard.append([InlineKeyboardButton("⚠️ DISOLVER ALIANZA", callback_data=f"alianza_disolver_{alianza_id}")])
    
    keyboard.append([InlineKeyboardButton("◀️ VOLVER", callback_data="menu_alianza")])
    
    await query.edit_message_text(text=mensaje, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

# ================= SOLICITUDES PENDIENTES =================

@requiere_login
async def ver_solicitudes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    alianza_id = query.data.replace("alianza_solicitudes_", "")
    
    if not es_admin_alianza(user_id, alianza_id):
        await query.answer("❌ No tienes permisos", show_alert=True)
        return
    
    solicitudes_data = load_json(ALIANZA_SOLICITUDES_FILE) or {}
    solicitudes = solicitudes_data.get(alianza_id, [])
    
    if not solicitudes:
        await query.edit_message_text(
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
            f"📭 <b>No hay solicitudes pendientes</b>\n"
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ VOLVER", callback_data=f"alianza_admin_{alianza_id}")
            ]])
        )
        return
    
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"📥 <b>SOLICITUDES PENDIENTES</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
    )
    keyboard = []
    for sol in solicitudes[:10]:
        uid = sol["user_id"]
        username = sol["username"]
        fecha = sol["fecha"][:16]
        mensaje += f"👤 {username} (ID: <code>{uid}</code>)\n   🕐 {fecha}\n\n"
        keyboard.append([
            InlineKeyboardButton(f"✅ Aceptar {username}", callback_data=f"alianza_aceptar_solicitud_{alianza_id}_{uid}"),
            InlineKeyboardButton(f"❌ Rechazar {username}", callback_data=f"alianza_rechazar_solicitud_{alianza_id}_{uid}")
        ])
    
    keyboard.append([InlineKeyboardButton("◀️ VOLVER", callback_data=f"alianza_admin_{alianza_id}")])
    await query.edit_message_text(text=mensaje, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

@requiere_login
async def aceptar_solicitud(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    partes = query.data.split("_")
    alianza_id = partes[3]
    solicitante_id = int(partes[4])
    admin_id = query.from_user.id
    
    if not es_admin_alianza(admin_id, alianza_id):
        await query.answer("❌ No tienes permisos", show_alert=True)
        return
    
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    username_sol = AuthSystem.obtener_username(solicitante_id)
    
    # Agregar a miembros
    miembros = load_json(ALIANZA_MIEMBROS_FILE) or {}
    if alianza_id not in miembros:
        miembros[alianza_id] = {}
    miembros[alianza_id][str(solicitante_id)] = {
        "user_id": solicitante_id,
        "username": username_sol,
        "rango": "miembro",
        "fecha_ingreso": ahora
    }
    save_json(ALIANZA_MIEMBROS_FILE, miembros)
    
    # Eliminar de solicitudes
    solicitudes_data = load_json(ALIANZA_SOLICITUDES_FILE) or {}
    if alianza_id in solicitudes_data:
        solicitudes_data[alianza_id] = [s for s in solicitudes_data[alianza_id] if s["user_id"] != solicitante_id]
        save_json(ALIANZA_SOLICITUDES_FILE, solicitudes_data)
    
    # Notificar al usuario
    try:
        datos = load_json(ALIANZA_DATOS_FILE) or {}
        alianza = datos.get(alianza_id, {})
        nombre_alianza = alianza.get("nombre", alianza_id)
        await context.bot.send_message(
            chat_id=solicitante_id,
            text=f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
                 f"✅ <b>¡SOLICITUD ACEPTADA!</b>\n"
                 f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
                 f"Has sido aceptado en <b>{nombre_alianza}</b> [{alianza_id}].\n\n"
                 f"🌍 Usa /start y ve a Alianzas para acceder.",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"❌ Error notificando a {solicitante_id}: {e}")
    
    await query.edit_message_text(
        f"✅ Solicitud de {username_sol} aceptada.",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("◀️ VOLVER", callback_data=f"alianza_solicitudes_{alianza_id}")
        ]])
    )

@requiere_login
async def rechazar_solicitud(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    partes = query.data.split("_")
    alianza_id = partes[3]
    solicitante_id = int(partes[4])
    admin_id = query.from_user.id
    
    if not es_admin_alianza(admin_id, alianza_id):
        await query.answer("❌ No tienes permisos", show_alert=True)
        return
    
    username_sol = AuthSystem.obtener_username(solicitante_id)
    
    # Eliminar de solicitudes
    solicitudes_data = load_json(ALIANZA_SOLICITUDES_FILE) or {}
    if alianza_id in solicitudes_data:
        solicitudes_data[alianza_id] = [s for s in solicitudes_data[alianza_id] if s["user_id"] != solicitante_id]
        save_json(ALIANZA_SOLICITUDES_FILE, solicitudes_data)
    
    # Notificar al usuario (opcional)
    try:
        datos = load_json(ALIANZA_DATOS_FILE) or {}
        alianza = datos.get(alianza_id, {})
        nombre_alianza = alianza.get("nombre", alianza_id)
        await context.bot.send_message(
            chat_id=solicitante_id,
            text=f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
                 f"❌ <b>SOLICITUD RECHAZADA</b>\n"
                 f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
                 f"Tu solicitud para unirte a <b>{nombre_alianza}</b> [{alianza_id}] ha sido rechazada.",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"❌ Error notificando a {solicitante_id}: {e}")
    
    await query.edit_message_text(
        f"❌ Solicitud de {username_sol} rechazada.",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("◀️ VOLVER", callback_data=f"alianza_solicitudes_{alianza_id}")
        ]])
    )

# ================= EXPULSAR MIEMBRO =================

@requiere_login
async def expulsar_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    alianza_id = query.data.replace("alianza_expulsar_", "")
    
    if not es_admin_alianza(user_id, alianza_id):
        await query.answer("❌ No tienes permisos", show_alert=True)
        return
    
    miembros = load_json(ALIANZA_MIEMBROS_FILE) or {}
    alianza_miembros = miembros.get(alianza_id, {})
    datos = load_json(ALIANZA_DATOS_FILE) or {}
    fundador_id = datos.get(alianza_id, {}).get("fundador")
    
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"❌ <b>EXPULSAR MIEMBRO</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"Selecciona el miembro a expulsar:\n\n"
    )
    keyboard = []
    for uid_str, miembro in alianza_miembros.items():
        uid = int(uid_str)
        if uid == fundador_id or uid == user_id:
            continue
        username = miembro.get("username", f"@{uid}")
        keyboard.append([InlineKeyboardButton(
            f"❌ {username}",
            callback_data=f"alianza_confirmar_expulsion_{alianza_id}_{uid}"
        )])
    keyboard.append([InlineKeyboardButton("◀️ CANCELAR", callback_data=f"alianza_admin_{alianza_id}")])
    
    await query.edit_message_text(text=mensaje, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

@requiere_login
async def confirmar_expulsion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    partes = query.data.split("_")
    alianza_id = partes[3]
    miembro_id = int(partes[4])
    admin_id = query.from_user.id
    
    if not es_admin_alianza(admin_id, alianza_id):
        await query.answer("❌ No tienes permisos", show_alert=True)
        return
    
    # Eliminar de miembros
    miembros = load_json(ALIANZA_MIEMBROS_FILE) or {}
    if alianza_id in miembros and str(miembro_id) in miembros[alianza_id]:
        del miembros[alianza_id][str(miembro_id)]
        save_json(ALIANZA_MIEMBROS_FILE, miembros)
    
    # Eliminar permisos de retiro
    permisos = load_json(ALIANZA_PERMISOS_FILE) or {}
    if alianza_id in permisos and miembro_id in permisos[alianza_id].get("retiro", []):
        permisos[alianza_id]["retiro"].remove(miembro_id)
        save_json(ALIANZA_PERMISOS_FILE, permisos)
    
    username = AuthSystem.obtener_username(miembro_id)
    admin_username = AuthSystem.obtener_username(admin_id)
    
    await query.edit_message_text(
        f"✅ <b>MIEMBRO EXPULSADO</b>\n\n{username} ha sido expulsado de la alianza.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("◀️ VOLVER", callback_data=f"alianza_admin_{alianza_id}")
        ]])
    )
    logger.info(f"❌ {username} expulsado de {alianza_id} por {admin_username}")

# ================= EDITAR DESCRIPCIÓN =================

@requiere_login
async def editar_descripcion_inicio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    alianza_id = query.data.replace("alianza_editar_", "")
    
    if not es_admin_alianza(user_id, alianza_id):
        await query.answer("❌ No tienes permisos", show_alert=True)
        return
    
    context.user_data['editando_desc_alianza'] = alianza_id
    
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"📝 <b>EDITAR DESCRIPCIÓN</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"Escribe la nueva descripción de la alianza (máx 200 caracteres):\n\n"
        f"<i>Envía /cancelar para abortar.</i>"
    )
    await query.edit_message_text(
        text=mensaje,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ CANCELAR", callback_data=f"alianza_admin_{alianza_id}")
        ]])
    )
    return EDITAR_DESCRIPCION

async def recibir_nueva_descripcion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    alianza_id = context.user_data.get('editando_desc_alianza')
    if not alianza_id:
        await update.message.reply_text("❌ Sesión expirada")
        return ConversationHandler.END
    
    texto = update.message.text.strip()
    if len(texto) > 200:
        await update.message.reply_text("❌ La descripción no puede exceder 200 caracteres. Intenta de nuevo.")
        return EDITAR_DESCRIPCION
    
    datos = load_json(ALIANZA_DATOS_FILE) or {}
    if alianza_id not in datos:
        await update.message.reply_text("❌ Alianza no encontrada")
        return ConversationHandler.END
    
    datos[alianza_id]["descripcion"] = texto
    save_json(ALIANZA_DATOS_FILE, datos)
    
    await update.message.reply_text(
        f"✅ Descripción actualizada.",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🌍 VOLVER A ALIANZA", callback_data="menu_alianza")
        ]])
    )
    context.user_data.pop('editando_desc_alianza', None)
    return ConversationHandler.END

# ================= DISOLVER ALIANZA =================

@requiere_login
async def disolver_confirmar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    alianza_id = query.data.replace("alianza_disolver_", "")
    
    if not es_fundador_alianza(user_id, alianza_id):
        await query.answer("❌ Solo el fundador puede disolver la alianza", show_alert=True)
        return
    
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"⚠️ <b>DISOLVER ALIANZA</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"¿Estás seguro de que quieres disolver la alianza?\n"
        f"Esta acción es irreversible y todos los datos se perderán.\n\n"
        f"<i>Confirma escribiendo 'DISOLVER' exactamente:</i>"
    )
    
    context.user_data['disolver_alianza'] = alianza_id
    await query.edit_message_text(
        text=mensaje,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ CANCELAR", callback_data=f"menu_alianza")
        ]])
    )
    return DISOLVER_CONFIRMAR

async def disolver_ejecutar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    alianza_id = context.user_data.get('disolver_alianza')
    if not alianza_id:
        await update.message.reply_text("❌ Sesión expirada")
        return ConversationHandler.END
    
    texto = update.message.text.strip()
    if texto != "DISOLVER":
        await update.message.reply_text("❌ Confirmación incorrecta. Operación cancelada.")
        context.user_data.pop('disolver_alianza', None)
        return ConversationHandler.END
    
    # Eliminar todos los archivos relacionados
    for archivo in [ALIANZA_DATOS_FILE, ALIANZA_MIEMBROS_FILE, ALIANZA_BANCO_FILE,
                    ALIANZA_PERMISOS_FILE, ALIANZA_MENSAJES_FILE, ALIANZA_SOLICITUDES_FILE]:
        data = load_json(archivo) or {}
        if alianza_id in data:
            del data[alianza_id]
            save_json(archivo, data)
    
    await update.message.reply_text(
        f"✅ La alianza ha sido disuelta.",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🌍 VOLVER", callback_data="menu_alianza")
        ]])
    )
    context.user_data.pop('disolver_alianza', None)
    logger.info(f"💥 Alianza {alianza_id} disuelta por {AuthSystem.obtener_username(user_id)}")
    return ConversationHandler.END

# ================= GESTIONAR PERMISOS =================

@requiere_login
async def gestionar_permisos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    alianza_id = query.data.replace("alianza_permisos_", "")
    
    if not es_admin_alianza(user_id, alianza_id):
        await query.answer("❌ No tienes permisos de administrador", show_alert=True)
        return
    
    datos = load_json(ALIANZA_DATOS_FILE) or {}
    alianza = datos.get(alianza_id, {})
    fundador_id = alianza.get("fundador")
    
    miembros = load_json(ALIANZA_MIEMBROS_FILE) or {}
    alianza_miembros = miembros.get(alianza_id, {})
    
    permisos = load_json(ALIANZA_PERMISOS_FILE) or {}
    alianza_permisos = permisos.get(alianza_id, {"retiro": []})
    retiro_permisos = alianza_permisos.get("retiro", [])
    
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"🔑 <b>PERMISOS DE RETIRO</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"Los miembros con permiso pueden retirar recursos del banco.\n\n"
        f"<b>MIEMBROS CON PERMISO:</b>\n"
    )
    
    if not retiro_permisos:
        mensaje += "   ❌ No hay miembros con permiso de retiro.\n\n"
    else:
        for uid in retiro_permisos[:10]:
            miembro = alianza_miembros.get(str(uid), {})
            username = miembro.get("username", f"@{uid}")
            mensaje += f"   ✅ {username}\n"
        if len(retiro_permisos) > 10:
            mensaje += f"   ... y {len(retiro_permisos) - 10} más\n"
        mensaje += "\n"
    
    mensaje += f"<i>Selecciona un miembro para dar/quitar permiso:</i>\n\n"
    mensaje += f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    
    keyboard = []
    fila = []
    for uid, miembro in alianza_miembros.items():
        if int(uid) == fundador_id:
            continue
        username = miembro.get("username", f"@{uid}")[:10]
        tiene_permiso = int(uid) in retiro_permisos
        prefijo = "✅" if tiene_permiso else "❌"
        fila.append(InlineKeyboardButton(
            f"{prefijo} {username}",
            callback_data=f"alianza_toggle_permiso_{alianza_id}_{uid}"
        ))
        if len(fila) == 2:
            keyboard.append(fila)
            fila = []
    if fila:
        keyboard.append(fila)
    
    keyboard.append([InlineKeyboardButton("◀️ VOLVER", callback_data=f"menu_alianza")])
    
    await query.edit_message_text(text=mensaje, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

@requiere_login
async def toggle_permiso(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    partes = query.data.split("_")
    alianza_id = partes[3]
    miembro_id = int(partes[4])
    admin_id = query.from_user.id
    
    if not es_admin_alianza(admin_id, alianza_id):
        await query.answer("❌ No tienes permisos de administrador", show_alert=True)
        return
    
    permisos = load_json(ALIANZA_PERMISOS_FILE) or {}
    if alianza_id not in permisos:
        permisos[alianza_id] = {"retiro": []}
    
    if miembro_id in permisos[alianza_id].get("retiro", []):
        permisos[alianza_id]["retiro"].remove(miembro_id)
        accion = "quitado"
    else:
        permisos[alianza_id]["retiro"].append(miembro_id)
        accion = "otorgado"
    
    save_json(ALIANZA_PERMISOS_FILE, permisos)
    
    miembro_username = AuthSystem.obtener_username(miembro_id)
    admin_username = AuthSystem.obtener_username(admin_id)
    
    await query.edit_message_text(
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"✅ <b>PERMISO DE RETIRO {accion.upper()}</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"👤 Miembro: {miembro_username}\n"
        f"🔑 Acción: {accion}\n"
        f"👑 Admin: {admin_username}\n\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("◀️ VOLVER", callback_data=f"alianza_permisos_{alianza_id}")
        ]])
    )
    logger.info(f"🔑 Permiso de retiro {accion} para {miembro_username} por {admin_username}")

# ================= CANCELAR CONVERSACIÓN =================

async def cancelar_conversacion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username_tag = AuthSystem.obtener_username(user_id)
    keys_to_clear = ['alianza_nombre', 'donacion_alianza', 'donacion_metal', 
                     'donacion_cristal', 'retiro_alianza', 'retiro_metal', 
                     'retiro_cristal', 'mejora_banco_alianza', 'mejora_banco_costo',
                     'mejora_banco_nuevo_nivel', 'chat_alianza', 'editando_desc_alianza',
                     'disolver_alianza']
    for key in keys_to_clear:
        if key in context.user_data:
            del context.user_data[key]
    await update.message.reply_text(
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"❌ <b>OPERACIÓN CANCELADA</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🌍 VOLVER A ALIANZA", callback_data="menu_alianza")
        ]])
    )
    return ConversationHandler.END

# ================= HANDLERS PARA CALLBACKS =================

async def alianza_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    if data == "menu_alianza":
        await menu_alianza_principal(update, context)
        return ConversationHandler.END
    elif data == "alianza_crear":
        return await iniciar_creacion_alianza(update, context)
    elif data == "alianza_buscar":
        return await iniciar_busqueda_alianza(update, context)
    elif data.startswith("alianza_solicitar_"):
        await enviar_solicitud_alianza(update, context)
    elif data.startswith("alianza_aceptar_") or data.startswith("alianza_rechazar_"):
        await decision_solicitud_alianza(update, context)
    elif data.startswith("alianza_donar_"):
        return await iniciar_donacion(update, context)
    elif data.startswith("alianza_confirmar_donacion_"):
        await confirmar_donacion(update, context)
    elif data.startswith("alianza_miembros_"):
        await ver_miembros(update, context)
    elif data.startswith("alianza_salir_"):
        await salir_alianza(update, context)
    elif data.startswith("alianza_admin_"):
        await panel_admin_alianza(update, context)
    elif data.startswith("alianza_permisos_"):
        await gestionar_permisos(update, context)
    elif data.startswith("alianza_toggle_permiso_"):
        await toggle_permiso(update, context)
    elif data.startswith("alianza_mejorar_banco_"):
        return await iniciar_mejora_banco(update, context)
    elif data == "alianza_confirmar_mejora_banco":
        return await confirmar_mejora_banco(update, context)
    elif data.startswith("alianza_chat_"):
        await ver_chat_alianza(update, context)
    elif data.startswith("alianza_escribir_chat_"):
        return await iniciar_escribir_chat(update, context)
    elif data.startswith("alianza_solicitudes_"):
        await ver_solicitudes(update, context)
    elif data.startswith("alianza_aceptar_solicitud_"):
        await aceptar_solicitud(update, context)
    elif data.startswith("alianza_rechazar_solicitud_"):
        await rechazar_solicitud(update, context)
    elif data.startswith("alianza_expulsar_"):
        await expulsar_menu(update, context)
    elif data.startswith("alianza_confirmar_expulsion_"):
        await confirmar_expulsion(update, context)
    elif data.startswith("alianza_editar_"):
        return await editar_descripcion_inicio(update, context)
    elif data.startswith("alianza_disolver_"):
        return await disolver_confirmar(update, context)
    return ConversationHandler.END

# ================= CONFIGURAR CONVERSATION HANDLERS =================

def obtener_conversation_handlers():
    crear_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(iniciar_creacion_alianza, pattern="^alianza_crear$")],
        states={
            NOMBRE_ALIANZA: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_nombre_alianza)],
            ETIQUETA_ALIANZA: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_etiqueta_alianza)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar_conversacion)]
    )
    
    buscar_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(iniciar_busqueda_alianza, pattern="^alianza_buscar$")],
        states={
            BUSCAR_NOMBRE: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_busqueda_alianza)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar_conversacion)]
    )
    
    donacion_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(iniciar_donacion, pattern="^alianza_donar_")],
        states={
            DONACION_METAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_donacion_metal)],
            DONACION_CRISTAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_donacion_cristal)],
            DONACION_DEUTERIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_donacion_deuterio)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar_conversacion)]
    )
    
    mejora_banco_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(iniciar_mejora_banco, pattern="^alianza_mejorar_banco_")],
        states={
            MEJORAR_BANCO_CONFIRMAR: [CallbackQueryHandler(confirmar_mejora_banco, pattern="^alianza_confirmar_mejora_banco$")],
        },
        fallbacks=[CommandHandler("cancelar", cancelar_conversacion)]
    )
    
    chat_escribir_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(iniciar_escribir_chat, pattern="^alianza_escribir_chat_")],
        states={
            MENSAJE_TEXTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_mensaje_chat)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar_conversacion)]
    )
    
    editar_desc_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(editar_descripcion_inicio, pattern="^alianza_editar_")],
        states={
            EDITAR_DESCRIPCION: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_nueva_descripcion)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar_conversacion)]
    )
    
    disolver_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(disolver_confirmar, pattern="^alianza_disolver_")],
        states={
            DISOLVER_CONFIRMAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, disolver_ejecutar)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar_conversacion)]
    )
    
    return [
        crear_handler,
        buscar_handler,
        donacion_handler,
        mejora_banco_handler,
        chat_escribir_handler,
        editar_desc_handler,
        disolver_handler
    ]

# ================= EXPORTAR =================

__all__ = [
    'menu_alianza_principal',
    'alianza_callback_handler',
    'obtener_conversation_handlers',
    'inicializar_archivos_alianza'
]
