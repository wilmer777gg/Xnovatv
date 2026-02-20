#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#██████╗ ███████╗████████╗██████╗  █████╗ ██╗     ███████╗
#██╔══██╗██╔════╝╚══██╔══╝██╔══██╗██╔══██╗██║     ██╔════╝
#██████╔╝███████╗   ██║   ██████╔╝███████║██║     ███████╗
#██╔══██╗╚════██║   ██║   ██╔══██╗██╔══██║██║     ╚════██║
#██║  ██║███████║   ██║   ██║  ██║██║  ██║███████╗███████║
#╚═╝  ╚═╝╚══════╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚══════╝

#🚀 ASTRO.IO v2.4.5 🚀
#💾 database.py - GESTIÓN DE ARCHIVOS JSON CON PERSISTENCIA HÍBRIDA
#=======================================
#✅ Versión CORREGIDA - 20 Feb 2026
#✅ Detección automática de rama GitHub
#✅ Sistema de fallback 100% funcional
#=======================================

import os
import json
import base64
import logging
import requests
import time
from typing import Any, Dict, List, Optional, Union, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

# ================= CONSTANTES =================
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

# ================= CONFIGURACIÓN DE GITHUB =================
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_OWNER = os.environ.get("GITHUB_OWNER")
GITHUB_REPO = os.environ.get("GITHUB_REPO")
GITHUB_API = "https://api.github.com"
USE_GITHUB_SYNC = os.getenv("USE_GITHUB_SYNC", "false").lower() == "true"

# ================= DETECCIÓN AUTOMÁTICA DE RAMA =================
def detectar_rama_github() -> str:
    """🔍 Detecta automáticamente la rama principal del repositorio"""
    if not all([GITHUB_TOKEN, GITHUB_OWNER, GITHUB_REPO]):
        return "main"
    
    headers = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    
    # Intentar con main primero, luego master
    for branch in ["main", "master"]:
        try:
            url = f"{GITHUB_API}/repos/{GITHUB_OWNER}/{GITHUB_REPO}/branches/{branch}"
            response = requests.get(url, headers=headers, timeout=5)
            
            if response.status_code == 200:
                logger.info(f"✅ Rama GitHub detectada: '{branch}'")
                return branch
        except:
            continue
    
    logger.warning("⚠️ No se pudo detectar rama GitHub, usando 'main'")
    return "main"

# Detectar rama al iniciar
GITHUB_BRANCH = detectar_rama_github()
HEADERS = {"Accept": "application/vnd.github.v3+json"}
if GITHUB_TOKEN:
    HEADERS["Authorization"] = f"token {GITHUB_TOKEN}"

# Cache de SHAs para archivos en GitHub
github_sha_cache = {}
# Control de frecuencia para guardados
last_save_time = {}

# ================= FUNCIONES AUXILIARES DE GITHUB =================

def _get_file_from_github(path: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Obtiene contenido y SHA de un archivo en GitHub.
    Retorna (contenido, sha) o (None, None) si no existe o hay error.
    """
    if not USE_GITHUB_SYNC or not all([GITHUB_OWNER, GITHUB_REPO, GITHUB_TOKEN]):
        return None, None

    url = f"{GITHUB_API}/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{path}?ref={GITHUB_BRANCH}"
    
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        
        if r.status_code == 200:
            data = r.json()
            content = base64.b64decode(data["content"]).decode("utf-8")
            logger.info(f"☁️ Archivo encontrado en GitHub: {path}")
            return content, data.get("sha")
        elif r.status_code == 404:
            logger.debug(f"ℹ️ Archivo no existe en GitHub: {path}")
            return None, None
        else:
            logger.warning(f"⚠️ Error GitHub {r.status_code}: {r.text[:100]}")
            return None, None
    except requests.exceptions.Timeout:
        logger.debug("⏱️ Timeout conectando con GitHub")
        return None, None
    except Exception as e:
        logger.debug(f"ℹ️ Error obteniendo archivo de GitHub: {e}")
        return None, None

def _put_file_to_github(path: str, content_str: str, sha: Optional[str] = None) -> Tuple[bool, Optional[str]]:
    """
    Guarda un archivo en GitHub.
    Retorna (éxito, nuevo_sha)
    """
    if not USE_GITHUB_SYNC or not all([GITHUB_OWNER, GITHUB_REPO, GITHUB_TOKEN]):
        return False, None

    url = f"{GITHUB_API}/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{path}"
    b64_content = base64.b64encode(content_str.encode("utf-8")).decode("utf-8")

    payload = {
        "message": f"Auto-backup: {path} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "content": b64_content,
        "branch": GITHUB_BRANCH
    }
    if sha:
        payload["sha"] = sha

    try:
        r = requests.put(url, headers=HEADERS, json=payload, timeout=10)
        
        if r.status_code in (200, 201):
            result = r.json()
            new_sha = result.get("content", {}).get("sha")
            logger.info(f"☁️ Guardado en GitHub: {path}")
            return True, new_sha
        else:
            logger.warning(f"⚠️ Error guardando en GitHub ({r.status_code}): {r.text[:100]}")
            return False, None
    except requests.exceptions.Timeout:
        logger.debug("⏱️ Timeout guardando en GitHub")
        return False, None
    except Exception as e:
        logger.debug(f"ℹ️ Error guardando en GitHub: {e}")
        return False, None

# ================= FUNCIONES AUXILIARES LOCALES =================

def _get_file_local(filepath: str) -> Tuple[Optional[str], None]:
    """Lee un archivo local"""
    if not os.path.exists(filepath):
        return None, None
    
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read(), None
    except Exception as e:
        logger.warning(f"⚠️ Error leyendo archivo local {filepath}: {e}")
        return None, None

def _put_file_local(filepath: str, content_str: str) -> bool:
    """Guarda un archivo local"""
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content_str)
        logger.info(f"📁 Guardado en local: {filepath}")
        return True
    except Exception as e:
        logger.error(f"❌ Error guardando archivo local {filepath}: {e}")
        return False

# ================= FUNCIONES PRINCIPALES CON FALLBACK =================

def load_json(filepath: str, default: Any = None) -> Any:
    """
    CARGA CON FALLBACK:
    1️⃣ Intenta desde GitHub (si está activado)
    2️⃣ Si falla, intenta desde local
    3️⃣ Si todo falla, retorna valor por defecto
    """
    # Determinar ruta relativa para GitHub
    if filepath.startswith(DATA_DIR):
        github_path = filepath[len(DATA_DIR)+1:]  # Quita 'data/'
    else:
        github_path = os.path.basename(filepath)
    
    # ========== 1️⃣ INTENTAR DESDE GITHUB ==========
    if USE_GITHUB_SYNC:
        try:
            content, sha = _get_file_from_github(github_path)
            if content is not None:
                data = json.loads(content)
                # Guardar SHA en caché para futuras escrituras
                if sha:
                    github_sha_cache[filepath] = sha
                return data
        except Exception as e:
            logger.debug(f"ℹ️ Error cargando desde GitHub: {e}")
    
    # ========== 2️⃣ FALLBACK A LOCAL ==========
    try:
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data
    except Exception as e:
        logger.debug(f"ℹ️ Error cargando desde local: {e}")
    
    # ========== 3️⃣ VALOR POR DEFECTO ==========
    if default is not None:
        return default
    return {} if filepath.endswith('.json') else []

def save_json(filepath: str, data: Any) -> bool:
    """
    GUARDA CON FALLBACK:
    1️⃣ Intenta en GitHub (si está activado)
    2️⃣ SIEMPRE guarda en local como respaldo
    3️⃣ Retorna True si al menos LOCAL funcionó
    """
    # Determinar ruta relativa para GitHub
    if filepath.startswith(DATA_DIR):
        github_path = filepath[len(DATA_DIR)+1:]  # Quita 'data/'
    else:
        github_path = os.path.basename(filepath)
    
    # Preparar contenido
    content_str = json.dumps(data, indent=2, ensure_ascii=False)
    
    # Control de frecuencia para evitar sobrecarga
    current_time = time.time()
    if filepath in last_save_time:
        if current_time - last_save_time[filepath] < 1:  # Mínimo 1 segundo
            return True
    last_save_time[filepath] = current_time
    
    # ========== 1️⃣ INTENTAR EN GITHUB ==========
    if USE_GITHUB_SYNC:
        try:
            # Obtener SHA de caché
            sha = github_sha_cache.get(filepath)
            
            # Guardar en GitHub
            success, new_sha = _put_file_to_github(github_path, content_str, sha)
            
            if success and new_sha:
                github_sha_cache[filepath] = new_sha
        except Exception as e:
            logger.debug(f"ℹ️ Error guardando en GitHub: {e}")
    
    # ========== 2️⃣ SIEMPRE GUARDAR EN LOCAL ==========
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content_str)
        return True
    except Exception as e:
        logger.error(f"❌ Error guardando en local: {e}")
        return False

# ================= FUNCIONES DE UTILIDAD =================

def get_file_path(filename: str) -> str:
    """Obtiene ruta completa en data/"""
    return os.path.join(DATA_DIR, filename)

def obtener_usuario(user_id: int, archivo: str) -> dict:
    """Obtiene datos de un usuario específico"""
    user_id_str = str(user_id)
    data = load_json(archivo, {})
    return data.get(user_id_str, {})

def guardar_usuario(user_id: int, archivo: str, datos_usuario: dict) -> bool:
    """Guarda datos de un usuario específico"""
    user_id_str = str(user_id)
    data = load_json(archivo, {})
    data[user_id_str] = datos_usuario
    return save_json(archivo, data)

def actualizar_campo_usuario(user_id: int, archivo: str, campo: str, valor: Any) -> bool:
    """Actualiza un campo específico de un usuario"""
    datos = obtener_usuario(user_id, archivo)
    datos[campo] = valor
    return guardar_usuario(user_id, archivo, datos)

def incrementar_campo_usuario(user_id: int, archivo: str, campo: str, cantidad: Union[int, float]) -> bool:
    """Incrementa un campo numérico de un usuario"""
    datos = obtener_usuario(user_id, archivo)
    valor_actual = datos.get(campo, 0)
    datos[campo] = valor_actual + cantidad
    return guardar_usuario(user_id, archivo, datos)

def obtener_recurso(user_id: int, recurso: str) -> Union[int, float]:
    """Obtiene un recurso específico"""
    from login import RECURSOS_FILE
    return obtener_usuario(user_id, RECURSOS_FILE).get(recurso, 0)

def actualizar_recurso(user_id: int, recurso: str, cantidad: Union[int, float]) -> bool:
    """Actualiza un recurso específico"""
    from login import RECURSOS_FILE
    return actualizar_campo_usuario(user_id, RECURSOS_FILE, recurso, cantidad)

def incrementar_recurso(user_id: int, recurso: str, cantidad: Union[int, float]) -> bool:
    """Incrementa un recurso específico"""
    from login import RECURSOS_FILE
    return incrementar_campo_usuario(user_id, RECURSOS_FILE, recurso, cantidad)

def agregar_a_lista_usuario(user_id: int, archivo: str, lista: str, elemento: Any) -> bool:
    """Agrega elemento a lista del usuario"""
    datos = obtener_usuario(user_id, archivo)
    if lista not in datos:
        datos[lista] = []
    if elemento not in datos[lista]:
        datos[lista].append(elemento)
    return guardar_usuario(user_id, archivo, datos)

def eliminar_de_lista_usuario(user_id: int, archivo: str, lista: str, elemento: Any) -> bool:
    """Elimina elemento de lista del usuario"""
    datos = obtener_usuario(user_id, archivo)
    if lista in datos and elemento in datos[lista]:
        datos[lista].remove(elemento)
        return guardar_usuario(user_id, archivo, datos)
    return True

# ================= EXPORTAR =================

__all__ = [
    'load_json',
    'save_json',
    'get_file_path',
    'DATA_DIR',
    'obtener_usuario',
    'guardar_usuario',
    'actualizar_campo_usuario',
    'incrementar_campo_usuario',
    'obtener_recurso',
    'actualizar_recurso',
    'incrementar_recurso',
    'agregar_a_lista_usuario',
    'eliminar_de_lista_usuario',
]
