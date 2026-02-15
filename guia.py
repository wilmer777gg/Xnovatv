#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#██████╗ ███████╗████████╗██████╗  █████╗ ██╗     ███████╗
#██╔══██╗██╔════╝╚══██╔══╝██╔══██╗██╔══██╗██║     ██╔════╝
#██████╔╝███████╗   ██║   ██████╔╝███████║██║     ███████╗
#██╔══██╗╚════██║   ██║   ██╔══██╗██╔══██║██║     ╚════██║
#██║  ██║███████║   ██║   ██║  ██║██║  ██║███████╗███████║
#╚═╝  ╚═╝╚══════╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚══════╝

#🚀 ASTRO.IO v2.4.0 🚀
#📖 guia.py - SISTEMA DE GUÍAS Y REQUISITOS
#============================================
#✅ MISMO ESTILO que menú principal
#✅ Separadores con 🌀
#✅ Formato consistente en todos los mensajes
#============================================

import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from login import AuthSystem, requiere_login
from database import load_json

logger = logging.getLogger(__name__)

# ================= CONSTANTES =================
DATA_DIR = "data"
EDIFICIOS_FILE = os.path.join(DATA_DIR, "edificios.json")
INVESTIGACIONES_FILE = os.path.join(DATA_DIR, "investigaciones.json")
ITEMS_POR_PAGINA = 4

# ================= CARGAR CONFIGURACIONES =================

def cargar_config_naves():
    """🚀 Carga configuración de naves desde flota.py"""
    try:
        from flota import CONFIG_NAVES
        return CONFIG_NAVES
    except ImportError:
        # Configuración de respaldo
        return {
            "cazador_ligero": {
                "nombre": "Cazador Ligero",
                "tipo": "combate",
                "icono": "🚀",
                "ataque": 50,
                "escudo": 10,
                "velocidad": 100,
                "capacidad": 5000,
                "consumo": 20,
                "requisitos": {"hangar": 1}
            },
            "cazador_pesado": {
                "nombre": "Cazador Pesado",
                "tipo": "combate",
                "icono": "⚔️",
                "ataque": 150,
                "escudo": 25,
                "velocidad": 80,
                "capacidad": 10000,
                "consumo": 30,
                "requisitos": {"hangar": 3}
            },
            "crucero": {
                "nombre": "Crucero",
                "tipo": "combate",
                "icono": "⚡",
                "ataque": 250,
                "escudo": 50,
                "velocidad": 90,
                "capacidad": 15000,
                "consumo": 35,
                "requisitos": {"hangar": 5}
            },
            "nave_batalla": {
                "nombre": "Nave de Batalla",
                "tipo": "combate",
                "icono": "💥",
                "ataque": 1000,
                "escudo": 200,
                "velocidad": 70,
                "capacidad": 75000,
                "consumo": 150,
                "requisitos": {"hangar": 7}
            },
            "nave_carga_pequena": {
                "nombre": "Nave de Carga Pequeña",
                "tipo": "civil",
                "icono": "📦",
                "ataque": 5,
                "escudo": 10,
                "velocidad": 120,
                "capacidad": 5000,
                "consumo": 10,
                "requisitos": {"hangar": 2}
            },
            "nave_carga_grande": {
                "nombre": "Nave de Carga Grande",
                "tipo": "civil",
                "icono": "🚛",
                "ataque": 5,
                "escudo": 25,
                "velocidad": 80,
                "capacidad": 25000,
                "consumo": 50,
                "requisitos": {"hangar": 4}
            }
        }

def cargar_config_defensas():
    """🛡️ Carga configuración de defensas desde defensa.py"""
    try:
        from defensa import CONFIG_DEFENSAS
        return CONFIG_DEFENSAS
    except ImportError:
        # Configuración de respaldo
        return {
            "lanza_misiles": {
                "nombre": "Lanzador de Misiles",
                "tipo": "ligera",
                "icono": "🚀",
                "ataque": 80,
                "escudo": 20,
                "costo": {"metal": 2000},
                "requisitos": {"hangar": 1}
            },
            "laser_ligero": {
                "nombre": "Láser Ligero",
                "tipo": "ligera",
                "icono": "🔫",
                "ataque": 100,
                "escudo": 25,
                "costo": {"metal": 1500, "cristal": 500},
                "requisitos": {"hangar": 2}
            },
            "canion_ionico": {
                "nombre": "Cañón Iónico",
                "tipo": "media",
                "icono": "⚡",
                "ataque": 150,
                "escudo": 500,
                "costo": {"metal": 2000, "cristal": 6000},
                "requisitos": {"hangar": 4}
            },
            "canion_plasma": {
                "nombre": "Cañón de Plasma",
                "tipo": "pesada",
                "icono": "☢️",
                "ataque": 3000,
                "escudo": 300,
                "costo": {"metal": 50000, "cristal": 50000, "deuterio": 30000},
                "requisitos": {"hangar": 8}
            }
        }

def cargar_config_edificios():
    """🏗️ Carga configuración de edificios desde edificios.py"""
    try:
        from edificios import CONSTRUCCIONES
        return CONSTRUCCIONES
    except ImportError:
        # Configuración de respaldo
        return {
            "metal": {
                "nombre": "Mina de Metal",
                "tipo": "mina",
                "icono": "🔩",
                "descripcion": "Produce metal para construcciones"
            },
            "cristal": {
                "nombre": "Mina de Cristal",
                "tipo": "mina",
                "icono": "💎",
                "descripcion": "Produce cristal para investigaciones"
            },
            "deuterio": {
                "nombre": "Sintetizador de Deuterio",
                "tipo": "mina",
                "icono": "🧪",
                "descripcion": "Produce deuterio para combustible"
            },
            "energia": {
                "nombre": "Planta de Energía",
                "tipo": "edificio",
                "icono": "⚡",
                "descripcion": "Genera energía para tus estructuras"
            },
            "laboratorio": {
                "nombre": "Laboratorio de Investigación",
                "tipo": "edificio",
                "icono": "🔬",
                "descripcion": "Permite investigar nuevas tecnologías"
            },
            "hangar": {
                "nombre": "Hangar Espacial",
                "tipo": "edificio",
                "icono": "🚀",
                "descripcion": "Construye y almacena naves"
            },
            "terraformer": {
                "nombre": "Terraformer",
                "tipo": "edificio",
                "icono": "🌍",
                "descripcion": "Expande los campos de tu planeta"
            }
        }

def cargar_config_investigaciones():
    """🔬 Carga configuración de investigaciones desde investigaciones.py"""
    try:
        from investigaciones import INVESTIGACIONES
        return INVESTIGACIONES
    except ImportError:
        # Configuración de respaldo
        return {
            "propulsion_combustion": {
                "nombre": "Propulsión por Combustión",
                "icono": "🚀",
                "grupo": "Propulsión",
                "requisitos": {"laboratorio": 1},
                "bonificacion": "+10% velocidad naves civiles"
            },
            "tecnologia_energia": {
                "nombre": "Tecnología de Energía",
                "icono": "🔋",
                "grupo": "Energía",
                "requisitos": {"laboratorio": 1},
                "bonificacion": "+5% producción de energía"
            },
            "tecnologia_laser": {
                "nombre": "Tecnología Láser",
                "icono": "🔬",
                "grupo": "Armamento",
                "requisitos": {"laboratorio": 2, "tecnologia_energia": 3},
                "bonificacion": "+15% daño armas láser"
            }
        }

# ================= FUNCIONES DE PAGINACIÓN =================

def paginar_lista(items: list, pagina: int, items_por_pagina: int = ITEMS_POR_PAGINA):
    """📑 Pagina una lista de items"""
    total_paginas = (len(items) + items_por_pagina - 1) // items_por_pagina
    pagina = max(1, min(pagina, total_paginas))
    
    inicio = (pagina - 1) * items_por_pagina
    fin = inicio + items_por_pagina
    
    return items[inicio:fin], pagina, total_paginas

# ================= MENÚ PRINCIPAL DE GUÍA =================

@requiere_login
async def guia_desbloqueo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📖 Menú principal de guías"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    username_tag = AuthSystem.obtener_username(user_id)
    
    texto = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"📖 <b>GUÍA DE DESBLOQUEO</b> - {username_tag}\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"Selecciona una categoría para ver los requisitos:\n\n"
        f"🚀 Naves espaciales\n"
        f"🛡️ Defensas planetarias\n"
        f"🏗️ Edificios\n"
        f"🔬 Investigaciones\n\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    )
    
    teclado = [
        [
            InlineKeyboardButton("🚀 NAVES", callback_data="guia_naves"),
            InlineKeyboardButton("🛡️ DEFENSAS", callback_data="guia_defensas")
        ],
        [
            InlineKeyboardButton("🏗️ EDIFICIOS", callback_data="guia_edificios"),
            InlineKeyboardButton("🔬 INVESTIGACIÓN", callback_data="guia_investigacion")
        ],
        [InlineKeyboardButton("◀️ VOLVER", callback_data="menu_principal")]
    ]
    
    await query.edit_message_text(
        text=texto,
        reply_markup=InlineKeyboardMarkup(teclado),
        parse_mode="HTML"
    )

# ================= GUÍA DE NAVES =================

@requiere_login
async def guia_naves(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🚀 Guía de naves espaciales - Vista general"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    username_tag = AuthSystem.obtener_username(user_id)
    
    CONFIG_NAVES = cargar_config_naves()
    
    texto = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"🚀 <b>NAVES ESPACIALES</b> - {username_tag}\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
    )
    
    # Naves de combate
    texto += "⚔️ <b>NAVES DE COMBATE:</b>\n"
    naves_combate = {k: v for k, v in CONFIG_NAVES.items() if v.get("tipo") == "combate"}
    for nave_id, config in list(naves_combate.items())[:4]:
        nombre = config.get("nombre", nave_id)
        requisitos = config.get("requisitos", {})
        hangar = requisitos.get("hangar", 1)
        ataque = config.get("ataque", 0)
        escudo = config.get("escudo", 0)
        velocidad = config.get("velocidad", 0)
        texto += f"   • {config.get('icono', '🚀')} {nombre}\n"
        texto += f"     └ Requisito: Hangar {hangar} | ⚔️ {ataque} | 🛡️ {escudo} | ⚡ {velocidad}\n"
    
    # Naves civiles
    texto += f"\n📦 <b>NAVES CIVILES:</b>\n"
    naves_civiles = {k: v for k, v in CONFIG_NAVES.items() if v.get("tipo") == "civil"}
    for nave_id, config in list(naves_civiles.items())[:4]:
        nombre = config.get("nombre", nave_id)
        requisitos = config.get("requisitos", {})
        hangar = requisitos.get("hangar", 1)
        capacidad = config.get("capacidad", 0)
        velocidad = config.get("velocidad", 0)
        texto += f"   • {config.get('icono', '📦')} {nombre}\n"
        texto += f"     └ Requisito: Hangar {hangar} | 📦 {capacidad:,} | ⚡ {velocidad}\n"
    
    texto += f"\n🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
    texto += f"<i>Mejora tu Hangar para desbloquear más naves</i>"
    
    teclado = [
        [InlineKeyboardButton("⬇️ VER TODAS LAS NAVES", callback_data="guia_naves_todas_1")],
        [InlineKeyboardButton("🔙 VOLVER", callback_data="guia_desbloqueo")]
    ]
    
    await query.edit_message_text(
        text=texto,
        reply_markup=InlineKeyboardMarkup(teclado),
        parse_mode="HTML"
    )

@requiere_login
async def guia_naves_todas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🚀 Guía de naves - Vista completa con paginación"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    username_tag = AuthSystem.obtener_username(user_id)
    
    # Obtener página
    data = query.data
    try:
        pagina = int(data.split("_")[3])
    except:
        pagina = 1
    
    CONFIG_NAVES = cargar_config_naves()
    
    # Convertir a lista para paginación
    items = list(CONFIG_NAVES.items())
    items_pagina, pagina, total_paginas = paginar_lista(items, pagina)
    
    texto = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"🚀 <b>TODAS LAS NAVES</b> - {username_tag}\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"Página {pagina}/{total_paginas}\n\n"
    )
    
    for nave_id, config in items_pagina:
        nombre = config.get("nombre", nave_id)
        tipo = config.get("tipo", "desconocido").capitalize()
        requisitos = config.get("requisitos", {})
        hangar = requisitos.get("hangar", 1)
        ataque = config.get("ataque", 0)
        escudo = config.get("escudo", 0)
        velocidad = config.get("velocidad", 0)
        capacidad = config.get("capacidad", 0)
        consumo = config.get("consumo", 0)
        
        texto += f"{config.get('icono', '🚀')} <b>{nombre}</b>\n"
        texto += f"   ├ Tipo: {tipo}\n"
        texto += f"   ├ Requisito: Hangar {hangar}\n"
        if ataque > 0:
            texto += f"   ├ ⚔️ Ataque: {ataque}\n"
        if escudo > 0:
            texto += f"   ├ 🛡️ Escudo: {escudo}\n"
        texto += f"   ├ ⚡ Velocidad: {velocidad}\n"
        if capacidad > 0:
            texto += f"   ├ 📦 Capacidad: {capacidad:,}\n"
        if consumo > 0:
            texto += f"   └ ⚡ Consumo: {consumo}\n"
        texto += "\n"
    
    texto += f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    
    # Botones de navegación
    teclado = []
    fila_navegacion = []
    
    if pagina > 1:
        fila_navegacion.append(InlineKeyboardButton("◀️ ANTERIOR", callback_data=f"guia_naves_todas_{pagina-1}"))
    fila_navegacion.append(InlineKeyboardButton(f"📄 {pagina}/{total_paginas}", callback_data="noop"))
    if pagina < total_paginas:
        fila_navegacion.append(InlineKeyboardButton("SIGUIENTE ▶️", callback_data=f"guia_naves_todas_{pagina+1}"))
    
    if fila_navegacion:
        teclado.append(fila_navegacion)
    
    teclado.append([InlineKeyboardButton("🔙 VOLVER", callback_data="guia_naves")])
    
    await query.edit_message_text(
        text=texto,
        reply_markup=InlineKeyboardMarkup(teclado),
        parse_mode="HTML"
    )

# ================= GUÍA DE DEFENSAS =================

@requiere_login
async def guia_defensas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🛡️ Guía de defensas planetarias - Vista general"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    username_tag = AuthSystem.obtener_username(user_id)
    
    CONFIG_DEFENSAS = cargar_config_defensas()
    
    texto = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"🛡️ <b>DEFENSAS PLANETARIAS</b> - {username_tag}\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
    )
    
    categorias = {
        "ligera": "🚀 DEFENSAS LIGERAS",
        "media": "⚡ DEFENSAS MEDIAS",
        "pesada": "☢️ DEFENSAS PESADAS",
        "escudo": "🛡️ ESCUDOS",
        "misil": "🎯 MISILES"
    }
    
    for tipo, titulo in categorias.items():
        defensas_tipo = {k: v for k, v in CONFIG_DEFENSAS.items() if v.get("tipo") == tipo}
        if defensas_tipo:
            texto += f"<b>{titulo}:</b>\n"
            for def_id, config in list(defensas_tipo.items())[:2]:
                nombre = config.get("nombre", def_id)
                requisitos = config.get("requisitos", {})
                hangar = requisitos.get("hangar", 1)
                ataque = config.get("ataque", 0)
                escudo = config.get("escudo", 0)
                texto += f"   • {config.get('icono', '🛡️')} {nombre}\n"
                texto += f"     └ Requisito: Hangar {hangar} | ⚔️ {ataque} | 🛡️ {escudo}\n"
    
    texto += f"\n🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
    texto += f"<i>Las defensas protegen tu planeta de ataques enemigos</i>"
    
    teclado = [
        [InlineKeyboardButton("⬇️ VER TODAS LAS DEFENSAS", callback_data="guia_defensas_todas_1")],
        [InlineKeyboardButton("🔙 VOLVER", callback_data="guia_desbloqueo")]
    ]
    
    await query.edit_message_text(
        text=texto,
        reply_markup=InlineKeyboardMarkup(teclado),
        parse_mode="HTML"
    )

@requiere_login
async def guia_defensas_todas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🛡️ Guía de defensas - Vista completa con paginación"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    username_tag = AuthSystem.obtener_username(user_id)
    
    # Obtener página
    data = query.data
    try:
        pagina = int(data.split("_")[3])
    except:
        pagina = 1
    
    CONFIG_DEFENSAS = cargar_config_defensas()
    
    items = list(CONFIG_DEFENSAS.items())
    items_pagina, pagina, total_paginas = paginar_lista(items, pagina)
    
    texto = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"🛡️ <b>TODAS LAS DEFENSAS</b> - {username_tag}\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"Página {pagina}/{total_paginas}\n\n"
    )
    
    for def_id, config in items_pagina:
        nombre = config.get("nombre", def_id)
        tipo = config.get("tipo", "desconocido").capitalize()
        requisitos = config.get("requisitos", {})
        hangar = requisitos.get("hangar", 1)
        ataque = config.get("ataque", 0)
        escudo = config.get("escudo", 0)
        
        texto += f"{config.get('icono', '🛡️')} <b>{nombre}</b>\n"
        texto += f"   ├ Tipo: {tipo}\n"
        texto += f"   ├ Requisito: Hangar {hangar}\n"
        texto += f"   ├ ⚔️ Ataque: {ataque}\n"
        texto += f"   └ 🛡️ Escudo: {escudo}\n\n"
    
    texto += f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    
    # Botones de navegación
    teclado = []
    fila_navegacion = []
    
    if pagina > 1:
        fila_navegacion.append(InlineKeyboardButton("◀️ ANTERIOR", callback_data=f"guia_defensas_todas_{pagina-1}"))
    fila_navegacion.append(InlineKeyboardButton(f"📄 {pagina}/{total_paginas}", callback_data="noop"))
    if pagina < total_paginas:
        fila_navegacion.append(InlineKeyboardButton("SIGUIENTE ▶️", callback_data=f"guia_defensas_todas_{pagina+1}"))
    
    if fila_navegacion:
        teclado.append(fila_navegacion)
    
    teclado.append([InlineKeyboardButton("🔙 VOLVER", callback_data="guia_defensas")])
    
    await query.edit_message_text(
        text=texto,
        reply_markup=InlineKeyboardMarkup(teclado),
        parse_mode="HTML"
    )

# ================= GUÍA DE EDIFICIOS =================

@requiere_login
async def guia_edificios(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🏗️ Guía de edificios y minas"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    username_tag = AuthSystem.obtener_username(user_id)
    
    CONSTRUCCIONES = cargar_config_edificios()
    
    texto = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"🏗️ <b>EDIFICIOS Y MINAS</b> - {username_tag}\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"⛏️ <b>MINAS:</b>\n"
    )
    
    for tipo in ["metal", "cristal", "deuterio"]:
        config = CONSTRUCCIONES.get(tipo, {})
        nombre = config.get("nombre", tipo)
        icono = config.get("icono", "⛏️")
        desc = config.get("descripcion", "Produce recursos")
        texto += f"   • {icono} {nombre}\n"
        texto += f"     └ {desc}\n"
    
    texto += f"\n🏢 <b>EDIFICIOS:</b>\n"
    for tipo in ["energia", "laboratorio", "hangar", "terraformer"]:
        config = CONSTRUCCIONES.get(tipo, {})
        nombre = config.get("nombre", tipo)
        icono = config.get("icono", "🏢")
        desc = config.get("descripcion", "Edificio especial")
        texto += f"   • {icono} {nombre}\n"
        texto += f"     └ {desc}\n"
    
    texto += f"\n🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    
    teclado = [[InlineKeyboardButton("🔙 VOLVER", callback_data="guia_desbloqueo")]]
    
    await query.edit_message_text(
        text=texto,
        reply_markup=InlineKeyboardMarkup(teclado),
        parse_mode="HTML"
    )

# ================= GUÍA DE INVESTIGACIONES =================

@requiere_login
async def guia_investigacion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🔬 Guía de investigaciones"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    username_tag = AuthSystem.obtener_username(user_id)
    
    INVESTIGACIONES = cargar_config_investigaciones()
    
    texto = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"🔬 <b>INVESTIGACIONES</b> - {username_tag}\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
    )
    
    # Agrupar por grupo
    grupos = {}
    for tech_id, config in INVESTIGACIONES.items():
        grupo = config.get("grupo", "Otros")
        if grupo not in grupos:
            grupos[grupo] = []
        grupos[grupo].append((tech_id, config))
    
    for grupo, tecnologias in grupos.items():
        texto += f"<b>{grupo}:</b>\n"
        for tech_id, config in tecnologias[:3]:
            nombre = config.get("nombre", tech_id)
            icono = config.get("icono", "🔬")
            requisitos = config.get("requisitos", {})
            lab = requisitos.get("laboratorio", 1)
            bonus = config.get("bonificacion", "")
            texto += f"   • {icono} {nombre}\n"
            texto += f"     └ Requisito: Laboratorio {lab}\n"
            if bonus:
                texto += f"       🎯 {bonus}\n"
        texto += "\n"
    
    texto += f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
    texto += "<i>Mejora tu Laboratorio para desbloquear más tecnologías</i>"
    
    teclado = [[InlineKeyboardButton("🔙 VOLVER", callback_data="guia_desbloqueo")]]
    
    await query.edit_message_text(
        text=texto,
        reply_markup=InlineKeyboardMarkup(teclado),
        parse_mode="HTML"
    )

# ================= HANDLER PRINCIPAL =================

async def guia_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🎯 Handler para todos los callbacks de guía"""
    query = update.callback_query
    data = query.data
    
    if data == "guia_desbloqueo":
        await guia_desbloqueo(update, context)
    
    elif data == "guia_naves":
        await guia_naves(update, context)
    elif data.startswith("guia_naves_todas_"):
        await guia_naves_todas(update, context)
    
    elif data == "guia_defensas":
        await guia_defensas(update, context)
    elif data.startswith("guia_defensas_todas_"):
        await guia_defensas_todas(update, context)
    
    elif data == "guia_edificios":
        await guia_edificios(update, context)
    
    elif data == "guia_investigacion":
        await guia_investigacion(update, context)
    
    return

# ================= EXPORTAR =================

__all__ = [
    'guia_desbloqueo',
    'guia_callback_handler'
]
