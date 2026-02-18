#!/data/data/com.termux/files/usr/bin/python3
# -*- coding: utf-8 -*-

#██████╗ ███████╗████████╗██████╗  █████╗ ██╗     ███████╗
#██╔══██╗██╔════╝╚══██╔══╝██╔══██╗██╔══██╗██║     ██╔════╝
#██████╔╝███████╗   ██║   ██████╔╝███████║██║     ███████╗
#██╔══██╗╚════██║   ██║   ██╔══██╗██╔══██║██║     ╚════██║
#██║  ██║███████║   ██║   ██║  ██║██║  ██║███████╗███████║
#╚═╝  ╚═╝╚══════╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚══════╝

#🚀 ASTRO.IO v2.4.5 🚀
# Versión v2.3.7 - AstroIO.py
# Desarrollado por @Neith07 y @Holows

"""
🚀 ASTROIO v2.3.7 - SISTEMA MODULAR COMPLETO
===================================================
✅ LOGIN CENTRALIZADO - AuthSystem
✅ VERIFICA/CREA TODOS LOS JSON AL INICIAR
✅ MENÚ PRINCIPAL CON DATOS EN TIEMPO REAL
✅ PANEL DE ADMIN COMPLETO
✅ EDIFICIOS - Sistema de colas en tiempo real
✅ FLOTA - Sistema de colas en tiempo real
✅ DEFENSA - Sistema de colas en tiempo real
✅ INVESTIGACIONES - Sistema de colas propio
✅ PUNTUACIÓN - Ranking y estadísticas en tiempo real
✅ ALIANZAS - Sistema completo con banco y permisos
✅ BACKUP - Exportar/Importar todos los datos del bot
✅ MERCADO - Sistema de mercado con Mercado Negro
✅ NAVEGACIÓN SIN SPAM - Mismo mensaje siempre
===================================================
"""

import logging
import os
import sys
import asyncio
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, 
    MessageHandler, filters, ConversationHandler, ContextTypes
)
from telegram.error import TimedOut, NetworkError

# ========== INICIALIZAR SISTEMA ==========
sys.path.append(os.path.dirname(__file__))

from login import inicializar_sistema, AuthSystem, requiere_login, requiere_admin, VERSION
from menus_principal import menu_principal, menu_bienvenida

# ========== VARIABLES DE ENTORNO ==========
TOKEN = os.environ.get("TOKEN")
if not TOKEN:
    raise RuntimeError("❌ La variable TOKEN no está definida")

try:
    ADMIN_USER_ID = int(os.environ.get("ADMIN_USER_ID", "0"))
except ValueError:
    ADMIN_USER_ID = 0
if ADMIN_USER_ID == 0:
    raise RuntimeError("❌ La variable ADMIN_USER_ID no está definida o no es válida")

# Opcionales
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "")  # Si está definida, se usa webhook
PORT = int(os.environ.get("PORT", "10000"))       # Puerto para webhook (Render asigna 10000 por defecto)

# Variables de GitHub
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_OWNER = os.environ.get("GITHUB_OWNER")
GITHUB_REPO = os.environ.get("GITHUB_REPO")
USE_GITHUB_SYNC = os.getenv("USE_GITHUB_SYNC", "false").lower() == "true"

# ✅ CREA TODOS LOS JSON Y VERIFICA TODO AL INICIAR
inicializar_sistema()

# ========== LOGGING ==========
log_dir = 'log'
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'AstroIO.log')

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ========== VERIFICAR CONFIGURACIÓN DE GITHUB ==========
def verificar_configuracion_github():
    """🔍 Verifica la configuración de GitHub al iniciar"""
    try:
        if USE_GITHUB_SYNC:
            if GITHUB_TOKEN and GITHUB_OWNER and GITHUB_REPO:
                logger.info("✅ GitHub Sync ACTIVADO - Respaldos en la nube")
                logger.info(f"📦 Repositorio: {GITHUB_OWNER}/{GITHUB_REPO}")
            else:
                logger.warning("⚠️ GitHub Sync configurado pero faltan variables")
                logger.warning("📌 Para activar, configura: GITHUB_TOKEN, GITHUB_OWNER, GITHUB_REPO")
        else:
            logger.info("📁 GitHub Sync DESACTIVADO - Solo respaldo local")
    except Exception as e:
        logger.warning(f"⚠️ No se pudo verificar GitHub: {e}")

# Llamar a la función
verificar_configuracion_github()

# ========== IMPORTAR MÓDULOS ==========
from usuarios import start_handler, decision_handler
from recursos import mostrar_recursos
from callback_handlers import callback_handler

# ========== IMPORTAR MÓDULOS DE ALIANZA ==========
try:
    from alianza import obtener_conversation_handlers
    ALIANZA_ACTIVA = True
    logger.info("✅ Sistema de alianzas cargado")
except ImportError as e:
    logger.warning(f"⚠️ Sistema de alianzas no disponible: {e}")
    ALIANZA_ACTIVA = False
    def obtener_conversation_handlers():
        return []

# ========== IMPORTAR MÓDULOS DE BACKUP ==========
try:
    from usuarios import obtener_conversation_handlers_backup
    BACKUP_ACTIVO = True
    logger.info("✅ Sistema de backup cargado")
except ImportError as e:
    logger.warning(f"⚠️ Sistema de backup no disponible: {e}")
    BACKUP_ACTIVO = False
    def obtener_conversation_handlers_backup():
        return []

# ========== IMPORTAR MÓDULOS DE ADMIN ==========
try:
    from usuarios import obtener_conversation_handlers_admin
    ADMIN_CONVERSATION_ACTIVO = True
    logger.info("✅ ConversationHandlers de admin cargados")
except ImportError as e:
    logger.warning(f"⚠️ ConversationHandlers de admin no disponibles: {e}")
    ADMIN_CONVERSATION_ACTIVO = False
    def obtener_conversation_handlers_admin():
        return []

# ========== IMPORTAR MÓDULOS DE MERCADO ==========
try:
    from mercado import obtener_conversation_handlers_mercado
    MERCADO_ACTIVO = True
    logger.info("✅ Sistema de mercado cargado")
except ImportError as e:
    logger.warning(f"⚠️ Sistema de mercado no disponible: {e}")
    MERCADO_ACTIVO = False
    def obtener_conversation_handlers_mercado():
        return []

# ========== HANDLERS ==========

async def start_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    🚀 Comando /start
    - SIEMPRE verifica datos en tiempo real
    - Usuarios con @username
    """
    user = update.effective_user
    user_id = user.id
    username = user.first_name or "Comandante"
    username_tag = AuthSystem.formatear_username(user_id, username)
    
    logger.info(f"📱 /start - {username_tag}")
    
    # ✅ Verificar si está registrado
    if not AuthSystem.esta_registrado(user_id):
        AuthSystem.registrar_usuario(user_id, username)
        logger.info(f"📌 Usuario registrado: {username_tag}")
    
    # ✅ Si está autorizado, va al menú principal
    if AuthSystem.esta_autorizado(user_id):
        # Mock Update para menu_principal
        class MockMessage:
            def __init__(self, chat_id):
                self.chat = type('obj', (), {'id': chat_id})
            async def reply_text(self, *args, **kwargs):
                pass
            async def edit_message_text(self, *args, **kwargs):
                pass
        
        class MockCallbackQuery:
            def __init__(self, user_id, username_tag):
                self.from_user = type('obj', (), {
                    'id': user_id,
                    'first_name': username_tag
                })
                self.data = "menu_principal"
                self.message = MockMessage(user_id)
                self._is_answer = False
            
            async def answer(self):
                self._is_answer = True
            
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
        
        mock_query = MockCallbackQuery(user_id, username_tag)
        mock_update = MockUpdate(mock_query)
        
        await menu_principal(mock_update, context)
        return
    
    # Si no, proceso normal de registro
    await start_handler(update, context)

async def admin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """👑 Comando /admin"""
    user_id = update.effective_user.id
    
    if not AuthSystem.es_admin(user_id):
        await update.message.reply_text(
            "❌ <b>ACCESO DENEGADO</b>\n\nNo tienes permisos de administrador.",
            parse_mode="HTML"
        )
        return
    
    # Mock para panel admin
    class MockMessage:
        def __init__(self, chat_id):
            self.chat = type('obj', (), {'id': chat_id})
        async def reply_text(self, *args, **kwargs):
            pass
        async def edit_message_text(self, *args, **kwargs):
            pass
    
    class MockCallbackQuery:
        def __init__(self, user_id):
            self.from_user = type('obj', (), {'id': user_id})
            self.data = "menu_admin"
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
    
    mock_query = MockCallbackQuery(user_id)
    mock_update = MockUpdate(mock_query)
    
    from usuarios import mostrar_panel_admin
    await mostrar_panel_admin(mock_update, context)

async def ayuda_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📋 Comando /ayuda"""
    ayuda_texto = (
        f"🤖 <b>ASTROIO {VERSION} - AYUDA</b>\n\n"
        f"📋 <b>COMANDOS:</b>\n"
        f"• /start - Menú principal / Registro\n"
        f"• /recursos - Ver recursos en tiempo real\n"
        f"• /ayuda - Esta ayuda\n\n"
        f"👑 <b>ADMIN:</b>\n"
        f"• /admin - Panel de administración\n\n"
        f"🎮 <b>SISTEMA:</b>\n"
        f"• Datos 100% actualizados en tiempo real\n"
        f"• Usuarios con @username\n"
        f"• Navegación sin spam - Un solo mensaje\n"
        f"• Sistema de colas en edificios, flota y defensa\n"
        f"• Sistema de backup completo (Exportar/Importar)\n"
        f"• Mercado Negro con ofertas de usuarios y sistema"
    )
    await update.message.reply_text(ayuda_texto, parse_mode="HTML")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """❌ Manejador global de errores"""
    logger.error(f"Error no capturado: {context.error}", exc_info=context.error)
    
    try:
        if update and hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.answer(
                "❌ Error interno. Intenta nuevamente.",
                show_alert=True
            )
    except:
        pass

async def recibir_mensajes_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    📨 Maneja mensajes de texto que no son comandos
    - Útil para ConversationHandlers
    """
    user_id = update.effective_user.id
    username_tag = AuthSystem.obtener_username(user_id)
    
    logger.debug(f"📨 Mensaje de {username_tag}: {update.message.text[:50]}...")
    
    # Si no hay una conversación activa, ignoramos
    pass

# ========== FUNCIÓN PARA VERIFICAR CONEXIÓN ==========
async def verificar_conexion(app):
    """🔌 Verifica conexión con Telegram antes de iniciar"""
    max_intentos = 5
    for intento in range(max_intentos):
        try:
            logger.info(f"📡 Intento de conexión {intento + 1}/{max_intentos}")
            # Probar conexión con get_me
            bot_info = await app.bot.get_me()
            logger.info(f"✅ Conexión exitosa - Bot: @{bot_info.username}")
            return True
        except (TimedOut, NetworkError) as e:
            logger.warning(f"❌ Error de conexión: {e}")
            if intento < max_intentos - 1:
                logger.info(f"⏳ Reintentando en 5 segundos...")
                await asyncio.sleep(5)
            else:
                logger.error("❌ No se pudo conectar después de varios intentos")
                return False
        except Exception as e:
            logger.error(f"❌ Error inesperado: {e}")
            return False
    return False

# ========== 🕐 TAREAS PROGRAMADAS ==========
def main():
    print("=" * 60)
    print(f"🚀 ASTROIO {VERSION} - SISTEMA MODULAR COMPLETO")
    print("=" * 60)
    print(f"✅ Versión: {VERSION}")
    print("✅ Archivos JSON verificados")
    print("✅ Sistema de login activado")
    print("✅ Datos en tiempo real - SIN CACHE")
    print("✅ Usuarios con @username")
    print("✅ Navegación sin spam")
    print("✅ Edificios - Colas en tiempo real")
    print("✅ Flota - Colas en tiempo real")
    print("✅ Defensa - Colas en tiempo real")
    print("✅ Investigaciones - Sistema de colas")
    print("✅ Puntuación - Ranking global")
    print("✅ Alianzas - Sistema completo" if ALIANZA_ACTIVA else "⚠️ Alianzas - No disponible")
    print("✅ Backup - Exportar/Importar datos" if BACKUP_ACTIVO else "⚠️ Backup - No disponible")
    print("✅ Mercado - Sistema de mercado" if MERCADO_ACTIVO else "⚠️ Mercado - No disponible")
    print("=" * 60)
    
    # Crear aplicación
    app = Application.builder().token(TOKEN).build()
    
    # Configurar timeouts (según versión)
    try:
        app.bot.request._request_timeout = 30
        app.bot.request.connect_timeout = 30
        app.bot.request.read_timeout = 30
    except:
        try:
            app.bot.request.timeout = 30
        except:
            pass
    
    # ========== COMANDOS ==========
    app.add_handler(CommandHandler("start", start_command_handler))
    app.add_handler(CommandHandler("recursos", mostrar_recursos))
    app.add_handler(CommandHandler("ayuda", ayuda_handler))
    app.add_handler(CommandHandler("admin", admin_handler))
    
    # ========== CONVERSATION HANDLERS (ALIANZA) ==========
    if ALIANZA_ACTIVA:
        for handler in obtener_conversation_handlers():
            app.add_handler(handler)
        logger.info(f"✅ {len(obtener_conversation_handlers())} ConversationHandlers de alianza registrados")
    
    # ========== CONVERSATION HANDLERS (ADMIN) ==========
    if ADMIN_CONVERSATION_ACTIVO:
        for handler in obtener_conversation_handlers_admin():
            app.add_handler(handler)
        logger.info(f"✅ {len(obtener_conversation_handlers_admin())} ConversationHandlers de admin registrados")
    
    # ========== CONVERSATION HANDLERS (BACKUP) ==========
    if BACKUP_ACTIVO:
        for handler in obtener_conversation_handlers_backup():
            app.add_handler(handler)
        logger.info(f"✅ {len(obtener_conversation_handlers_backup())} ConversationHandlers de backup registrados")
    
    # ========== CONVERSATION HANDLERS (MERCADO) ==========
    if MERCADO_ACTIVO:
        for handler in obtener_conversation_handlers_mercado():
            app.add_handler(handler)
        logger.info(f"✅ {len(obtener_conversation_handlers_mercado())} ConversationHandlers de mercado registrados")
    
    # ========== CALLBACKS ==========
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(CallbackQueryHandler(decision_handler, pattern="^(aceptar_|cancelar_).*$"))
    
    # ========== MENSAJES DE TEXTO ==========
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_mensajes_handler))
    
    # ========== MENSAJES DE DOCUMENTOS ==========
    app.add_handler(MessageHandler(filters.Document.FileExtension("txt"), recibir_mensajes_handler))
    
    # ========== 🕐 TAREAS PROGRAMADAS (COLAS) ==========
    job_queue = app.job_queue
    if job_queue:
        # COLAS DE EDIFICIOS
        try:
            from edificios import procesar_colas_background as procesar_colas_edificios
            job_queue.run_repeating(procesar_colas_edificios, interval=60, first=10)
            logger.info("✅ Tarea programada: Colas de edificios (cada 60s)")
        except Exception as e:
            logger.error(f"❌ Error en colas de edificios: {e}")
        
        # COLAS DE FLOTA
        try:
            from flota import procesar_colas_background as procesar_colas_flota
            job_queue.run_repeating(procesar_colas_flota, interval=60, first=15)
            logger.info("✅ Tarea programada: Colas de flota (cada 60s)")
        except Exception as e:
            logger.error(f"❌ Error en colas de flota: {e}")
        
        # COLAS DE DEFENSA
        try:
            from defensa import procesar_colas_background as procesar_colas_defensa
            job_queue.run_repeating(procesar_colas_defensa, interval=60, first=20)
            logger.info("✅ Tarea programada: Colas de defensa (cada 60s)")
        except Exception as e:
            logger.error(f"❌ Error en colas de defensa: {e}")
        
        # COLAS DE INVESTIGACIONES
        try:
            from investigaciones import procesar_colas_background as procesar_colas_investigacion
            job_queue.run_repeating(procesar_colas_investigacion, interval=60, first=25)
            logger.info("✅ Tarea programada: Colas de investigación (cada 60s)")
        except Exception as e:
            logger.error(f"❌ Error en colas de investigación: {e}")
    else:
        logger.warning("⚠️ Job queue no disponible - Las colas no se procesarán automáticamente")
    
    # ========== ERRORES ==========
    app.add_error_handler(error_handler)
    
    print("\n🚀 Iniciando bot...")
    print("=" * 60 + "\n")
    
    # Decidir modo: webhook si WEBHOOK_URL está definida, sino polling
    if WEBHOOK_URL:
        # Configurar webhook
        async def setup_webhook():
            webhook_url = f"{WEBHOOK_URL.rstrip('/')}/{TOKEN}"
            await app.bot.set_webhook(url=webhook_url)
            logger.info(f"✅ Webhook configurado en {webhook_url}")
            # Iniciar webhook (corriendo en el puerto asignado)
            await app.start_webhook(
                listen="0.0.0.0",
                port=PORT,
                url_path=TOKEN,
                webhook_url=webhook_url
            )
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(setup_webhook())
            logger.info(f"🚀 Bot iniciado en modo webhook en puerto {PORT}")
            loop.run_forever()
        except KeyboardInterrupt:
            print("\n👋 Bot detenido manualmente")
        finally:
            loop.close()
    else:
        # Modo polling (local)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            if loop.run_until_complete(verificar_conexion(app)):
                logger.info("✅ Conexión verificada. Iniciando bot en modo polling...")
                app.run_polling(
                    allowed_updates=Update.ALL_TYPES,
                    drop_pending_updates=True
                )
            else:
                logger.error("❌ No se pudo establecer conexión. Saliendo...")
                print("\n❌ Error de conexión. Verifica tu internet y reintenta.")
        except KeyboardInterrupt:
            print("\n👋 Bot detenido manualmente")
        except Exception as e:
            print(f"\n❌ Error crítico: {e}")
            import traceback
            traceback.print_exc()
        finally:
            loop.close()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Bot detenido manualmente")
    except Exception as e:
        print(f"\n❌ Error crítico: {e}")
        import traceback
        traceback.print_exc()
