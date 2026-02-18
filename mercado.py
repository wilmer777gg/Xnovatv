#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#██████╗ ███████╗████████╗██████╗  █████╗ ██╗     ███████╗
#██╔══██╗██╔════╝╚══██╔══╝██╔══██╗██╔══██╗██║     ██╔════╝
#██████╔╝███████╗   ██║   ██████╔╝███████║██║     ███████╗
#██╔══██╗╚════██║   ██║   ██╔══██╗██╔══██║██║     ╚════██║
#██║  ██║███████║   ██║   ██║  ██║██║  ██║███████╗███████║
#╚═╝  ╚═╝╚══════╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚══════╝

#🚀 ASTRO.IO v2.4.5 🚀
#💰 mercado.py - SISTEMA DE MERCADO (MERCADO NEGRO)
#====================================================
#✅ Ofertas de usuarios con comisión 2%+8%
#✅ Ofertas del sistema (Mercado Negro) solo admin
#✅ Panel de administración exclusivo para admins
#✅ Expiración de ofertas a las 24h (devuelve ítems)
#✅ Fondo del proyecto acumula comisiones
#✅ Admin puede crear múltiples lotes de una misma oferta
#✅ Notificaciones al vendedor y comprador al completar venta
#✅ 7 ofertas por página con navegación
#====================================================

import os
import logging
import sqlite3
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    MessageHandler, filters, CallbackQueryHandler
)
from telegram.error import BadRequest

from login import AuthSystem, requiere_login, requiere_admin
from utils import abreviar_numero, formatear_tiempo_corto

logger = logging.getLogger(__name__)

# ================= CONSTANTES =================
DB_NAME = "market.db"
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, DB_NAME)

# Cantidad de ofertas por página
ITEMS_POR_PAGINA = 7

# Estados para ConversationHandler
(
    SELECCION_TIPO_VENTA,
    SELECCION_ITEM_VENTA,
    INGRESAR_CANTIDAD_VENTA,
    INGRESAR_PRECIO_VENTA,
    CONFIRMAR_VENTA,
    SELECCION_COMPRA,
    CONFIRMAR_COMPRA,
    ADMIN_SELECCION_TIPO,
    ADMIN_INGRESAR_NOMBRE,
    ADMIN_INGRESAR_PRECIO_UNITARIO,
    ADMIN_INGRESAR_CANTIDAD_LOTE,
    ADMIN_INGRESAR_NUMERO_LOTES,
    ADMIN_CONFIRMAR_LOTES,
    ADMIN_SELECCION_EDITAR,
    ADMIN_INGRESAR_EDIT_CAMPO,
    ADMIN_INGRESAR_EDIT_VALOR,
    ADMIN_SELECCION_ELIMINAR,
    ADMIN_CONFIRMAR_ELIMINAR,
) = range(18)

# Comisiones
COMISION_INICIAL = 0.02  # 2%
COMISION_FINAL = 0.08    # 8%

# ================= BASE DE DATOS =================

def crear_tablas():
    """Crea las tablas necesarias si no existen."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Ofertas de usuarios
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_offers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT NOT NULL,
            item_type TEXT NOT NULL,
            item_name TEXT NOT NULL,
            cantidad INTEGER NOT NULL,
            precio_base INTEGER NOT NULL,
            estado TEXT DEFAULT 'activo',
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Ofertas del sistema (Mercado Negro)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS system_offers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_type TEXT NOT NULL,
            item_name TEXT NOT NULL,
            cantidad INTEGER NOT NULL,
            precio_nxt INTEGER NOT NULL,
            vendedor TEXT DEFAULT 'Mercado Negro',
            estado TEXT DEFAULT 'activo',
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Fondo del proyecto
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS project_fund (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            total_nxt INTEGER DEFAULT 0
        )
    """)

    # Inicializar fondo si no existe
    cursor.execute("INSERT OR IGNORE INTO project_fund (id, total_nxt) VALUES (1, 0)")

    conn.commit()
    conn.close()
    logger.info("✅ Tablas de mercado creadas/verificadas.")

# Llamar a la creación al importar el módulo
crear_tablas()

# ================= FUNCIONES AUXILIARES DE BASE DE DATOS =================

def get_db_connection():
    return sqlite3.connect(DB_PATH)

# ---- User offers ----
def crear_oferta_usuario(user_id: int, username: str, item_type: str, item_name: str, cantidad: int, precio_base: int) -> int:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO user_offers (user_id, username, item_type, item_name, cantidad, precio_base)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, username, item_type, item_name, cantidad, precio_base))
    conn.commit()
    oferta_id = cursor.lastrowid
    conn.close()
    return oferta_id

def listar_ofertas_usuario(estado: str = 'activo', user_id: int = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    if user_id:
        cursor.execute("""
            SELECT id, user_id, username, item_type, item_name, cantidad, precio_base, fecha_creacion
            FROM user_offers
            WHERE estado = ? AND user_id = ?
            ORDER BY fecha_creacion DESC
        """, (estado, user_id))
    else:
        cursor.execute("""
            SELECT id, user_id, username, item_type, item_name, cantidad, precio_base, fecha_creacion
            FROM user_offers
            WHERE estado = ?
            ORDER BY fecha_creacion DESC
        """, (estado,))
    ofertas = cursor.fetchall()
    conn.close()
    return ofertas

def obtener_oferta_usuario(oferta_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM user_offers WHERE id = ?", (oferta_id,))
    oferta = cursor.fetchone()
    conn.close()
    return oferta

def actualizar_estado_oferta_usuario(oferta_id: int, nuevo_estado: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE user_offers SET estado = ? WHERE id = ?", (nuevo_estado, oferta_id))
    conn.commit()
    conn.close()

# ---- System offers ----
def crear_oferta_sistema(item_type: str, item_name: str, cantidad: int, precio: int) -> int:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO system_offers (item_type, item_name, cantidad, precio_nxt)
        VALUES (?, ?, ?, ?)
    """, (item_type, item_name, cantidad, precio))
    conn.commit()
    oferta_id = cursor.lastrowid
    conn.close()
    return oferta_id

def crear_multiples_ofertas_sistema(item_type: str, item_name: str, cantidad_por_lote: int, precio_unitario: int, numero_lotes: int) -> list:
    """Crea múltiples ofertas iguales y devuelve lista de IDs."""
    ids = []
    conn = get_db_connection()
    cursor = conn.cursor()
    for _ in range(numero_lotes):
        cursor.execute("""
            INSERT INTO system_offers (item_type, item_name, cantidad, precio_nxt)
            VALUES (?, ?, ?, ?)
        """, (item_type, item_name, cantidad_por_lote, precio_unitario))
        ids.append(cursor.lastrowid)
    conn.commit()
    conn.close()
    return ids

def listar_ofertas_sistema(estado: str = 'activo'):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, item_type, item_name, cantidad, precio_nxt, fecha_creacion
        FROM system_offers
        WHERE estado = ?
        ORDER BY fecha_creacion DESC
    """, (estado,))
    ofertas = cursor.fetchall()
    conn.close()
    return ofertas

def obtener_oferta_sistema(oferta_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM system_offers WHERE id = ?", (oferta_id,))
    oferta = cursor.fetchone()
    conn.close()
    return oferta

def actualizar_oferta_sistema(oferta_id: int, **kwargs):
    campos = []
    valores = []
    for key, value in kwargs.items():
        if key in ('item_type', 'item_name', 'cantidad', 'precio_nxt', 'estado'):
            campos.append(f"{key} = ?")
            valores.append(value)
    if not campos:
        return False
    valores.append(oferta_id)
    query = f"UPDATE system_offers SET {', '.join(campos)} WHERE id = ?"
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(query, valores)
    conn.commit()
    success = cursor.rowcount > 0
    conn.close()
    return success

def eliminar_oferta_sistema(oferta_id: int):
    return actualizar_oferta_sistema(oferta_id, estado='inactivo')

# ---- Project fund ----
def obtener_fondo_proyecto() -> int:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT total_nxt FROM project_fund WHERE id = 1")
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else 0

def sumar_fondo_proyecto(cantidad: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE project_fund SET total_nxt = total_nxt + ? WHERE id = 1", (cantidad,))
    conn.commit()
    conn.close()

# ================= FUNCIONES AUXILIARES PARA OBTENER ÍTEMS DEL USUARIO =================

def obtener_recursos_usuario_para_venta(user_id: int) -> list:
    """Devuelve lista de recursos del usuario con cantidad > 0."""
    from recursos import obtener_recursos_usuario
    recursos = obtener_recursos_usuario(user_id)
    items = []
    nombres_mostrar = {
        'metal': '🔩 Metal',
        'cristal': '💎 Cristal',
        'deuterio': '🧪 Deuterio',
        'materia_oscura': '🌑 Materia Oscura',
        'nxt20': '🪙 NXT-20'
    }
    for recurso, nombre_mostrar in nombres_mostrar.items():
        cant = recursos.get(recurso, 0)
        if cant > 0:
            items.append(('recurso', recurso, nombre_mostrar, cant))
    return items

def obtener_naves_usuario_para_venta(user_id: int) -> list:
    try:
        from flota import obtener_flota, CONFIG_NAVES
    except ImportError:
        return []
    
    flota = obtener_flota(user_id)
    items = []
    for nave_id, cant in flota.items():
        if cant > 0 and nave_id in CONFIG_NAVES:
            config = CONFIG_NAVES[nave_id]
            nombre = config.get('nombre', nave_id)
            icono = config.get('icono', '🚀')
            items.append(('nave', nave_id, f"{icono} {nombre}", cant))
    return items

def obtener_defensas_usuario_para_venta(user_id: int) -> list:
    try:
        from defensa import obtener_defensas, CONFIG_DEFENSAS
    except ImportError:
        return []
    
    defensas = obtener_defensas(user_id)
    items = []
    for def_id, cant in defensas.items():
        if cant > 0 and def_id in CONFIG_DEFENSAS:
            config = CONFIG_DEFENSAS[def_id]
            nombre = config.get('nombre', def_id)
            icono = config.get('icono', '🛡️')
            items.append(('defensa', def_id, f"{icono} {nombre}", cant))
    return items

def obtener_items_usuario(user_id: int, tipo: str = None) -> list:
    """Obtiene todos los items del usuario, opcionalmente filtrados por tipo."""
    items = []
    if tipo is None or tipo == 'recurso':
        items.extend(obtener_recursos_usuario_para_venta(user_id))
    if tipo is None or tipo == 'nave':
        items.extend(obtener_naves_usuario_para_venta(user_id))
    if tipo is None or tipo == 'defensa':
        items.extend(obtener_defensas_usuario_para_venta(user_id))
    return items

# ================= FUNCIONES PARA MODIFICAR INVENTARIO =================

def restar_item_usuario(user_id: int, tipo: str, nombre: str, cantidad: int) -> bool:
    """Resta cantidad del inventario del usuario. Retorna True si éxito."""
    if tipo == 'recurso':
        from recursos import obtener_recursos_usuario, guardar_recursos_usuario
        recursos = obtener_recursos_usuario(user_id)
        if recursos.get(nombre, 0) < cantidad:
            return False
        recursos[nombre] = recursos.get(nombre, 0) - cantidad
        guardar_recursos_usuario(user_id, recursos)
        return True
    elif tipo == 'nave':
        from flota import obtener_flota, guardar_flota
        flota = obtener_flota(user_id)
        if flota.get(nombre, 0) < cantidad:
            return False
        flota[nombre] = flota.get(nombre, 0) - cantidad
        guardar_flota(user_id, flota)
        return True
    elif tipo == 'defensa':
        from defensa import obtener_defensas, guardar_defensas
        defensas = obtener_defensas(user_id)
        if defensas.get(nombre, 0) < cantidad:
            return False
        defensas[nombre] = defensas.get(nombre, 0) - cantidad
        guardar_defensas(user_id, defensas)
        return True
    return False

def sumar_item_usuario(user_id: int, tipo: str, nombre: str, cantidad: int) -> bool:
    """Suma cantidad al inventario del usuario."""
    if tipo == 'recurso':
        from recursos import obtener_recursos_usuario, guardar_recursos_usuario
        recursos = obtener_recursos_usuario(user_id)
        recursos[nombre] = recursos.get(nombre, 0) + cantidad
        guardar_recursos_usuario(user_id, recursos)
        return True
    elif tipo == 'nave':
        from flota import obtener_flota, guardar_flota
        flota = obtener_flota(user_id)
        flota[nombre] = flota.get(nombre, 0) + cantidad
        guardar_flota(user_id, flota)
        return True
    elif tipo == 'defensa':
        from defensa import obtener_defensas, guardar_defensas
        defensas = obtener_defensas(user_id)
        defensas[nombre] = defensas.get(nombre, 0) + cantidad
        guardar_defensas(user_id, defensas)
        return True
    return False

# ================= FUNCIONES DE NEGOCIO =================

def descontar_comision_inicial(precio_base: int) -> int:
    return int(precio_base * COMISION_INICIAL)

def descontar_comision_final(precio_base: int) -> int:
    return int(precio_base * COMISION_FINAL)

def registrar_oferta_usuario_db(user_id: int, username: str, item_type: str, item_name: str, cantidad: int, precio_base: int) -> tuple:
    """Crea la oferta, descuenta comisión inicial y la suma al fondo."""
    comision = descontar_comision_inicial(precio_base)
    # Verificar que el usuario tiene suficientes NXT para pagar la comisión
    from recursos import obtener_recursos_usuario
    recursos = obtener_recursos_usuario(user_id)
    if recursos.get('nxt20', 0) < comision:
        return None, "❌ No tienes suficientes NXT-20 para pagar la comisión inicial."
    # Descontar comisión
    recursos['nxt20'] = recursos.get('nxt20', 0) - comision
    from recursos import guardar_recursos_usuario
    guardar_recursos_usuario(user_id, recursos)
    # Crear oferta
    oferta_id = crear_oferta_usuario(user_id, username, item_type, item_name, cantidad, precio_base)
    sumar_fondo_proyecto(comision)
    return oferta_id, comision

def expirar_ofertas_usuario():
    """Marca como expiradas las ofertas de usuario con más de 24h y devuelve los ítems."""
    conn = get_db_connection()
    cursor = conn.cursor()
    limite = (datetime.now() - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
    # Obtener ofertas a expirar
    cursor.execute("""
        SELECT id, user_id, item_type, item_name, cantidad
        FROM user_offers
        WHERE estado = 'activo' AND fecha_creacion < ?
    """, (limite,))
    ofertas = cursor.fetchall()
    for oferta in ofertas:
        oferta_id, user_id, item_type, item_name, cantidad = oferta
        # Devolver ítems al usuario
        sumar_item_usuario(user_id, item_type, item_name, cantidad)
        # Marcar como expirado
        cursor.execute("UPDATE user_offers SET estado = 'expirado' WHERE id = ?", (oferta_id,))
    conn.commit()
    conn.close()

def procesar_compra_usuario(oferta_id: int, comprador_id: int, context: ContextTypes.DEFAULT_TYPE) -> dict:
    """Marca la oferta como vendida, aplica comisión final, transfiere NXT y entrega ítems al comprador."""
    oferta = obtener_oferta_usuario(oferta_id)
    if not oferta or oferta[7] != 'activo':  # índice 7 es estado
        return {'error': 'oferta_no_disponible'}
    
    vendedor_id = oferta[1]
    username_vendedor = oferta[2]
    item_type = oferta[3]
    item_name = oferta[4]
    cantidad = oferta[5]
    precio_base = oferta[6]

    # Verificar que el comprador tiene suficientes NXT
    from recursos import obtener_recursos_usuario
    recursos_comprador = obtener_recursos_usuario(comprador_id)
    if recursos_comprador.get('nxt20', 0) < precio_base:
        return {'error': 'comprador_sin_nxt'}

    # Calcular comisiones
    comision_inicial = descontar_comision_inicial(precio_base)  # ya pagada por el vendedor
    comision_final = descontar_comision_final(precio_base)
    ganancia_vendedor = precio_base - comision_inicial - comision_final

    # Transferir NXT: comprador paga precio_base, vendedor recibe ganancia, fondo recibe comisión final
    recursos_comprador['nxt20'] -= precio_base
    from recursos import guardar_recursos_usuario
    guardar_recursos_usuario(comprador_id, recursos_comprador)

    recursos_vendedor = obtener_recursos_usuario(vendedor_id)
    recursos_vendedor['nxt20'] = recursos_vendedor.get('nxt20', 0) + ganancia_vendedor
    guardar_recursos_usuario(vendedor_id, recursos_vendedor)

    sumar_fondo_proyecto(comision_final)

    # Entregar ítems al comprador
    sumar_item_usuario(comprador_id, item_type, item_name, cantidad)

    # Marcar oferta como vendida
    actualizar_estado_oferta_usuario(oferta_id, 'vendido')

    # ===== NOTIFICACIONES =====
    username_comprador = AuthSystem.obtener_username(comprador_id)
    
    # Notificar al vendedor
    try:
        context.application.bot.send_message(
            chat_id=vendedor_id,
            text=(
                f"💰 <b>¡VENTA REALIZADA!</b>\n\n"
                f"Has vendido:\n"
                f"📦 {item_name} x{cantidad}\n"
                f"👤 Comprador: @{username_comprador}\n"
                f"💵 Ganancia: {ganancia_vendedor} 🪙 NXT-20\n\n"
                f"Los fondos han sido añadidos a tu cuenta."
            ),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error notificando al vendedor {vendedor_id}: {e}")
    
    # Notificar al comprador
    try:
        context.application.bot.send_message(
            chat_id=comprador_id,
            text=(
                f"✅ <b>¡COMPRA REALIZADA!</b>\n\n"
                f"Has comprado:\n"
                f"📦 {item_name} x{cantidad}\n"
                f"👤 Vendedor: @{username_vendedor}\n"
                f"💰 Pagado: {precio_base} 🪙 NXT-20\n\n"
                f"Los ítems han sido añadidos a tu inventario."
            ),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error notificando al comprador {comprador_id}: {e}")

    return {
        'exito': True,
        'oferta_id': oferta_id,
        'vendedor_id': vendedor_id,
        'comprador_id': comprador_id,
        'item_type': item_type,
        'item_name': item_name,
        'cantidad': cantidad,
        'precio_base': precio_base,
        'ganancia_vendedor': ganancia_vendedor
    }

def procesar_compra_sistema(oferta_id: int, comprador_id: int, context: ContextTypes.DEFAULT_TYPE) -> dict:
    """Procesa la compra de una oferta del sistema."""
    oferta = obtener_oferta_sistema(oferta_id)
    if not oferta or oferta[6] != 'activo':  # índice 6 es estado
        return {'error': 'oferta_no_disponible'}
    # oferta: (id, item_type, item_name, cantidad, precio_nxt, vendedor, estado, fecha)
    item_type = oferta[1]
    item_name = oferta[2]
    cantidad = oferta[3]
    precio = oferta[4]

    # Verificar que el comprador tiene suficientes NXT
    from recursos import obtener_recursos_usuario
    recursos_comprador = obtener_recursos_usuario(comprador_id)
    if recursos_comprador.get('nxt20', 0) < precio:
        return {'error': 'comprador_sin_nxt'}

    # Descontar NXT del comprador (todo va al fondo del proyecto)
    recursos_comprador['nxt20'] -= precio
    from recursos import guardar_recursos_usuario
    guardar_recursos_usuario(comprador_id, recursos_comprador)

    # Sumar al fondo del proyecto
    sumar_fondo_proyecto(precio)

    # Entregar ítems al comprador
    sumar_item_usuario(comprador_id, item_type, item_name, cantidad)

    # Marcar oferta como vendida
    actualizar_oferta_sistema(oferta_id, estado='vendido')

    return {
        'exito': True,
        'oferta_id': oferta_id,
        'comprador_id': comprador_id,
        'item_type': item_type,
        'item_name': item_name,
        'cantidad': cantidad,
        'precio': precio
    }

# ================= TECLADOS INLINE =================

def mercado_principal_keyboard(user_id: int) -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("📦 VER OFERTAS", callback_data="mercado_ver")],
        [InlineKeyboardButton("💰 VENDER", callback_data="mercado_vender")],
    ]
    if AuthSystem.es_admin(user_id):
        keyboard.append([InlineKeyboardButton("⚙️ ADMIN MERCADO NEGRO", callback_data="mercado_admin")])
    keyboard.append([InlineKeyboardButton("◀️ VOLVER", callback_data="menu_principal")])
    return InlineKeyboardMarkup(keyboard)

def seleccionar_tipo_venta_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("🔩 RECURSOS", callback_data="mercado_venta_tipo_recurso")],
        [InlineKeyboardButton("🚀 NAVES", callback_data="mercado_venta_tipo_nave")],
        [InlineKeyboardButton("🛡️ DEFENSAS", callback_data="mercado_venta_tipo_defensa")],
        [InlineKeyboardButton("🔙 CANCELAR", callback_data="mercado_principal")],
    ]
    return InlineKeyboardMarkup(keyboard)

def items_keyboard(items, pagina=0, items_por_pagina=ITEMS_POR_PAGINA):
    """Genera teclado con lista de items para seleccionar."""
    kb = []
    start = pagina * items_por_pagina
    end = min(start + items_por_pagina, len(items))
    
    for item in items[start:end]:
        tipo, nombre_id, nombre_mostrar, cantidad = item
        callback = f"mercado_venta_item_{tipo}_{nombre_id}"
        kb.append([InlineKeyboardButton(f"{nombre_mostrar} ({cantidad})", callback_data=callback)])
    
    nav = []
    if pagina > 0:
        nav.append(InlineKeyboardButton("⬅️ ANTERIOR", callback_data=f"mercado_venta_page:{pagina-1}"))
    if end < len(items):
        nav.append(InlineKeyboardButton("➡️ SIGUIENTE", callback_data=f"mercado_venta_page:{pagina+1}"))
    if nav:
        kb.append(nav)
    
    kb.append([InlineKeyboardButton("🔙 CANCELAR", callback_data="mercado_vender")])
    return InlineKeyboardMarkup(kb)

def admin_panel_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("➕ CREAR OFERTAS", callback_data="mercado_admin_crear")],
        [InlineKeyboardButton("📋 LISTAR OFERTAS", callback_data="mercado_admin_listar")],
        [InlineKeyboardButton("✏️ EDITAR", callback_data="mercado_admin_editar")],
        [InlineKeyboardButton("❌ ELIMINAR", callback_data="mercado_admin_eliminar")],
        [InlineKeyboardButton("💰 VER FONDO", callback_data="mercado_admin_fondo")],
        [InlineKeyboardButton("◀️ VOLVER", callback_data="mercado_principal")],
    ]
    return InlineKeyboardMarkup(keyboard)

def admin_tipo_oferta_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("🚀 NAVE", callback_data="mercado_admin_tipo_nave")],
        [InlineKeyboardButton("🛡️ DEFENSA", callback_data="mercado_admin_tipo_defensa")],
        [InlineKeyboardButton("🔩 RECURSO", callback_data="mercado_admin_tipo_recurso")],
        [InlineKeyboardButton("🔙 CANCELAR", callback_data="mercado_admin")],
    ]
    return InlineKeyboardMarkup(keyboard)

def admin_ofertas_paginador(ofertas, pagina=0, accion="listar"):
    """Genera teclado con lista de ofertas del sistema y navegación."""
    kb = []
    start = pagina * ITEMS_POR_PAGINA
    end = min(start + ITEMS_POR_PAGINA, len(ofertas))
    
    for oferta in ofertas[start:end]:
        oferta_id, item_type, item_name, cantidad, precio, _ = oferta[:6]
        nombre_mostrar = f"{item_type}: {item_name} x{cantidad} - {precio} NXT"
        callback = f"mercado_admin_{accion}_select:{oferta_id}"
        kb.append([InlineKeyboardButton(nombre_mostrar, callback_data=callback)])

    nav = []
    if pagina > 0:
        nav.append(InlineKeyboardButton("⬅️ ANTERIOR", callback_data=f"mercado_admin_{accion}_page:{pagina-1}"))
    if end < len(ofertas):
        nav.append(InlineKeyboardButton("➡️ SIGUIENTE", callback_data=f"mercado_admin_{accion}_page:{pagina+1}"))
    if nav:
        kb.append(nav)
    
    kb.append([InlineKeyboardButton("🔙 CANCELAR", callback_data="mercado_admin")])
    return InlineKeyboardMarkup(kb)

def confirmar_keyboard(accion: str, oferta_id: int) -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton("✅ SÍ", callback_data=f"mercado_admin_{accion}_confirm:{oferta_id}")],
        [InlineKeyboardButton("❌ NO", callback_data="mercado_admin")]
    ]
    return InlineKeyboardMarkup(kb)

# ================= HANDLERS PRINCIPALES =================

@requiere_login
async def mercado_principal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menú principal del mercado."""
    query = update.callback_query
    if not query:
        return
    await query.answer()
    user_id = query.from_user.id
    username_tag = AuthSystem.obtener_username(user_id)

    # Ejecutar expiración automática
    expirar_ofertas_usuario()

    texto = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"💰 <b>MERCADO NEGRO</b> - {username_tag}\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"Bienvenido al mercado interestelar.\n"
        f"• Puedes vender recursos, naves y defensas.\n"
        f"• Comisión total: 10% (2% al publicar + 8% al vender).\n"
        f"• Las ofertas duran 24h.\n\n"
        f"Selecciona una opción:\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    )
    await query.edit_message_text(
        text=texto,
        reply_markup=mercado_principal_keyboard(user_id),
        parse_mode="HTML"
    )

# ================= VENTA DE USUARIO =================

@requiere_login
async def mercado_vender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inicia el proceso de venta."""
    query = update.callback_query
    await query.answer()
    
    texto = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"💰 <b>VENDER - SELECCIONAR TIPO</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"¿Qué tipo de ítem deseas vender?\n\n"
        f"Selecciona una opción:"
    )
    await query.edit_message_text(
        text=texto,
        reply_markup=seleccionar_tipo_venta_keyboard(),
        parse_mode="HTML"
    )
    return SELECCION_TIPO_VENTA

async def mercado_venta_seleccionar_tipo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Procesa la selección del tipo de ítem a vender."""
    query = update.callback_query
    await query.answer()
    data = query.data
    tipo = data.split('_')[3]  # mercado_venta_tipo_recurso -> recurso
    
    user_id = query.from_user.id
    items = obtener_items_usuario(user_id, tipo)
    
    if not items:
        await query.edit_message_text(
            f"❌ No tienes {tipo}s para vender.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 VOLVER", callback_data="mercado_vender")
            ]])
        )
        return SELECCION_TIPO_VENTA
    
    context.user_data['venta_tipo'] = tipo
    context.user_data['venta_items'] = items
    context.user_data['venta_pagina'] = 0
    
    texto = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"💰 <b>VENDER - SELECCIONAR ÍTEM</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"Selecciona el ítem que deseas vender:"
    )
    await query.edit_message_text(
        text=texto,
        reply_markup=items_keyboard(items, 0),
        parse_mode="HTML"
    )
    return SELECCION_ITEM_VENTA

async def mercado_venta_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cambia de página en la lista de ítems."""
    query = update.callback_query
    await query.answer()
    pagina = int(query.data.split(':')[1])
    
    items = context.user_data.get('venta_items', [])
    if not items:
        return SELECCION_ITEM_VENTA
    
    context.user_data['venta_pagina'] = pagina
    await query.edit_message_reply_markup(reply_markup=items_keyboard(items, pagina))
    return SELECCION_ITEM_VENTA

async def mercado_venta_seleccionar_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Procesa la selección del ítem específico."""
    query = update.callback_query
    await query.answer()
    data = query.data
    partes = data.split('_')
    # formato: mercado_venta_item_{tipo}_{nombre_id}
    tipo = partes[3]
    nombre_id = '_'.join(partes[4:])
    
    items = context.user_data.get('venta_items', [])
    item_seleccionado = None
    for item in items:
        if item[0] == tipo and item[1] == nombre_id:
            item_seleccionado = item
            break
    
    if not item_seleccionado:
        await query.edit_message_text("❌ Error al seleccionar el ítem.")
        return SELECCION_ITEM_VENTA
    
    context.user_data['venta_item_tipo'] = tipo
    context.user_data['venta_item_nombre_id'] = nombre_id
    context.user_data['venta_item_nombre_mostrar'] = item_seleccionado[2]
    context.user_data['venta_item_cantidad_max'] = item_seleccionado[3]
    
    texto = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"💰 <b>VENDER - INGRESAR CANTIDAD</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"Ítem seleccionado: {item_seleccionado[2]}\n"
        f"Cantidad disponible: {item_seleccionado[3]}\n\n"
        f"Escribe la cantidad que deseas vender (máx {item_seleccionado[3]}):"
    )
    await query.edit_message_text(
        text=texto,
        parse_mode="HTML"
    )
    return INGRESAR_CANTIDAD_VENTA

async def mercado_venta_ingresar_cantidad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Procesa la cantidad ingresada."""
    try:
        cantidad = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("❌ Por favor, ingresa un número válido.")
        return INGRESAR_CANTIDAD_VENTA
    
    max_cantidad = context.user_data.get('venta_item_cantidad_max', 0)
    if cantidad <= 0 or cantidad > max_cantidad:
        await update.message.reply_text(f"❌ La cantidad debe ser entre 1 y {max_cantidad}.")
        return INGRESAR_CANTIDAD_VENTA
    
    context.user_data['venta_cantidad'] = cantidad
    
    texto = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"💰 <b>VENDER - INGRESAR PRECIO</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"Ítem: {context.user_data['venta_item_nombre_mostrar']}\n"
        f"Cantidad: {cantidad}\n\n"
        f"Escribe el precio TOTAL en 🪙 NXT-20 (por el lote completo):"
    )
    await update.message.reply_text(texto, parse_mode="HTML")
    return INGRESAR_PRECIO_VENTA

async def mercado_venta_ingresar_precio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Procesa el precio ingresado y muestra confirmación."""
    try:
        precio = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("❌ Por favor, ingresa un número válido.")
        return INGRESAR_PRECIO_VENTA
    
    if precio <= 0:
        await update.message.reply_text("❌ El precio debe ser mayor a 0.")
        return INGRESAR_PRECIO_VENTA
    
    context.user_data['venta_precio'] = precio
    comision = descontar_comision_inicial(precio)
    
    texto = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"💰 <b>CONFIRMAR VENTA</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"📦 Ítem: {context.user_data['venta_item_nombre_mostrar']}\n"
        f"🔢 Cantidad: {context.user_data['venta_cantidad']}\n"
        f"💵 Precio total: {precio} 🪙 NXT-20\n"
        f"💰 Comisión inicial (2%): {comision} 🪙 NXT-20\n"
        f"📝 Al venderse, se descontará otro 8%\n\n"
        f"¿Confirmas la publicación?\n\n"
        f"<i>Nota: La comisión inicial se descuenta AHORA de tus NXT-20.</i>"
    )
    keyboard = [
        [InlineKeyboardButton("✅ CONFIRMAR", callback_data="mercado_venta_confirmar")],
        [InlineKeyboardButton("❌ CANCELAR", callback_data="mercado_principal")]
    ]
    await update.message.reply_text(
        text=texto,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )
    return CONFIRMAR_VENTA

async def mercado_venta_confirmar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirma la venta y crea la oferta."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    username = AuthSystem.obtener_username(user_id)
    tipo = context.user_data['venta_item_tipo']
    nombre_id = context.user_data['venta_item_nombre_id']
    cantidad = context.user_data['venta_cantidad']
    precio = context.user_data['venta_precio']
    
    # Verificar que todavía tiene los ítems (por si acaso)
    items_actuales = obtener_items_usuario(user_id, tipo)
    tiene_item = False
    for item in items_actuales:
        if item[0] == tipo and item[1] == nombre_id and item[3] >= cantidad:
            tiene_item = True
            break
    
    if not tiene_item:
        await query.edit_message_text(
            "❌ Ya no tienes suficientes ítems para vender.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 VOLVER", callback_data="mercado_principal")
            ]])
        )
        # Limpiar datos
        for key in list(context.user_data.keys()):
            if key.startswith('venta_'):
                del context.user_data[key]
        return ConversationHandler.END
    
    # Restar ítems del inventario
    exito_resta = restar_item_usuario(user_id, tipo, nombre_id, cantidad)
    if not exito_resta:
        await query.edit_message_text(
            "❌ Error al retirar los ítems de tu inventario.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 VOLVER", callback_data="mercado_principal")
            ]])
        )
        return ConversationHandler.END
    
    # Registrar oferta (esto descuenta la comisión inicial)
    oferta_id, comision = registrar_oferta_usuario_db(user_id, username, tipo, nombre_id, cantidad, precio)
    
    if oferta_id is None:
        # Si falló, devolver los ítems
        sumar_item_usuario(user_id, tipo, nombre_id, cantidad)
        await query.edit_message_text(
            f"❌ {comision}",  # El mensaje de error viene de registrar_oferta_usuario_db
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 VOLVER", callback_data="mercado_principal")
            ]])
        )
        return ConversationHandler.END
    
    # Éxito
    texto = (
        f"✅ <b>OFERTA PUBLICADA</b>\n\n"
        f"ID: {oferta_id}\n"
        f"📦 {context.user_data['venta_item_nombre_mostrar']} x{cantidad}\n"
        f"💵 Precio: {precio} 🪙 NXT-20\n"
        f"💰 Comisión descontada: {comision} NXT-20\n\n"
        f"Tu oferta estará activa por 24 horas."
    )
    await query.edit_message_text(
        text=texto,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 VOLVER AL MERCADO", callback_data="mercado_principal")
        ]]),
        parse_mode="HTML"
    )
    
    # Limpiar datos
    for key in list(context.user_data.keys()):
        if key.startswith('venta_'):
            del context.user_data[key]
    
    return ConversationHandler.END

# ================= VER OFERTAS Y COMPRAR =================

@requiere_login
async def mercado_ver_ofertas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra ofertas activas de usuarios y sistema."""
    query = update.callback_query
    await query.answer()
    
    # Ejecutar expiración automática
    expirar_ofertas_usuario()
    
    ofertas_user = listar_ofertas_usuario('activo')
    ofertas_sys = listar_ofertas_sistema('activo')
    
    texto = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"📦 <b>OFERTAS ACTIVAS</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
    )
    
    if ofertas_sys:
        texto += "🏛️ <b>MERCADO NEGRO:</b>\n"
        for o in ofertas_sys[:ITEMS_POR_PAGINA]:
            item_type, item_name, cantidad, precio = o[1], o[2], o[3], o[4]
            nombre_mostrar = item_name
            if item_type == 'recurso':
                nombres = {'metal':'🔩 Metal','cristal':'💎 Cristal','deuterio':'🧪 Deuterio','materia_oscura':'🌑 MO','nxt20':'🪙 NXT'}
                nombre_mostrar = nombres.get(item_name, item_name)
            elif item_type == 'nave':
                try:
                    from flota import CONFIG_NAVES
                    if item_name in CONFIG_NAVES:
                        icono = CONFIG_NAVES[item_name].get('icono', '🚀')
                        nombre = CONFIG_NAVES[item_name].get('nombre', item_name)
                        nombre_mostrar = f"{icono} {nombre}"
                except:
                    pass
            elif item_type == 'defensa':
                try:
                    from defensa import CONFIG_DEFENSAS
                    if item_name in CONFIG_DEFENSAS:
                        icono = CONFIG_DEFENSAS[item_name].get('icono', '🛡️')
                        nombre = CONFIG_DEFENSAS[item_name].get('nombre', item_name)
                        nombre_mostrar = f"{icono} {nombre}"
                except:
                    pass
            texto += f"   • ID {o[0]}: {nombre_mostrar} x{cantidad} - {precio} NXT\n"
    else:
        texto += "🏛️ <b>MERCADO NEGRO:</b> No hay ofertas.\n"
    
    if ofertas_user:
        texto += "\n👤 <b>JUGADORES:</b>\n"
        for o in ofertas_user[:ITEMS_POR_PAGINA]:
            oferta_id, user_id, username, item_type, item_name, cantidad, precio, fecha = o
            nombre_mostrar = item_name
            if item_type == 'recurso':
                nombres = {'metal':'🔩 Metal','cristal':'💎 Cristal','deuterio':'🧪 Deuterio','materia_oscura':'🌑 MO','nxt20':'🪙 NXT'}
                nombre_mostrar = nombres.get(item_name, item_name)
            elif item_type == 'nave':
                try:
                    from flota import CONFIG_NAVES
                    if item_name in CONFIG_NAVES:
                        icono = CONFIG_NAVES[item_name].get('icono', '🚀')
                        nombre = CONFIG_NAVES[item_name].get('nombre', item_name)
                        nombre_mostrar = f"{icono} {nombre}"
                except:
                    pass
            elif item_type == 'defensa':
                try:
                    from defensa import CONFIG_DEFENSAS
                    if item_name in CONFIG_DEFENSAS:
                        icono = CONFIG_DEFENSAS[item_name].get('icono', '🛡️')
                        nombre = CONFIG_DEFENSAS[item_name].get('nombre', item_name)
                        nombre_mostrar = f"{icono} {nombre}"
                except:
                    pass
            texto += f"   • ID {oferta_id}: @{username} - {nombre_mostrar} x{cantidad} - {precio} NXT\n"
    else:
        texto += "\n👤 <b>JUGADORES:</b> No hay ofertas.\n"
    
    texto += f"\n🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
    texto += f"<i>Selecciona una oferta para comprar:</i>"
    
    # Crear lista combinada para paginación
    all_ofertas = []
    for o in ofertas_sys:
        all_ofertas.append(('sistema', o))
    for o in ofertas_user:
        all_ofertas.append(('usuario', o))
    
    if not all_ofertas:
        kb = [[InlineKeyboardButton("🔙 VOLVER", callback_data="mercado_principal")]]
        await query.edit_message_text(
            texto.replace("<i>Selecciona una oferta para comprar:</i>", "📭 No hay ofertas activas."),
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode="HTML"
        )
        return
    
    # Guardar en contexto para paginación
    context.user_data['ofertas_ver'] = all_ofertas
    context.user_data['ofertas_pagina'] = 0
    
    await mostrar_pagina_ofertas_compra(update, context, 0)

async def mostrar_pagina_ofertas_compra(update: Update, context: ContextTypes.DEFAULT_TYPE, pagina: int):
    """Muestra una página de ofertas para comprar (7 por página)."""
    query = update.callback_query
    all_ofertas = context.user_data.get('ofertas_ver', [])
    
    total_paginas = (len(all_ofertas) + ITEMS_POR_PAGINA - 1) // ITEMS_POR_PAGINA
    pagina = max(0, min(pagina, total_paginas - 1))
    
    start = pagina * ITEMS_POR_PAGINA
    end = min(start + ITEMS_POR_PAGINA, len(all_ofertas))
    ofertas_pagina = all_ofertas[start:end]
    
    texto = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"📦 <b>COMPRAR - Página {pagina+1}/{total_paginas}</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
    )
    
    kb = []
    for tipo, oferta in ofertas_pagina:
        if tipo == 'sistema':
            o = oferta
            item_type, item_name, cantidad, precio = o[1], o[2], o[3], o[4]
            nombre_mostrar = item_name
            if item_type == 'recurso':
                nombres = {'metal':'🔩 Metal','cristal':'💎 Cristal','deuterio':'🧪 Deuterio','materia_oscura':'🌑 MO','nxt20':'🪙 NXT'}
                nombre_mostrar = nombres.get(item_name, item_name)
            elif item_type == 'nave':
                try:
                    from flota import CONFIG_NAVES
                    if item_name in CONFIG_NAVES:
                        icono = CONFIG_NAVES[item_name].get('icono', '🚀')
                        nombre = CONFIG_NAVES[item_name].get('nombre', item_name)
                        nombre_mostrar = f"{icono} {nombre}"
                except:
                    pass
            elif item_type == 'defensa':
                try:
                    from defensa import CONFIG_DEFENSAS
                    if item_name in CONFIG_DEFENSAS:
                        icono = CONFIG_DEFENSAS[item_name].get('icono', '🛡️')
                        nombre = CONFIG_DEFENSAS[item_name].get('nombre', item_name)
                        nombre_mostrar = f"{icono} {nombre}"
                except:
                    pass
            texto_item = f"🏛️ {nombre_mostrar} x{cantidad} - {precio} NXT"
            callback = f"mercado_comprar_sistema_{o[0]}"
        else:  # usuario
            o = oferta
            oferta_id, user_id, username, item_type, item_name, cantidad, precio, fecha = o
            nombre_mostrar = item_name
            if item_type == 'recurso':
                nombres = {'metal':'🔩 Metal','cristal':'💎 Cristal','deuterio':'🧪 Deuterio','materia_oscura':'🌑 MO','nxt20':'🪙 NXT'}
                nombre_mostrar = nombres.get(item_name, item_name)
            elif item_type == 'nave':
                try:
                    from flota import CONFIG_NAVES
                    if item_name in CONFIG_NAVES:
                        icono = CONFIG_NAVES[item_name].get('icono', '🚀')
                        nombre = CONFIG_NAVES[item_name].get('nombre', item_name)
                        nombre_mostrar = f"{icono} {nombre}"
                except:
                    pass
            elif item_type == 'defensa':
                try:
                    from defensa import CONFIG_DEFENSAS
                    if item_name in CONFIG_DEFENSAS:
                        icono = CONFIG_DEFENSAS[item_name].get('icono', '🛡️')
                        nombre = CONFIG_DEFENSAS[item_name].get('nombre', item_name)
                        nombre_mostrar = f"{icono} {nombre}"
                except:
                    pass
            texto_item = f"👤 @{username} - {nombre_mostrar} x{cantidad} - {precio} NXT"
            callback = f"mercado_comprar_usuario_{oferta_id}"
        
        kb.append([InlineKeyboardButton(texto_item, callback_data=callback)])
    
    # Botones de navegación
    nav = []
    if pagina > 0:
        nav.append(InlineKeyboardButton("⬅️ ANTERIOR", callback_data=f"mercado_ver_page:{pagina-1}"))
    if pagina < total_paginas - 1:
        nav.append(InlineKeyboardButton("➡️ SIGUIENTE", callback_data=f"mercado_ver_page:{pagina+1}"))
    if nav:
        kb.append(nav)
    
    kb.append([InlineKeyboardButton("🔙 VOLVER", callback_data="mercado_principal")])
    
    await query.edit_message_text(
        text=texto,
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="HTML"
    )

async def mercado_ver_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cambia de página en la lista de ofertas."""
    query = update.callback_query
    await query.answer()
    pagina = int(query.data.split(':')[1])
    context.user_data['ofertas_pagina'] = pagina
    await mostrar_pagina_ofertas_compra(update, context, pagina)

async def mercado_comprar_seleccion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra confirmación de compra."""
    query = update.callback_query
    await query.answer()
    data = query.data
    partes = data.split('_')
    tipo = partes[2]  # sistema o usuario
    oferta_id = int(partes[3])
    
    context.user_data['compra_tipo'] = tipo
    context.user_data['compra_oferta_id'] = oferta_id
    
    if tipo == 'sistema':
        oferta = obtener_oferta_sistema(oferta_id)
        if not oferta:
            await query.edit_message_text("❌ Oferta no encontrada.")
            return
        item_type, item_name, cantidad, precio = oferta[1], oferta[2], oferta[3], oferta[4]
        nombre_mostrar = item_name
        if item_type == 'recurso':
            nombres = {'metal':'🔩 Metal','cristal':'💎 Cristal','deuterio':'🧪 Deuterio','materia_oscura':'🌑 MO','nxt20':'🪙 NXT'}
            nombre_mostrar = nombres.get(item_name, item_name)
        elif item_type == 'nave':
            try:
                from flota import CONFIG_NAVES
                if item_name in CONFIG_NAVES:
                    icono = CONFIG_NAVES[item_name].get('icono', '🚀')
                    nombre = CONFIG_NAVES[item_name].get('nombre', item_name)
                    nombre_mostrar = f"{icono} {nombre}"
            except:
                pass
        elif item_type == 'defensa':
            try:
                from defensa import CONFIG_DEFENSAS
                if item_name in CONFIG_DEFENSAS:
                    icono = CONFIG_DEFENSAS[item_name].get('icono', '🛡️')
                    nombre = CONFIG_DEFENSAS[item_name].get('nombre', item_name)
                    nombre_mostrar = f"{icono} {nombre}"
            except:
                pass
        texto = (
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
            f"🛒 <b>CONFIRMAR COMPRA</b>\n"
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
            f"📦 {nombre_mostrar} x{cantidad}\n"
            f"💰 Precio: {precio} NXT-20\n\n"
            f"¿Confirmas la compra?"
        )
    else:  # usuario
        oferta = obtener_oferta_usuario(oferta_id)
        if not oferta:
            await query.edit_message_text("❌ Oferta no encontrada.")
            return
        user_id, username, item_type, item_name, cantidad, precio = oferta[1], oferta[2], oferta[3], oferta[4], oferta[5], oferta[6]
        nombre_mostrar = item_name
        if item_type == 'recurso':
            nombres = {'metal':'🔩 Metal','cristal':'💎 Cristal','deuterio':'🧪 Deuterio','materia_oscura':'🌑 MO','nxt20':'🪙 NXT'}
            nombre_mostrar = nombres.get(item_name, item_name)
        elif item_type == 'nave':
            try:
                from flota import CONFIG_NAVES
                if item_name in CONFIG_NAVES:
                    icono = CONFIG_NAVES[item_name].get('icono', '🚀')
                    nombre = CONFIG_NAVES[item_name].get('nombre', item_name)
                    nombre_mostrar = f"{icono} {nombre}"
            except:
                pass
        elif item_type == 'defensa':
            try:
                from defensa import CONFIG_DEFENSAS
                if item_name in CONFIG_DEFENSAS:
                    icono = CONFIG_DEFENSAS[item_name].get('icono', '🛡️')
                    nombre = CONFIG_DEFENSAS[item_name].get('nombre', item_name)
                    nombre_mostrar = f"{icono} {nombre}"
            except:
                pass
        texto = (
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
            f"🛒 <b>CONFIRMAR COMPRA</b>\n"
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
            f"Vendedor: @{username}\n"
            f"📦 {nombre_mostrar} x{cantidad}\n"
            f"💰 Precio: {precio} NXT-20\n\n"
            f"¿Confirmas la compra?"
        )
    
    keyboard = [
        [InlineKeyboardButton("✅ CONFIRMAR", callback_data=f"mercado_comprar_confirmar_{tipo}_{oferta_id}")],
        [InlineKeyboardButton("❌ CANCELAR", callback_data="mercado_ver")]
    ]
    await query.edit_message_text(
        text=texto,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

async def mercado_comprar_confirmar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ejecuta la compra confirmada y envía notificaciones."""
    query = update.callback_query
    await query.answer()
    data = query.data
    partes = data.split('_')
    tipo = partes[3]
    oferta_id = int(partes[4])
    
    comprador_id = query.from_user.id
    
    if tipo == 'sistema':
        resultado = procesar_compra_sistema(oferta_id, comprador_id, context)
    else:
        resultado = procesar_compra_usuario(oferta_id, comprador_id, context)
    
    if 'error' in resultado:
        texto_error = {
            'oferta_no_disponible': "❌ Esta oferta ya no está disponible.",
            'comprador_sin_nxt': "❌ No tienes suficientes NXT-20."
        }.get(resultado['error'], f"❌ Error: {resultado['error']}")
        
        await query.edit_message_text(
            texto_error,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 VOLVER", callback_data="mercado_ver")
            ]]),
            parse_mode="HTML"
        )
        return
    
    # Mensaje de éxito para el chat actual
    if tipo == 'sistema':
        texto_exito = (
            f"✅ <b>COMPRA REALIZADA</b>\n\n"
            f"Has comprado del Mercado Negro:\n"
            f"📦 {resultado['item_name']} x{resultado['cantidad']}\n"
            f"💰 Pagado: {resultado['precio']} NXT-20"
        )
    else:
        texto_exito = (
            f"✅ <b>COMPRA REALIZADA</b>\n\n"
            f"Has comprado a @{resultado.get('username', 'Usuario')}:\n"
            f"📦 {resultado['item_name']} x{resultado['cantidad']}\n"
            f"💰 Pagado: {resultado['precio_base']} NXT-20"
        )
    
    await query.edit_message_text(
        texto_exito,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 VOLVER AL MERCADO", callback_data="mercado_principal")
        ]]),
        parse_mode="HTML"
    )

# ================= PANEL DE ADMINISTRACIÓN =================

@requiere_admin
async def mercado_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        "⚙️ <b>PANEL DE ADMINISTRACIÓN DEL MERCADO NEGRO</b>\n"
        "🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        "Selecciona una opción:",
        reply_markup=admin_panel_keyboard(),
        parse_mode="HTML"
    )

@requiere_admin
async def mercado_admin_fondo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    fondo = obtener_fondo_proyecto()
    await query.edit_message_text(
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"💰 <b>FONDO DEL PROYECTO</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"Total acumulado: <b>{fondo} NXT-20</b>\n\n"
        f"Este fondo proviene de las comisiones de ventas.\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("◀️ VOLVER", callback_data="mercado_admin")
        ]]),
        parse_mode="HTML"
    )

# ---------- CREAR OFERTAS (MÚLTIPLES LOTES) ----------
@requiere_admin
async def admin_crear_inicio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        "➕ <b>CREAR OFERTAS DEL MERCADO NEGRO</b>\n"
        "🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        "Paso 1/5: Elige el tipo de ítem.",
        reply_markup=admin_tipo_oferta_keyboard(),
        parse_mode="HTML"
    )
    return ADMIN_SELECCION_TIPO

async def admin_crear_tipo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    tipo = data.split('_')[3]  # mercado_admin_tipo_nave -> nave
    
    context.user_data['admin_crear_tipo'] = tipo
    
    await query.edit_message_text(
        f"✅ Tipo: {tipo}\n\n"
        "Paso 2/5: Escribe el NOMBRE del ítem.\n"
        "Ejemplos: 'Cazador Ligero', 'Lanzador de Misiles', 'metal', etc."
    )
    return ADMIN_INGRESAR_NOMBRE

async def admin_crear_nombre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nombre = update.message.text.strip()
    if len(nombre) < 2 or len(nombre) > 50:
        await update.message.reply_text("❌ El nombre debe tener entre 2 y 50 caracteres.")
        return ADMIN_INGRESAR_NOMBRE
    
    context.user_data['admin_crear_nombre'] = nombre
    
    await update.message.reply_text(
        "Paso 3/5: Escribe el PRECIO UNITARIO por lote (en 🪙 NXT-20).\n"
        "Ejemplo: Si quieres vender cada lote a 100 🪙 NXT, escribes 100."
    )
    return ADMIN_INGRESAR_PRECIO_UNITARIO

async def admin_crear_precio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        precio = int(update.message.text.strip())
        if precio <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Precio inválido. Debe ser un número entero positivo.")
        return ADMIN_INGRESAR_PRECIO_UNITARIO
    
    context.user_data['admin_crear_precio'] = precio
    
    await update.message.reply_text(
        "Paso 4/5: Escribe la CANTIDAD por lote (número entero positivo).\n"
        "Ejemplo: Si quieres hacer lote 10, escribes 10."
    )
    return ADMIN_INGRESAR_CANTIDAD_LOTE

async def admin_crear_cantidad_lote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        cantidad = int(update.message.text.strip())
        if cantidad <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Cantidad inválida. Debe ser un número entero positivo.")
        return ADMIN_INGRESAR_CANTIDAD_LOTE
    
    context.user_data['admin_crear_cantidad_lote'] = cantidad
    
    await update.message.reply_text(
        "Paso 5/5: Escribe el NÚMERO DE LOTES que deseas crear.\n"
        "Ejemplo: Si quieres 5 lotes iguales, escribe 5."
    )
    return ADMIN_INGRESAR_NUMERO_LOTES

async def admin_crear_numero_lotes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        num_lotes = int(update.message.text.strip())
        if num_lotes <= 0:
            raise ValueError
        if num_lotes > 100:
            await update.message.reply_text("❌ No puedes crear más de 100 lotes a la vez.")
            return ADMIN_INGRESAR_NUMERO_LOTES
    except ValueError:
        await update.message.reply_text("❌ Número inválido. Debe ser un número entero positivo.")
        return ADMIN_INGRESAR_NUMERO_LOTES
    
    tipo = context.user_data['admin_crear_tipo']
    nombre = context.user_data['admin_crear_nombre']
    precio = context.user_data['admin_crear_precio']
    cantidad_lote = context.user_data['admin_crear_cantidad_lote']
    
    context.user_data['admin_crear_num_lotes'] = num_lotes
    
    resumen = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"➕ <b>CONFIRMAR CREACIÓN DE LOTES</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"Tipo: {tipo}\n"
        f"Nombre: {nombre}\n"
        f"Cantidad por lote: {cantidad_lote}\n"
        f"Precio por lote: {precio} 🪙 NXT\n"
        f"Número de lotes: {num_lotes}\n"
        f"Total de ítems: {cantidad_lote * num_lotes}\n"
        f"Valor total: {precio * num_lotes} 🪙 NXT\n\n"
        f"¿Confirmar?"
    )
    kb = [
        [InlineKeyboardButton("✅ SÍ, CREAR", callback_data="admin_crear_confirmar")],
        [InlineKeyboardButton("❌ NO, CANCELAR", callback_data="mercado_admin")]
    ]
    await update.message.reply_text(resumen, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
    return ADMIN_CONFIRMAR_LOTES

async def admin_crear_confirmar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    tipo = context.user_data['admin_crear_tipo']
    nombre = context.user_data['admin_crear_nombre']
    precio = context.user_data['admin_crear_precio']
    cantidad_lote = context.user_data['admin_crear_cantidad_lote']
    num_lotes = context.user_data['admin_crear_num_lotes']
    
    ids = crear_multiples_ofertas_sistema(tipo, nombre, cantidad_lote, precio, num_lotes)
    
    # Limpiar datos
    for key in list(context.user_data.keys()):
        if key.startswith('admin_crear_'):
            del context.user_data[key]
    
    texto = f"✅ <b>OFERTAS CREADAS</b>\n\nSe han creado {num_lotes} lotes con ID: {', '.join(map(str, ids))}"
    await query.edit_message_text(
        texto,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("◀️ VOLVER AL PANEL", callback_data="mercado_admin")
        ]]),
        parse_mode="HTML"
    )
    return ConversationHandler.END

# ---------- LISTAR OFERTAS (admin) ----------
@requiere_admin
async def admin_listar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    ofertas = listar_ofertas_sistema('activo')
    if not ofertas:
        await query.edit_message_text(
            "📭 No hay ofertas activas en el Mercado Negro.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ VOLVER", callback_data="mercado_admin")
            ]])
        )
        return
    # Mostrar primera página
    pagina = 0
    context.user_data['admin_listar_pagina'] = pagina
    await mostrar_pagina_ofertas_admin(update, context, pagina, 'listar')

async def mostrar_pagina_ofertas_admin(update, context, pagina, accion):
    query = update.callback_query
    ofertas = listar_ofertas_sistema('activo')
    if not ofertas:
        await query.edit_message_text("📭 No hay ofertas.", reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("◀️ VOLVER", callback_data="mercado_admin")
        ]]))
        return
    
    total_paginas = (len(ofertas) + ITEMS_POR_PAGINA - 1) // ITEMS_POR_PAGINA
    pagina = max(0, min(pagina, total_paginas - 1))
    
    texto = f"📋 <b>OFERTAS ACTIVAS</b> (página {pagina+1}/{total_paginas})\n\n"
    start = pagina * ITEMS_POR_PAGINA
    end = min(start + ITEMS_POR_PAGINA, len(ofertas))
    
    for o in ofertas[start:end]:
        texto += f"ID {o[0]}: {o[1]} {o[2]} x{o[3]} - {o[4]} NXT\n"
    texto += "\nSelecciona una oferta para ver detalles:"
    kb = admin_ofertas_paginador(ofertas, pagina, accion)
    await query.edit_message_text(texto, reply_markup=kb, parse_mode="HTML")

async def admin_listar_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    pagina = int(data.split(':')[1])
    await mostrar_pagina_ofertas_admin(update, context, pagina, 'listar')

async def admin_listar_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    oferta_id = int(query.data.split(':')[1])
    oferta = obtener_oferta_sistema(oferta_id)
    if not oferta:
        await query.edit_message_text("❌ Oferta no encontrada.")
        return
    texto = (
        f"📋 <b>DETALLE DE OFERTA</b>\n\n"
        f"ID: {oferta[0]}\n"
        f"Tipo: {oferta[1]}\n"
        f"Nombre: {oferta[2]}\n"
        f"Cantidad: {oferta[3]}\n"
        f"Precio: {oferta[4]} NXT\n"
        f"Vendedor: {oferta[5]}\n"
        f"Estado: {oferta[6]}\n"
        f"Creada: {oferta[7]}"
    )
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("◀️ VOLVER", callback_data="mercado_admin_listar")
    ]])
    await query.edit_message_text(texto, reply_markup=kb, parse_mode="HTML")

# ---------- EDITAR OFERTA ----------
@requiere_admin
async def admin_editar_inicio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    ofertas = listar_ofertas_sistema('activo')
    if not ofertas:
        await query.edit_message_text("📭 No hay ofertas para editar.", reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("◀️ VOLVER", callback_data="mercado_admin")
        ]]))
        return
    await mostrar_pagina_ofertas_admin(update, context, 0, 'editar')
    return ADMIN_SELECCION_EDITAR

async def admin_editar_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    pagina = int(query.data.split(':')[1])
    await mostrar_pagina_ofertas_admin(update, context, pagina, 'editar')
    return ADMIN_SELECCION_EDITAR

async def admin_editar_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    oferta_id = int(query.data.split(':')[1])
    context.user_data['admin_editar_id'] = oferta_id
    oferta = obtener_oferta_sistema(oferta_id)
    texto = (
        f"✏️ <b>EDITAR OFERTA ID {oferta_id}</b>\n\n"
        f"1. Tipo: {oferta[1]}\n"
        f"2. Nombre: {oferta[2]}\n"
        f"3. Cantidad: {oferta[3]}\n"
        f"4. Precio: {oferta[4]}\n\n"
        f"Escribe el número del campo que deseas modificar (1-4):"
    )
    await query.edit_message_text(texto, parse_mode="HTML")
    return ADMIN_INGRESAR_EDIT_CAMPO

async def admin_editar_campo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        campo = int(update.message.text.strip())
        if campo not in [1,2,3,4]:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Por favor, ingresa un número del 1 al 4.")
        return ADMIN_INGRESAR_EDIT_CAMPO
    context.user_data['admin_editar_campo'] = campo
    nombres = {1:'tipo',2:'nombre',3:'cantidad',4:'precio'}
    await update.message.reply_text(f"Ingresa el nuevo valor para '{nombres[campo]}':")
    return ADMIN_INGRESAR_EDIT_VALOR

async def admin_editar_valor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    valor = update.message.text.strip()
    campo = context.user_data['admin_editar_campo']
    oferta_id = context.user_data['admin_editar_id']

    if campo in [3,4]:  # cantidad o precio deben ser números
        try:
            valor_int = int(valor)
            if valor_int <= 0:
                raise ValueError
            valor = valor_int
        except ValueError:
            await update.message.reply_text("❌ Debe ser un número entero positivo.")
            return ADMIN_INGRESAR_EDIT_VALOR

    # Actualizar en BD
    mapeo = {1:'item_type', 2:'item_name', 3:'cantidad', 4:'precio_nxt'}
    campo_bd = mapeo[campo]
    actualizar_oferta_sistema(oferta_id, **{campo_bd: valor})

    # Limpiar datos
    context.user_data.pop('admin_editar_campo', None)
    context.user_data.pop('admin_editar_id', None)

    await update.message.reply_text(
        f"✅ Campo actualizado correctamente.",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("◀️ VOLVER AL PANEL", callback_data="mercado_admin")
        ]])
    )
    return ConversationHandler.END

# ---------- ELIMINAR OFERTA ----------
@requiere_admin
async def admin_eliminar_inicio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    ofertas = listar_ofertas_sistema('activo')
    if not ofertas:
        await query.edit_message_text("📭 No hay ofertas para eliminar.", reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("◀️ VOLVER", callback_data="mercado_admin")
        ]]))
        return
    await mostrar_pagina_ofertas_admin(update, context, 0, 'eliminar')
    return ADMIN_SELECCION_ELIMINAR

async def admin_eliminar_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    pagina = int(query.data.split(':')[1])
    await mostrar_pagina_ofertas_admin(update, context, pagina, 'eliminar')
    return ADMIN_SELECCION_ELIMINAR

async def admin_eliminar_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    oferta_id = int(query.data.split(':')[1])
    context.user_data['admin_eliminar_id'] = oferta_id
    oferta = obtener_oferta_sistema(oferta_id)
    texto = (
        f"❓ ¿Estás seguro de eliminar la oferta?\n\n"
        f"ID: {oferta_id}\n"
        f"Tipo: {oferta[1]}\n"
        f"Nombre: {oferta[2]}\n"
        f"Cantidad: {oferta[3]}\n"
        f"Precio: {oferta[4]} NXT"
    )
    await query.edit_message_text(texto, reply_markup=confirmar_keyboard('eliminar', oferta_id), parse_mode="HTML")
    return ADMIN_CONFIRMAR_ELIMINAR

async def admin_eliminar_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    oferta_id = int(query.data.split(':')[1])
    eliminar_oferta_sistema(oferta_id)
    context.user_data.pop('admin_eliminar_id', None)
    await query.edit_message_text(
        f"✅ Oferta {oferta_id} eliminada (marcada como inactiva).",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("◀️ VOLVER AL PANEL", callback_data="mercado_admin")
        ]])
    )
    return ConversationHandler.END

# ================= CONVERSATION HANDLERS =================

# Venta de usuario
venta_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(mercado_vender, pattern="^mercado_vender$")],
    states={
        SELECCION_TIPO_VENTA: [
            CallbackQueryHandler(mercado_venta_seleccionar_tipo, pattern="^mercado_venta_tipo_")
        ],
        SELECCION_ITEM_VENTA: [
            CallbackQueryHandler(mercado_venta_page, pattern="^mercado_venta_page:"),
            CallbackQueryHandler(mercado_venta_seleccionar_item, pattern="^mercado_venta_item_")
        ],
        INGRESAR_CANTIDAD_VENTA: [MessageHandler(filters.TEXT & ~filters.COMMAND, mercado_venta_ingresar_cantidad)],
        INGRESAR_PRECIO_VENTA: [MessageHandler(filters.TEXT & ~filters.COMMAND, mercado_venta_ingresar_precio)],
        CONFIRMAR_VENTA: [CallbackQueryHandler(mercado_venta_confirmar, pattern="^mercado_venta_confirmar$")],
    },
    fallbacks=[CommandHandler("cancelar", lambda u,c: ConversationHandler.END)],
    name="mercado_venta",
    persistent=False
)

# Admin crear múltiples lotes
admin_crear_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(admin_crear_inicio, pattern="^mercado_admin_crear$")],
    states={
        ADMIN_SELECCION_TIPO: [CallbackQueryHandler(admin_crear_tipo, pattern="^mercado_admin_tipo_")],
        ADMIN_INGRESAR_NOMBRE: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_crear_nombre)],
        ADMIN_INGRESAR_PRECIO_UNITARIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_crear_precio)],
        ADMIN_INGRESAR_CANTIDAD_LOTE: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_crear_cantidad_lote)],
        ADMIN_INGRESAR_NUMERO_LOTES: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_crear_numero_lotes)],
        ADMIN_CONFIRMAR_LOTES: [CallbackQueryHandler(admin_crear_confirmar, pattern="^admin_crear_confirmar$")],
    },
    fallbacks=[CommandHandler("cancelar", lambda u,c: ConversationHandler.END)],
    name="mercado_admin_crear",
    persistent=False
)

# Admin editar
admin_editar_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(admin_editar_inicio, pattern="^mercado_admin_editar$")],
    states={
        ADMIN_SELECCION_EDITAR: [
            CallbackQueryHandler(admin_editar_page, pattern="^mercado_admin_editar_page:"),
            CallbackQueryHandler(admin_editar_select, pattern="^mercado_admin_editar_select:")
        ],
        ADMIN_INGRESAR_EDIT_CAMPO: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_editar_campo)],
        ADMIN_INGRESAR_EDIT_VALOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_editar_valor)],
    },
    fallbacks=[CommandHandler("cancelar", lambda u,c: ConversationHandler.END)],
    name="mercado_admin_editar",
    persistent=False
)

# Admin eliminar
admin_eliminar_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(admin_eliminar_inicio, pattern="^mercado_admin_eliminar$")],
    states={
        ADMIN_SELECCION_ELIMINAR: [
            CallbackQueryHandler(admin_eliminar_page, pattern="^mercado_admin_eliminar_page:"),
            CallbackQueryHandler(admin_eliminar_select, pattern="^mercado_admin_eliminar_select:"),
            CallbackQueryHandler(admin_eliminar_confirm, pattern="^mercado_admin_eliminar_confirm:"),
        ],
    },
    fallbacks=[CommandHandler("cancelar", lambda u,c: ConversationHandler.END)],
    name="mercado_admin_eliminar",
    persistent=False
)

def obtener_conversation_handlers_mercado():
    return [venta_conv, admin_crear_conv, admin_editar_conv, admin_eliminar_conv]

# ================= CALLBACK ROUTER =================
async def mercado_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    if data == "mercado_principal":
        await mercado_principal(update, context)
    elif data == "mercado_vender":
        # El ConversationHandler se activará automáticamente
        # Solo necesitamos pasar el control al handler de entrada
        await mercado_vender(update, context)
    elif data == "mercado_ver":
        await mercado_ver_ofertas(update, context)
    elif data.startswith("mercado_ver_page:"):
        await mercado_ver_page(update, context)
    elif data.startswith("mercado_comprar_sistema_") or data.startswith("mercado_comprar_usuario_"):
        await mercado_comprar_seleccion(update, context)
    elif data.startswith("mercado_comprar_confirmar_"):
        await mercado_comprar_confirmar(update, context)
    elif data == "mercado_admin":
        await mercado_admin_panel(update, context)
    elif data == "mercado_admin_fondo":
        await mercado_admin_fondo(update, context)
    elif data == "mercado_admin_listar":
        await admin_listar(update, context)
    elif data.startswith("mercado_admin_listar_page:"):
        await admin_listar_page(update, context)
    elif data.startswith("mercado_admin_listar_select:"):
        await admin_listar_select(update, context)
    # Otros callbacks son manejados por los ConversationHandlers
    else:
        logger.warning(f"Callback de mercado no manejado: {data}")

# ================= EXPORTAR =================
__all__ = [
    'mercado_callback_handler',
    'obtener_conversation_handlers_mercado',
    'mercado_principal',
]
