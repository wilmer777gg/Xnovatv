#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#██████╗ ███████╗████████╗██████╗  █████╗ ██╗     ███████╗
#██╔══██╗██╔════╝╚══██╔══╝██╔══██╗██╔══██╗██║     ██╔════╝
#██████╔╝███████╗   ██║   ██████╔╝███████║██║     ███████╗
#██╔══██╗╚════██║   ██║   ██╔══██╗██╔══██║██║     ╚════██║
#██║  ██║███████║   ██║   ██║  ██║██║  ██║███████╗███████║
#╚═╝  ╚═╝╚══════╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚══════╝

#🚀 ASTRO.IO v2.4.0 🚀
#🔐 login.py - SISTEMA CENTRAL DE AUTENTICACIÓN Y ARCHIVOS
#==========================================================
#✅ VERSIÓN CORREGIDA - CON LOGGING EXTREMO
#==========================================================

import os
import json
import logging
import random
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database import load_json, save_json

# Configurar logging más detallado
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# ================= CONFIGURACIÓN DE RUTAS =================
DATA_DIR = "data"

# ================= CONFIGURACIÓN DE GITHUB (AÑADIDO) =================
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_OWNER = os.environ.get("GITHUB_OWNER")
GITHUB_REPO = os.environ.get("GITHUB_REPO")
USE_GITHUB_SYNC = os.getenv("USE_GITHUB_SYNC", "true").lower() == "true"

# ========== ARCHIVOS JSON EXISTENTES ==========
ADMINS_FILE = os.path.join(DATA_DIR, "admin.json")
AUTHORIZED_USERS_FILE = os.path.join(DATA_DIR, "authorized_users.json")
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")
DATA_FILE = os.path.join(DATA_DIR, "data.json")
COLAS_FILE = os.path.join(DATA_DIR, "colas.json")

RECURSOS_FILE = os.path.join(DATA_DIR, "recursos.json")
RECURSOS_USUARIO_FILE = os.path.join(DATA_DIR, "recursos_usuario.json")

EDIFICIOS_FILE = os.path.join(DATA_DIR, "edificios.json")
EDIFICIOS_USUARIO_FILE = os.path.join(DATA_DIR, "edificios_usuario.json")
MINAS_FILE = os.path.join(DATA_DIR, "minas.json")
CAMPOS_FILE = os.path.join(DATA_DIR, "campos.json")

DEFENSA_FILE = os.path.join(DATA_DIR, "defensa.json")
DEFENSA_USUARIO_FILE = os.path.join(DATA_DIR, "defensa_usuario.json")

FLOTA_FILE = os.path.join(DATA_DIR, "flota.json")
FLOTA_USUARIO_FILE = os.path.join(DATA_DIR, "flota_usuario.json")

INVESTIGACIONES_FILE = os.path.join(DATA_DIR, "investigaciones.json")
INVESTIGACIONES_USUARIO_FILE = os.path.join(DATA_DIR, "investigaciones_usuario.json")

# ========== 🆕 NUEVAS BASES DE DATOS DE FLOTA ==========
MISIONES_FLOTA_FILE = os.path.join(DATA_DIR, "misiones_flota.json")
BAJAS_FLOTA_FILE = os.path.join(DATA_DIR, "bajas_flota.json")
GALAXIA_FILE = os.path.join(DATA_DIR, "galaxia.json")

# ========== 📖 GUÍA CACHE ==========
GUIA_CACHE_FILE = os.path.join(DATA_DIR, "guia_cache.json")

# ========== 🌍 SISTEMA DE ALIANZAS ==========
ALIANZA_DATOS_FILE = os.path.join(DATA_DIR, "alianza_datos.json")
ALIANZA_MIEMBROS_FILE = os.path.join(DATA_DIR, "alianza_miembros.json")
ALIANZA_BANCO_FILE = os.path.join(DATA_DIR, "alianza_banco.json")
ALIANZA_PERMISOS_FILE = os.path.join(DATA_DIR, "alianza_permisos.json")

# ================= CONFIGURACIÓN =================
ADMIN_USER_ID = 7470037078
VERSION = "v2.4.0"

# ✅ RECURSOS INICIALES
RECURSOS_INICIALES = {
    "metal": 800,
    "cristal": 500,
    "deuterio": 0,
    "materia_oscura": 0,
    "nxt20": 0,
    "energia": 0
}

# 🌍 CONFIGURACIÓN DE COORDENADAS
GALAXIA_DEFAULT = 1
SISTEMA_MIN = 1
SISTEMA_MAX = 100
PLANETA_MIN = 1
PLANETA_MAX = 15

logger = logging.getLogger(__name__)

# ================= FUNCIONES DE COORDENADAS =================

def generar_coordenadas_aleatorias() -> dict:
    """🌍 Genera coordenadas aleatorias para un nuevo jugador"""
    galaxia = GALAXIA_DEFAULT
    sistema = random.randint(SISTEMA_MIN, SISTEMA_MAX)
    planeta = random.randint(PLANETA_MIN, PLANETA_MAX)
    
    return {
        "galaxia": galaxia,
        "sistema": sistema,
        "planeta": planeta,
        "nombre": f"Planeta {galaxia}:{sistema}:{planeta}"
    }

def coordenadas_a_string(coords: dict) -> str:
    """🌍 Convierte coordenadas a string formato 1:100:16"""
    return f"{coords['galaxia']}:{coords['sistema']}:{coords['planeta']}"

def obtener_coordenadas_libres() -> dict:
    """🔍 Busca coordenadas libres en la galaxia"""
    galaxia_data = load_json(GALAXIA_FILE) or {}
    
    for _ in range(100):
        coords = generar_coordenadas_aleatorias()
        coords_str = coordenadas_a_string(coords)
        
        ocupado = False
        for user_data in galaxia_data.values():
            user_coords = user_data.get("coordenadas", {})
            if coordenadas_a_string(user_coords) == coords_str:
                ocupado = True
                break
        
        if not ocupado:
            return coords
    
    for sistema in range(1, SISTEMA_MAX + 1):
        for planeta in range(1, PLANETA_MAX + 1):
            coords = {"galaxia": GALAXIA_DEFAULT, "sistema": sistema, "planeta": planeta}
            coords_str = coordenadas_a_string(coords)
            
            ocupado = False
            for user_data in galaxia_data.values():
                user_coords = user_data.get("coordenadas", {})
                if coordenadas_a_string(user_coords) == coords_str:
                    ocupado = True
                    break
            
            if not ocupado:
                return coords
    
    return generar_coordenadas_aleatorias()

# ================= VERIFICACIÓN DE TODOS LOS JSON =================

def verificar_todos_archivos() -> Dict[str, str]:
    """✅ VERIFICA Y CREA TODOS LOS ARCHIVOS JSON"""
    logger.info("=" * 50)
    logger.info(f"🔍 VERIFICANDO ARCHIVOS JSON - {VERSION}")
    logger.info("=" * 50)
    
    os.makedirs(DATA_DIR, exist_ok=True)
    resultados = {}
    
    # admin.json - Asegurar que el admin principal existe
    if not os.path.exists(ADMINS_FILE):
        logger.warning("⚠️ admin.json no existe - creando...")
        admins = {str(ADMIN_USER_ID): {
            "username": f"@{ADMIN_USER_ID}",
            "nombre": "Admin Principal",
            "fecha_registro": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "agregado_por": "sistema",
            "permisos": ["todos"]
        }}
        save_json(ADMINS_FILE, admins)
        resultados[ADMINS_FILE] = "creado"
        logger.info(f"👑 Archivo admin.json creado con admin principal {ADMIN_USER_ID}")
    else:
        admins = load_json(ADMINS_FILE) or {}
        if str(ADMIN_USER_ID) not in admins:
            logger.warning(f"⚠️ Admin principal {ADMIN_USER_ID} no está en admin.json - añadiendo...")
            admins[str(ADMIN_USER_ID)] = {
                "username": f"@{ADMIN_USER_ID}",
                "nombre": "Admin Principal",
                "fecha_registro": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "agregado_por": "sistema",
                "permisos": ["todos"]
            }
            save_json(ADMINS_FILE, admins)
            logger.info(f"👑 Admin principal {ADMIN_USER_ID} añadido a admin.json")
        resultados[ADMINS_FILE] = "existe"
    
    # authorized_users.json
    if not os.path.exists(AUTHORIZED_USERS_FILE):
        logger.warning("⚠️ authorized_users.json no existe - creando...")
        autorizados = [ADMIN_USER_ID]
        save_json(AUTHORIZED_USERS_FILE, autorizados)
        resultados[AUTHORIZED_USERS_FILE] = "creado"
    else:
        autorizados = load_json(AUTHORIZED_USERS_FILE) or []
        if ADMIN_USER_ID not in autorizados:
            logger.warning(f"⚠️ Admin principal {ADMIN_USER_ID} no está autorizado - autorizando...")
            autorizados.append(ADMIN_USER_ID)
            save_json(AUTHORIZED_USERS_FILE, autorizados)
            logger.info(f"👑 Admin principal {ADMIN_USER_ID} autorizado")
        resultados[AUTHORIZED_USERS_FILE] = "existe"
    
    # config.json
    if not os.path.exists(CONFIG_FILE):
        config = {
            "version": VERSION,
            "nombre_bot": "AstroIO",
            "admin_principal": ADMIN_USER_ID,
            "recursos_iniciales": RECURSOS_INICIALES,
            "mantenimiento": False,
            "fecha_inicio": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        save_json(CONFIG_FILE, config)
        resultados[CONFIG_FILE] = "creado"
    else:
        config = load_json(CONFIG_FILE) or {}
        config["version"] = VERSION
        save_json(CONFIG_FILE, config)
        resultados[CONFIG_FILE] = "actualizado"
    
    # data.json
    if not os.path.exists(DATA_FILE):
        save_json(DATA_FILE, {})
        resultados[DATA_FILE] = "creado"
    else:
        resultados[DATA_FILE] = "existe"
    
    # colas.json
    if not os.path.exists(COLAS_FILE):
        save_json(COLAS_FILE, {})
        resultados[COLAS_FILE] = "creado"
    else:
        resultados[COLAS_FILE] = "existe"
    
    # recursos.json
    if not os.path.exists(RECURSOS_FILE):
        save_json(RECURSOS_FILE, {})
        resultados[RECURSOS_FILE] = "creado"
    else:
        resultados[RECURSOS_FILE] = "existe"
    
    # recursos_usuario.json
    if not os.path.exists(RECURSOS_USUARIO_FILE):
        save_json(RECURSOS_USUARIO_FILE, {})
        resultados[RECURSOS_USUARIO_FILE] = "creado"
    else:
        resultados[RECURSOS_USUARIO_FILE] = "existe"
    
    # edificios.json
    if not os.path.exists(EDIFICIOS_FILE):
        edificios_config = {
            "energia": {"nombre": "Planta de Energía", "nivel_maximo": 100},
            "laboratorio": {"nombre": "Laboratorio", "nivel_maximo": 30},
            "hangar": {"nombre": "Hangar", "nivel_maximo": 20},
            "terraformer": {"nombre": "Terraformer", "nivel_maximo": 10}
        }
        save_json(EDIFICIOS_FILE, edificios_config)
        resultados[EDIFICIOS_FILE] = "creado"
    else:
        resultados[EDIFICIOS_FILE] = "existe"
    
    # edificios_usuario.json
    if not os.path.exists(EDIFICIOS_USUARIO_FILE):
        save_json(EDIFICIOS_USUARIO_FILE, {})
        resultados[EDIFICIOS_USUARIO_FILE] = "creado"
    else:
        resultados[EDIFICIOS_USUARIO_FILE] = "existe"
    
    # minas.json
    if not os.path.exists(MINAS_FILE):
        save_json(MINAS_FILE, {})
        resultados[MINAS_FILE] = "creado"
    else:
        resultados[MINAS_FILE] = "existe"
    
    # campos.json
    if not os.path.exists(CAMPOS_FILE):
        save_json(CAMPOS_FILE, {})
        resultados[CAMPOS_FILE] = "creado"
    else:
        resultados[CAMPOS_FILE] = "existe"
    
    # defensa.json
    if not os.path.exists(DEFENSA_FILE):
        save_json(DEFENSA_FILE, {})
        resultados[DEFENSA_FILE] = "creado"
    else:
        resultados[DEFENSA_FILE] = "existe"
    
    # defensa_usuario.json
    if not os.path.exists(DEFENSA_USUARIO_FILE):
        save_json(DEFENSA_USUARIO_FILE, {})
        resultados[DEFENSA_USUARIO_FILE] = "creado"
    else:
        resultados[DEFENSA_USUARIO_FILE] = "existe"
    
    # flota.json
    if not os.path.exists(FLOTA_FILE):
        save_json(FLOTA_FILE, {})
        resultados[FLOTA_FILE] = "creado"
    else:
        resultados[FLOTA_FILE] = "existe"
    
    # flota_usuario.json
    if not os.path.exists(FLOTA_USUARIO_FILE):
        save_json(FLOTA_USUARIO_FILE, {})
        resultados[FLOTA_USUARIO_FILE] = "creado"
    else:
        resultados[FLOTA_USUARIO_FILE] = "existe"
    
    # investigaciones.json
    if not os.path.exists(INVESTIGACIONES_FILE):
        save_json(INVESTIGACIONES_FILE, {})
        resultados[INVESTIGACIONES_FILE] = "creado"
    else:
        resultados[INVESTIGACIONES_FILE] = "existe"
    
    # investigaciones_usuario.json
    if not os.path.exists(INVESTIGACIONES_USUARIO_FILE):
        save_json(INVESTIGACIONES_USUARIO_FILE, {})
        resultados[INVESTIGACIONES_USUARIO_FILE] = "creado"
    else:
        resultados[INVESTIGACIONES_USUARIO_FILE] = "existe"
    
    # misiones_flota.json
    if not os.path.exists(MISIONES_FLOTA_FILE):
        save_json(MISIONES_FLOTA_FILE, {})
        resultados[MISIONES_FLOTA_FILE] = "creado"
    else:
        resultados[MISIONES_FLOTA_FILE] = "existe"
    
    # bajas_flota.json
    if not os.path.exists(BAJAS_FLOTA_FILE):
        save_json(BAJAS_FLOTA_FILE, {})
        resultados[BAJAS_FLOTA_FILE] = "creado"
    else:
        resultados[BAJAS_FLOTA_FILE] = "existe"
    
    # galaxia.json
    if not os.path.exists(GALAXIA_FILE):
        save_json(GALAXIA_FILE, {})
        resultados[GALAXIA_FILE] = "creado"
    else:
        resultados[GALAXIA_FILE] = "existe"
    
    # guia_cache.json
    if not os.path.exists(GUIA_CACHE_FILE):
        guia_cache_inicial = {
            "ultima_actualizacion": datetime.now().isoformat(),
            "naves": {},
            "defensas": {},
            "edificios": {},
            "investigaciones": {}
        }
        save_json(GUIA_CACHE_FILE, guia_cache_inicial)
        resultados[GUIA_CACHE_FILE] = "creado"
    else:
        resultados[GUIA_CACHE_FILE] = "existe"
    
    # alianza_datos.json
    if not os.path.exists(ALIANZA_DATOS_FILE):
        save_json(ALIANZA_DATOS_FILE, {})
        resultados[ALIANZA_DATOS_FILE] = "creado"
    else:
        resultados[ALIANZA_DATOS_FILE] = "existe"
    
    # alianza_miembros.json
    if not os.path.exists(ALIANZA_MIEMBROS_FILE):
        save_json(ALIANZA_MIEMBROS_FILE, {})
        resultados[ALIANZA_MIEMBROS_FILE] = "creado"
    else:
        resultados[ALIANZA_MIEMBROS_FILE] = "existe"
    
    # alianza_banco.json
    if not os.path.exists(ALIANZA_BANCO_FILE):
        save_json(ALIANZA_BANCO_FILE, {})
        resultados[ALIANZA_BANCO_FILE] = "creado"
    else:
        resultados[ALIANZA_BANCO_FILE] = "existe"
    
    # alianza_permisos.json
    if not os.path.exists(ALIANZA_PERMISOS_FILE):
        save_json(ALIANZA_PERMISOS_FILE, {})
        resultados[ALIANZA_PERMISOS_FILE] = "creado"
    else:
        resultados[ALIANZA_PERMISOS_FILE] = "existe"
    
    creados = sum(1 for v in resultados.values() if v == "creado")
    actualizados = sum(1 for v in resultados.values() if v == "actualizado")
    
    logger.info("=" * 50)
    logger.info(f"📊 VERIFICACIÓN COMPLETADA - {VERSION}")
    logger.info(f"   ✅ Existentes: {len(resultados) - creados - actualizados}")
    logger.info(f"   🆕 Creados: {creados}")
    logger.info(f"   🔄 Actualizados: {actualizados}")
    logger.info(f"   📁 Total archivos: {len(resultados)}")
    logger.info("=" * 50)
    
    return resultados

# ================= SISTEMA DE AUTENTICACIÓN =================

class AuthSystem:
    """Sistema centralizado de autenticación"""
    
    @staticmethod
    def formatear_username(user_id: int, username: str = None) -> str:
        if username:
            if not username.startswith('@'):
                return f"@{username}"
            return username
        return f"@{user_id}"
    
    @staticmethod
    def esta_registrado(user_id: int) -> bool:
        data = load_json(DATA_FILE) or {}
        return str(user_id) in data
    
    @staticmethod
    def esta_autorizado(user_id: int) -> bool:
        autorizados = load_json(AUTHORIZED_USERS_FILE) or []
        return user_id in autorizados
    
    @staticmethod
    def es_admin(user_id: int) -> bool:
        admins = load_json(ADMINS_FILE) or {}
        return str(user_id) in admins
    
    @staticmethod
    def obtener_todos_admins() -> Dict[str, dict]:
        """👑 Obtiene todos los administradores"""
        admins = load_json(ADMINS_FILE) or {}
        logger.info(f"🔍 AuthSystem.obtener_todos_admins() encontró {len(admins)} admins: {list(admins.keys())}")
        return admins
    
    @staticmethod
    def obtener_usuarios_pendientes() -> List[int]:
        data = load_json(DATA_FILE) or {}
        autorizados = load_json(AUTHORIZED_USERS_FILE) or []
        
        pendientes = []
        for user_id_str, user_data in data.items():
            user_id = int(user_id_str)
            if user_id not in autorizados and not user_data.get("autorizado", False):
                pendientes.append(user_id)
        return pendientes
    
    @staticmethod
    def obtener_todos_usuarios() -> Dict[int, dict]:
        data = load_json(DATA_FILE) or {}
        usuarios = {}
        for user_id_str, user_data in data.items():
            usuarios[int(user_id_str)] = user_data
        return usuarios
    
    @staticmethod
    def obtener_usuario(user_id: int) -> dict:
        data = load_json(DATA_FILE) or {}
        return data.get(str(user_id), {})
    
    @staticmethod
    def obtener_username(user_id: int) -> str:
        data = load_json(DATA_FILE) or {}
        usuario = data.get(str(user_id), {})
        username = usuario.get("username", f"@{user_id}")
        if not username.startswith('@'):
            return f"@{username}"
        return username
    
    @staticmethod
    def obtener_recursos(user_id: int) -> dict:
        recursos_data = load_json(RECURSOS_FILE) or {}
        return recursos_data.get(str(user_id), {})
    
    @staticmethod
    def actualizar_recursos(user_id: int, recursos: dict) -> bool:
        user_id_str = str(user_id)
        recursos_data = load_json(RECURSOS_FILE) or {}
        recursos_data[user_id_str] = recursos
        return save_json(RECURSOS_FILE, recursos_data)
    
    @staticmethod
    def obtener_minas(user_id: int) -> dict:
        minas_data = load_json(MINAS_FILE) or {}
        return minas_data.get(str(user_id), {
            "metal": 0, "cristal": 0, "deuterio": 0
        })
    
    @staticmethod
    def obtener_edificios(user_id: int) -> dict:
        edificios_data = load_json(EDIFICIOS_USUARIO_FILE) or {}
        return edificios_data.get(str(user_id), {
            "energia": 0, "laboratorio": 0, "hangar": 0, "terraformer": 0
        })
    
    @staticmethod
    def obtener_campos(user_id: int) -> dict:
        campos_data = load_json(CAMPOS_FILE) or {}
        return campos_data.get(str(user_id), {
            "total": 163, "usados": 0, "adicionales": 0
        })
    
    @staticmethod
    def obtener_flota(user_id: int) -> dict:
        flota_data = load_json(FLOTA_USUARIO_FILE) or {}
        return flota_data.get(str(user_id), {})
    
    @staticmethod
    def obtener_defensa(user_id: int) -> dict:
        defensa_data = load_json(DEFENSA_USUARIO_FILE) or {}
        return defensa_data.get(str(user_id), {})
    
    @staticmethod
    def obtener_investigaciones(user_id: int) -> dict:
        inv_data = load_json(INVESTIGACIONES_USUARIO_FILE) or {}
        return inv_data.get(str(user_id), {})
    
    @staticmethod
    def obtener_coordenadas(user_id: int) -> dict:
        user_id_str = str(user_id)
        galaxia_data = load_json(GALAXIA_FILE) or {}
        return galaxia_data.get(user_id_str, {}).get("coordenadas", {
            "galaxia": 1,
            "sistema": 1,
            "planeta": 1,
            "nombre": "Planeta 1:1:1"
        })
    
    @staticmethod
    def obtener_datos_completos(user_id: int) -> dict:
        return {
            "user_id": user_id,
            "username": AuthSystem.obtener_username(user_id),
            "recursos": AuthSystem.obtener_recursos(user_id),
            "minas": AuthSystem.obtener_minas(user_id),
            "edificios": AuthSystem.obtener_edificios(user_id),
            "campos": AuthSystem.obtener_campos(user_id),
            "flota": AuthSystem.obtener_flota(user_id),
            "defensa": AuthSystem.obtener_defensa(user_id),
            "investigaciones": AuthSystem.obtener_investigaciones(user_id),
            "coordenadas": AuthSystem.obtener_coordenadas(user_id)
        }
    
    @staticmethod
    def registrar_usuario(user_id: int, username: str = None) -> bool:
        user_id_str = str(user_id)
        data = load_json(DATA_FILE) or {}
        
        if user_id_str in data:
            logger.info(f"👤 Usuario {user_id} ya estaba registrado")
            return True
        
        username_formateado = AuthSystem.formatear_username(user_id, username)
        
        ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data[user_id_str] = {
            "id": user_id,
            "user_id": user_id,
            "username": username_formateado,
            "username_raw": username if username else str(user_id),
            "nombre": username or "Comandante",
            "fecha_registro": ahora,
            "ultima_actualizacion": ahora,
            "ultima_actualizacion_recursos": ahora,
            "autorizado": False,
            "version": VERSION
        }
        
        exito = save_json(DATA_FILE, data)
        if exito:
            logger.info(f"✅ Usuario {username_formateado} registrado exitosamente")
        else:
            logger.error(f"❌ Error al registrar usuario {username_formateado}")
        return exito
    
    @staticmethod
    def inicializar_usuario_completo(user_id: int, username: str = None) -> bool:
        user_id_str = str(user_id)
        exito = True
        username_formateado = AuthSystem.formatear_username(user_id, username)
        
        # 1. RECURSOS INICIALES
        recursos_data = load_json(RECURSOS_FILE) or {}
        if user_id_str not in recursos_data:
            recursos_data[user_id_str] = RECURSOS_INICIALES.copy()
            exito = exito and save_json(RECURSOS_FILE, recursos_data)
            logger.info(f"💰 Recursos iniciales asignados a {username_formateado}")
        
        # 2. MINAS nivel 0
        minas_data = load_json(MINAS_FILE) or {}
        if user_id_str not in minas_data:
            minas_data[user_id_str] = {"metal": 0, "cristal": 0, "deuterio": 0}
            exito = exito and save_json(MINAS_FILE, minas_data)
        
        # 3. EDIFICIOS nivel 0
        edificios_data = load_json(EDIFICIOS_USUARIO_FILE) or {}
        if user_id_str not in edificios_data:
            edificios_data[user_id_str] = {
                "energia": 0, "laboratorio": 0, "hangar": 0, "terraformer": 0
            }
            exito = exito and save_json(EDIFICIOS_USUARIO_FILE, edificios_data)
        
        # 4. CAMPOS
        campos_data = load_json(CAMPOS_FILE) or {}
        if user_id_str not in campos_data:
            campos_data[user_id_str] = {"total": 163, "usados": 0, "adicionales": 0}
            exito = exito and save_json(CAMPOS_FILE, campos_data)
        
        # 5. FLOTA vacía
        flota_data = load_json(FLOTA_USUARIO_FILE) or {}
        if user_id_str not in flota_data:
            flota_data[user_id_str] = {}
            exito = exito and save_json(FLOTA_USUARIO_FILE, flota_data)
        
        # 6. DEFENSA vacía
        defensa_data = load_json(DEFENSA_USUARIO_FILE) or {}
        if user_id_str not in defensa_data:
            defensa_data[user_id_str] = {}
            exito = exito and save_json(DEFENSA_USUARIO_FILE, defensa_data)
        
        # 7. INVESTIGACIONES nivel 0
        inv_data = load_json(INVESTIGACIONES_USUARIO_FILE) or {}
        if user_id_str not in inv_data:
            inv_data[user_id_str] = {}
            exito = exito and save_json(INVESTIGACIONES_USUARIO_FILE, inv_data)
        
        # 8. COORDENADAS ALEATORIAS
        galaxia_data = load_json(GALAXIA_FILE) or {}
        if user_id_str not in galaxia_data:
            coordenadas = obtener_coordenadas_libres()
            galaxia_data[user_id_str] = {
                "user_id": user_id,
                "username": username_formateado,
                "coordenadas": coordenadas,
                "fecha_asignacion": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            exito = exito and save_json(GALAXIA_FILE, galaxia_data)
            logger.info(f"🌍 Coordenadas {coordenadas['galaxia']}:{coordenadas['sistema']}:{coordenadas['planeta']} asignadas a {username_formateado}")
        
        # 9. MARCAR COMO AUTORIZADO
        data = load_json(DATA_FILE) or {}
        if user_id_str in data:
            data[user_id_str]["autorizado"] = True
            data[user_id_str]["fecha_autorizacion"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            data[user_id_str]["version"] = VERSION
            data[user_id_str]["ultima_actualizacion_recursos"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            exito = exito and save_json(DATA_FILE, data)
        
        return exito
    
    @staticmethod
    def autorizar_usuario(user_id: int, username: str = None) -> Tuple[bool, str]:
        user_id_str = str(user_id)
        username_formateado = AuthSystem.formatear_username(user_id, username)
        
        autorizados = load_json(AUTHORIZED_USERS_FILE) or []
        if user_id in autorizados:
            return False, "❌ El usuario ya está autorizado"
        
        autorizados.append(user_id)
        if not save_json(AUTHORIZED_USERS_FILE, autorizados):
            return False, "❌ Error al guardar lista de autorizados"
        
        if not AuthSystem.inicializar_usuario_completo(user_id, username):
            return False, "⚠️ Error en inicialización de recursos"
        
        logger.info(f"✅ Usuario {username_formateado} autorizado")
        return True, f"✅ Usuario {username_formateado} autorizado"
    
    @staticmethod
    def rechazar_usuario(user_id: int) -> bool:
        user_id_str = str(user_id)
        data = load_json(DATA_FILE) or {}
        
        if user_id_str in data:
            del data[user_id_str]
            return save_json(DATA_FILE, data)
        return True

    # ================= 🔧 NUEVOS MÉTODOS DE MANTENIMIENTO =================
    
    @staticmethod
    def obtener_estado_mantenimiento() -> bool:
        """🔧 Obtiene el estado actual del modo mantenimiento"""
        config = load_json(CONFIG_FILE) or {}
        return config.get("mantenimiento", False)

    @staticmethod
    def establecer_mantenimiento(estado: bool) -> bool:
        """🔧 Activa o desactiva el modo mantenimiento"""
        config = load_json(CONFIG_FILE) or {}
        config["mantenimiento"] = estado
        return save_json(CONFIG_FILE, config)

# ================= 🔥 FUNCIÓN DE NOTIFICACIÓN CORREGIDA - CON LOGS EXTREMOS =================

async def notificar_admins(context: ContextTypes.DEFAULT_TYPE, user_id: int, username: str):
    """
    📨 NOTIFICA A TODOS LOS ADMINISTRADORES - VERSIÓN CON LOGS EXTREMOS
    """
    logger.info("=" * 60)
    logger.info("🚨 INICIANDO notificar_admins()")
    logger.info(f"👤 Nuevo usuario: {username} (ID: {user_id})")
    
    # Obtener admins
    admins = AuthSystem.obtener_todos_admins()
    
    logger.info(f"👑 Admins encontrados en DB: {len(admins)}")
    logger.info(f"👑 IDs de admins: {list(admins.keys())}")
    
    # Verificar que el admin principal está en la lista
    if str(ADMIN_USER_ID) not in admins:
        logger.error(f"❌ CRÍTICO: Admin principal {ADMIN_USER_ID} NO está en admin.json")
        logger.info(f"📝 Contenido de admin.json: {admins}")
    else:
        logger.info(f"✅ Admin principal {ADMIN_USER_ID} encontrado en admin.json")
    
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"📨 <b>NUEVA SOLICITUD DE REGISTRO</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"👤 Usuario: @{username}\n"
        f"🆔 ID: <code>{user_id}</code>\n"
        f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        f"Selecciona una acción:\n\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("✅ ACEPTAR", callback_data=f"aceptar_{user_id}"),
            InlineKeyboardButton("❌ RECHAZAR", callback_data=f"cancelar_{user_id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    notificaciones_enviadas = 0
    
    # Si no hay admins, usar el admin principal
    if not admins:
        logger.warning("⚠️ No hay administradores en admin.json")
        logger.info("📨 Intentando notificar al admin principal por defecto")
        try:
            logger.info(f"📨 Enviando a admin principal {ADMIN_USER_ID}")
            await context.bot.send_message(
                chat_id=ADMIN_USER_ID,
                text=mensaje,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
            notificaciones_enviadas = 1
            logger.info(f"✅ Notificación enviada al admin principal {ADMIN_USER_ID}")
        except Exception as e:
            logger.error(f"❌ Error CRÍTICO enviando a admin principal: {e}")
            logger.error(f"❌ Tipo de error: {type(e).__name__}")
            logger.error(f"❌ Detalle: {str(e)}")
        logger.info(f"📨 TOTAL: {notificaciones_enviadas}")
        logger.info("=" * 60)
        return notificaciones_enviadas
    
    # Notificar a todos los admins
    logger.info(f"📨 Procesando {len(admins)} administradores...")
    
    for admin_id_str in admins.keys():
        try:
            admin_id = int(admin_id_str)
            logger.info(f"📨 Procesando admin ID: {admin_id}")
            
            # Verificar si el bot puede enviar mensajes a este admin
            try:
                chat = await context.bot.get_chat(admin_id)
                logger.info(f"✅ Chat válido: {chat.first_name} (ID: {chat.id})")
            except Exception as e:
                logger.error(f"❌ No se puede acceder al chat del admin {admin_id}")
                logger.error(f"❌ Error: {e}")
                logger.error(f"❌ El admin debe iniciar el bot primero (enviar /start)")
                continue
            
            logger.info(f"📨 Enviando mensaje a admin {admin_id}...")
            await context.bot.send_message(
                chat_id=admin_id,
                text=mensaje,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
            notificaciones_enviadas += 1
            logger.info(f"✅ Mensaje enviado exitosamente a admin {admin_id}")
            
        except Exception as e:
            logger.error(f"❌ Error enviando a admin {admin_id_str}")
            logger.error(f"❌ Tipo de error: {type(e).__name__}")
            logger.error(f"❌ Mensaje: {str(e)}")
            continue
    
    # Si no se pudo notificar a nadie, intentar con el admin principal como último recurso
    if notificaciones_enviadas == 0:
        logger.warning("⚠️ No se pudo notificar a ningún admin de la lista")
        logger.info("📨 Intentando envío de EMERGENCIA al admin principal")
        try:
            await context.bot.send_message(
                chat_id=ADMIN_USER_ID,
                text=mensaje + "\n\n⚠️ ENVÍO DE EMERGENCIA",
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
            notificaciones_enviadas = 1
            logger.info(f"✅ Notificación de emergencia enviada a {ADMIN_USER_ID}")
        except Exception as e:
            logger.error(f"❌ Error CRÍTICO: no se pudo notificar ni al admin principal")
            logger.error(f"❌ Error final: {e}")
    
    logger.info(f"📨 RESULTADO FINAL: {notificaciones_enviadas} notificaciones enviadas")
    logger.info("=" * 60)
    
    return notificaciones_enviadas

# ================= DECORADORES =================

def requiere_login(func):
    from functools import wraps
    
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not user:
            return
        
        if not AuthSystem.esta_autorizado(user.id):
            if update.message:
                await update.message.reply_text(
                    "❌ <b>No autorizado</b>\n\nUsa /start para solicitar acceso.",
                    parse_mode="HTML"
                )
            return
        
        return await func(update, context)
    return wrapper

def requiere_admin(func):
    from functools import wraps
    
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not user:
            return
        
        if not AuthSystem.es_admin(user.id):
            if update.message:
                await update.message.reply_text(
                    "❌ <b>Acceso denegado</b>\n\nSe requieren permisos de administrador.",
                    parse_mode="HTML"
                )
            elif update.callback_query:
                await update.callback_query.answer(
                    "❌ No tienes permisos de administrador",
                    show_alert=True
                )
            return
        
        return await func(update, context)
    return wrapper

# ================= INICIALIZACIÓN =================

def inicializar_sistema():
    """🚀 LLAMAR AL INICIAR EL BOT"""
    logger.info("=" * 50)
    logger.info(f"🚀 INICIALIZANDO ASTROIO {VERSION}")
    logger.info("=" * 50)
    
    verificar_todos_archivos()
    
    autorizados = load_json(AUTHORIZED_USERS_FILE) or []
    if ADMIN_USER_ID not in autorizados:
        autorizados.append(ADMIN_USER_ID)
        save_json(AUTHORIZED_USERS_FILE, autorizados)
        logger.info(f"👑 Admin principal {ADMIN_USER_ID} autorizado")
    
    if not AuthSystem.esta_registrado(ADMIN_USER_ID):
        AuthSystem.registrar_usuario(ADMIN_USER_ID, "Admin")
        AuthSystem.inicializar_usuario_completo(ADMIN_USER_ID, "Admin")
        logger.info(f"👑 Admin principal registrado")
    
    logger.info("=" * 50)
    logger.info(f"✅ SISTEMA INICIALIZADO - {VERSION}")
    logger.info("=" * 50)
    
    return True

# ================= EXPORTAR =================

__all__ = [
    'inicializar_sistema',
    'verificar_todos_archivos',
    'AuthSystem',
    'notificar_admins',
    'requiere_login',
    'requiere_admin',
    'VERSION',
    'ADMIN_USER_ID',
    'RECURSOS_INICIALES',
    'MISIONES_FLOTA_FILE',
    'BAJAS_FLOTA_FILE',
    'GALAXIA_FILE',
    'GUIA_CACHE_FILE',
    'ALIANZA_DATOS_FILE',
    'ALIANZA_MIEMBROS_FILE',
    'ALIANZA_BANCO_FILE',
    'ALIANZA_PERMISOS_FILE',
    'generar_coordenadas_aleatorias',
    'obtener_coordenadas_libres',
    'coordenadas_a_string',
    # 👇 EXPORTAR LAS NUEVAS VARIABLES DE GITHUB
    'GITHUB_TOKEN',
    'GITHUB_OWNER',
    'GITHUB_REPO',
    'USE_GITHUB_SYNC'
]
