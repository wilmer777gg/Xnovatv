#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#██████╗ ███████╗████████╗██████╗  █████╗ ██╗     ███████╗
#██╔══██╗██╔════╝╚══██╔══╝██╔══██╗██╔══██╗██║     ██╔════╝
#██████╔╝███████╗   ██║   ██████╔╝███████║██║     ███████╗
#██╔══██╗╚════██║   ██║   ██╔══██╗██╔══██║██║     ╚════██║
#██║  ██║███████║   ██║   ██║  ██║██║  ██║███████╗███████║
#╚═╝  ╚═╝╚══════╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚══════╝

#🚀 ASTRO.IO v2.4.5 🚀
#👑 usuarios.py - GESTIÓN DE USUARIOS Y PANEL DE ADMINISTRACIÓN
#===========================================================
#✅ NOTIFICACIONES A ADMIN CORREGIDAS
#✅ BOTONES DIRECTOS EN LISTA DE PENDIENTES
#✅ FUNCIÓN notificar_admins() IMPORTADA DE LOGIN
#✅ BOTÓN DE MANTENIMIENTO EN PANEL ADMIN
#===========================================================

import os
import sys
import json
import logging
import io
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters, CallbackQueryHandler

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from login import AuthSystem, ADMIN_USER_ID, requiere_admin, notificar_admins
from database import load_json, save_json
from utils import abreviar_numero

logger = logging.getLogger(__name__)

# ================= CONSTANTES =================
DATA_DIR = "data"
BACKUP_DIR = "backups"
DATA_FILE = os.path.join(DATA_DIR, "data.json")
AUTHORIZED_USERS_FILE = os.path.join(DATA_DIR, "authorized_users.json")
ADMINS_FILE = os.path.join(DATA_DIR, "admin.json")
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")
RECURSOS_FILE = os.path.join(DATA_DIR, "recursos.json")
RECURSOS_USUARIO_FILE = os.path.join(DATA_DIR, "recursos_usuario.json")
MINAS_FILE = os.path.join(DATA_DIR, "minas.json")
EDIFICIOS_USUARIO_FILE = os.path.join(DATA_DIR, "edificios_usuario.json")
CAMPOS_FILE = os.path.join(DATA_DIR, "campos.json")
FLOTA_USUARIO_FILE = os.path.join(DATA_DIR, "flota_usuario.json")
DEFENSA_USUARIO_FILE = os.path.join(DATA_DIR, "defensa_usuario.json")
INVESTIGACIONES_USUARIO_FILE = os.path.join(DATA_DIR, "investigaciones_usuario.json")
COLAS_EDIFICIOS_FILE = os.path.join(DATA_DIR, "colas_edificios.json")
COLAS_FLOTA_FILE = os.path.join(DATA_DIR, "colas_flota.json")
COLAS_DEFENSA_FILE = os.path.join(DATA_DIR, "colas_defensa.json")
GALAXIA_FILE = os.path.join(DATA_DIR, "galaxia.json")
ALIANZA_DATOS_FILE = os.path.join(DATA_DIR, "alianza_datos.json")
ALIANZA_MIEMBROS_FILE = os.path.join(DATA_DIR, "alianza_miembros.json")
ALIANZA_BANCO_FILE = os.path.join(DATA_DIR, "alianza_banco.json")
ALIANZA_PERMISOS_FILE = os.path.join(DATA_DIR, "alianza_permisos.json")

# Archivos de misiones
try:
    from base_flotas import MISIONES_FLOTA_FILE, BAJAS_FLOTA_FILE
except:
    MISIONES_FLOTA_FILE = os.path.join(DATA_DIR, "misiones_flota.json")
    BAJAS_FLOTA_FILE = os.path.join(DATA_DIR, "bajas_flota.json")

# ========== ESTADOS PARA CONVERSATION HANDLERS ==========
SELECCIONAR_USUARIO, INGRESAR_METAL, INGRESAR_CRISTAL, INGRESAR_DEUTERIO = range(4)
SELECCIONAR_USUARIO_NAVE, INGRESAR_NAVE, INGRESAR_CANTIDAD_NAVE = range(4, 7)
SELECCIONAR_USUARIO_DEFENSA, INGRESAR_DEFENSA, INGRESAR_CANTIDAD_DEFENSA = range(7, 10)
SELECCIONAR_USUARIO_EDIFICIO, INGRESAR_EDIFICIO, INGRESAR_NIVEL = range(10, 13)
SELECCIONAR_USUARIO_INVESTIGACION, INGRESAR_INVESTIGACION, INGRESAR_NIVEL_INV = range(13, 16)
SELECCIONAR_USUARIO_ADMIN, CONFIRMAR_ADMIN = range(16, 18)
INGRESAR_ANUNCIO = 18
ESPERANDO_ARCHIVO_BACKUP = 50

# ================= FUNCIONES AUXILIARES =================

def obtener_username_display(user_id: int) -> str:
    """Obtiene username formateado para mostrar"""
    username = AuthSystem.obtener_username(user_id)
    if not username or username == f"@{user_id}":
        return f"Usuario {user_id}"
    return username

def obtener_lista_usuarios_autorizados() -> list:
    """Obtiene lista de usuarios autorizados con sus nombres"""
    autorizados = load_json(AUTHORIZED_USERS_FILE) or []
    usuarios = []
    for uid in autorizados:
        username = obtener_username_display(uid)
        usuarios.append((uid, username))
    return usuarios

def es_admin_principal(user_id: int) -> bool:
    """Verifica si el usuario es el administrador principal"""
    return user_id == ADMIN_USER_ID

# ================= FUNCIONES DE BACKUP =================

def obtener_todos_archivos_json() -> list:
    """📋 Obtiene lista de TODOS los archivos JSON del sistema"""
    return [
        ("data.json", DATA_FILE),
        ("authorized_users.json", AUTHORIZED_USERS_FILE),
        ("admin.json", ADMINS_FILE),
        ("config.json", CONFIG_FILE),
        ("recursos.json", RECURSOS_FILE),
        ("recursos_usuario.json", RECURSOS_USUARIO_FILE),
        ("minas.json", MINAS_FILE),
        ("edificios_usuario.json", EDIFICIOS_USUARIO_FILE),
        ("campos.json", CAMPOS_FILE),
        ("flota_usuario.json", FLOTA_USUARIO_FILE),
        ("defensa_usuario.json", DEFENSA_USUARIO_FILE),
        ("investigaciones_usuario.json", INVESTIGACIONES_USUARIO_FILE),
        ("colas_edificios.json", COLAS_EDIFICIOS_FILE),
        ("colas_flota.json", COLAS_FLOTA_FILE),
        ("colas_defensa.json", COLAS_DEFENSA_FILE),
        ("galaxia.json", GALAXIA_FILE),
        ("misiones_flota.json", MISIONES_FLOTA_FILE),
        ("bajas_flota.json", BAJAS_FLOTA_FILE),
        ("alianza_datos.json", ALIANZA_DATOS_FILE),
        ("alianza_miembros.json", ALIANZA_MIEMBROS_FILE),
        ("alianza_banco.json", ALIANZA_BANCO_FILE),
        ("alianza_permisos.json", ALIANZA_PERMISOS_FILE),
    ]

def crear_backup_completo() -> tuple:
    """💾 Crea un backup completo de TODOS los archivos JSON"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre_archivo = f"astroio_backup_{timestamp}.txt"
    
    os.makedirs(BACKUP_DIR, exist_ok=True)
    
    contenido = []
    resumen = []
    total_archivos = 0
    total_tamano = 0
    
    contenido.append("=" * 80)
    contenido.append(f"🚀 ASTRO.IO - BACKUP COMPLETO")
    contenido.append(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    contenido.append(f"🆔 Admin: {ADMIN_USER_ID}")
    contenido.append(f"📁 Versión: v2.4.0")
    contenido.append("=" * 80)
    contenido.append("")
    
    for nombre, ruta in obtener_todos_archivos_json():
        try:
            if os.path.exists(ruta):
                with open(ruta, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                json_str = json.dumps(data, indent=2, ensure_ascii=False)
                tamano = len(json_str)
                total_tamano += tamano
                total_archivos += 1
                
                if isinstance(data, dict):
                    num_keys = len(data)
                    resumen.append(f"   ✅ {nombre}: {num_keys} registros, {tamano} bytes")
                elif isinstance(data, list):
                    num_items = len(data)
                    resumen.append(f"   ✅ {nombre}: {num_items} items, {tamano} bytes")
                else:
                    resumen.append(f"   ✅ {nombre}: {tamano} bytes")
                
                contenido.append(f"📄 ARCHIVO: {nombre}")
                contenido.append(f"📊 TAMAÑO: {tamano} bytes")
                contenido.append("-" * 40)
                contenido.append(json_str)
                contenido.append("")
                contenido.append("=" * 40)
                contenido.append("")
            else:
                resumen.append(f"   ⚠️ {nombre}: No existe (se creará al importar)")
        except Exception as e:
            logger.error(f"❌ Error leyendo {nombre}: {e}")
            resumen.append(f"   ❌ {nombre}: Error - {str(e)[:50]}")
    
    resumen_completo = [
        "=" * 80,
        "📊 RESUMEN DEL BACKUP",
        "=" * 80,
        f"📁 Total archivos: {total_archivos}",
        f"💾 Tamaño total: {total_tamano} bytes ({total_tamano/1024:.2f} KB)",
        f"📅 Timestamp: {timestamp}",
        "-" * 40,
        *resumen,
        "=" * 80,
        "",
    ]
    
    contenido_final = resumen_completo + contenido
    
    ruta_local = os.path.join(BACKUP_DIR, nombre_archivo)
    with open(ruta_local, 'w', encoding='utf-8') as f:
        f.write("\n".join(contenido_final))
    
    contenido_bytes = "\n".join(contenido_final).encode('utf-8')
    
    return contenido_bytes, nombre_archivo, resumen_completo

def restaurar_backup_desde_texto(texto: str) -> tuple:
    """📥 Restaura un backup desde el contenido del archivo .txt"""
    estadisticas = {
        "archivos_restaurados": 0,
        "archivos_omitidos": 0,
        "errores": 0,
        "detalle": []
    }
    
    try:
        secciones = texto.split("📄 ARCHIVO: ")
        
        for seccion in secciones[1:]:
            try:
                lineas = seccion.split("\n")
                nombre_archivo = lineas[0].strip()
                
                json_start = 0
                for i, linea in enumerate(lineas):
                    if linea.startswith("{"):
                        json_start = i
                        break
                
                if json_start > 0:
                    json_str = "\n".join(lineas[json_start:])
                    if "=" * 40 in json_str:
                        json_str = json_str.split("=" * 40)[0].strip()
                    
                    data = json.loads(json_str)
                    
                    ruta = None
                    for name, path in obtener_todos_archivos_json():
                        if name == nombre_archivo:
                            ruta = path
                            break
                    
                    if ruta:
                        with open(ruta, 'w', encoding='utf-8') as f:
                            json.dump(data, f, indent=2, ensure_ascii=False)
                        estadisticas["archivos_restaurados"] += 1
                        estadisticas["detalle"].append(f"✅ {nombre_archivo}: Restaurado")
                        logger.info(f"✅ Archivo restaurado: {nombre_archivo}")
                    else:
                        estadisticas["archivos_omitidos"] += 1
                        estadisticas["detalle"].append(f"⚠️ {nombre_archivo}: Ruta no encontrada")
                else:
                    estadisticas["errores"] += 1
                    estadisticas["detalle"].append(f"❌ {nombre_archivo}: No se encontró JSON válido")
                    
            except json.JSONDecodeError as e:
                estadisticas["errores"] += 1
                estadisticas["detalle"].append(f"❌ {nombre_archivo}: JSON inválido - {str(e)[:50]}")
            except Exception as e:
                estadisticas["errores"] += 1
                estadisticas["detalle"].append(f"❌ {nombre_archivo}: Error - {str(e)[:50]}")
        
        return True, "✅ Backup restaurado correctamente", estadisticas
        
    except Exception as e:
        logger.error(f"❌ Error restaurando backup: {e}")
        return False, f"❌ Error al restaurar backup: {str(e)}", estadisticas

# ================= 💾 MENÚ DE BACKUP =================

@requiere_admin
async def backup_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """💾 Muestra el menú principal de backup"""
    query = update.callback_query
    await query.answer()
    
    admin_id = query.from_user.id
    admin_username = AuthSystem.obtener_username(admin_id)
    es_principal = (admin_id == ADMIN_USER_ID)
    
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"💾 <b>SISTEMA DE BACKUP</b> - {admin_username}\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"📤 <b>EXPORTAR:</b> Crea un archivo .txt con TODOS los datos\n"
        f"   • Usuarios y autorizaciones\n"
        f"   • Recursos y edificios\n"
        f"   • Flotas y defensas\n"
        f"   • Investigaciones y colas\n"
        f"   • Galaxia y misiones\n"
        f"   • Alianzas y bancos\n\n"
    )
    
    if es_principal:
        mensaje += (
            f"📥 <b>IMPORTAR:</b> Restaura datos desde un archivo .txt\n"
            f"   ⚠️ <b>SOLO EL ADMIN PRINCIPAL</b> puede importar\n"
            f"   ⚠️ Esta acción SOBRESCRIBIRÁ los datos actuales\n\n"
        )
    else:
        mensaje += (
            f"🔒 <b>IMPORTAR:</b> Solo disponible para el administrador principal\n\n"
        )
    
    keyboard = [
        [InlineKeyboardButton("📤 EXPORTAR BACKUP", callback_data="admin_backup_exportar")],
    ]
    
    if es_principal:
        keyboard.append([InlineKeyboardButton("📥 IMPORTAR BACKUP", callback_data="admin_backup_importar")])
    
    keyboard.append([InlineKeyboardButton("📁 VER BACKUPS", callback_data="admin_backup_listar")])
    keyboard.append([InlineKeyboardButton("◀️ VOLVER", callback_data="menu_admin")])
    
    await query.edit_message_text(
        text=mensaje,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

@requiere_admin
async def backup_exportar_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📤 Exporta y envía el backup completo"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        "💾 <b>CREANDO BACKUP...</b>\n"
        "🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        "⏳ Por favor espera, esto puede tomar unos segundos.\n\n"
        "🌀 ━━━━━━━━━━━━━━━━━━━ 🌀",
        parse_mode="HTML"
    )
    
    try:
        contenido_bytes, nombre_archivo, resumen = crear_backup_completo()
        
        await context.bot.send_document(
            chat_id=query.from_user.id,
            document=io.BytesIO(contenido_bytes),
            filename=nombre_archivo,
            caption=(
                f"✅ <b>BACKUP COMPLETO</b>\n"
                f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"📁 {nombre_archivo}"
            ),
            parse_mode="HTML"
        )
        
        mensaje = (
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
            f"✅ <b>BACKUP EXPORTADO CORRECTAMENTE</b>\n"
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
            f"📁 Archivo: <code>{nombre_archivo}</code>\n"
            f"💾 Tamaño: {len(contenido_bytes)} bytes\n"
            f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"📤 El archivo ha sido enviado a este chat.\n"
            f"💾 También se guardó una copia en la carpeta <code>backups/</code>\n\n"
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
        )
        
        keyboard = [[InlineKeyboardButton("◀️ VOLVER AL MENÚ BACKUP", callback_data="admin_backup")]]
        
    except Exception as e:
        logger.error(f"❌ Error creando backup: {e}")
        mensaje = f"❌ <b>ERROR AL CREAR BACKUP</b>\n\n{str(e)}"
        keyboard = [[InlineKeyboardButton("◀️ VOLVER", callback_data="admin_backup")]]
    
    await context.bot.send_message(
        chat_id=query.from_user.id,
        text=mensaje,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

@requiere_admin
async def backup_importar_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📥 Menú para importar backup"""
    query = update.callback_query
    await query.answer()
    
    admin_id = query.from_user.id
    
    if admin_id != ADMIN_USER_ID:
        await query.edit_message_text(
            "❌ <b>ACCESO DENEGADO</b>\n\n"
            "Solo el administrador principal puede importar backups.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ VOLVER", callback_data="admin_backup")
            ]])
        )
        return
    
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"📥 <b>IMPORTAR BACKUP</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"⚠️ <b>¡ADVERTENCIA!</b>\n\n"
        f"Esta acción SOBRESCRIBIRÁ todos los datos actuales:\n"
        f"• Usuarios y autorizaciones\n"
        f"• Recursos y edificios\n"
        f"• Flotas y defensas\n"
        f"• Investigaciones y colas\n"
        f"• Galaxia y misiones\n"
        f"• Alianzas y bancos\n\n"
        f"<b>Por favor, envía el archivo .txt del backup</b>\n\n"
        f"<i>El archivo debe ser el mismo que generó el bot con 'EXPORTAR BACKUP'</i>\n\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    )
    
    keyboard = [[InlineKeyboardButton("◀️ CANCELAR", callback_data="admin_backup")]]
    
    await query.edit_message_text(
        text=mensaje,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )
    
    return ESPERANDO_ARCHIVO_BACKUP

async def backup_recibir_archivo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📥 Recibe y procesa el archivo de backup"""
    user_id = update.effective_user.id
    
    if user_id != ADMIN_USER_ID:
        await update.message.reply_text(
            "❌ <b>ACCESO DENEGADO</b>\n\n"
            "Solo el administrador principal puede importar backups.",
            parse_mode="HTML"
        )
        return ConversationHandler.END
    
    document = update.message.document
    
    if not document or not document.file_name.endswith('.txt'):
        await update.message.reply_text(
            "❌ Por favor, envía un archivo .txt válido.",
            parse_mode="HTML"
        )
        return ESPERANDO_ARCHIVO_BACKUP
    
    await update.message.reply_text(
        "🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        "📥 <b>PROCESANDO BACKUP...</b>\n"
        "🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        "⏳ Por favor espera, esto puede tomar unos segundos.\n\n"
        "🌀 ━━━━━━━━━━━━━━━━━━━ 🌀",
        parse_mode="HTML"
    )
    
    try:
        file = await context.bot.get_file(document.file_id)
        file_bytes = await file.download_as_bytearray()
        contenido = file_bytes.decode('utf-8')
        
        exito, mensaje, estadisticas = restaurar_backup_desde_texto(contenido)
        
        resultado = (
            f"{'✅' if exito else '⚠️'} <b>RESULTADO DE LA IMPORTACIÓN</b>\n"
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
            f"📊 <b>ESTADÍSTICAS:</b>\n"
            f"   ✅ Restaurados: {estadisticas['archivos_restaurados']}\n"
            f"   ⚠️ Omitidos: {estadisticas['archivos_omitidos']}\n"
            f"   ❌ Errores: {estadisticas['errores']}\n\n"
            f"📋 <b>DETALLE:</b>\n"
        )
        
        for detalle in estadisticas["detalle"][:15]:
            resultado += f"   {detalle}\n"
        
        if len(estadisticas["detalle"]) > 15:
            resultado += f"   ... y {len(estadisticas['detalle']) - 15} más\n"
        
        resultado += f"\n🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
        
        keyboard = [[InlineKeyboardButton("◀️ VOLVER AL PANEL", callback_data="menu_admin")]]
        
        await update.message.reply_text(
            text=resultado,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
        
        logger.info(f"✅ Backup importado por admin principal {user_id}")
        
    except Exception as e:
        logger.error(f"❌ Error importando backup: {e}")
        await update.message.reply_text(
            f"❌ <b>ERROR AL IMPORTAR BACKUP</b>\n\n{str(e)}",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ VOLVER", callback_data="admin_backup")
            ]])
        )
    
    return ConversationHandler.END

@requiere_admin
async def backup_listar_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📁 Muestra la lista de backups disponibles"""
    query = update.callback_query
    await query.answer()
    
    os.makedirs(BACKUP_DIR, exist_ok=True)
    
    try:
        archivos = os.listdir(BACKUP_DIR)
        backups = [f for f in archivos if f.startswith("astroio_backup_") and f.endswith(".txt")]
        backups.sort(reverse=True)
        
        mensaje = (
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
            f"📁 <b>BACKUPS DISPONIBLES</b>\n"
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        )
        
        if not backups:
            mensaje += "📭 No hay backups guardados en la carpeta <code>backups/</code>\n\n"
            mensaje += "Usa 'EXPORTAR BACKUP' para crear tu primer backup.\n\n"
        else:
            mensaje += f"📊 Total: {len(backups)} backups\n\n"
            
            for i, backup in enumerate(backups[:10], 1):
                ruta = os.path.join(BACKUP_DIR, backup)
                tamano = os.path.getsize(ruta)
                fecha_mod = datetime.fromtimestamp(os.path.getmtime(ruta))
                
                mensaje += f"{i}. <code>{backup}</code>\n"
                mensaje += f"   💾 {tamano} bytes ({tamano/1024:.2f} KB)\n"
                mensaje += f"   📅 {fecha_mod.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            
            if len(backups) > 10:
                mensaje += f"... y {len(backups) - 10} backups más\n"
        
        mensaje += f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
        
        keyboard = [
            [InlineKeyboardButton("◀️ VOLVER AL MENÚ BACKUP", callback_data="admin_backup")],
            [InlineKeyboardButton("🏠 MENÚ PRINCIPAL", callback_data="menu_principal")]
        ]
        
    except Exception as e:
        logger.error(f"❌ Error listando backups: {e}")
        mensaje = f"❌ <b>Error al listar backups</b>\n\n{str(e)}"
        keyboard = [[InlineKeyboardButton("◀️ VOLVER", callback_data="admin_backup")]]
    
    await query.edit_message_text(
        text=mensaje,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

@requiere_admin
async def backup_limpiar_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🧹 Limpia backups antiguos (solo admin principal)"""
    query = update.callback_query
    await query.answer()
    
    admin_id = query.from_user.id
    
    if admin_id != ADMIN_USER_ID:
        await query.edit_message_text(
            "❌ <b>ACCESO DENEGADO</b>\n\n"
            "Solo el administrador principal puede limpiar backups.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ VOLVER", callback_data="admin_backup")
            ]])
        )
        return
    
    try:
        os.makedirs(BACKUP_DIR, exist_ok=True)
        archivos = os.listdir(BACKUP_DIR)
        backups = [f for f in archivos if f.startswith("astroio_backup_") and f.endswith(".txt")]
        backups.sort()
        
        eliminados = 0
        espacio_liberado = 0
        
        if len(backups) > 10:
            for backup in backups[:-10]:
                ruta = os.path.join(BACKUP_DIR, backup)
                espacio_liberado += os.path.getsize(ruta)
                os.remove(ruta)
                eliminados += 1
        
        mensaje = (
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
            f"🧹 <b>BACKUPS LIMPIADOS</b>\n"
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
            f"✅ Eliminados: {eliminados} backups\n"
            f"💾 Espacio liberado: {espacio_liberado/1024:.2f} KB\n"
            f"📁 Se mantienen los últimos 10 backups\n\n"
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
        )
        
    except Exception as e:
        logger.error(f"❌ Error limpiando backups: {e}")
        mensaje = f"❌ <b>Error al limpiar backups</b>\n\n{str(e)}"
    
    keyboard = [[InlineKeyboardButton("◀️ VOLVER", callback_data="admin_backup")]]
    
    await query.edit_message_text(
        text=mensaje,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

async def backup_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🎯 Handler para callbacks de backup"""
    query = update.callback_query
    data = query.data
    
    if data == "admin_backup":
        await backup_menu_handler(update, context)
    elif data == "admin_backup_exportar":
        await backup_exportar_handler(update, context)
    elif data == "admin_backup_importar":
        return await backup_importar_menu(update, context)
    elif data == "admin_backup_listar":
        await backup_listar_handler(update, context)
    elif data == "admin_backup_limpiar":
        await backup_limpiar_handler(update, context)
    
    return ConversationHandler.END

def obtener_conversation_handlers_backup():
    """🔄 Retorna los ConversationHandlers para backup"""
    backup_import_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(backup_importar_menu, pattern="^admin_backup_importar$")],
        states={
            ESPERANDO_ARCHIVO_BACKUP: [MessageHandler(filters.Document.FileExtension("txt"), backup_recibir_archivo_handler)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar_conversacion_admin)],
        name="admin_backup_import",
        persistent=False
    )
    return [backup_import_handler]

# ================= CANCELAR CONVERSACIÓN =================

async def cancelar_conversacion_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """❌ Cancela la conversación actual"""
    await update.message.reply_text(
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"❌ <b>OPERACIÓN CANCELADA</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("◀️ VOLVER AL PANEL", callback_data="menu_admin")
        ]])
    )
    
    keys_to_clear = [
        'admin_recurso_user', 'admin_recurso_metal', 'admin_recurso_cristal',
        'admin_flota_user', 'admin_flota_nave',
        'admin_defensa_user', 'admin_defensa_tipo',
        'admin_edificio_user', 'admin_edificio_tipo',
        'admin_investigacion_user', 'admin_investigacion_tipo',
        'admin_nuevo_user'
    ]
    
    for key in keys_to_clear:
        if key in context.user_data:
            del context.user_data[key]
    
    return ConversationHandler.END

# ================= HANDLER DE REGISTRO - CORREGIDO =================

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📝 Manejador para el comando /start - Registro de nuevos usuarios"""
    user = update.effective_user
    user_id = user.id
    username = user.first_name or "Comandante"
    
    logger.info(f"📱 Registro: {user_id} (@{username})")
    
    # 🔧 Verificar si el modo mantenimiento está activado
    if AuthSystem.obtener_estado_mantenimiento():
        # Si es ADMIN, puede pasar
        if AuthSystem.es_admin(user_id):
            # Admin puede seguir
            pass
        else:
            # Usuario normal ve mensaje de mantenimiento
            mensaje_mantenimiento = (
                f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
                f"🔧 <b>MANTENIMIENTO PROGRAMADO</b>\n"
                f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
                f"Estimado comandante,\n\n"
                f"El servidor se encuentra en mantenimiento en estos momentos.\n\n"
                f"⚙️ Estamos trabajando para tener el servicio online lo más pronto posible.\n\n"
                f"Por favor, intenta más tarde.\n\n"
                f"Disculpa las molestias.\n\n"
                f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
            )
            
            # Botón de comunidad
            keyboard = [[InlineKeyboardButton("👥 COMUNIDAD", url="https://t.me/+FwdrSAJU5rA5Yzcx")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                text=mensaje_mantenimiento,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
            return
    
    # Verificar si ya está autorizado
    if AuthSystem.esta_autorizado(user_id):
        # Usuario ya autorizado - ir al menú principal
        from menus_principal import menu_principal
        
        class MockMessage:
            def __init__(self, chat_id):
                self.chat = type('obj', (), {'id': chat_id})
        
        class MockCallbackQuery:
            def __init__(self, user_id, username):
                self.from_user = type('obj', (), {
                    'id': user_id,
                    'first_name': username
                })
                self.data = "menu_principal"
                self.message = MockMessage(user_id)
            
            async def answer(self):
                pass
            
            async def edit_message_text(self, text, reply_markup=None, parse_mode=None):
                await context.bot.send_message(
                    chat_id=self.from_user.id,
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode
                )
        
        class MockUpdate:
            def __init__(self, query):
                self.callback_query = query
        
        mock_query = MockCallbackQuery(user_id, username)
        mock_update = MockUpdate(mock_query)
        
        await menu_principal(mock_update, context)
        return
    
    # Verificar si ya está registrado (pendiente)
    if AuthSystem.esta_registrado(user_id):
        await update.message.reply_text(
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
            f"⏳ <b>SOLICITUD PENDIENTE</b>\n"
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
            f"Ya estás registrado.\n"
            f"Espera la aprobación de un administrador.\n\n"
            f"Recibirás un mensaje cuando seas aceptado.\n\n"
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀",
            parse_mode="HTML"
        )
        return
    
    # Registrar nuevo usuario
    AuthSystem.registrar_usuario(user_id, username)
    
    # ========== 🔴 USAR LA FUNCIÓN DE NOTIFICACIÓN DE LOGIN ==========
    notificaciones_enviadas = await notificar_admins(context, user_id, username)
    
    logger.info(f"📨 Notificaciones enviadas: {notificaciones_enviadas}")
    
    # Confirmar al usuario
    await update.message.reply_text(
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"⏳ <b>SOLICITUD ENVIADA</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"Tu solicitud de registro ha sido enviada.\n"
        f"Recibirás un mensaje cuando sea aprobada.\n\n"
        f"Gracias por tu paciencia, comandante.\n\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀",
        parse_mode="HTML"
    )

# ================= 👑 DECISIONES DE ADMIN =================

async def decision_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """👑 Manejador para aceptar/rechazar usuarios"""
    query = update.callback_query
    await query.answer()
    
    try:
        accion, user_id_str = query.data.split("_")
        user_id = int(user_id_str)
    except Exception as e:
        logger.error(f"❌ Error parseando callback: {query.data} - {e}")
        await query.edit_message_text("❌ Datos inválidos", parse_mode="HTML")
        return
    
    admin_id = query.from_user.id
    admin_username = obtener_username_display(admin_id)
    usuario_data = AuthSystem.obtener_usuario(user_id)
    username = usuario_data.get("username", f"Usuario {user_id}")
    
    if accion == "aceptar":
        success, message = AuthSystem.autorizar_usuario(user_id, username.replace('@', ''))
        
        if success:
            # ========== ✅ ENVIAR MENSAJE DE BIENVENIDA ==========
            try:
                from menus_principal import menu_bienvenida
                
                # Obtener el username limpio
                username_limpio = username.replace('@', '') if username.startswith('@') else username
                
                # Enviar bienvenida
                await menu_bienvenida(context, user_id, username_limpio)
                logger.info(f"✅ Bienvenida enviada a {username}")
                
            except Exception as e:
                logger.error(f"❌ Error en menu_bienvenida: {e}")
                
                # FALLBACK: Enviar mensaje simple
                try:
                    mensaje_bienvenida = (
                        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
                        f"✅ <b>¡BIENVENIDO A ASTROIO!</b>\n"
                        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
                        f"¡Has sido autorizado!\n\n"
                        f"Usa /start para comenzar tu aventura espacial.\n\n"
                        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
                    )
                    
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=mensaje_bienvenida,
                        parse_mode="HTML"
                    )
                    logger.info(f"✅ Mensaje de bienvenida simple enviado a {username}")
                    
                except Exception as e2:
                    logger.error(f"❌ Error enviando mensaje simple a {user_id}: {e2}")
            
            # ========== ✅ ACTUALIZAR MENSAJE DEL ADMIN ==========
            await query.edit_message_text(
                f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
                f"✅ <b>USUARIO ACEPTADO</b>\n"
                f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
                f"👤 Usuario: {username}\n"
                f"🆔 ID: <code>{user_id}</code>\n"
                f"👑 Admin: {admin_username}\n"
                f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀",
                parse_mode="HTML"
            )
            logger.info(f"✅ Usuario {username} aceptado por {admin_username}")
        else:
            await query.edit_message_text(
                f"❌ <b>Error al aceptar usuario</b>\n\n{message}",
                parse_mode="HTML"
            )
    
    elif accion == "cancelar":
        AuthSystem.rechazar_usuario(user_id)
        
        # ========== ❌ ENVIAR MENSAJE DE RECHAZO ==========
        try:
            mensaje_rechazo = (
                f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
                f"❌ <b>SOLICITUD RECHAZADA</b>\n"
                f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
                f"Tu solicitud de registro ha sido rechazada.\n\n"
                f"Si crees que esto es un error, contacta con el administrador.\n\n"
                f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
            )
            
            await context.bot.send_message(
                chat_id=user_id,
                text=mensaje_rechazo,
                parse_mode="HTML"
            )
            logger.info(f"✅ Mensaje de rechazo enviado a {username}")
        except Exception as e:
            logger.error(f"❌ Error notificando rechazo a {user_id}: {e}")
        
        # ========== ✅ ACTUALIZAR MENSAJE DEL ADMIN ==========
        await query.edit_message_text(
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
            f"❌ <b>USUARIO RECHAZADO</b>\n"
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
            f"👤 Usuario: {username}\n"
            f"🆔 ID: <code>{user_id}</code>\n"
            f"👑 Admin: {admin_username}\n"
            f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀",
            parse_mode="HTML"
        )
        logger.info(f"❌ Usuario {username} rechazado por {admin_username}")

# ================= 👑 PANEL DE ADMINISTRACIÓN - CON MANTENIMIENTO =================

@requiere_admin
async def mostrar_panel_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """👑 Muestra el panel principal de administración"""
    query = update.callback_query
    if not query:
        logger.error("❌ mostrar_panel_admin sin callback_query")
        return
    
    await query.answer()
    admin_id = query.from_user.id
    admin_username = obtener_username_display(admin_id)
    es_principal = es_admin_principal(admin_id)
    
    usuarios = AuthSystem.obtener_todos_usuarios()
    autorizados = load_json(AUTHORIZED_USERS_FILE) or []
    admins = load_json(ADMINS_FILE) or {}
    pendientes = AuthSystem.obtener_usuarios_pendientes()
    
    total_usuarios = len(usuarios)
    total_autorizados = len(autorizados)
    total_admins = len(admins)
    total_pendientes = len(pendientes)
    
    # 🔧 Obtener estado del mantenimiento
    mantenimiento_activo = AuthSystem.obtener_estado_mantenimiento()
    estado_mant = "🔴 ACTIVADO" if mantenimiento_activo else "🟢 DESACTIVADO"
    texto_boton = "🔴 DESACTIVAR" if mantenimiento_activo else "🟢 ACTIVAR"
    
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"👑 <b>PANEL DE ADMINISTRACIÓN</b> - {admin_username}\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"📊 <b>ESTADÍSTICAS DEL SISTEMA</b>\n"
        f"   ├ 👥 Usuarios totales: {total_usuarios}\n"
        f"   ├ ✅ Autorizados: {total_autorizados}\n"
        f"   ├ ⏳ Pendientes: {total_pendientes}\n"
        f"   ├ 👑 Administradores: {total_admins}\n"
        f"   └ 🆔 Tu ID: <code>{admin_id}</code>\n"
        f"      {'👑 ADMIN PRINCIPAL' if es_principal else '👤 ADMINISTRADOR'}\n\n"
        f"🖥️ <b>ESTADO DEL SERVIDOR</b>\n"
        f"   └ 🔧 MANTENIMIENTO: {estado_mant}\n"
        f"⚙️ <b>HERRAMIENTAS DE ADMINISTRACIÓN</b>\n"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("📋 VER PENDIENTES", callback_data="admin_pendientes"),
            InlineKeyboardButton("📋 LISTA USUARIOS", callback_data="admin_lista_usuarios")
        ],
        [
            InlineKeyboardButton("💰 REGALAR RECURSOS", callback_data="admin_regalar_recursos"),
            InlineKeyboardButton("🚀 REGALAR NAVES", callback_data="admin_regalar_flota")
        ],
        [
            InlineKeyboardButton("🛡️ REGALAR DEFENSAS", callback_data="admin_regalar_defensa"),
            InlineKeyboardButton("🏗️ MODIFICAR NIVEL", callback_data="admin_modificar_nivel")
        ],
        [
            InlineKeyboardButton("🔬 MEJORAR INVEST.", callback_data="admin_mejorar_investigacion"),
            InlineKeyboardButton("📢 ENVIAR ANUNCIO", callback_data="admin_enviar_anuncio")
        ],
        [
            InlineKeyboardButton("🧹 LIMPIAR COLAS", callback_data="admin_limpiar_colas"),
            InlineKeyboardButton("📊 ESTADÍSTICAS", callback_data="admin_estadisticas")
        ],
    ]
    
    if es_principal:
        keyboard.append([
            InlineKeyboardButton("👑 AGREGAR ADMIN", callback_data="admin_agregar"),
            InlineKeyboardButton("🗑️ REMOVER ADMIN", callback_data="admin_remover")
        ])
        keyboard.append([
            InlineKeyboardButton("💾 SISTEMA BACKUP", callback_data="admin_backup"),
            InlineKeyboardButton("⚠️ REINICIO FÁBRICA", callback_data="admin_reinicio_fabrica")
        ])
        # 🔧 Botón de mantenimiento
        keyboard.append([
            InlineKeyboardButton(f"🔧 {texto_boton} MANTENIMIENTO", callback_data="admin_toggle_mantenimiento")
        ])
    else:
        keyboard.append([
            InlineKeyboardButton("💾 EXPORTAR BACKUP", callback_data="admin_backup_exportar"),
            InlineKeyboardButton("📁 VER BACKUPS", callback_data="admin_backup_listar")
        ])
    
    keyboard.append([InlineKeyboardButton("🏠 MENÚ PRINCIPAL", callback_data="menu_principal")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        await query.edit_message_text(
            text=mensaje,
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
        logger.info(f"✅ Panel admin mostrado a {admin_username}")
    except Exception as e:
        logger.error(f"❌ Error mostrando panel admin: {e}")

# ================= 📋 GESTIÓN DE USUARIOS PENDIENTES =================

@requiere_admin
async def admin_pendientes_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📋 Muestra lista de usuarios pendientes con botones de acción"""
    query = update.callback_query
    await query.answer()
    
    pendientes = AuthSystem.obtener_usuarios_pendientes()
    
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"📋 <b>USUARIOS PENDIENTES</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
    )
    
    if not pendientes:
        mensaje += "✅ No hay usuarios pendientes de autorización.\n\n"
        mensaje += f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
        keyboard = [[InlineKeyboardButton("◀️ VOLVER", callback_data="menu_admin")]]
    else:
        mensaje += f"📊 <b>Total: {len(pendientes)} usuarios</b>\n\n"
        
        # Crear teclado con botones para cada usuario
        keyboard = []
        
        for idx, user_id in enumerate(pendientes[:10], 1):
            usuario = AuthSystem.obtener_usuario(user_id)
            username = usuario.get("username", f"Usuario {user_id}")
            nombre = username.replace('@', '') if username.startswith('@') else username
            
            mensaje += f"{idx}. <b>{nombre}</b>\n"
            mensaje += f"   🆔 <code>{user_id}</code>\n"
            mensaje += f"   📅 {usuario.get('fecha_registro', 'Desconocida')[:10]}\n\n"
            
            keyboard.append([
                InlineKeyboardButton(f"✅ ACEPTAR {idx}", callback_data=f"aceptar_{user_id}"),
                InlineKeyboardButton(f"❌ RECHAZAR {idx}", callback_data=f"cancelar_{user_id}")
            ])
        
        if len(pendientes) > 10:
            mensaje += f"... y {len(pendientes) - 10} usuarios más\n\n"
        
        mensaje += f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
        
        keyboard.append([InlineKeyboardButton("◀️ VOLVER", callback_data="menu_admin")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(mensaje, parse_mode="HTML", reply_markup=reply_markup)

@requiere_admin
async def admin_lista_usuarios(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📋 Muestra lista de todos los usuarios"""
    query = update.callback_query
    await query.answer()
    
    usuarios = AuthSystem.obtener_todos_usuarios()
    autorizados = load_json(AUTHORIZED_USERS_FILE) or []
    admins = load_json(ADMINS_FILE) or {}
    
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"📋 <b>TODOS LOS USUARIOS</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
    )
    
    if not usuarios:
        mensaje += "❌ No hay usuarios registrados.\n\n"
    else:
        usuarios_ordenados = sorted(usuarios.items(), key=lambda x: int(x[0]))
        
        for user_id_str, user_data in usuarios_ordenados[:20]:
            user_id = int(user_id_str)
            username = user_data.get("username", f"Usuario {user_id}")
            estado = "✅" if user_id in autorizados else "⏳"
            admin = "👑" if str(user_id) in admins else "  "
            fecha = user_data.get("fecha_registro", "Desconocida")[:10]
            
            mensaje += f"{admin}{estado} {username}\n"
            mensaje += f"   🆔 <code>{user_id}</code>\n"
            mensaje += f"   📅 {fecha}\n\n"
        
        if len(usuarios) > 20:
            mensaje += f"📊 ... y {len(usuarios) - 20} usuarios más\n\n"
        
        mensaje += f"📊 Total: {len(usuarios)} usuarios\n\n"
    
    mensaje += f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    
    keyboard = [
        [InlineKeyboardButton("◀️ VOLVER", callback_data="menu_admin")],
        [InlineKeyboardButton("🏠 MENÚ PRINCIPAL", callback_data="menu_principal")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(mensaje, parse_mode="HTML", reply_markup=reply_markup)

# ================= 📊 ESTADÍSTICAS =================

@requiere_admin
async def admin_estadisticas_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📊 Muestra estadísticas detalladas del sistema"""
    query = update.callback_query
    await query.answer()
    
    usuarios = AuthSystem.obtener_todos_usuarios()
    autorizados = load_json(AUTHORIZED_USERS_FILE) or []
    pendientes = AuthSystem.obtener_usuarios_pendientes()
    admins = load_json(ADMINS_FILE) or {}
    
    recursos_data = load_json(RECURSOS_FILE) or {}
    total_metal = sum(u.get("metal", 0) for u in recursos_data.values())
    total_cristal = sum(u.get("cristal", 0) for u in recursos_data.values())
    total_deuterio = sum(u.get("deuterio", 0) for u in recursos_data.values())
    
    flota_data = load_json(FLOTA_USUARIO_FILE) or {}
    total_naves = sum(sum(f.values()) for f in flota_data.values())
    
    defensa_data = load_json(DEFENSA_USUARIO_FILE) or {}
    total_defensas = sum(sum(d.values()) for d in defensa_data.values())
    
    colas_edificios = load_json(COLAS_EDIFICIOS_FILE) or {}
    colas_flota = load_json(COLAS_FLOTA_FILE) or {}
    colas_defensa = load_json(COLAS_DEFENSA_FILE) or {}
    total_colas = (
        sum(len(c) for c in colas_edificios.values()) +
        sum(len(c) for c in colas_flota.values()) +
        sum(len(c) for c in colas_defensa.values())
    )
    
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"📊 <b>ESTADÍSTICAS DEL SISTEMA</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"👥 <b>USUARIOS:</b>\n"
        f"   ├ Registrados: {len(usuarios)}\n"
        f"   ├ Autorizados: {len(autorizados)}\n"
        f"   ├ Pendientes: {len(pendientes)}\n"
        f"   └ Administradores: {len(admins)}\n\n"
        f"💰 <b>RECURSOS TOTALES:</b>\n"
        f"   ├ 🔩 Metal: {abreviar_numero(total_metal)}\n"
        f"   ├ 💎 Cristal: {abreviar_numero(total_cristal)}\n"
        f"   └ 🧪 Deuterio: {abreviar_numero(total_deuterio)}\n\n"
        f"🚀 <b>FLOTA TOTAL:</b> {abreviar_numero(total_naves)} naves\n"
        f"🛡️ <b>DEFENSAS TOTALES:</b> {abreviar_numero(total_defensas)} unidades\n"
        f"📋 <b>COLAS ACTIVAS:</b> {total_colas} construcciones\n\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    )
    
    keyboard = [[InlineKeyboardButton("◀️ VOLVER", callback_data="menu_admin")]]
    
    await query.edit_message_text(
        text=mensaje,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

@requiere_admin
async def limpiar_colas_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🧹 Limpia todas las colas de construcción de un usuario"""
    query = update.callback_query
    await query.answer()
    
    usuarios = obtener_lista_usuarios_autorizados()
    
    if not usuarios:
        await query.edit_message_text(
            "❌ <b>No hay usuarios autorizados</b>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ VOLVER", callback_data="menu_admin")
            ]])
        )
        return
    
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"🧹 <b>LIMPIAR COLAS</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"Selecciona el usuario para limpiar sus colas:\n\n"
    )
    
    keyboard = []
    for uid, username in usuarios[:10]:
        display_name = username[:20] + ".." if len(username) > 20 else username
        keyboard.append([InlineKeyboardButton(
            f"{display_name}",
            callback_data=f"admin_limpiar_colas_{uid}"
        )])
    
    keyboard.append([InlineKeyboardButton("◀️ CANCELAR", callback_data="menu_admin")])
    
    await query.edit_message_text(
        text=mensaje,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

async def ejecutar_limpiar_colas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """✅ Ejecuta la limpieza de colas"""
    query = update.callback_query
    await query.answer()
    
    user_id = int(query.data.split("_")[3])
    username = AuthSystem.obtener_username(user_id)
    admin_username = AuthSystem.obtener_username(query.from_user.id)
    
    colas_edificios = load_json(COLAS_EDIFICIOS_FILE) or {}
    colas_flota = load_json(COLAS_FLOTA_FILE) or {}
    colas_defensa = load_json(COLAS_DEFENSA_FILE) or {}
    
    total_eliminadas = 0
    
    if str(user_id) in colas_edificios:
        total_eliminadas += len(colas_edificios[str(user_id)])
        del colas_edificios[str(user_id)]
    
    if str(user_id) in colas_flota:
        total_eliminadas += len(colas_flota[str(user_id)])
        del colas_flota[str(user_id)]
    
    if str(user_id) in colas_defensa:
        total_eliminadas += len(colas_defensa[str(user_id)])
        del colas_defensa[str(user_id)]
    
    save_json(COLAS_EDIFICIOS_FILE, colas_edificios)
    save_json(COLAS_FLOTA_FILE, colas_flota)
    save_json(COLAS_DEFENSA_FILE, colas_defensa)
    
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"✅ <b>COLAS LIMPIADAS</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"👤 Usuario: {username}\n"
        f"🧹 Se eliminaron <b>{total_eliminadas}</b> construcciones:\n"
        f"   • 🏗️ Edificios\n"
        f"   • 🚀 Flota\n"
        f"   • 🛡️ Defensa\n\n"
        f"👑 Admin: {admin_username}\n\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    )
    
    keyboard = [[InlineKeyboardButton("◀️ VOLVER AL PANEL", callback_data="menu_admin")]]
    
    await query.edit_message_text(
        text=mensaje,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

# ================= 👑 AGREGAR ADMINISTRADOR =================

@requiere_admin
async def agregar_admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """👑 Inicia el proceso para agregar un nuevo administrador"""
    query = update.callback_query
    await query.answer()
    
    admin_id = query.from_user.id
    
    if not es_admin_principal(admin_id):
        await query.edit_message_text(
            "❌ <b>ACCESO DENEGADO</b>\n\n"
            "Solo el administrador principal puede agregar nuevos administradores.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ VOLVER", callback_data="menu_admin")
            ]])
        )
        return ConversationHandler.END
    
    usuarios = obtener_lista_usuarios_autorizados()
    admins = load_json(ADMINS_FILE) or {}
    usuarios_no_admin = [(uid, username) for uid, username in usuarios if str(uid) not in admins]
    
    if not usuarios_no_admin:
        await query.edit_message_text(
            "❌ <b>No hay usuarios disponibles</b>\n\n"
            "Todos los usuarios autorizados ya son administradores.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ VOLVER", callback_data="menu_admin")
            ]])
        )
        return ConversationHandler.END
    
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"👑 <b>AGREGAR ADMINISTRADOR</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"Selecciona el usuario que será promovido:\n\n"
        f"<i>Solo el administrador principal puede realizar esta acción.</i>\n\n"
    )
    
    keyboard = []
    for uid, username in usuarios_no_admin[:10]:
        display_name = username[:25] + ".." if len(username) > 25 else username
        keyboard.append([InlineKeyboardButton(
            f"👤 {display_name}",
            callback_data=f"admin_agregar_user_{uid}"
        )])
    
    keyboard.append([InlineKeyboardButton("◀️ CANCELAR", callback_data="menu_admin")])
    
    await query.edit_message_text(
        text=mensaje,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )
    
    return SELECCIONAR_USUARIO_ADMIN

async def seleccionar_usuario_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📝 Selecciona usuario para convertir en administrador"""
    query = update.callback_query
    await query.answer()
    
    user_id = int(query.data.split("_")[3])
    context.user_data['admin_nuevo_user'] = user_id
    
    usuario = AuthSystem.obtener_usuario(user_id)
    username = usuario.get("username", f"Usuario {user_id}")
    
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"👑 <b>CONFIRMAR NUEVO ADMINISTRADOR</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"¿Estás seguro de promover a <b>{username}</b>?\n\n"
        f"✅ Podrá:\n"
        f"   • Aceptar usuarios\n"
        f"   • Regalar recursos\n"
        f"   • Modificar niveles\n"
        f"   • Enviar anuncios\n"
        f"   • Exportar backups\n\n"
        f"❌ NO podrá:\n"
        f"   • Agregar administradores\n"
        f"   • Importar backups\n"
        f"   • Reiniciar el sistema\n\n"
        f"¿Confirmas esta acción?\n\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("✅ SÍ, HACER ADMIN", callback_data="admin_confirmar_agregar"),
            InlineKeyboardButton("❌ NO, CANCELAR", callback_data="menu_admin")
        ]
    ]
    
    await query.edit_message_text(
        text=mensaje,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )
    
    return CONFIRMAR_ADMIN

async def confirmar_agregar_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """✅ Ejecuta la promoción a administrador"""
    query = update.callback_query
    await query.answer()
    
    admin_principal_id = query.from_user.id
    
    if not es_admin_principal(admin_principal_id):
        await query.edit_message_text(
            "❌ <b>ACCESO DENEGADO</b>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ VOLVER", callback_data="menu_admin")
            ]])
        )
        return ConversationHandler.END
    
    user_id = context.user_data.get('admin_nuevo_user')
    
    if not user_id:
        await query.edit_message_text(
            "❌ <b>Error</b>\n\nNo se encontró el usuario seleccionado.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ VOLVER", callback_data="menu_admin")
            ]])
        )
        return ConversationHandler.END
    
    usuario = AuthSystem.obtener_usuario(user_id)
    username = usuario.get("username", f"Usuario {user_id}")
    username_formateado = AuthSystem.formatear_username(user_id, username.replace('@', ''))
    
    admins = load_json(ADMINS_FILE) or {}
    
    if str(user_id) in admins:
        await query.edit_message_text(
            f"❌ <b>El usuario ya es administrador</b>\n\n{username}",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ VOLVER", callback_data="menu_admin")
            ]])
        )
        return ConversationHandler.END
    
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    admins[str(user_id)] = {
        "username": username_formateado,
        "nombre": usuario.get("nombre", "Administrador"),
        "fecha_registro": ahora,
        "agregado_por": admin_principal_id,
        "agregado_por_username": AuthSystem.obtener_username(admin_principal_id),
        "permisos": ["basicos"]
    }
    
    if save_json(ADMINS_FILE, admins):
        mensaje = (
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
            f"✅ <b>ADMINISTRADOR AGREGADO</b>\n"
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
            f"👤 Nuevo administrador: {username_formateado}\n"
            f"🆔 ID: <code>{user_id}</code>\n"
            f"👑 Agregado por: {AuthSystem.obtener_username(admin_principal_id)}\n"
            f"📅 Fecha: {ahora}\n\n"
            f"🔑 Permisos: básicos\n\n"
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
        )
        
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
                    f"👑 <b>¡FELICIDADES!</b>\n"
                    f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
                    f"Has sido promovido a <b>ADMINISTRADOR</b>.\n\n"
                    f"Ahora tienes acceso al panel de administración.\n"
                    f"Usa /admin para acceder.\n\n"
                    f"Promovido por: {AuthSystem.obtener_username(admin_principal_id)}\n\n"
                    f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
                ),
                parse_mode="HTML"
            )
            logger.info(f"✅ Notificación enviada a nuevo admin {user_id}")
        except Exception as e:
            logger.error(f"❌ Error notificando a nuevo admin {user_id}: {e}")
        
        logger.info(f"✅ {username_formateado} fue promovido a administrador por {AuthSystem.obtener_username(admin_principal_id)}")
    else:
        mensaje = "❌ <b>Error al guardar</b>\n\nNo se pudo agregar el administrador."
    
    keyboard = [[InlineKeyboardButton("◀️ VOLVER AL PANEL", callback_data="menu_admin")]]
    
    await query.edit_message_text(
        text=mensaje,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )
    
    if 'admin_nuevo_user' in context.user_data:
        del context.user_data['admin_nuevo_user']
    
    return ConversationHandler.END

# ================= 👑 LISTA DE ADMINISTRADORES =================

@requiere_admin
async def lista_administradores_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📋 Muestra la lista de administradores"""
    query = update.callback_query
    await query.answer()
    
    admin_id = query.from_user.id
    admins = load_json(ADMINS_FILE) or {}
    
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"👑 <b>LISTA DE ADMINISTRADORES</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
    )
    
    if not admins:
        mensaje += "❌ No hay administradores registrados.\n\n"
    else:
        admin_items = []
        for uid_str, admin_data in admins.items():
            uid = int(uid_str)
            username = admin_data.get("username", f"@{uid}")
            fecha = admin_data.get("fecha_registro", "Desconocida")[:10]
            es_principal = "👑 PRINCIPAL" if uid == ADMIN_USER_ID else "👤 ADMIN"
            agregado_por = admin_data.get("agregado_por_username", "Sistema")
            admin_items.append((uid, username, es_principal, fecha, agregado_por, uid == ADMIN_USER_ID))
        
        admin_items.sort(key=lambda x: (not x[5], x[0]))
        
        for idx, (uid, username, rol, fecha, agregado_por, _) in enumerate(admin_items, 1):
            mensaje += f"{idx}. {rol} {username}\n"
            mensaje += f"   🆔 <code>{uid}</code>\n"
            mensaje += f"   📅 Desde: {fecha}\n"
            mensaje += f"   👑 Agregado por: {agregado_por}\n\n"
    
    mensaje += f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    
    keyboard = [
        [InlineKeyboardButton("👑 AGREGAR ADMIN", callback_data="admin_agregar")],
        [InlineKeyboardButton("◀️ VOLVER", callback_data="menu_admin")]
    ]
    
    if not es_admin_principal(admin_id):
        keyboard = [[InlineKeyboardButton("◀️ VOLVER", callback_data="menu_admin")]]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(mensaje, parse_mode="HTML", reply_markup=reply_markup)

# ================= 🗑️ REMOVER ADMINISTRADOR =================

@requiere_admin
async def remover_admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🗑️ Inicia el proceso para remover un administrador"""
    query = update.callback_query
    await query.answer()
    
    admin_id = query.from_user.id
    
    if not es_admin_principal(admin_id):
        await query.edit_message_text(
            "❌ <b>ACCESO DENEGADO</b>\n\n"
            "Solo el administrador principal puede remover administradores.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ VOLVER", callback_data="menu_admin")
            ]])
        )
        return
    
    admins = load_json(ADMINS_FILE) or {}
    admins_no_principal = [(int(uid), data) for uid, data in admins.items() if int(uid) != ADMIN_USER_ID]
    
    if not admins_no_principal:
        await query.edit_message_text(
            "❌ <b>No hay administradores para remover</b>\n\n"
            "Solo existe el administrador principal.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ VOLVER", callback_data="menu_admin")
            ]])
        )
        return
    
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"🗑️ <b>REMOVER ADMINISTRADOR</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"Selecciona el administrador que deseas remover:\n\n"
    )
    
    keyboard = []
    for uid, data in admins_no_principal[:10]:
        username = data.get("username", f"@{uid}")
        display_name = username[:25] + ".." if len(username) > 25 else username
        keyboard.append([InlineKeyboardButton(
            f"👤 {display_name}",
            callback_data=f"admin_remover_user_{uid}"
        )])
    
    keyboard.append([InlineKeyboardButton("◀️ CANCELAR", callback_data="menu_admin")])
    
    await query.edit_message_text(
        text=mensaje,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

async def confirmar_remover_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """✅ Confirma y ejecuta la remoción de administrador"""
    query = update.callback_query
    await query.answer()
    
    user_id = int(query.data.split("_")[3])
    admin_principal_id = query.from_user.id
    
    if not es_admin_principal(admin_principal_id):
        await query.edit_message_text(
            "❌ <b>ACCESO DENEGADO</b>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ VOLVER", callback_data="menu_admin")
            ]])
        )
        return
    
    admins = load_json(ADMINS_FILE) or {}
    
    if str(user_id) not in admins:
        await query.edit_message_text(
            "❌ <b>El usuario no es administrador</b>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ VOLVER", callback_data="menu_admin")
            ]])
        )
        return
    
    admin_data = admins[str(user_id)]
    username = admin_data.get("username", f"Usuario {user_id}")
    
    del admins[str(user_id)]
    
    if save_json(ADMINS_FILE, admins):
        mensaje = (
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
            f"✅ <b>ADMINISTRADOR REMOVIDO</b>\n"
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
            f"👤 Usuario: {username}\n"
            f"🆔 ID: <code>{user_id}</code>\n"
            f"👑 Removido por: {AuthSystem.obtener_username(admin_principal_id)}\n"
            f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
        )
        
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
                    f"👑 <b>HAS SIDO REMOVIDO</b>\n"
                    f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
                    f"Has sido removido como administrador.\n\n"
                    f"Ya no tienes acceso al panel de administración.\n\n"
                    f"Removido por: {AuthSystem.obtener_username(admin_principal_id)}\n\n"
                    f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
                ),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"❌ Error notificando a {user_id}: {e}")
        
        logger.info(f"✅ {username} fue removido de administrador por {AuthSystem.obtener_username(admin_principal_id)}")
    else:
        mensaje = "❌ <b>Error al guardar</b>\n\nNo se pudo remover el administrador."
    
    keyboard = [[InlineKeyboardButton("◀️ VOLVER AL PANEL", callback_data="menu_admin")]]
    
    await query.edit_message_text(
        text=mensaje,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

# ================= 👑 ADMIN CALLBACK HANDLER =================

async def admin_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🎯 Handler para callbacks específicos de admin"""
    query = update.callback_query
    data = query.data
    
    if data == "admin_pendientes":
        await admin_pendientes_handler(update, context)
    elif data == "admin_lista_usuarios":
        await admin_lista_usuarios(update, context)
    elif data == "admin_limpiar_colas":
        await limpiar_colas_handler(update, context)
    elif data.startswith("admin_limpiar_colas_"):
        await ejecutar_limpiar_colas(update, context)
    elif data == "admin_reinicio_fabrica":
        await reinicio_fabrica_menu(update, context)
    elif data == "admin_confirmar_reinicio":
        await confirmar_reinicio_fabrica(update, context)
    elif data == "admin_estadisticas":
        await admin_estadisticas_handler(update, context)
    elif data == "admin_remover":
        await remover_admin_menu(update, context)
    elif data.startswith("admin_remover_user_"):
        await confirmar_remover_admin(update, context)
    
    return

# ================= 🔧 TOGGLE MANTENIMIENTO =================

@requiere_admin
async def toggle_mantenimiento_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🔧 Alterna el estado del modo mantenimiento"""
    query = update.callback_query
    await query.answer()
    
    admin_id = query.from_user.id
    admin_username = AuthSystem.obtener_username(admin_id)
    
    estado_actual = AuthSystem.obtener_estado_mantenimiento()
    nuevo_estado = not estado_actual
    
    AuthSystem.establecer_mantenimiento(nuevo_estado)
    
    estado_texto = "ACTIVADO 🔴" if nuevo_estado else "DESACTIVADO 🟢"
    
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"🔧 <b>MODO MANTENIMIENTO</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"📊 ESTADO ACTUALIZADO\n\n"
        f"🖥️ Servidor: <b>{estado_texto}</b>\n"
        f"⚠️ Los administradores NO se ven afectados\n\n"
        f"👑 Admin: {admin_username}\n"
        f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    )
    
    keyboard = [
        [InlineKeyboardButton("◀️ VOLVER AL PANEL", callback_data="menu_admin")],
        [InlineKeyboardButton("🏠 MENÚ PRINCIPAL", callback_data="menu_principal")]
    ]
    
    await query.edit_message_text(
        text=mensaje,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )
    
    logger.info(f"🔧 Admin {admin_username} cambió mantenimiento a {nuevo_estado}")

# ================= ⚠️ REINICIO A FÁBRICA =================

@requiere_admin
async def reinicio_fabrica_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """⚠️ Menú de confirmación para reinicio a fábrica"""
    query = update.callback_query
    await query.answer()
    
    admin_id = query.from_user.id
    
    if not es_admin_principal(admin_id):
        await query.edit_message_text(
            "❌ <b>ACCESO DENEGADO</b>\n\n"
            "Solo el administrador principal puede ejecutar esta acción.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ VOLVER", callback_data="menu_admin")
            ]])
        )
        return
    
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"⚠️ <b>REINICIO A FÁBRICA</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"⚠️ <b>¡ADVERTENCIA!</b>\n\n"
        f"Esta acción eliminará <b>TODOS</b> los datos:\n"
        f"• Todos los usuarios\n"
        f"• Todos los recursos\n"
        f"• Todos los edificios\n"
        f"• Todas las flotas\n"
        f"• Todas las defensas\n"
        f"• Todas las investigaciones\n"
        f"• Todas las colas\n"
        f"• Todas las misiones\n\n"
        f"Solo se conservará el administrador principal.\n\n"
        f"¿Estás ABSOLUTAMENTE SEGURO?\n\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("⚠️ SÍ, REINICIAR", callback_data="admin_confirmar_reinicio"),
            InlineKeyboardButton("❌ NO, CANCELAR", callback_data="menu_admin")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(mensaje, parse_mode="HTML", reply_markup=reply_markup)

@requiere_admin
async def confirmar_reinicio_fabrica(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """⚠️ Ejecuta el reinicio a fábrica"""
    query = update.callback_query
    await query.answer()
    
    admin_id = query.from_user.id
    admin_username = obtener_username_display(admin_id)
    
    if not es_admin_principal(admin_id):
        await query.edit_message_text(
            "❌ <b>ACCESO DENEGADO</b>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ VOLVER", callback_data="menu_admin")
            ]])
        )
        return
    
    try:
        save_json(DATA_FILE, {})
        save_json(AUTHORIZED_USERS_FILE, [ADMIN_USER_ID])
        save_json(RECURSOS_FILE, {})
        save_json(MINAS_FILE, {})
        save_json(EDIFICIOS_USUARIO_FILE, {})
        save_json(CAMPOS_FILE, {})
        save_json(FLOTA_USUARIO_FILE, {})
        save_json(DEFENSA_USUARIO_FILE, {})
        save_json(INVESTIGACIONES_USUARIO_FILE, {})
        
        save_json(COLAS_EDIFICIOS_FILE, {})
        save_json(COLAS_FLOTA_FILE, {})
        save_json(COLAS_DEFENSA_FILE, {})
        
        try:
            from base_flotas import MISIONES_FLOTA_FILE, BAJAS_FLOTA_FILE
            save_json(MISIONES_FLOTA_FILE, {})
            save_json(BAJAS_FLOTA_FILE, {})
        except:
            pass
        
        from login import RECURSOS_INICIALES
        AuthSystem.registrar_usuario(ADMIN_USER_ID, "Admin")
        AuthSystem.inicializar_usuario_completo(ADMIN_USER_ID, "Admin")
        
        admins = {str(ADMIN_USER_ID): {
            "username": f"@{ADMIN_USER_ID}",
            "nombre": "Admin Principal",
            "fecha_registro": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "agregado_por": "sistema",
            "permisos": ["todos"]
        }}
        save_json(ADMINS_FILE, admins)
        
        await query.edit_message_text(
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
            f"✅ <b>REINICIO A FÁBRICA COMPLETADO</b>\n"
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
            f"Todos los datos han sido eliminados.\n"
            f"El sistema ha sido restaurado a su estado inicial.\n\n"
            f"👑 Admin: {admin_username}\n"
            f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🏠 MENÚ PRINCIPAL", callback_data="menu_principal")
            ]])
        )
        
        logger.warning(f"⚠️ REINICIO A FÁBRICA ejecutado por {admin_username}")
        
    except Exception as e:
        logger.error(f"❌ Error en reinicio a fábrica: {e}")
        await query.edit_message_text(
            f"❌ <b>ERROR EN REINICIO</b>\n\n{str(e)}",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ VOLVER", callback_data="menu_admin")
            ]])
        )

# ================= 🏗️ SUBIR NIVEL CONSTRUCCIÓN (COMPATIBILIDAD) =================

@requiere_admin
async def subir_nivel_construccion_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    🏗️ Función de compatibilidad que redirige a modificar_nivel_menu
    """
    logger.info(f"🔄 Redirigiendo subir_nivel_construccion_menu -> modificar_nivel_menu")
    await modificar_nivel_menu(update, context)

# ================= 🏗️ MODIFICAR NIVEL DE EDIFICIO =================

@requiere_admin
async def modificar_nivel_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🏗️ Inicia el proceso para modificar nivel de edificio"""
    query = update.callback_query
    await query.answer()
    
    usuarios = obtener_lista_usuarios_autorizados()
    
    if not usuarios:
        await query.edit_message_text(
            "❌ <b>No hay usuarios autorizados</b>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ VOLVER", callback_data="menu_admin")
            ]])
        )
        return ConversationHandler.END
    
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"🏗️ <b>MODIFICAR NIVEL</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"Selecciona el usuario:\n\n"
    )
    
    keyboard = []
    for uid, username in usuarios[:10]:
        display_name = username[:20] + ".." if len(username) > 20 else username
        keyboard.append([InlineKeyboardButton(
            f"{display_name}",
            callback_data=f"admin_edificio_user_{uid}"
        )])
    
    keyboard.append([InlineKeyboardButton("◀️ CANCELAR", callback_data="menu_admin")])
    
    await query.edit_message_text(
        text=mensaje,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )
    
    return SELECCIONAR_USUARIO_EDIFICIO

async def seleccionar_usuario_edificio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📝 Selecciona usuario para modificar edificio"""
    query = update.callback_query
    await query.answer()
    
    user_id = int(query.data.split("_")[3])
    context.user_data['admin_edificio_user'] = user_id
    
    usuario = AuthSystem.obtener_usuario(user_id)
    username = usuario.get("username", f"Usuario {user_id}")
    
    try:
        from edificios import CONSTRUCCIONES
    except ImportError:
        await query.edit_message_text(
            "❌ <b>Error</b>\n\nNo se pudo cargar la configuración de edificios.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ VOLVER", callback_data="menu_admin")
            ]])
        )
        return ConversationHandler.END
    
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"🏗️ <b>MODIFICAR NIVEL</b> - {username}\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"Selecciona el edificio:\n\n"
    )
    
    keyboard = []
    
    keyboard.append([InlineKeyboardButton("⛏️ MINAS", callback_data="noop")])
    fila = []
    for tipo in ["metal", "cristal", "deuterio"]:
        config = CONSTRUCCIONES[tipo]
        fila.append(InlineKeyboardButton(
            f"{config['icono']} {config['nombre'].split()[0]}",
            callback_data=f"admin_edificio_tipo_{tipo}"
        ))
    keyboard.append(fila)
    
    keyboard.append([InlineKeyboardButton("🏢 EDIFICIOS", callback_data="noop")])
    fila = []
    for tipo in ["energia", "laboratorio", "hangar", "terraformer"]:
        config = CONSTRUCCIONES[tipo]
        fila.append(InlineKeyboardButton(
            f"{config['icono']} {config['nombre'].split()[0]}",
            callback_data=f"admin_edificio_tipo_{tipo}"
        ))
    keyboard.append(fila)
    
    keyboard.append([InlineKeyboardButton("◀️ CANCELAR", callback_data="menu_admin")])
    
    await query.edit_message_text(
        text=mensaje,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )
    
    return INGRESAR_EDIFICIO

async def seleccionar_tipo_edificio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📝 Selecciona tipo de edificio"""
    query = update.callback_query
    await query.answer()
    
    edificio = query.data.split("_")[3]
    context.user_data['admin_edificio_tipo'] = edificio
    
    try:
        from edificios import CONSTRUCCIONES, obtener_nivel
        config = CONSTRUCCIONES[edificio]
        user_id = context.user_data.get('admin_edificio_user')
        nivel_actual = obtener_nivel(user_id, edificio)
    except:
        await query.edit_message_text(
            "❌ <b>Error</b>\n\nNo se pudo cargar la configuración del edificio.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ VOLVER", callback_data="menu_admin")
            ]])
        )
        return ConversationHandler.END
    
    usuario = AuthSystem.obtener_usuario(user_id)
    username = usuario.get("username", f"Usuario {user_id}")
    
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"🏗️ <b>MODIFICAR NIVEL</b> - {username}\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"Edificio: {config['icono']} {config['nombre']}\n"
        f"Nivel actual: {nivel_actual}\n"
        f"Nivel máximo: {config['max_nivel']}\n\n"
        f"Escribe el NUEVO NIVEL que deseas asignar:\n\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    )
    
    keyboard = [[InlineKeyboardButton("◀️ CANCELAR", callback_data="menu_admin")]]
    
    await query.edit_message_text(
        text=mensaje,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )
    
    return INGRESAR_NIVEL

async def ingresar_nivel_edificio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📝 Recibe nivel y ejecuta"""
    try:
        nivel = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("❌ Por favor, ingresa un número válido.")
        return INGRESAR_NIVEL
    
    user_id = context.user_data.get('admin_edificio_user')
    edificio = context.user_data.get('admin_edificio_tipo')
    
    try:
        from edificios import CONSTRUCCIONES, obtener_nivel, actualizar_campos, calcular_campos_usados
        config = CONSTRUCCIONES[edificio]
    except:
        await update.message.reply_text("❌ Error al cargar configuración del edificio.")
        return ConversationHandler.END
    
    if nivel < 0 or nivel > config["max_nivel"]:
        await update.message.reply_text(f"❌ El nivel debe ser entre 0 y {config['max_nivel']}.")
        return INGRESAR_NIVEL
    
    if edificio in ["metal", "cristal", "deuterio"]:
        minas_data = load_json(MINAS_FILE) or {}
        minas_usuario = minas_data.get(str(user_id), {})
        minas_usuario[edificio] = nivel
        minas_data[str(user_id)] = minas_usuario
        save_json(MINAS_FILE, minas_data)
    else:
        edificios_data = load_json(EDIFICIOS_USUARIO_FILE) or {}
        edificios_usuario = edificios_data.get(str(user_id), {})
        edificios_usuario[edificio] = nivel
        edificios_data[str(user_id)] = edificios_usuario
        save_json(EDIFICIOS_USUARIO_FILE, edificios_data)
    
    if edificio == "terraformer":
        campos_data = load_json(CAMPOS_FILE) or {}
        campos = campos_data.get(str(user_id), {"total": 163, "usados": 0, "adicionales": 0})
        campos_adicionales = nivel * 5
        campos["adicionales"] = campos_adicionales
        campos["total"] = 163 + campos_adicionales
        from edificios import calcular_campos_usados
        campos["usados"] = calcular_campos_usados(user_id)
        campos_data[str(user_id)] = campos
        save_json(CAMPOS_FILE, campos_data)
    else:
        actualizar_campos(user_id)
    
    username = AuthSystem.obtener_username(user_id)
    admin_username = AuthSystem.obtener_username(update.effective_user.id)
    
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"✅ <b>NIVEL MODIFICADO</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"👤 Usuario: {username}\n"
        f"🏗️ Edificio: {config['icono']} {config['nombre']}\n"
        f"📊 Nivel nuevo: <b>{nivel}</b>\n\n"
        f"👑 Admin: {admin_username}\n\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    )
    
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=(
                f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
                f"🏗️ <b>¡TU EDIFICIO HA SIDO MODIFICADO!</b>\n"
                f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
                f"{config['icono']} {config['nombre']}\n"
                f"📊 Nuevo nivel: {nivel}\n\n"
                f"👑 Administrador: {admin_username}\n\n"
                f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
            ),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"❌ Error notificando a {user_id}: {e}")
    
    keyboard = [[InlineKeyboardButton("◀️ VOLVER AL PANEL", callback_data="menu_admin")]]
    
    await update.message.reply_text(
        text=mensaje,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )
    
    keys = ['admin_edificio_user', 'admin_edificio_tipo']
    for key in keys:
        if key in context.user_data:
            del context.user_data[key]
    
    return ConversationHandler.END

# ================= 🔬 MEJORAR INVESTIGACIÓN =================

@requiere_admin
async def mejorar_investigacion_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🔬 Inicia el proceso para mejorar investigación"""
    query = update.callback_query
    await query.answer()
    
    usuarios = obtener_lista_usuarios_autorizados()
    
    if not usuarios:
        await query.edit_message_text(
            "❌ <b>No hay usuarios autorizados</b>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ VOLVER", callback_data="menu_admin")
            ]])
        )
        return ConversationHandler.END
    
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"🔬 <b>MEJORAR INVESTIGACIÓN</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"Selecciona el usuario:\n\n"
    )
    
    keyboard = []
    for uid, username in usuarios[:10]:
        display_name = username[:20] + ".." if len(username) > 20 else username
        keyboard.append([InlineKeyboardButton(
            f"{display_name}",
            callback_data=f"admin_investigacion_user_{uid}"
        )])
    
    keyboard.append([InlineKeyboardButton("◀️ CANCELAR", callback_data="menu_admin")])
    
    await query.edit_message_text(
        text=mensaje,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )
    
    return SELECCIONAR_USUARIO_INVESTIGACION

async def seleccionar_usuario_investigacion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📝 Selecciona usuario para mejorar investigación"""
    query = update.callback_query
    await query.answer()
    
    user_id = int(query.data.split("_")[3])
    context.user_data['admin_investigacion_user'] = user_id
    
    usuario = AuthSystem.obtener_usuario(user_id)
    username = usuario.get("username", f"Usuario {user_id}")
    
    try:
        from investigaciones import INVESTIGACIONES
    except ImportError:
        await query.edit_message_text(
            "❌ <b>Error</b>\n\nNo se pudo cargar la configuración de investigaciones.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ VOLVER", callback_data="menu_admin")
            ]])
        )
        return ConversationHandler.END
    
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"🔬 <b>MEJORAR INVESTIGACIÓN</b> - {username}\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"Selecciona la tecnología:\n\n"
    )
    
    keyboard = []
    grupos = {}
    for tech_id, config in INVESTIGACIONES.items():
        grupo = config.get("grupo", "Otros")
        if grupo not in grupos:
            grupos[grupo] = []
        grupos[grupo].append((tech_id, config))
    
    for grupo, tecnologias in grupos.items():
        keyboard.append([InlineKeyboardButton(f"──── {grupo} ────", callback_data="noop")])
        fila = []
        for tech_id, config in tecnologias[:4]:
            icono = config.get("icono", "🔬")
            nombre = config.get("nombre", tech_id)[:10]
            fila.append(InlineKeyboardButton(
                f"{icono} {nombre}",
                callback_data=f"admin_investigacion_tipo_{tech_id}"
            ))
            if len(fila) == 2:
                keyboard.append(fila)
                fila = []
        if fila:
            keyboard.append(fila)
    
    keyboard.append([InlineKeyboardButton("◀️ CANCELAR", callback_data="menu_admin")])
    
    await query.edit_message_text(
        text=mensaje,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )
    
    return INGRESAR_INVESTIGACION

async def seleccionar_tipo_investigacion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📝 Selecciona tipo de investigación"""
    query = update.callback_query
    await query.answer()
    
    tech_id = query.data.split("_")[3]
    context.user_data['admin_investigacion_tipo'] = tech_id
    
    try:
        from investigaciones import INVESTIGACIONES, obtener_datos_investigacion
        config = INVESTIGACIONES[tech_id]
        user_id = context.user_data.get('admin_investigacion_user')
        datos_inv = obtener_datos_investigacion(user_id)
        nivel_actual = datos_inv["investigaciones"].get(tech_id, 0)
    except:
        await query.edit_message_text(
            "❌ <b>Error</b>\n\nNo se pudo cargar la configuración de la investigación.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ VOLVER", callback_data="menu_admin")
            ]])
        )
        return ConversationHandler.END
    
    usuario = AuthSystem.obtener_usuario(user_id)
    username = usuario.get("username", f"Usuario {user_id}")
    
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"🔬 <b>MEJORAR INVESTIGACIÓN</b> - {username}\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"Tecnología: {config['icono']} {config['nombre']}\n"
        f"Nivel actual: {nivel_actual}\n"
        f"Nivel máximo: {config['max_nivel']}\n\n"
        f"Escribe el NUEVO NIVEL que deseas asignar:\n\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    )
    
    keyboard = [[InlineKeyboardButton("◀️ CANCELAR", callback_data="menu_admin")]]
    
    await query.edit_message_text(
        text=mensaje,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )
    
    return INGRESAR_NIVEL_INV

async def ingresar_nivel_investigacion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📝 Recibe nivel y ejecuta"""
    try:
        nivel = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("❌ Por favor, ingresa un número válido.")
        return INGRESAR_NIVEL_INV
    
    user_id = context.user_data.get('admin_investigacion_user')
    tech_id = context.user_data.get('admin_investigacion_tipo')
    
    try:
        from investigaciones import INVESTIGACIONES, guardar_investigacion, obtener_datos_investigacion
        config = INVESTIGACIONES[tech_id]
    except:
        await update.message.reply_text("❌ Error al cargar configuración de la investigación.")
        return ConversationHandler.END
    
    if nivel < 0 or nivel > config["max_nivel"]:
        await update.message.reply_text(f"❌ El nivel debe ser entre 0 y {config['max_nivel']}.")
        return INGRESAR_NIVEL_INV
    
    datos_inv = obtener_datos_investigacion(user_id)
    investigaciones = datos_inv["investigaciones"].copy()
    investigaciones[tech_id] = nivel
    guardar_investigacion(user_id, investigaciones=investigaciones)
    
    username = AuthSystem.obtener_username(user_id)
    admin_username = AuthSystem.obtener_username(update.effective_user.id)
    
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"✅ <b>INVESTIGACIÓN MEJORADA</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"👤 Usuario: {username}\n"
        f"🔬 Tecnología: {config['icono']} {config['nombre']}\n"
        f"📊 Nivel nuevo: <b>{nivel}</b>\n\n"
        f"👑 Admin: {admin_username}\n\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    )
    
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=(
                f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
                f"🔬 <b>¡TU INVESTIGACIÓN HA SIDO MEJORADA!</b>\n"
                f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
                f"{config['icono']} {config['nombre']}\n"
                f"📊 Nuevo nivel: {nivel}\n\n"
                f"👑 Administrador: {admin_username}\n\n"
                f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
            ),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"❌ Error notificando a {user_id}: {e}")
    
    keyboard = [[InlineKeyboardButton("◀️ VOLVER AL PANEL", callback_data="menu_admin")]]
    
    await update.message.reply_text(
        text=mensaje,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )
    
    keys = ['admin_investigacion_user', 'admin_investigacion_tipo']
    for key in keys:
        if key in context.user_data:
            del context.user_data[key]
    
    return ConversationHandler.END

# ================= 📢 ENVIAR ANUNCIO =================

@requiere_admin
async def enviar_anuncio_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📢 Inicia el proceso para enviar anuncio global"""
    query = update.callback_query
    await query.answer()
    
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"📢 <b>ENVIAR ANUNCIO GLOBAL</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"Escribe el mensaje que deseas enviar a TODOS los usuarios:\n\n"
        f"<i>Puedes usar formato HTML: &lt;b&gt;negrita&lt;/b&gt;, &lt;i&gt;cursiva&lt;/i&gt;</i>\n\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    )
    
    keyboard = [[InlineKeyboardButton("◀️ CANCELAR", callback_data="menu_admin")]]
    
    await query.edit_message_text(
        text=mensaje,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )
    
    return INGRESAR_ANUNCIO

async def recibir_anuncio_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📝 Recibe el anuncio y lo envía"""
    anuncio = update.message.text.strip()
    
    if not anuncio:
        await update.message.reply_text("❌ El anuncio no puede estar vacío.")
        return INGRESAR_ANUNCIO
    
    admin_username = AuthSystem.obtener_username(update.effective_user.id)
    
    autorizados = load_json(AUTHORIZED_USERS_FILE) or []
    
    mensaje_anuncio = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"📢 <b>ANUNCIO GLOBAL</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"{anuncio}\n\n"
        f"────────────────────────────\n"
        f"👑 Administrador: {admin_username}\n"
        f"📅 {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    )
    
    enviados = 0
    fallidos = 0
    
    for user_id in autorizados:
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=mensaje_anuncio,
                parse_mode="HTML"
            )
            enviados += 1
        except Exception as e:
            fallidos += 1
            logger.error(f"❌ Error enviando anuncio a {user_id}: {e}")
    
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"✅ <b>ANUNCIO ENVIADO</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"📊 Estadísticas:\n"
        f"   ✅ Enviados: {enviados}\n"
        f"   ❌ Fallidos: {fallidos}\n"
        f"   📦 Total: {len(autorizados)}\n\n"
        f"👑 Admin: {admin_username}\n\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    )
    
    keyboard = [[InlineKeyboardButton("◀️ VOLVER AL PANEL", callback_data="menu_admin")]]
    
    await update.message.reply_text(
        text=mensaje,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )
    
    return ConversationHandler.END

# ================= 💰 REGALAR RECURSOS =================

@requiere_admin
async def regalar_recursos_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """💰 Inicia el proceso para regalar recursos"""
    query = update.callback_query
    await query.answer()
    
    usuarios = obtener_lista_usuarios_autorizados()
    
    if not usuarios:
        await query.edit_message_text(
            "❌ <b>No hay usuarios autorizados</b>\n\n"
            "Primero debes autorizar al menos un usuario.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ VOLVER", callback_data="menu_admin")
            ]])
        )
        return ConversationHandler.END
    
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"💰 <b>REGALAR RECURSOS</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"Selecciona el usuario:\n\n"
    )
    
    keyboard = []
    for uid, username in usuarios[:10]:
        display_name = username[:20] + ".." if len(username) > 20 else username
        keyboard.append([InlineKeyboardButton(
            f"{display_name}",
            callback_data=f"admin_recurso_user_{uid}"
        )])
    
    keyboard.append([InlineKeyboardButton("◀️ CANCELAR", callback_data="menu_admin")])
    
    await query.edit_message_text(
        text=mensaje,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )
    
    return SELECCIONAR_USUARIO

async def seleccionar_usuario_recursos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📝 Selecciona usuario para regalar recursos"""
    query = update.callback_query
    await query.answer()
    
    user_id = int(query.data.split("_")[3])
    context.user_data['admin_recurso_user'] = user_id
    
    usuario = AuthSystem.obtener_usuario(user_id)
    username = usuario.get("username", f"Usuario {user_id}")
    
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"💰 <b>REGALAR RECURSOS</b> - {username}\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"Escribe la cantidad de <b>METAL</b>:\n\n"
        f"<i>0 para omitir</i>\n\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    )
    
    keyboard = [[InlineKeyboardButton("◀️ CANCELAR", callback_data="menu_admin")]]
    
    await query.edit_message_text(
        text=mensaje,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )
    
    return INGRESAR_METAL

async def ingresar_metal_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📝 Recibe cantidad de metal"""
    try:
        cantidad = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("❌ Por favor, ingresa un número válido.")
        return INGRESAR_METAL
    
    if cantidad < 0:
        await update.message.reply_text("❌ La cantidad no puede ser negativa.")
        return INGRESAR_METAL
    
    context.user_data['admin_recurso_metal'] = cantidad
    
    user_id = context.user_data.get('admin_recurso_user')
    usuario = AuthSystem.obtener_usuario(user_id)
    username = usuario.get("username", f"Usuario {user_id}")
    
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"💰 <b>REGALAR RECURSOS</b> - {username}\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"Metal: {abreviar_numero(cantidad)}\n\n"
        f"Escribe la cantidad de <b>CRISTAL</b>:\n\n"
        f"<i>0 para omitir</i>\n\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    )
    
    await update.message.reply_text(mensaje, parse_mode="HTML")
    return INGRESAR_CRISTAL

async def ingresar_cristal_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📝 Recibe cantidad de cristal"""
    try:
        cantidad = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("❌ Por favor, ingresa un número válido.")
        return INGRESAR_CRISTAL
    
    if cantidad < 0:
        await update.message.reply_text("❌ La cantidad no puede ser negativa.")
        return INGRESAR_CRISTAL
    
    context.user_data['admin_recurso_cristal'] = cantidad
    
    user_id = context.user_data.get('admin_recurso_user')
    usuario = AuthSystem.obtener_usuario(user_id)
    username = usuario.get("username", f"Usuario {user_id}")
    
    metal = context.user_data.get('admin_recurso_metal', 0)
    cristal = cantidad
    
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"💰 <b>REGALAR RECURSOS</b> - {username}\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"Metal: {abreviar_numero(metal)}\n"
        f"Cristal: {abreviar_numero(cristal)}\n\n"
        f"Escribe la cantidad de <b>DEUTERIO</b>:\n\n"
        f"<i>0 para omitir</i>\n\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    )
    
    await update.message.reply_text(mensaje, parse_mode="HTML")
    return INGRESAR_DEUTERIO

async def ingresar_deuterio_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📝 Recibe cantidad de deuterio y ejecuta"""
    try:
        deuterio = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("❌ Por favor, ingresa un número válido.")
        return INGRESAR_DEUTERIO
    
    if deuterio < 0:
        await update.message.reply_text("❌ La cantidad no puede ser negativa.")
        return INGRESAR_DEUTERIO
    
    user_id = context.user_data.get('admin_recurso_user')
    metal = context.user_data.get('admin_recurso_metal', 0)
    cristal = context.user_data.get('admin_recurso_cristal', 0)
    
    recursos_data = load_json(RECURSOS_FILE) or {}
    recursos = recursos_data.get(str(user_id), {
        "metal": 0, "cristal": 0, "deuterio": 0, "materia_oscura": 0, "nxt20": 0, "energia": 0
    })
    
    recursos["metal"] = recursos.get("metal", 0) + metal
    recursos["cristal"] = recursos.get("cristal", 0) + cristal
    recursos["deuterio"] = recursos.get("deuterio", 0) + deuterio
    
    recursos_data[str(user_id)] = recursos
    save_json(RECURSOS_FILE, recursos_data)
    
    username = AuthSystem.obtener_username(user_id)
    admin_username = AuthSystem.obtener_username(update.effective_user.id)
    
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"✅ <b>RECURSOS REGALADOS</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"👤 Usuario: {username}\n"
        f"💰 Recursos añadidos:\n"
        f"   🔩 Metal: +{abreviar_numero(metal)}\n"
        f"   💎 Cristal: +{abreviar_numero(cristal)}\n"
        f"   🧪 Deuterio: +{abreviar_numero(deuterio)}\n\n"
        f"👑 Admin: {admin_username}\n\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    )
    
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=(
                f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
                f"💰 <b>¡HAS RECIBIDO RECURSOS!</b>\n"
                f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
                f"🔩 Metal: +{abreviar_numero(metal)}\n"
                f"💎 Cristal: +{abreviar_numero(cristal)}\n"
                f"🧪 Deuterio: +{abreviar_numero(deuterio)}\n\n"
                f"👑 Administrador: {admin_username}\n\n"
                f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
            ),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"❌ Error notificando a {user_id}: {e}")
    
    keyboard = [[InlineKeyboardButton("◀️ VOLVER AL PANEL", callback_data="menu_admin")]]
    
    await update.message.reply_text(
        text=mensaje,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )
    
    keys = ['admin_recurso_user', 'admin_recurso_metal', 'admin_recurso_cristal']
    for key in keys:
        if key in context.user_data:
            del context.user_data[key]
    
    return ConversationHandler.END

# ================= 🚀 REGALAR NAVES =================

@requiere_admin
async def regalar_flota_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🚀 Inicia el proceso para regalar naves"""
    query = update.callback_query
    await query.answer()
    
    usuarios = obtener_lista_usuarios_autorizados()
    
    if not usuarios:
        await query.edit_message_text(
            "❌ <b>No hay usuarios autorizados</b>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ VOLVER", callback_data="menu_admin")
            ]])
        )
        return ConversationHandler.END
    
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"🚀 <b>REGALAR NAVES</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"Selecciona el usuario:\n\n"
    )
    
    keyboard = []
    for uid, username in usuarios[:10]:
        display_name = username[:20] + ".." if len(username) > 20 else username
        keyboard.append([InlineKeyboardButton(
            f"{display_name}",
            callback_data=f"admin_flota_user_{uid}"
        )])
    
    keyboard.append([InlineKeyboardButton("◀️ CANCELAR", callback_data="menu_admin")])
    
    await query.edit_message_text(
        text=mensaje,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )
    
    return SELECCIONAR_USUARIO_NAVE

async def seleccionar_usuario_flota(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📝 Selecciona usuario para regalar naves"""
    query = update.callback_query
    await query.answer()
    
    user_id = int(query.data.split("_")[3])
    context.user_data['admin_flota_user'] = user_id
    
    usuario = AuthSystem.obtener_usuario(user_id)
    username = usuario.get("username", f"Usuario {user_id}")
    
    try:
        from flota import CONFIG_NAVES
    except ImportError:
        await query.edit_message_text(
            "❌ <b>Error</b>\n\nNo se pudo cargar la configuración de naves.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ VOLVER", callback_data="menu_admin")
            ]])
        )
        return ConversationHandler.END
    
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"🚀 <b>REGALAR NAVES</b> - {username}\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"Selecciona la nave:\n\n"
    )
    
    keyboard = []
    fila = []
    for i, (nave_id, config) in enumerate(CONFIG_NAVES.items()):
        icono = config.get("icono", "🚀")
        nombre = config.get("nombre", nave_id)[:15]
        fila.append(InlineKeyboardButton(
            f"{icono} {nombre}",
            callback_data=f"admin_flota_nave_{nave_id}"
        ))
        if len(fila) == 2:
            keyboard.append(fila)
            fila = []
    
    if fila:
        keyboard.append(fila)
    
    keyboard.append([InlineKeyboardButton("◀️ CANCELAR", callback_data="menu_admin")])
    
    await query.edit_message_text(
        text=mensaje,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )
    
    return INGRESAR_NAVE

async def seleccionar_nave_flota(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📝 Selecciona tipo de nave"""
    query = update.callback_query
    await query.answer()
    
    nave_id = query.data.split("_")[3]
    context.user_data['admin_flota_nave'] = nave_id
    
    try:
        from flota import CONFIG_NAVES
        config = CONFIG_NAVES[nave_id]
    except:
        await query.edit_message_text(
            "❌ <b>Error</b>\n\nNo se pudo cargar la configuración de la nave.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ VOLVER", callback_data="menu_admin")
            ]])
        )
        return ConversationHandler.END
    
    user_id = context.user_data.get('admin_flota_user')
    usuario = AuthSystem.obtener_usuario(user_id)
    username = usuario.get("username", f"Usuario {user_id}")
    
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"🚀 <b>REGALAR NAVES</b> - {username}\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"Nave: {config['icono']} {config['nombre']}\n\n"
        f"Escribe la cantidad que deseas regalar:\n\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    )
    
    keyboard = [[InlineKeyboardButton("◀️ CANCELAR", callback_data="menu_admin")]]
    
    await query.edit_message_text(
        text=mensaje,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )
    
    return INGRESAR_CANTIDAD_NAVE

async def ingresar_cantidad_flota(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📝 Recibe cantidad y ejecuta"""
    try:
        cantidad = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("❌ Por favor, ingresa un número válido.")
        return INGRESAR_CANTIDAD_NAVE
    
    if cantidad <= 0 or cantidad > 1000000:
        await update.message.reply_text("❌ La cantidad debe ser entre 1 y 1.000.000.")
        return INGRESAR_CANTIDAD_NAVE
    
    user_id = context.user_data.get('admin_flota_user')
    nave_id = context.user_data.get('admin_flota_nave')
    
    try:
        from flota import CONFIG_NAVES
        config = CONFIG_NAVES[nave_id]
    except:
        await update.message.reply_text("❌ Error al cargar configuración de la nave.")
        return ConversationHandler.END
    
    flota_data = load_json(FLOTA_USUARIO_FILE) or {}
    flota = flota_data.get(str(user_id), {})
    
    flota[nave_id] = flota.get(nave_id, 0) + cantidad
    flota_data[str(user_id)] = flota
    save_json(FLOTA_USUARIO_FILE, flota_data)
    
    username = AuthSystem.obtener_username(user_id)
    admin_username = AuthSystem.obtener_username(update.effective_user.id)
    
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"✅ <b>NAVES REGALADAS</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"👤 Usuario: {username}\n"
        f"🚀 Nave: {config['icono']} {config['nombre']}\n"
        f"📦 Cantidad: +{abreviar_numero(cantidad)}\n"
        f"📊 Total ahora: {abreviar_numero(flota.get(nave_id, 0))}\n\n"
        f"👑 Admin: {admin_username}\n\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    )
    
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=(
                f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
                f"🚀 <b>¡HAS RECIBIDO NAVES!</b>\n"
                f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
                f"{config['icono']} {config['nombre']}: +{cantidad}\n"
                f"📊 Total: {flota.get(nave_id, 0)}\n\n"
                f"👑 Administrador: {admin_username}\n\n"
                f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
            ),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"❌ Error notificando a {user_id}: {e}")
    
    keyboard = [[InlineKeyboardButton("◀️ VOLVER AL PANEL", callback_data="menu_admin")]]
    
    await update.message.reply_text(
        text=mensaje,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )
    
    keys = ['admin_flota_user', 'admin_flota_nave']
    for key in keys:
        if key in context.user_data:
            del context.user_data[key]
    
    return ConversationHandler.END

# ================= 🛡️ REGALAR DEFENSAS =================

@requiere_admin
async def regalar_defensa_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🛡️ Inicia el proceso para regalar defensas"""
    query = update.callback_query
    await query.answer()
    
    usuarios = obtener_lista_usuarios_autorizados()
    
    if not usuarios:
        await query.edit_message_text(
            "❌ <b>No hay usuarios autorizados</b>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ VOLVER", callback_data="menu_admin")
            ]])
        )
        return ConversationHandler.END
    
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"🛡️ <b>REGALAR DEFENSAS</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"Selecciona el usuario:\n\n"
    )
    
    keyboard = []
    for uid, username in usuarios[:10]:
        display_name = username[:20] + ".." if len(username) > 20 else username
        keyboard.append([InlineKeyboardButton(
            f"{display_name}",
            callback_data=f"admin_defensa_user_{uid}"
        )])
    
    keyboard.append([InlineKeyboardButton("◀️ CANCELAR", callback_data="menu_admin")])
    
    await query.edit_message_text(
        text=mensaje,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )
    
    return SELECCIONAR_USUARIO_DEFENSA

async def seleccionar_usuario_defensa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📝 Selecciona usuario para regalar defensas"""
    query = update.callback_query
    await query.answer()
    
    user_id = int(query.data.split("_")[3])
    context.user_data['admin_defensa_user'] = user_id
    
    usuario = AuthSystem.obtener_usuario(user_id)
    username = usuario.get("username", f"Usuario {user_id}")
    
    try:
        from defensa import CONFIG_DEFENSAS
    except ImportError:
        await query.edit_message_text(
            "❌ <b>Error</b>\n\nNo se pudo cargar la configuración de defensas.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ VOLVER", callback_data="menu_admin")
            ]])
        )
        return ConversationHandler.END
    
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"🛡️ <b>REGALAR DEFENSAS</b> - {username}\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"Selecciona la defensa:\n\n"
    )
    
    keyboard = []
    fila = []
    for i, (def_id, config) in enumerate(CONFIG_DEFENSAS.items()):
        icono = config.get("icono", "🛡️")
        nombre = config.get("nombre", def_id)[:15]
        fila.append(InlineKeyboardButton(
            f"{icono} {nombre}",
            callback_data=f"admin_defensa_tipo_{def_id}"
        ))
        if len(fila) == 2:
            keyboard.append(fila)
            fila = []
    
    if fila:
        keyboard.append(fila)
    
    keyboard.append([InlineKeyboardButton("◀️ CANCELAR", callback_data="menu_admin")])
    
    await query.edit_message_text(
        text=mensaje,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )
    
    return INGRESAR_DEFENSA

async def seleccionar_tipo_defensa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📝 Selecciona tipo de defensa"""
    query = update.callback_query
    await query.answer()
    
    def_id = query.data.split("_")[3]
    context.user_data['admin_defensa_tipo'] = def_id
    
    try:
        from defensa import CONFIG_DEFENSAS
        config = CONFIG_DEFENSAS[def_id]
    except:
        await query.edit_message_text(
            "❌ <b>Error</b>\n\nNo se pudo cargar la configuración de la defensa.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ VOLVER", callback_data="menu_admin")
            ]])
        )
        return ConversationHandler.END
    
    user_id = context.user_data.get('admin_defensa_user')
    usuario = AuthSystem.obtener_usuario(user_id)
    username = usuario.get("username", f"Usuario {user_id}")
    
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"🛡️ <b>REGALAR DEFENSAS</b> - {username}\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"Defensa: {config['icono']} {config['nombre']}\n\n"
        f"Escribe la cantidad que deseas regalar:\n\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    )
    
    keyboard = [[InlineKeyboardButton("◀️ CANCELAR", callback_data="menu_admin")]]
    
    await query.edit_message_text(
        text=mensaje,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )
    
    return INGRESAR_CANTIDAD_DEFENSA

async def ingresar_cantidad_defensa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📝 Recibe cantidad y ejecuta"""
    try:
        cantidad = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("❌ Por favor, ingresa un número válido.")
        return INGRESAR_CANTIDAD_DEFENSA
    
    if cantidad <= 0 or cantidad > 1000000:
        await update.message.reply_text("❌ La cantidad debe ser entre 1 y 1.000.000.")
        return INGRESAR_CANTIDAD_DEFENSA
    
    user_id = context.user_data.get('admin_defensa_user')
    def_id = context.user_data.get('admin_defensa_tipo')
    
    try:
        from defensa import CONFIG_DEFENSAS
        config = CONFIG_DEFENSAS[def_id]
    except:
        await update.message.reply_text("❌ Error al cargar configuración de la defensa.")
        return ConversationHandler.END
    
    defensa_data = load_json(DEFENSA_USUARIO_FILE) or {}
    defensas = defensa_data.get(str(user_id), {})
    
    defensas[def_id] = defensas.get(def_id, 0) + cantidad
    defensa_data[str(user_id)] = defensas
    save_json(DEFENSA_USUARIO_FILE, defensa_data)
    
    username = AuthSystem.obtener_username(user_id)
    admin_username = AuthSystem.obtener_username(update.effective_user.id)
    
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"✅ <b>DEFENSAS REGALADAS</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"👤 Usuario: {username}\n"
        f"🛡️ Defensa: {config['icono']} {config['nombre']}\n"
        f"📦 Cantidad: +{abreviar_numero(cantidad)}\n"
        f"📊 Total ahora: {abreviar_numero(defensas.get(def_id, 0))}\n\n"
        f"👑 Admin: {admin_username}\n\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    )
    
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=(
                f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
                f"🛡️ <b>¡HAS RECIBIDO DEFENSAS!</b>\n"
                f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
                f"{config['icono']} {config['nombre']}: +{cantidad}\n"
                f"📊 Total: {defensas.get(def_id, 0)}\n\n"
                f"👑 Administrador: {admin_username}\n\n"
                f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
            ),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"❌ Error notificando a {user_id}: {e}")
    
    keyboard = [[InlineKeyboardButton("◀️ VOLVER AL PANEL", callback_data="menu_admin")]]
    
    await update.message.reply_text(
        text=mensaje,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )
    
    keys = ['admin_defensa_user', 'admin_defensa_tipo']
    for key in keys:
        if key in context.user_data:
            del context.user_data[key]
    
    return ConversationHandler.END

# ================= 🔄 OBTENER CONVERSATION HANDLERS =================

def obtener_conversation_handlers_admin():
    """🔄 Retorna los ConversationHandlers para el panel de admin"""
    
    recursos_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(regalar_recursos_menu, pattern="^admin_regalar_recursos$")],
        states={
            SELECCIONAR_USUARIO: [CallbackQueryHandler(seleccionar_usuario_recursos, pattern="^admin_recurso_user_")],
            INGRESAR_METAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, ingresar_metal_handler)],
            INGRESAR_CRISTAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, ingresar_cristal_handler)],
            INGRESAR_DEUTERIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, ingresar_deuterio_handler)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar_conversacion_admin)],
        name="admin_recursos",
        persistent=False
    )
    
    flota_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(regalar_flota_menu, pattern="^admin_regalar_flota$")],
        states={
            SELECCIONAR_USUARIO_NAVE: [CallbackQueryHandler(seleccionar_usuario_flota, pattern="^admin_flota_user_")],
            INGRESAR_NAVE: [CallbackQueryHandler(seleccionar_nave_flota, pattern="^admin_flota_nave_")],
            INGRESAR_CANTIDAD_NAVE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ingresar_cantidad_flota)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar_conversacion_admin)],
        name="admin_flota",
        persistent=False
    )
    
    defensa_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(regalar_defensa_menu, pattern="^admin_regalar_defensa$")],
        states={
            SELECCIONAR_USUARIO_DEFENSA: [CallbackQueryHandler(seleccionar_usuario_defensa, pattern="^admin_defensa_user_")],
            INGRESAR_DEFENSA: [CallbackQueryHandler(seleccionar_tipo_defensa, pattern="^admin_defensa_tipo_")],
            INGRESAR_CANTIDAD_DEFENSA: [MessageHandler(filters.TEXT & ~filters.COMMAND, ingresar_cantidad_defensa)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar_conversacion_admin)],
        name="admin_defensa",
        persistent=False
    )
    
    edificio_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(modificar_nivel_menu, pattern="^admin_modificar_nivel$")],
        states={
            SELECCIONAR_USUARIO_EDIFICIO: [CallbackQueryHandler(seleccionar_usuario_edificio, pattern="^admin_edificio_user_")],
            INGRESAR_EDIFICIO: [CallbackQueryHandler(seleccionar_tipo_edificio, pattern="^admin_edificio_tipo_")],
            INGRESAR_NIVEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, ingresar_nivel_edificio)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar_conversacion_admin)],
        name="admin_edificio",
        persistent=False
    )
    
    investigacion_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(mejorar_investigacion_menu, pattern="^admin_mejorar_investigacion$")],
        states={
            SELECCIONAR_USUARIO_INVESTIGACION: [CallbackQueryHandler(seleccionar_usuario_investigacion, pattern="^admin_investigacion_user_")],
            INGRESAR_INVESTIGACION: [CallbackQueryHandler(seleccionar_tipo_investigacion, pattern="^admin_investigacion_tipo_")],
            INGRESAR_NIVEL_INV: [MessageHandler(filters.TEXT & ~filters.COMMAND, ingresar_nivel_investigacion)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar_conversacion_admin)],
        name="admin_investigacion",
        persistent=False
    )
    
    anuncio_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(enviar_anuncio_menu, pattern="^admin_enviar_anuncio$")],
        states={
            INGRESAR_ANUNCIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_anuncio_handler)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar_conversacion_admin)],
        name="admin_anuncio",
        persistent=False
    )
    
    agregar_admin_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(agregar_admin_menu, pattern="^admin_agregar$")],
        states={
            SELECCIONAR_USUARIO_ADMIN: [CallbackQueryHandler(seleccionar_usuario_admin, pattern="^admin_agregar_user_")],
            CONFIRMAR_ADMIN: [CallbackQueryHandler(confirmar_agregar_admin, pattern="^admin_confirmar_agregar$")],
        },
        fallbacks=[CommandHandler("cancelar", cancelar_conversacion_admin)],
        name="admin_agregar",
        persistent=False
    )
    
    return [
        recursos_handler,
        flota_handler,
        defensa_handler,
        edificio_handler,
        investigacion_handler,
        anuncio_handler,
        agregar_admin_handler
    ]

# ================= EXPORTAR =================

__all__ = [
    'start_handler',
    'decision_handler',
    'mostrar_panel_admin',
    'admin_callback_handler',
    'obtener_conversation_handlers_admin',
    'admin_pendientes_handler',
    'admin_lista_usuarios',
    'reinicio_fabrica_menu',
    'confirmar_reinicio_fabrica',
    'limpiar_colas_handler',
    'ejecutar_limpiar_colas',
    'agregar_admin_menu',
    'lista_administradores_handler',
    'remover_admin_menu',
    'confirmar_remover_admin',
    'admin_estadisticas_handler',
    'regalar_recursos_menu',
    'regalar_flota_menu',
    'regalar_defensa_menu',
    'modificar_nivel_menu',
    'subir_nivel_construccion_menu',
    'mejorar_investigacion_menu',
    'enviar_anuncio_menu',
    'backup_menu_handler',
    'backup_callback_handler',
    'obtener_conversation_handlers_backup',
    'crear_backup_completo',
    'restaurar_backup_desde_texto',
    'backup_exportar_handler',
    'backup_importar_menu',
    'backup_recibir_archivo_handler',
    'backup_listar_handler',
    'backup_limpiar_handler',
    'toggle_mantenimiento_handler'  # 👈 NUEVO
]
