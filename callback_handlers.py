#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#██████╗ ███████╗████████╗██████╗  █████╗ ██╗     ███████╗
#██╔══██╗██╔════╝╚══██╔══╝██╔══██╗██╔══██╗██║     ██╔════╝
#██████╔╝███████╗   ██║   ██████╔╝███████║██║     ███████╗
#██╔══██╗╚════██║   ██║   ██╔══██╗██╔══██║██║     ╚════██║
#██║  ██║███████║   ██║   ██║  ██║██║  ██║███████╗███████║
#╚═╝  ╚═╝╚══════╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚══════╝

#🚀 ASTRO.IO v2.4.5 🚀
#🎯 callback_handlers.py - ÚNICO PUNTO DE ENTRADA PARA TODOS LOS CALLBACKS
#===========================================================
#✅ MISMO ESTILO que menú principal
#✅ MANEJO CORRECTO de solicitudes pendientes
#✅ NUEVO CALLBACK PARA MANTENIMIENTO
#✅ INTEGRACIÓN CON MERCADO
#⚠️ LOS CALLBACKS DE ADMIN (aceptar_/rechazar_) SON MANEJADOS DIRECTAMENTE EN AstroIO.py
#===========================================================

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from menus_principal import menu_principal
from recursos import menu_recursos_handler
from usuarios import (
    mostrar_panel_admin, admin_pendientes_handler, admin_lista_usuarios,
    regalar_recursos_menu, reinicio_fabrica_menu, confirmar_reinicio_fabrica,
    subir_nivel_construccion_menu, regalar_flota_menu, regalar_defensa_menu,
    mejorar_investigacion_menu, admin_callback_handler, limpiar_colas_handler,
    admin_estadisticas_handler, lista_administradores_handler, remover_admin_menu,
    backup_callback_handler, obtener_conversation_handlers_backup,
    toggle_mantenimiento_handler  # 👈 SOLO mantenimiento, NO decision_handler
)
from edificios import (
    menu_edificios_principal, submenu_edificio, construir_handler,
    ver_cola_handler as edificios_ver_cola,
    cancelar_construccion_handler as edificios_cancelar
)
from flota import (
    menu_flota_principal, submenu_nave, confirmar_construccion_handler,
    comprar_nave_handler, personalizar_cantidad_handler,
    ver_cola_handler as flota_ver_cola,
    cancelar_construccion_handler as flota_cancelar
)
from defensa import (
    menu_defensa_principal, submenu_defensa, confirmar_construccion_defensa_handler,
    comprar_defensa_handler, personalizar_cantidad_defensa_handler,
    ver_cola_handler as defensa_ver_cola,
    cancelar_construccion_handler as defensa_cancelar
)
from investigaciones import (
    menu_investigaciones_principal, submenu_investigacion,
    iniciar_investigacion_handler
)
from puntuacion import puntuacion_callback_handler
from alianza import alianza_callback_handler
from guia import guia_callback_handler
from base_flotas import (
    menu_flota_principal as menu_base_flotas_principal,
    reporte_misiones_activas,
    reporte_historial_bajas
)
from mercado import mercado_callback_handler

logger = logging.getLogger(__name__)

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🎯 ÚNICO handler para TODOS los callbacks del bot"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = query.from_user.id
    
    logger.info(f"📱 Callback: {data} - User: {user_id}")
    
    # ========== ⚠️ IMPORTANTE: DECISIONES DE ADMIN ==========
    # Los callbacks "aceptar_*" y "rechazar_*" son manejados DIRECTAMENTE
    # por handlers específicos en AstroIO.py con mayor prioridad.
    # Este bloque está COMENTADO para evitar conflictos.
    """
    if data.startswith("aceptar_") or data.startswith("rechazar_"):
        logger.info(f"👑 Procesando decisión admin: {data}")
        # Estos son manejados por handlers directos en AstroIO.py
        return
    """
    
    # ========== MENÚ PRINCIPAL ==========
    if data == "menu_principal":
        await menu_principal(update, context)
    
    # ========== RECURSOS ==========
    elif data == "menu_recursos":
        await menu_recursos_handler(update, context)
    
    # ========== EDIFICIOS ==========
    elif data == "menu_edificios":
        await menu_edificios_principal(update, context)
    elif data.startswith("edificio_"):
        await submenu_edificio(update, context)
    elif data.startswith("construir_"):
        await construir_handler(update, context)
    elif data == "edificios_cola":
        await edificios_ver_cola(update, context)
    elif data.startswith("edificios_cancelar_"):
        await edificios_cancelar(update, context)
    
    # ========== FLOTA ==========
    elif data == "menu_flota":
        await menu_flota_principal(update, context)
    elif data.startswith("nave_"):
        await submenu_nave(update, context)
    elif data.startswith("confirmar_"):
        await confirmar_construccion_handler(update, context)
    elif data.startswith("comprar_"):
        await comprar_nave_handler(update, context)
    elif data.startswith("personalizar_") and not data.startswith("personalizar_defensa_"):
        await personalizar_cantidad_handler(update, context)
    elif data == "flota_cola":
        await flota_ver_cola(update, context)
    elif data.startswith("flota_cancelar_"):
        await flota_cancelar(update, context)
    
    # ========== DEFENSA ==========
    elif data == "menu_defensa":
        await menu_defensa_principal(update, context)
    elif data.startswith("defensa_"):
        await submenu_defensa(update, context)
    elif data.startswith("confirmar_defensa_"):
        await confirmar_construccion_defensa_handler(update, context)
    elif data.startswith("comprar_defensa_"):
        await comprar_defensa_handler(update, context)
    elif data.startswith("personalizar_defensa_"):
        await personalizar_cantidad_defensa_handler(update, context)
    elif data == "defensa_cola":
        await defensa_ver_cola(update, context)
    elif data.startswith("defensa_cancelar_"):
        await defensa_cancelar(update, context)
    
    # ========== INVESTIGACIONES ==========
    elif data == "menu_investigaciones":
        await menu_investigaciones_principal(update, context)
    elif data.startswith("investigacion_"):
        await submenu_investigacion(update, context)
    elif data.startswith("investigar_"):
        await iniciar_investigacion_handler(update, context)
    
    # ========== ALIANZA ==========
    elif data == "menu_alianza" or data.startswith("alianza_"):
        await alianza_callback_handler(update, context)
    
    # ========== BASE DE FLOTAS ==========
    elif data == "menu_base_flotas":
        await menu_base_flotas_principal(update, context)
    elif data == "flota_misiones":
        await reporte_misiones_activas(update, context)
    elif data == "flota_bajas":
        await reporte_historial_bajas(update, context)
    elif data.startswith("flota_enviar_"):
        await query.edit_message_text(
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
            f"🚀 <b>ENVIAR MISIÓN</b>\n"
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
            f"Función en desarrollo.\n\n"
            f"Próximamente podrás enviar flotas a misiones.\n\n"
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ VOLVER", callback_data="menu_base_flotas")
            ]])
        )
    
    # ========== GUÍA ==========
    elif data.startswith("guia_"):
        await guia_callback_handler(update, context)
    
    # ========== PUNTUACIÓN ==========
    elif data == "menu_puntuacion" or data.startswith("puntuacion_") or data.startswith("ranking_"):
        await puntuacion_callback_handler(update, context)
    
    # ========== MERCADO ==========
    elif data.startswith("mercado_"):
        await mercado_callback_handler(update, context)
    
    # ========== ADMIN - PANEL PRINCIPAL ==========
    elif data == "menu_admin":
        await mostrar_panel_admin(update, context)
    
    # ========== ADMIN - LISTAS ==========
    elif data == "admin_pendientes":
        await admin_pendientes_handler(update, context)
    elif data == "admin_lista_usuarios":
        await admin_lista_usuarios(update, context)
    elif data == "admin_lista_admins":
        await lista_administradores_handler(update, context)
    
    # ========== 👑 CALLBACK PARA MANTENIMIENTO ==========
    elif data == "admin_toggle_mantenimiento":
        logger.info(f"🔧 Admin {user_id} alternando modo mantenimiento")
        await toggle_mantenimiento_handler(update, context)
    
    # ========== ADMIN - GESTIÓN DE ADMINISTRADORES ==========
    elif data == "admin_agregar":
        # Manejado por ConversationHandler
        return
    elif data.startswith("admin_agregar_user_"):
        return
    elif data == "admin_confirmar_agregar":
        return
    elif data == "admin_remover":
        await remover_admin_menu(update, context)
    elif data.startswith("admin_remover_user_"):
        await admin_callback_handler(update, context)
    
    # ========== ADMIN - REGALAR RECURSOS ==========
    elif data == "admin_regalar_recursos":
        return
    elif data.startswith("admin_recurso_user_"):
        return
    
    # ========== ADMIN - REGALAR NAVES ==========
    elif data == "admin_regalar_flota":
        return
    elif data.startswith("admin_flota_user_"):
        return
    elif data.startswith("admin_flota_nave_"):
        return
    
    # ========== ADMIN - REGALAR DEFENSAS ==========
    elif data == "admin_regalar_defensa":
        return
    elif data.startswith("admin_defensa_user_"):
        return
    elif data.startswith("admin_defensa_tipo_"):
        return
    
    # ========== ADMIN - MODIFICAR NIVELES ==========
    elif data == "admin_modificar_nivel":
        return
    elif data.startswith("admin_edificio_user_"):
        return
    elif data.startswith("admin_edificio_tipo_"):
        return
    
    # ========== ADMIN - MEJORAR INVESTIGACIÓN ==========
    elif data == "admin_mejorar_investigacion":
        return
    elif data.startswith("admin_investigacion_user_"):
        return
    elif data.startswith("admin_investigacion_tipo_"):
        return
    
    # ========== ADMIN - ANUNCIOS ==========
    elif data == "admin_enviar_anuncio":
        return
    
    # ========== ADMIN - LIMPIAR COLAS ==========
    elif data == "admin_limpiar_colas":
        await limpiar_colas_handler(update, context)
    elif data.startswith("admin_limpiar_colas_"):
        await admin_callback_handler(update, context)
    
    # ========== ADMIN - ESTADÍSTICAS ==========
    elif data == "admin_estadisticas":
        await admin_estadisticas_handler(update, context)
    
    # ========== ADMIN - REINICIO FÁBRICA ==========
    elif data == "admin_reinicio_fabrica":
        await reinicio_fabrica_menu(update, context)
    elif data == "admin_confirmar_reinicio":
        await confirmar_reinicio_fabrica(update, context)
    
    # ========== ADMIN - BACKUP ==========
    elif data == "admin_backup" or data.startswith("admin_backup_"):
        await backup_callback_handler(update, context)
    
    # ========== NOOP ==========
    elif data == "noop":
        pass
    
    # ========== NO RECONOCIDO ==========
    else:
        logger.warning(f"⚠️ Callback no manejado: {data}")
        await query.edit_message_text(
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
            f"⚠️ <b>FUNCIÓN EN DESARROLLO</b>\n"
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
            f"Este módulo estará disponible próximamente.\n\n"
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ VOLVER", callback_data="menu_principal")
            ]])
        )

__all__ = ['callback_handler']
