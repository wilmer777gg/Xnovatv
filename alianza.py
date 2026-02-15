#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#██████╗ ███████╗████████╗██████╗  █████╗ ██╗     ███████╗
#██╔══██╗██╔════╝╚══██╔══╝██╔══██╗██╔══██╗██║     ██╔════╝
#██████╔╝███████╗   ██║   ██████╔╝███████║██║     ███████╗
#██╔══██╗╚════██║   ██║   ██╔══██╗██╔══██║██║     ╚════██║
#██║  ██║███████║   ██║   ██║  ██║██║  ██║███████╗███████║
#╚═╝  ╚═╝╚══════╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚══════╝

#🚀 ASTRO.IO v2.4.0 🚀
#🌍 alianza.py - SISTEMA COMPLETO DE ALIANZAS
#================================================
#✅ MISMO ESTILO que menú principal
#✅ Diseño con separadores 🌀
#✅ Formato consistente en todos los mensajes
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

# Estados para ConversationHandler
NOMBRE_ALIANZA, ETIQUETA_ALIANZA = range(2)
BUSCAR_NOMBRE, BUSCAR_ETIQUETA = range(2, 4)
DONACION_METAL, DONACION_CRISTAL, DONACION_DEUTERIO = range(4, 7)
RETIRO_METAL, RETIRO_CRISTAL, RETIRO_DEUTERIO = range(7, 10)

# ================= FUNCIONES DE INICIALIZACIÓN =================

def inicializar_archivos_alianza():
    """📁 Crea los archivos JSON de alianza si no existen"""
    os.makedirs(DATA_DIR, exist_ok=True)
    
    if not os.path.exists(ALIANZA_DATOS_FILE):
        save_json(ALIANZA_DATOS_FILE, {})
    
    if not os.path.exists(ALIANZA_MIEMBROS_FILE):
        save_json(ALIANZA_MIEMBROS_FILE, {})
    
    if not os.path.exists(ALIANZA_BANCO_FILE):
        save_json(ALIANZA_BANCO_FILE, {})
    
    if not os.path.exists(ALIANZA_PERMISOS_FILE):
        save_json(ALIANZA_PERMISOS_FILE, {})

# Inicializar al importar
inicializar_archivos_alianza()

# ================= FUNCIONES AUXILIARES =================

def generar_id_alianza(etiqueta: str) -> str:
    """🔑 Genera ID único para la alianza basado en etiqueta"""
    return etiqueta.upper().replace(" ", "")[:10]

def obtener_alianza_usuario(user_id: int) -> tuple:
    """
    🔍 Obtiene la alianza de un usuario
    Retorna: (alianza_id, datos_alianza) o (None, None) si no pertenece
    """
    user_id_str = str(user_id)
    miembros_data = load_json(ALIANZA_MIEMBROS_FILE) or {}
    
    for alianza_id, miembros in miembros_data.items():
        if user_id_str in miembros:
            datos = load_json(ALIANZA_DATOS_FILE) or {}
            return alianza_id, datos.get(alianza_id, {})
    
    return None, None

def es_fundador_alianza(user_id: int, alianza_id: str) -> bool:
    """👑 Verifica si el usuario es fundador de la alianza"""
    datos = load_json(ALIANZA_DATOS_FILE) or {}
    alianza = datos.get(alianza_id, {})
    return alianza.get("fundador") == user_id

def es_admin_alianza(user_id: int, alianza_id: str) -> bool:
    """🔐 Verifica si el usuario es fundador o tiene permisos de admin"""
    if es_fundador_alianza(user_id, alianza_id):
        return True
    
    miembros = load_json(ALIANZA_MIEMBROS_FILE) or {}
    alianza_miembros = miembros.get(alianza_id, {})
    miembro = alianza_miembros.get(str(user_id), {})
    return miembro.get("rango") == "admin"

def puede_retirar(user_id: int, alianza_id: str) -> bool:
    """💸 Verifica si el usuario puede retirar recursos"""
    permisos = load_json(ALIANZA_PERMISOS_FILE) or {}
    alianza_permisos = permisos.get(alianza_id, {})
    return user_id in alianza_permisos.get("retiro", [])

# ================= MENÚ PRINCIPAL DE ALIANZA =================

@requiere_login
async def menu_alianza_principal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🌍 Menú principal de alianza - SIEMPRE edita el mensaje actual"""
    query = update.callback_query
    if not query:
        logger.error("❌ menu_alianza_principal sin callback_query")
        return
    
    await query.answer()
    user_id = query.from_user.id
    username_tag = AuthSystem.obtener_username(user_id)
    
    # Verificar si ya pertenece a una alianza
    alianza_id, alianza_datos = obtener_alianza_usuario(user_id)
    
    if alianza_id:
        # Usuario ya está en una alianza → Menú de alianza
        await menu_alianza_interno(update, context, alianza_id, alianza_datos)
    else:
        # Usuario no está en alianza → Menú de creación/búsqueda
        await menu_sin_alianza(update, context)

async def menu_sin_alianza(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🌍 Menú para usuarios sin alianza"""
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
        [
            InlineKeyboardButton("📌 CREAR ALIANZA", callback_data="alianza_crear"),
            InlineKeyboardButton("🔍 BUSCAR ALIANZA", callback_data="alianza_buscar")
        ],
        [InlineKeyboardButton("◀️ VOLVER", callback_data="menu_principal")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        await query.edit_message_text(
            text=mensaje,
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"❌ Error en menu_sin_alianza: {e}")

async def menu_alianza_interno(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                               alianza_id: str, alianza_datos: dict):
    """🌍 Menú interno de alianza (para miembros)"""
    query = update.callback_query
    user_id = query.from_user.id
    username_tag = AuthSystem.obtener_username(user_id)
    
    # Obtener datos actualizados
    banco = load_json(ALIANZA_BANCO_FILE) or {}
    alianza_banco = banco.get(alianza_id, {"metal": 0, "cristal": 0, "deuterio": 0})
    
    miembros = load_json(ALIANZA_MIEMBROS_FILE) or {}
    alianza_miembros = miembros.get(alianza_id, {})
    total_miembros = len(alianza_miembros)
    
    # Verificar rangos
    es_fundador = es_fundador_alianza(user_id, alianza_id)
    es_admin = es_admin_alianza(user_id, alianza_id)
    puede_ret = puede_retirar(user_id, alianza_id)
    
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"🌍 <b>{alianza_datos.get('nombre', 'ALIANZA')}</b> [{alianza_datos.get('etiqueta', '???')}]\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"👑 Fundador: {alianza_datos.get('fundador_username', '@Desconocido')}\n"
        f"👥 Miembros: {total_miembros}\n"
        f"📅 Fundación: {alianza_datos.get('fecha_creacion', 'Desconocida')[:10]}\n\n"
        f"💰 <b>BANCO DE LA ALIANZA</b>\n"
        f"🔩 Metal: {abreviar_numero(alianza_banco.get('metal', 0))}\n"
        f"💎 Cristal: {abreviar_numero(alianza_banco.get('cristal', 0))}\n"
        f"🧪 Deuterio: {abreviar_numero(alianza_banco.get('deuterio', 0))}\n\n"
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
    
    # Construir teclado
    keyboard = [
        [
            InlineKeyboardButton("💰 DONAR", callback_data=f"alianza_donar_{alianza_id}"),
            InlineKeyboardButton("💸 RETIRAR", callback_data=f"alianza_retirar_{alianza_id}")
        ],
        [
            InlineKeyboardButton("📋 MIEMBROS", callback_data=f"alianza_miembros_{alianza_id}"),
            InlineKeyboardButton("📊 ESTADÍSTICAS", callback_data=f"alianza_stats_{alianza_id}")
        ]
    ]
    
    # Botones de administración (solo fundador/admins)
    if es_fundador or es_admin:
        keyboard.append([
            InlineKeyboardButton("🔑 PERMISOS", callback_data=f"alianza_permisos_{alianza_id}"),
            InlineKeyboardButton("⚙️ ADMIN", callback_data=f"alianza_admin_{alianza_id}")
        ])
    
    # Botón de salir (solo para miembros no fundadores)
    if not es_fundador:
        keyboard.append([InlineKeyboardButton("🚪 SALIR DE ALIANZA", callback_data=f"alianza_salir_{alianza_id}")])
    
    keyboard.append([InlineKeyboardButton("◀️ VOLVER", callback_data="menu_principal")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        await query.edit_message_text(
            text=mensaje,
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"❌ Error en menu_alianza_interno: {e}")

# ================= CREACIÓN DE ALIANZA =================

@requiere_login
async def iniciar_creacion_alianza(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📌 Inicia el proceso de creación de alianza"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    username_tag = AuthSystem.obtener_username(user_id)
    
    # Verificar que no esté ya en una alianza
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
    """📝 Recibe el nombre de la alianza"""
    user_id = update.effective_user.id
    username_tag = AuthSystem.obtener_username(user_id)
    nombre = update.message.text.strip()
    
    # Validar longitud
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
    
    # Verificar si el nombre ya existe
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
            f"El nombre '{nombre}' ya está siendo usado por otra alianza.\n\n"
            f"<i>Escribe otro nombre o envía /cancelar:</i>",
            parse_mode="HTML"
        )
        return NOMBRE_ALIANZA
    
    # Guardar nombre en contexto
    context.user_data['alianza_nombre'] = nombre
    
    # Pedir etiqueta
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
    """📝 Recibe la etiqueta de la alianza y la crea"""
    user_id = update.effective_user.id
    username_tag = AuthSystem.obtener_username(user_id)
    etiqueta = update.message.text.strip().upper()
    
    # Validar longitud
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
    
    # Validar solo letras
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
    
    # Verificar si la etiqueta ya existe
    datos = load_json(ALIANZA_DATOS_FILE) or {}
    etiqueta_existe = etiqueta in datos
    
    if etiqueta_existe:
        await update.message.reply_text(
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
            f"❌ <b>ETIQUETA NO DISPONIBLE</b>\n"
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
            f"La etiqueta '{etiqueta}' ya está siendo usada por otra alianza.\n\n"
            f"<i>Escribe otra etiqueta o envía /cancelar:</i>",
            parse_mode="HTML"
        )
        return ETIQUETA_ALIANZA
    
    # Obtener nombre del contexto
    nombre = context.user_data.get('alianza_nombre', 'Alianza sin nombre')
    
    # ========== CREAR ALIANZA ==========
    alianza_id = etiqueta
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 1. Guardar en alianza_datos.json
    datos = load_json(ALIANZA_DATOS_FILE) or {}
    datos[alianza_id] = {
        "id": alianza_id,
        "nombre": nombre,
        "etiqueta": etiqueta,
        "fundador": user_id,
        "fundador_username": username_tag,
        "fecha_creacion": ahora,
        "descripcion": ""
    }
    save_json(ALIANZA_DATOS_FILE, datos)
    
    # 2. Guardar en alianza_miembros.json
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
    
    # 3. Inicializar banco
    banco = load_json(ALIANZA_BANCO_FILE) or {}
    banco[alianza_id] = {
        "metal": 0,
        "cristal": 0,
        "deuterio": 0
    }
    save_json(ALIANZA_BANCO_FILE, banco)
    
    # 4. Inicializar permisos
    permisos = load_json(ALIANZA_PERMISOS_FILE) or {}
    permisos[alianza_id] = {
        "retiro": [user_id]  # Fundador puede retirar
    }
    save_json(ALIANZA_PERMISOS_FILE, permisos)
    
    # Limpiar contexto
    del context.user_data['alianza_nombre']
    
    # Mensaje de éxito
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
    
    await update.message.reply_text(
        text=mensaje,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )
    
    logger.info(f"✅ Alianza creada: {nombre} [{etiqueta}] por {username_tag}")
    
    return ConversationHandler.END

# ================= BÚSQUEDA DE ALIANZA =================

@requiere_login
async def iniciar_busqueda_alianza(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🔍 Inicia el proceso de búsqueda de alianza"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    username_tag = AuthSystem.obtener_username(user_id)
    
    # Verificar que no esté ya en una alianza
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
    
    await query.edit_message_text(
        text=mensaje,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ CANCELAR", callback_data="menu_alianza")
        ]])
    )
    
    return BUSCAR_NOMBRE

async def recibir_busqueda_alianza(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📝 Recibe el nombre/etiqueta y busca la alianza"""
    user_id = update.effective_user.id
    username_tag = AuthSystem.obtener_username(user_id)
    busqueda = update.message.text.strip()
    
    # Buscar alianza por nombre o etiqueta
    datos = load_json(ALIANZA_DATOS_FILE) or {}
    alianza_encontrada = None
    alianza_id = None
    
    # Buscar por etiqueta (ID)
    if busqueda.upper() in datos:
        alianza_id = busqueda.upper()
        alianza_encontrada = datos[alianza_id]
    else:
        # Buscar por nombre
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
            f"No se encontró ninguna alianza con el nombre o etiqueta '{busqueda}'.\n\n"
            f"<i>Escribe otro nombre/etiqueta o envía /cancelar:</i>",
            parse_mode="HTML"
        )
        return BUSCAR_NOMBRE
    
    # Mostrar información de la alianza y enviar solicitud
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
        [
            InlineKeyboardButton("✅ ENVIAR SOLICITUD", callback_data=f"alianza_solicitar_{alianza_id}"),
            InlineKeyboardButton("❌ CANCELAR", callback_data="menu_alianza")
        ]
    ]
    
    await update.message.reply_text(
        text=mensaje,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )
    
    return ConversationHandler.END

# ================= SOLICITUDES DE ALIANZA =================

@requiere_login
async def enviar_solicitud_alianza(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📨 Envía una solicitud para unirse a una alianza"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    username_tag = AuthSystem.obtener_username(user_id)
    alianza_id = query.data.replace("alianza_solicitar_", "")
    
    # Verificar que no esté ya en una alianza
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
    
    # Obtener datos de la alianza
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
    
    # Notificar al fundador
    fundador_id = alianza.get("fundador")
    
    mensaje_admin = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"📨 <b>SOLICITUD DE INGRESO</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"👤 Usuario: {username_tag}\n"
        f"🆔 ID: <code>{user_id}</code>\n"
        f"🌍 Alianza: {alianza.get('nombre')} [{alianza_id}]\n"
        f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        f"¿Aceptas esta solicitud?\n\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("✅ ACEPTAR", callback_data=f"alianza_aceptar_{user_id}_{alianza_id}"),
            InlineKeyboardButton("❌ RECHAZAR", callback_data=f"alianza_rechazar_{user_id}_{alianza_id}")
        ]
    ]
    
    try:
        await context.bot.send_message(
            chat_id=fundador_id,
            text=mensaje_admin,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
        
        await query.edit_message_text(
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
            f"✅ <b>SOLICITUD ENVIADA</b>\n"
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
            f"Tu solicitud ha sido enviada al fundador de {alianza.get('nombre')}.\n"
            f"Recibirás una notificación cuando sea respondida.\n\n"
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ VOLVER", callback_data="menu_alianza")
            ]])
        )
        
        logger.info(f"📨 Solicitud de {username_tag} para unirse a {alianza_id}")
        
    except Exception as e:
        logger.error(f"❌ Error notificando al fundador: {e}")
        await query.edit_message_text(
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
            f"❌ <b>ERROR AL ENVIAR SOLICITUD</b>\n"
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
            f"No se pudo contactar al fundador de la alianza.\n\n"
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ VOLVER", callback_data="menu_alianza")
            ]])
        )

@requiere_login
async def decision_solicitud_alianza(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """👑 Manejador para aceptar/rechazar solicitudes de alianza"""
    query = update.callback_query
    await query.answer()
    
    try:
        partes = query.data.split("_")
        accion = partes[1]
        solicitante_id = int(partes[2])
        alianza_id = partes[3]
    except Exception as e:
        logger.error(f"❌ Error parseando callback: {query.data} - {e}")
        await query.edit_message_text(
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
            f"❌ <b>ERROR</b>\n"
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
            f"Datos inválidos.\n\n"
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀",
            parse_mode="HTML"
        )
        return
    
    admin_id = query.from_user.id
    admin_username = AuthSystem.obtener_username(admin_id)
    solicitante_username = AuthSystem.obtener_username(solicitante_id)
    
    # Verificar que el admin sea fundador o admin de la alianza
    if not es_admin_alianza(admin_id, alianza_id):
        await query.answer("❌ No tienes permisos para gestionar solicitudes", show_alert=True)
        return
    
    if accion == "aceptar":
        # ========== ACEPTAR SOLICITUD ==========
        ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 1. Agregar a miembros
        miembros = load_json(ALIANZA_MIEMBROS_FILE) or {}
        if alianza_id not in miembros:
            miembros[alianza_id] = {}
        
        miembros[alianza_id][str(solicitante_id)] = {
            "user_id": solicitante_id,
            "username": solicitante_username,
            "rango": "miembro",
            "fecha_ingreso": ahora
        }
        save_json(ALIANZA_MIEMBROS_FILE, miembros)
        
        # 2. Notificar al solicitante
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
                     f"🌍 Usa /start y ve a Alianzas para acceder.\n\n"
                     f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀",
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"❌ Error notificando a {solicitante_id}: {e}")
        
        # 3. Responder al admin
        await query.edit_message_text(
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
            f"✅ <b>SOLICITUD ACEPTADA</b>\n"
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
            f"👤 Usuario: {solicitante_username}\n"
            f"🌍 Alianza: {alianza_id}\n"
            f"👑 Admin: {admin_username}\n"
            f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀",
            parse_mode="HTML"
        )
        
        logger.info(f"✅ {solicitante_username} aceptado en {alianza_id} por {admin_username}")
        
    elif accion == "rechazar":
        # ========== RECHAZAR SOLICITUD ==========
        try:
            datos = load_json(ALIANZA_DATOS_FILE) or {}
            alianza = datos.get(alianza_id, {})
            nombre_alianza = alianza.get("nombre", alianza_id)
            
            await context.bot.send_message(
                chat_id=solicitante_id,
                text=f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
                     f"❌ <b>SOLICITUD RECHAZADA</b>\n"
                     f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
                     f"Tu solicitud para unirte a <b>{nombre_alianza}</b> [{alianza_id}] "
                     f"ha sido rechazada.\n\n"
                     f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀",
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"❌ Error notificando a {solicitante_id}: {e}")
        
        await query.edit_message_text(
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
            f"❌ <b>SOLICITUD RECHAZADA</b>\n"
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
            f"👤 Usuario: {solicitante_username}\n"
            f"🌍 Alianza: {alianza_id}\n"
            f"👑 Admin: {admin_username}\n"
            f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀",
            parse_mode="HTML"
        )
        
        logger.info(f"❌ {solicitante_username} rechazado en {alianza_id} por {admin_username}")

# ================= DONACIONES =================

@requiere_login
async def iniciar_donacion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """💰 Inicia el proceso de donación"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    alianza_id = query.data.replace("alianza_donar_", "")
    
    # Verificar que pertenezca a la alianza
    alianza_actual, _ = obtener_alianza_usuario(user_id)
    if alianza_actual != alianza_id:
        await query.answer("❌ No perteneces a esta alianza", show_alert=True)
        return
    
    # Obtener recursos del usuario
    recursos_data = load_json(RECURSOS_FILE) or {}
    recursos = recursos_data.get(str(user_id), {"metal": 0, "cristal": 0, "deuterio": 0})
    
    # Guardar alianza_id en contexto
    context.user_data['donacion_alianza'] = alianza_id
    
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"💰 <b>DONAR METAL</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"Tus recursos disponibles: 🔩 {abreviar_numero(recursos.get('metal', 0))}\n\n"
        f"Escribe la cantidad de metal que deseas donar:\n\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    )
    
    await query.edit_message_text(
        text=mensaje,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ CANCELAR", callback_data=f"menu_alianza")
        ]])
    )
    
    return DONACION_METAL

async def recibir_donacion_metal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📝 Recibe cantidad de metal para donar"""
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
    
    if cantidad <= 0:
        await update.message.reply_text(
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
            f"❌ <b>ERROR</b>\n"
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
            f"La cantidad debe ser mayor a 0.\n\n"
            f"<i>Escribe la cantidad o envía /cancelar:</i>",
            parse_mode="HTML"
        )
        return DONACION_METAL
    
    # Verificar recursos
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
    
    # Guardar cantidad
    context.user_data['donacion_metal'] = cantidad
    
    # Pedir cristal
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"💰 <b>DONAR CRISTAL</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"Tus recursos disponibles: 💎 {abreviar_numero(recursos.get('cristal', 0))}\n\n"
        f"Escribe la cantidad de cristal que deseas donar:\n\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    )
    
    await update.message.reply_text(
        text=mensaje,
        parse_mode="HTML"
    )
    
    return DONACION_CRISTAL

async def recibir_donacion_cristal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📝 Recibe cantidad de cristal para donar"""
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
    
    if cantidad <= 0:
        await update.message.reply_text(
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
            f"❌ <b>ERROR</b>\n"
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
            f"La cantidad debe ser mayor a 0.\n\n"
            f"<i>Escribe la cantidad o envía /cancelar:</i>",
            parse_mode="HTML"
        )
        return DONACION_CRISTAL
    
    # Verificar recursos
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
    
    # Guardar cantidad
    context.user_data['donacion_cristal'] = cantidad
    
    # Pedir deuterio
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"💰 <b>DONAR DEUTERIO</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"Tus recursos disponibles: 🧪 {abreviar_numero(recursos.get('deuterio', 0))}\n\n"
        f"Escribe la cantidad de deuterio que deseas donar:\n\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    )
    
    await update.message.reply_text(
        text=mensaje,
        parse_mode="HTML"
    )
    
    return DONACION_DEUTERIO

async def recibir_donacion_deuterio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📝 Recibe cantidad de deuterio y confirma donación"""
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
    
    if cantidad <= 0:
        await update.message.reply_text(
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
            f"❌ <b>ERROR</b>\n"
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
            f"La cantidad debe ser mayor a 0.\n\n"
            f"<i>Escribe la cantidad o envía /cancelar:</i>",
            parse_mode="HTML"
        )
        return DONACION_DEUTERIO
    
    # Verificar recursos
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
    
    # Obtener cantidades
    metal = context.user_data.get('donacion_metal', 0)
    cristal = context.user_data.get('donacion_cristal', 0)
    deuterio = cantidad
    
    # Confirmación
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"✅ <b>CONFIRMAR DONACIÓN</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"Vas a donar a la alianza:\n\n"
        f"🔩 Metal: {abreviar_numero(metal)}\n"
        f"💎 Cristal: {abreviar_numero(cristal)}\n"
        f"🧪 Deuterio: {abreviar_numero(deuterio)}\n\n"
        f"¿Confirmas esta donación?\n\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("✅ CONFIRMAR", callback_data=f"alianza_confirmar_donacion_{alianza_id}_{metal}_{cristal}_{deuterio}"),
            InlineKeyboardButton("❌ CANCELAR", callback_data="menu_alianza")
        ]
    ]
    
    await update.message.reply_text(
        text=mensaje,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )
    
    return ConversationHandler.END

@requiere_login
async def confirmar_donacion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """✅ Ejecuta la donación confirmada"""
    query = update.callback_query
    await query.answer()
    
    partes = query.data.split("_")
    alianza_id = partes[3]
    metal = int(partes[4])
    cristal = int(partes[5])
    deuterio = int(partes[6])
    
    user_id = query.from_user.id
    username_tag = AuthSystem.obtener_username(user_id)
    
    # ========== 1. DESCONTAR RECURSOS DEL USUARIO ==========
    recursos_data = load_json(RECURSOS_FILE) or {}
    recursos = recursos_data.get(str(user_id), {})
    
    recursos['metal'] = recursos.get('metal', 0) - metal
    recursos['cristal'] = recursos.get('cristal', 0) - cristal
    recursos['deuterio'] = recursos.get('deuterio', 0) - deuterio
    
    recursos_data[str(user_id)] = recursos
    save_json(RECURSOS_FILE, recursos_data)
    
    # ========== 2. SUMAR AL BANCO DE LA ALIANZA ==========
    banco = load_json(ALIANZA_BANCO_FILE) or {}
    
    if alianza_id not in banco:
        banco[alianza_id] = {"metal": 0, "cristal": 0, "deuterio": 0}
    
    banco[alianza_id]['metal'] = banco[alianza_id].get('metal', 0) + metal
    banco[alianza_id]['cristal'] = banco[alianza_id].get('cristal', 0) + cristal
    banco[alianza_id]['deuterio'] = banco[alianza_id].get('deuterio', 0) + deuterio
    
    save_json(ALIANZA_BANCO_FILE, banco)
    
    # ========== 3. MENSAJE DE ÉXITO ==========
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"✅ <b>DONACIÓN COMPLETADA</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"Has donado a la alianza:\n\n"
        f"🔩 Metal: {abreviar_numero(metal)}\n"
        f"💎 Cristal: {abreviar_numero(cristal)}\n"
        f"🧪 Deuterio: {abreviar_numero(deuterio)}\n\n"
        f"💰 Recursos descontados de tu cuenta.\n"
        f"🏦 Recursos añadidos al banco de la alianza.\n\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    )
    
    keyboard = [
        [InlineKeyboardButton("🌍 VOLVER A ALIANZA", callback_data="menu_alianza")],
        [InlineKeyboardButton("🏠 MENÚ PRINCIPAL", callback_data="menu_principal")]
    ]
    
    await query.edit_message_text(
        text=mensaje,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )
    
    logger.info(f"💰 {username_tag} donó {metal}M {cristal}C {deuterio}D a {alianza_id}")

# ================= LISTA DE MIEMBROS =================

@requiere_login
async def ver_miembros(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📋 Muestra la lista de miembros de la alianza"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    alianza_id = query.data.replace("alianza_miembros_", "")
    
    # Verificar que pertenezca a la alianza
    alianza_actual, _ = obtener_alianza_usuario(user_id)
    if alianza_actual != alianza_id:
        await query.answer("❌ No perteneces a esta alianza", show_alert=True)
        return
    
    # Obtener datos
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
                InlineKeyboardButton("◀️ VOLVER", callback_data=f"menu_alianza")
            ]])
        )
        return
    
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"📋 <b>MIEMBROS DE {alianza.get('nombre', 'ALIANZA')}</b> [{alianza_id}]\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
    )
    
    # Separar por rangos
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
        [InlineKeyboardButton("◀️ VOLVER", callback_data=f"menu_alianza")],
        [InlineKeyboardButton("🏠 MENÚ PRINCIPAL", callback_data="menu_principal")]
    ]
    
    await query.edit_message_text(
        text=mensaje,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

# ================= SALIR DE ALIANZA =================

@requiere_login
async def salir_alianza(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🚪 Sale de la alianza (solo miembros, no fundadores)"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    username_tag = AuthSystem.obtener_username(user_id)
    alianza_id = query.data.replace("alianza_salir_", "")
    
    # Verificar que no sea fundador
    if es_fundador_alianza(user_id, alianza_id):
        await query.answer("❌ Los fundadores no pueden salir, deben disolver la alianza", show_alert=True)
        return
    
    # Eliminar de miembros
    miembros = load_json(ALIANZA_MIEMBROS_FILE) or {}
    if alianza_id in miembros and str(user_id) in miembros[alianza_id]:
        del miembros[alianza_id][str(user_id)]
        save_json(ALIANZA_MIEMBROS_FILE, miembros)
        
        # Quitar permisos de retiro
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

# ================= PANEL DE ADMINISTRACIÓN DE ALIANZA =================

@requiere_login
async def panel_admin_alianza(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """⚙️ Panel de administración de alianza"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    alianza_id = query.data.replace("alianza_admin_", "")
    
    # Verificar permisos de admin
    if not es_admin_alianza(user_id, alianza_id):
        await query.answer("❌ No tienes permisos de administrador", show_alert=True)
        return
    
    datos = load_json(ALIANZA_DATOS_FILE) or {}
    alianza = datos.get(alianza_id, {})
    
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"⚙️ <b>ADMINISTRACIÓN DE {alianza.get('nombre', 'ALIANZA')}</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"Selecciona una opción:\n\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    )
    
    keyboard = [
        [InlineKeyboardButton("📥 SOLICITUDES PENDIENTES", callback_data=f"alianza_solicitudes_{alianza_id}")],
        [InlineKeyboardButton("🔑 GESTIONAR PERMISOS", callback_data=f"alianza_permisos_{alianza_id}")],
        [InlineKeyboardButton("❌ EXPULSAR MIEMBRO", callback_data=f"alianza_expulsar_{alianza_id}")],
        [InlineKeyboardButton("📝 EDITAR DESCRIPCIÓN", callback_data=f"alianza_editar_{alianza_id}")]
    ]
    
    # Solo fundador puede disolver
    if es_fundador_alianza(user_id, alianza_id):
        keyboard.append([InlineKeyboardButton("⚠️ DISOLVER ALIANZA", callback_data=f"alianza_disolver_{alianza_id}")])
    
    keyboard.append([InlineKeyboardButton("◀️ VOLVER", callback_data=f"menu_alianza")])
    
    await query.edit_message_text(
        text=mensaje,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

@requiere_login
async def gestionar_permisos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🔑 Gestiona permisos de retiro"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    alianza_id = query.data.replace("alianza_permisos_", "")
    
    # Verificar permisos de admin
    if not es_admin_alianza(user_id, alianza_id):
        await query.answer("❌ No tienes permisos de administrador", show_alert=True)
        return
    
    # Obtener datos
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
    
    # Crear botones para miembros (máximo 12)
    keyboard = []
    fila = []
    
    for i, (uid, miembro) in enumerate(list(alianza_miembros.items())[:12]):
        if int(uid) == alianza.get("fundador"):
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
    
    keyboard.append([InlineKeyboardButton("◀️ VOLVER", callback_data=f"alianza_admin_{alianza_id}")])
    
    await query.edit_message_text(
        text=mensaje,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

@requiere_login
async def toggle_permiso(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🔄 Activa/desactiva permiso de retiro"""
    query = update.callback_query
    await query.answer()
    
    partes = query.data.split("_")
    alianza_id = partes[3]
    miembro_id = int(partes[4])
    
    admin_id = query.from_user.id
    
    # Verificar permisos de admin
    if not es_admin_alianza(admin_id, alianza_id):
        await query.answer("❌ No tienes permisos de administrador", show_alert=True)
        return
    
    # Obtener permisos actuales
    permisos = load_json(ALIANZA_PERMISOS_FILE) or {}
    if alianza_id not in permisos:
        permisos[alianza_id] = {"retiro": []}
    
    if miembro_id in permisos[alianza_id].get("retiro", []):
        permisos[alianza_id]["retiro"].remove(miembro_id)
        accion = "quitado"
    else:
        if "retiro" not in permisos[alianza_id]:
            permisos[alianza_id]["retiro"] = []
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
    """❌ Cancela la conversación actual"""
    user_id = update.effective_user.id
    username_tag = AuthSystem.obtener_username(user_id)
    
    keys_to_clear = ['alianza_nombre', 'donacion_alianza', 'donacion_metal', 
                     'donacion_cristal', 'retiro_alianza', 'retiro_metal', 
                     'retiro_cristal']
    
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
    """🎯 Handler para callbacks de alianza"""
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
    
    return ConversationHandler.END

# ================= CONFIGURAR CONVERSATION HANDLERS =================

def obtener_conversation_handlers():
    """🔄 Retorna los ConversationHandlers para alianza"""
    
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
    
    return [crear_handler, buscar_handler, donacion_handler]

# ================= EXPORTAR =================

__all__ = [
    'menu_alianza_principal',
    'alianza_callback_handler',
    'obtener_conversation_handlers',
    'inicializar_archivos_alianza'
]
