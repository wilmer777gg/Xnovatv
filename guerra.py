#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#⚔️ guerra.py - SISTEMA DE GUERRA DE ALIANZAS CON INTERFAZ COMPLETA
#===================================================
#✅ En alianza: TODOS ven el botón ⚔️ GUERRA
#✅ TODOS pueden ver puntos de guerra de todos
#✅ TODOS pueden enviar flotas a la guerra
#✅ Admins de alianza pueden buscar rivales
#✅ Admin principal configura temporadas en /admin
#✅ Interfaz completa con todos los menús
#===================================================

import os
import json
import logging
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, ConversationHandler, CommandHandler, MessageHandler, filters

from login import AuthSystem, requiere_login, requiere_admin
from database import load_json, save_json
from utils import abreviar_numero, formatear_tiempo

logger = logging.getLogger(__name__)

# ================= CONSTANTES =================
DATA_DIR = "data"
ALIANZA_DATOS_FILE = os.path.join(DATA_DIR, "alianza_datos.json")
ALIANZA_MIEMBROS_FILE = os.path.join(DATA_DIR, "alianza_miembros.json")
ALIANZA_PERMISOS_FILE = os.path.join(DATA_DIR, "alianza_permisos.json")
GUERRAS_FILE = os.path.join(DATA_DIR, "guerras.json")
TEMPORADAS_GUERRA_FILE = os.path.join(DATA_DIR, "temporadas_guerra.json")
HISTORIAL_GUERRAS_FILE = os.path.join(DATA_DIR, "historial_guerras.json")
PUNTOS_GUERRA_FILE = os.path.join(DATA_DIR, "puntos_guerra.json")
FLOTA_USUARIO_FILE = os.path.join(DATA_DIR, "flota_usuario.json")
DEFENSA_USUARIO_FILE = os.path.join(DATA_DIR, "defensa_usuario.json")
RECURSOS_FILE = os.path.join(DATA_DIR, "recursos.json")
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")

# ================= CONFIGURACIÓN POR DEFECTO =================
DURACION_GUERRA_HORAS = 12
RANGO_EMPAREJAMIENTO = 0.05  # ±5%
MINIMO_MIEMBROS_ALIANZA = 3
MAX_ASALTOS = 10

# Estados para ConversationHandler
NOMBRE_TEMPORADA, ENVIANDO_FLOTAS, SELECCIONANDO_CANTIDAD = range(3)

# ================= CONFIGURACIÓN DE PESOS =================
PESOS_NAVES = {
    "cazador_ligero": 30,
    "cazador_pesado": 60,
    "crucero": 120,
    "nave_batalla": 240,
    "acorazado": 360,
    "destructor": 480,
    "estrella_muerte": 3000,
    "nave_carga_pequena": 18,
    "nave_carga_grande": 36,
    "reciclador": 48,
    "sonda_espionaje": 6,
    "satelite_solar": 12
}

# ================= FUNCIONES AUXILIARES DE ALIANZA =================

def obtener_alianza_usuario(user_id: int) -> tuple:
    """Obtiene la alianza de un usuario"""
    user_id_str = str(user_id)
    miembros_data = load_json(ALIANZA_MIEMBROS_FILE) or {}
    
    for alianza_id, miembros in miembros_data.items():
        if isinstance(miembros, dict) and user_id_str in miembros:
            datos = load_json(ALIANZA_DATOS_FILE) or {}
            return alianza_id, datos.get(alianza_id, {})
        elif isinstance(miembros, list) and user_id_str in miembros:
            datos = load_json(ALIANZA_DATOS_FILE) or {}
            return alianza_id, datos.get(alianza_id, {})
    
    return None, None

def obtener_miembros_alianza(alianza_id: str) -> dict:
    """Obtiene los miembros de una alianza"""
    miembros_data = load_json(ALIANZA_MIEMBROS_FILE) or {}
    miembros = miembros_data.get(alianza_id, {})
    
    # Si es lista, convertir a diccionario
    if isinstance(miembros, list):
        miembros_dict = {}
        for uid in miembros:
            if isinstance(uid, (int, str)):
                miembros_dict[str(uid)] = {"username": f"@{uid}"}
        return miembros_dict
    
    return miembros

def obtener_alianza_nombre(user_id: int) -> str:
    """Obtiene el nombre de la alianza del usuario"""
    alianza_id, _ = obtener_alianza_usuario(user_id)
    if not alianza_id:
        return "Sin alianza"
    
    datos = load_json(ALIANZA_DATOS_FILE) or {}
    alianza = datos.get(alianza_id, {})
    return alianza.get("nombre", "Alianza")

def es_fundador_alianza(user_id: int, alianza_id: str) -> bool:
    """Verifica si el usuario es fundador de la alianza"""
    datos = load_json(ALIANZA_DATOS_FILE) or {}
    alianza = datos.get(alianza_id, {})
    return alianza.get("fundador") == user_id

def es_admin_alianza(user_id: int, alianza_id: str) -> bool:
    """Verifica si el usuario es admin de la alianza"""
    # El fundador siempre es admin
    if es_fundador_alianza(user_id, alianza_id):
        return True
    
    # Verificar en miembros
    miembros = obtener_miembros_alianza(alianza_id)
    miembro = miembros.get(str(user_id), {})
    
    if isinstance(miembro, dict):
        return miembro.get("rango") == "admin"
    return False

# ================= FUNCIONES DE CONFIGURACIÓN GLOBAL =================

def obtener_configuracion_guerra() -> dict:
    """Obtiene la configuración global de guerra"""
    config = load_json(CONFIG_FILE) or {}
    guerra_config = config.get("guerra", {})
    
    # Valores por defecto
    return {
        "duracion_horas": guerra_config.get("duracion_horas", DURACION_GUERRA_HORAS),
        "rango_emparejamiento": guerra_config.get("rango_emparejamiento", RANGO_EMPAREJAMIENTO),
        "minimo_miembros": guerra_config.get("minimo_miembros", MINIMO_MIEMBROS_ALIANZA),
        "max_asaltos": guerra_config.get("max_asaltos", MAX_ASALTOS)
    }

def guardar_configuracion_guerra(config: dict) -> bool:
    """Guarda la configuración global de guerra"""
    data = load_json(CONFIG_FILE) or {}
    data["guerra"] = config
    return save_json(CONFIG_FILE, data)

# ================= FUNCIONES DE TEMPORADAS =================

def inicializar_puntos_guerra():
    """📊 Inicializa el archivo de puntos de guerra"""
    if not os.path.exists(PUNTOS_GUERRA_FILE):
        estructura_inicial = {
            "temporada_actual": None,
            "fecha_inicio": None,
            "fecha_fin": None,
            "nombre_temporada": None,
            "usuarios": {},  # user_id: {"puntos": 0, "nombre": "...", "alianza": "...", "naves_enviadas": {}}
            "historial_temporadas": []
        }
        save_json(PUNTOS_GUERRA_FILE, estructura_inicial)
        logger.info("✅ Archivo de puntos de guerra inicializado")

def obtener_estado_temporada() -> dict:
    """📅 Obtiene el estado actual de la temporada de guerra"""
    data = load_json(PUNTOS_GUERRA_FILE) or {}
    
    return {
        "activa": data.get("temporada_actual") is not None,
        "temporada_id": data.get("temporada_actual"),
        "nombre": data.get("nombre_temporada", "Sin temporada"),
        "fecha_inicio": data.get("fecha_inicio"),
        "fecha_fin": data.get("fecha_fin"),
        "tiempo_restante": calcular_tiempo_restante(data.get("fecha_fin"))
    }

def calcular_tiempo_restante(fecha_fin_str: Optional[str]) -> Optional[int]:
    """Calcula el tiempo restante en segundos"""
    if not fecha_fin_str:
        return None
    
    try:
        fecha_fin = datetime.fromisoformat(fecha_fin_str)
        ahora = datetime.now()
        segundos = max(0, int((fecha_fin - ahora).total_seconds()))
        return segundos
    except:
        return None

def iniciar_temporada_global(nombre: str) -> bool:
    """🎬 Inicia una nueva temporada de guerra (solo admin principal)"""
    data = load_json(PUNTOS_GUERRA_FILE) or {}
    
    # Guardar temporada anterior en historial si existe
    if data.get("temporada_actual"):
        data.setdefault("historial_temporadas", []).append({
            "id": data["temporada_actual"],
            "nombre": data.get("nombre_temporada"),
            "fecha_inicio": data.get("fecha_inicio"),
            "fecha_fin": datetime.now().isoformat(),
            "usuarios": data.get("usuarios", {})
        })
    
    # Obtener configuración
    config = obtener_configuracion_guerra()
    duracion = config["duracion_horas"]
    
    # Calcular fecha de fin
    fecha_fin = datetime.now() + timedelta(hours=duracion)
    
    # Crear nueva temporada
    data["temporada_actual"] = f"temp_{int(datetime.now().timestamp())}"
    data["nombre_temporada"] = nombre
    data["fecha_inicio"] = datetime.now().isoformat()
    data["fecha_fin"] = fecha_fin.isoformat()
    data["usuarios"] = {}  # Reiniciar puntos
    
    return save_json(PUNTOS_GUERRA_FILE, data)

def cerrar_temporada_global() -> dict:
    """🔚 Cierra la temporada actual (solo admin principal)"""
    data = load_json(PUNTOS_GUERRA_FILE) or {}
    
    if not data.get("temporada_actual"):
        return {"exito": False, "mensaje": "No hay temporada activa"}
    
    # Guardar en historial
    historial = {
        "id": data["temporada_actual"],
        "nombre": data.get("nombre_temporada"),
        "fecha_inicio": data.get("fecha_inicio"),
        "fecha_fin": datetime.now().isoformat(),
        "usuarios": data.get("usuarios", {}).copy()
    }
    
    data.setdefault("historial_temporadas", []).append(historial)
    
    # Limpiar temporada actual
    data["temporada_actual"] = None
    data["nombre_temporada"] = None
    data["fecha_inicio"] = None
    data["fecha_fin"] = None
    
    save_json(PUNTOS_GUERRA_FILE, data)
    
    return {
        "exito": True,
        "mensaje": "Temporada cerrada correctamente",
        "historial": historial
    }

# ================= FUNCIONES DE PUNTOS =================

def obtener_puntos_usuario(user_id: int) -> dict:
    """🎯 Obtiene los puntos de guerra de un usuario"""
    user_id_str = str(user_id)
    data = load_json(PUNTOS_GUERRA_FILE) or {}
    
    # Inicializar estructura si no existe
    if "usuarios" not in data:
        data["usuarios"] = {}
    
    # Obtener o crear registro del usuario
    if user_id_str not in data["usuarios"]:
        data["usuarios"][user_id_str] = {
            "puntos": 0,
            "nombre": AuthSystem.obtener_username(user_id),
            "alianza": obtener_alianza_nombre(user_id),
            "naves_enviadas": {},
            "ultima_actualizacion": datetime.now().isoformat(),
            "historial": []
        }
        save_json(PUNTOS_GUERRA_FILE, data)
    
    return data["usuarios"][user_id_str]

def obtener_todos_puntos_alianza(alianza_id: str) -> list:
    """📋 Obtiene los puntos de TODOS los miembros de una alianza (TODOS VEN TODO)"""
    miembros = obtener_miembros_alianza(alianza_id)
    data = load_json(PUNTOS_GUERRA_FILE) or {}
    
    resultados = []
    for uid_str in miembros.keys():
        user_id = int(uid_str)
        puntos_data = data.get("usuarios", {}).get(uid_str, {
            "puntos": 0,
            "nombre": AuthSystem.obtener_username(user_id)
        })
        
        # Obtener naves enviadas
        naves_enviadas = puntos_data.get("naves_enviadas", {})
        total_naves = sum(naves_enviadas.values()) if isinstance(naves_enviadas, dict) else 0
        
        resultados.append({
            "user_id": user_id,
            "nombre": puntos_data.get("nombre", f"@{user_id}"),
            "puntos": puntos_data.get("puntos", 0),
            "naves_enviadas": total_naves,
            "detalle_naves": naves_enviadas
        })
    
    # Ordenar por puntos (mayor a menor)
    resultados.sort(key=lambda x: x["puntos"], reverse=True)
    return resultados

def obtener_ranking_global() -> list:
    """🌍 Obtiene el ranking global de jugadores"""
    data = load_json(PUNTOS_GUERRA_FILE) or {}
    usuarios = data.get("usuarios", {})
    
    ranking = []
    for uid_str, info in usuarios.items():
        ranking.append({
            "user_id": int(uid_str),
            "nombre": info.get("nombre", f"@{uid_str}"),
            "puntos": info.get("puntos", 0),
            "alianza": info.get("alianza", "Sin alianza")
        })
    
    ranking.sort(key=lambda x: x["puntos"], reverse=True)
    return ranking

def obtener_ranking_alianzas() -> list:
    """🏰 Obtiene el ranking de alianzas por puntos totales"""
    data = load_json(PUNTOS_GUERRA_FILE) or {}
    usuarios = data.get("usuarios", {})
    
    # Agrupar por alianza
    alianzas = {}
    for uid_str, info in usuarios.items():
        alianza = info.get("alianza", "Sin alianza")
        puntos = info.get("puntos", 0)
        
        if alianza not in alianzas:
            alianzas[alianza] = 0
        alianzas[alianza] += puntos
    
    # Convertir a lista para ranking
    ranking = [{"nombre": k, "puntos": v} for k, v in alianzas.items()]
    ranking.sort(key=lambda x: x["puntos"], reverse=True)
    
    return ranking

def actualizar_puntos_usuario(user_id: int, puntos_ganados: int, batalla_id: str = None):
    """➕ Añade puntos a un usuario y guarda en historial"""
    user_id_str = str(user_id)
    data = load_json(PUNTOS_GUERRA_FILE) or {}
    
    if "usuarios" not in data:
        data["usuarios"] = {}
    
    if user_id_str not in data["usuarios"]:
        data["usuarios"][user_id_str] = {
            "puntos": 0,
            "nombre": AuthSystem.obtener_username(user_id),
            "alianza": obtener_alianza_nombre(user_id),
            "naves_enviadas": {},
            "historial": []
        }
    
    # Actualizar puntos
    data["usuarios"][user_id_str]["puntos"] += puntos_ganados
    data["usuarios"][user_id_str]["ultima_actualizacion"] = datetime.now().isoformat()
    
    # Guardar en historial
    if "historial" not in data["usuarios"][user_id_str]:
        data["usuarios"][user_id_str]["historial"] = []
    
    data["usuarios"][user_id_str]["historial"].append({
        "fecha": datetime.now().isoformat(),
        "puntos": puntos_ganados,
        "batalla_id": batalla_id,
        "total_acumulado": data["usuarios"][user_id_str]["puntos"]
    })
    
    # Mantener solo últimos 20 registros
    if len(data["usuarios"][user_id_str]["historial"]) > 20:
        data["usuarios"][user_id_str]["historial"] = data["usuarios"][user_id_str]["historial"][-20:]
    
    save_json(PUNTOS_GUERRA_FILE, data)
    logger.info(f"✅ Usuario {user_id} ganó {puntos_ganados} puntos. Total: {data['usuarios'][user_id_str]['puntos']}")

def registrar_naves_enviadas(user_id: int, naves: dict):
    """🚀 Registra las naves que un usuario envía a la guerra"""
    user_id_str = str(user_id)
    data = load_json(PUNTOS_GUERRA_FILE) or {}
    
    if "usuarios" not in data:
        data["usuarios"] = {}
    
    if user_id_str not in data["usuarios"]:
        data["usuarios"][user_id_str] = {
            "puntos": 0,
            "nombre": AuthSystem.obtener_username(user_id),
            "alianza": obtener_alianza_nombre(user_id),
            "naves_enviadas": {},
            "historial": []
        }
    
    # Registrar naves enviadas
    if "naves_enviadas" not in data["usuarios"][user_id_str]:
        data["usuarios"][user_id_str]["naves_enviadas"] = {}
    
    for nave, cantidad in naves.items():
        if cantidad > 0:
            data["usuarios"][user_id_str]["naves_enviadas"][nave] = \
                data["usuarios"][user_id_str]["naves_enviadas"].get(nave, 0) + cantidad
    
    save_json(PUNTOS_GUERRA_FILE, data)
    logger.info(f"🚀 Usuario {user_id} envió {naves} naves a la guerra")

# ================= FUNCIONES DE FLOTA =================

def obtener_flota_usuario(user_id: int) -> dict:
    """🚀 Obtiene la flota disponible del usuario"""
    flota_data = load_json(FLOTA_USUARIO_FILE) or {}
    return flota_data.get(str(user_id), {})

def obtener_config_naves():
    """📋 Obtiene la configuración de naves desde flota.py"""
    try:
        from flota import CONFIG_NAVES
        return CONFIG_NAVES
    except ImportError:
        # Configuración de respaldo
        return {
            "cazador_ligero": {
                "nombre": "Cazador Ligero",
                "icono": "🚀",
                "ataque": 50,
                "escudo": 10,
                "velocidad": 100,
                "consumo": 20
            },
            "cazador_pesado": {
                "nombre": "Cazador Pesado",
                "icono": "⚔️",
                "ataque": 150,
                "escudo": 25,
                "velocidad": 80,
                "consumo": 30
            },
            "crucero": {
                "nombre": "Crucero",
                "icono": "⚡",
                "ataque": 250,
                "escudo": 50,
                "velocidad": 90,
                "consumo": 35
            },
            "nave_batalla": {
                "nombre": "Nave de Batalla",
                "icono": "💥",
                "ataque": 1000,
                "escudo": 200,
                "velocidad": 70,
                "consumo": 150
            }
        }

def calcular_daño_total_alianza(alianza_id: str) -> int:
    """
    Calcula el daño total de la alianza sumando el daño de todas las naves enviadas.
    """
    miembros_puntos = obtener_todos_puntos_alianza(alianza_id)
    config_naves = obtener_config_naves()
    
    daño_total = 0
    
    for miembro in miembros_puntos:
        naves = miembro.get("detalle_naves", {})
        for nave_id, cantidad in naves.items():
            if nave_id in config_naves:
                daño_total += config_naves[nave_id].get("ataque", 0) * cantidad
    
    return daño_total

def calcular_consumo_deuterio(naves: dict) -> int:
    """⚡ Calcula el consumo de deuterio para enviar naves"""
    config_naves = obtener_config_naves()
    consumo = 0
    
    for nave_id, cantidad in naves.items():
        if nave_id in config_naves:
            consumo += config_naves[nave_id].get("consumo", 20) * cantidad
    
    return consumo

def verificar_recursos_suficientes(user_id: int, naves: dict) -> tuple:
    """💰 Verifica si el usuario tiene suficientes recursos"""
    recursos_data = load_json(RECURSOS_FILE) or {}
    recursos = recursos_data.get(str(user_id), {})
    
    deuterio_necesario = calcular_consumo_deuterio(naves)
    deuterio_disponible = recursos.get("deuterio", 0)
    
    if deuterio_necesario > deuterio_disponible:
        return False, f"❌ Necesitas {abreviar_numero(deuterio_necesario)} deuterio (tienes: {abreviar_numero(deuterio_disponible)})"
    
    return True, "✅ Recursos suficientes"

def descontar_recursos(user_id: int, naves: dict) -> bool:
    """💸 Descuenta los recursos por enviar naves"""
    recursos_data = load_json(RECURSOS_FILE) or {}
    recursos = recursos_data.get(str(user_id), {})
    
    deuterio_necesario = calcular_consumo_deuterio(naves)
    
    if recursos.get("deuterio", 0) < deuterio_necesario:
        return False
    
    recursos["deuterio"] = recursos.get("deuterio", 0) - deuterio_necesario
    recursos_data[str(user_id)] = recursos
    return save_json(RECURSOS_FILE, recursos_data)

# ================= FUNCIONES DE BATALLA =================

def generar_clima_aleatorio() -> str:
    """🌦️ Genera un clima aleatorio para la batalla"""
    climas = ["normal", "tormenta_ionica", "lluvia_meteoritos", "campo_gravitatorio", "viento_solar"]
    return random.choice(climas)

def obtener_todas_las_alianzas() -> list:
    """Obtiene todas las alianzas con su daño total y miembros activos"""
    datos = load_json(ALIANZA_DATOS_FILE) or {}
    
    alianzas = []
    for alianza_id, info in datos.items():
        num_miembros = len(obtener_miembros_alianza(alianza_id))
        daño_total = calcular_daño_total_alianza(alianza_id)
        
        alianzas.append({
            "id": alianza_id,
            "nombre": info.get("nombre", "Alianza sin nombre"),
            "etiqueta": info.get("etiqueta", alianza_id),
            "miembros_activos": num_miembros,
            "daño_total": daño_total
        })
    
    return alianzas

def seleccionar_rivales(alianza: dict) -> list:
    """
    Selecciona rivales dentro del rango configurado
    """
    config = obtener_configuracion_guerra()
    rango = config["rango_emparejamiento"]
    
    rango_min = alianza["daño_total"] * (1 - rango)
    rango_max = alianza["daño_total"] * (1 + rango)
    
    todas = obtener_todas_las_alianzas()
    
    rivales = [
        rival for rival in todas
        if rival["id"] != alianza["id"]
        and rival["miembros_activos"] >= config["minimo_miembros"]
        and rango_min <= rival["daño_total"] <= rango_max
    ]
    
    # Ordenar por cercanía de daño
    rivales.sort(key=lambda x: abs(x["daño_total"] - alianza["daño_total"]))
    
    return rivales[:4]  # Máximo 4 rivales para elegir

def iniciar_batalla(alianza_atacante: dict, alianza_defensora: dict) -> dict:
    """
    Inicia una nueva batalla entre dos alianzas
    """
    clima = generar_clima_aleatorio()
    config = obtener_configuracion_guerra()
    
    # Calcular fecha de fin
    fecha_fin = datetime.now() + timedelta(hours=config["duracion_horas"])
    
    batalla = {
        "id": f"war_{int(datetime.now().timestamp())}",
        "atacante_id": alianza_atacante["id"],
        "atacante_nombre": alianza_atacante["nombre"],
        "defensor_id": alianza_defensora["id"],
        "defensor_nombre": alianza_defensora["nombre"],
        "inicio": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "fin": fecha_fin.strftime("%Y-%m-%d %H:%M:%S"),
        "clima": clima,
        "asaltos": [],
        "resultado": None,
        "puntos_atacante": 0,
        "puntos_defensor": 0,
        "participantes_atacante": {},
        "participantes_defensor": {},
        "estado": "en_curso",
        "daño_atacante": alianza_atacante["daño_total"],
        "daño_defensor": alianza_defensora["daño_total"]
    }
    
    # Guardar batalla
    guerras = load_json(GUERRAS_FILE) or {}
    guerras[batalla["id"]] = batalla
    save_json(GUERRAS_FILE, guerras)
    
    return batalla

def obtener_batallas_alianza(alianza_id: str) -> list:
    """Obtiene todas las batallas de una alianza"""
    guerras = load_json(GUERRAS_FILE) or {}
    
    resultado = []
    for guerra_id, guerra in guerras.items():
        if guerra.get("atacante_id") == alianza_id or guerra.get("defensor_id") == alianza_id:
            resultado.append(guerra)
    
    # Ordenar por fecha (más recientes primero)
    resultado.sort(key=lambda x: x.get("inicio", ""), reverse=True)
    return resultado

# ================= HANDLERS DE GUERRA (TODOS VEN) =================

@requiere_login
async def menu_guerra(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """⚔️ Menú principal de guerra (visible para TODOS los miembros)"""
    query = update.callback_query
    if not query:
        return
    
    await query.answer()
    user_id = query.from_user.id
    username_tag = AuthSystem.obtener_username(user_id)
    
    # Obtener alianza del usuario
    alianza_id, alianza_datos = obtener_alianza_usuario(user_id)
    
    if not alianza_id:
        await query.edit_message_text(
            text=(
                f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
                f"⚔️ <b>GUERRA DE ALIANZAS</b> - {username_tag}\n"
                f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
                f"❌ No perteneces a ninguna alianza.\n\n"
                f"Únete o crea una alianza para participar en guerras."
            ),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🌍 IR A ALIANZAS", callback_data="menu_alianza")
            ]])
        )
        return
    
    # Verificar si el usuario es admin de alianza
    es_admin = es_admin_alianza(user_id, alianza_id)
    
    # Obtener datos
    mis_puntos = obtener_puntos_usuario(user_id)
    todos_puntos = obtener_todos_puntos_alianza(alianza_id)
    temporada = obtener_estado_temporada()
    batallas = obtener_batallas_alianza(alianza_id)
    batallas_activas = [b for b in batallas if b.get("estado") == "en_curso"]
    
    # Calcular totales
    total_puntos_alianza = sum(m["puntos"] for m in todos_puntos)
    mi_posicion = next((i+1 for i, m in enumerate(todos_puntos) if m["user_id"] == user_id), 0)
    
    # Construir mensaje
    texto = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"⚔️ <b>GUERRA DE ALIANZAS</b> - {username_tag}\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"🏰 <b>{alianza_datos.get('nombre', 'ALIANZA')}</b> [{alianza_id}]\n"
        f"👥 Miembros: {len(todos_puntos)}\n"
        f"💥 Daño total: {abreviar_numero(calcular_daño_total_alianza(alianza_id))}\n\n"
    )
    
    # Mostrar estado de temporada
    if temporada["activa"]:
        tiempo_restante = temporada["tiempo_restante"]
        if tiempo_restante:
            texto += f"⏳ <b>Temporada:</b> {temporada['nombre']}\n"
            texto += f"   ⏱️ Restante: {formatear_tiempo(tiempo_restante)}\n\n"
    else:
        texto += f"⏸️ <b>Sin temporada activa</b>\n\n"
    
    # Mostrar ranking de puntos (TODOS VEN TODO)
    texto += f"📊 <b>PUNTOS DE GUERRA</b>\n"
    texto += f"━━━━━━━━━━━━━━━━━━━\n"
    
    for i, miembro in enumerate(todos_puntos[:10], 1):
        medalla = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        texto += f"{medalla} {miembro['nombre']}: {abreviar_numero(miembro['puntos'])} pts"
        if miembro['user_id'] == user_id:
            texto += " ← TÚ"
        texto += "\n"
    
    if len(todos_puntos) > 10:
        texto += f"... y {len(todos_puntos) - 10} miembros más\n"
    
    texto += f"━━━━━━━━━━━━━━━━━━━\n"
    texto += f"📋 Total alianza: {abreviar_numero(total_puntos_alianza)} pts\n"
    texto += f"📍 Tu posición: #{mi_posicion}\n\n"
    
    # Mostrar batallas activas
    if batallas_activas:
        texto += f"⚔️ <b>BATALLAS ACTIVAS:</b>\n"
        for batalla in batallas_activas[:2]:
            es_atacante = batalla["atacante_id"] == alianza_id
            rival = batalla["defensor_nombre"] if es_atacante else batalla["atacante_nombre"]
            
            try:
                fecha_fin = datetime.fromisoformat(batalla["fin"])
                tiempo_restante = max(0, int((fecha_fin - datetime.now()).total_seconds()))
                texto += f"   vs {rival}: {formatear_tiempo(tiempo_restante)} restantes\n"
            except:
                texto += f"   vs {rival}\n"
        texto += "\n"
    
    texto += f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    
    # Botones para TODOS
    keyboard = [
        [InlineKeyboardButton("🚀 ENVIAR FLOTAS", callback_data="guerra_enviar_flotas")],
        [InlineKeyboardButton("📊 MIS PUNTOS", callback_data="guerra_mis_puntos")],
    ]
    
    # Botón de ranking global (para todos)
    keyboard.append([InlineKeyboardButton("🌍 RANKING GLOBAL", callback_data="guerra_ranking_global")])
    
    # Botones SOLO para admins de alianza
    if es_admin:
        admin_row = []
        if temporada["activa"]:
            admin_row.append(InlineKeyboardButton("⚔️ BUSCAR RIVAL", callback_data="guerra_buscar"))
        
        if admin_row:
            keyboard.append(admin_row)
        
        # Ver batallas activas (solo admins)
        if batallas_activas:
            keyboard.append([InlineKeyboardButton("📋 ADMIN GUERRA", callback_data="guerra_admin_panel")])
    
    keyboard.append([InlineKeyboardButton("◀️ VOLVER", callback_data="menu_alianza")])
    
    await query.edit_message_text(
        text=texto,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

@requiere_login
async def mis_puntos_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📊 Muestra los puntos detallados del usuario"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    username_tag = AuthSystem.obtener_username(user_id)
    
    puntos_data = obtener_puntos_usuario(user_id)
    temporada = obtener_estado_temporada()
    alianza_id, alianza_datos = obtener_alianza_usuario(user_id)
    
    texto = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"📊 <b>TUS PUNTOS DE GUERRA</b> - {username_tag}\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"🏆 <b>Puntos totales:</b> {abreviar_numero(puntos_data.get('puntos', 0))}\n"
        f"📅 <b>Temporada:</b> {temporada.get('nombre', 'Sin temporada')}\n\n"
    )
    
    # Mostrar naves enviadas
    naves_enviadas = puntos_data.get("naves_enviadas", {})
    if naves_enviadas:
        texto += f"🚀 <b>NAVES ENVIADAS:</b>\n"
        config_naves = obtener_config_naves()
        for nave, cantidad in naves_enviadas.items():
            icono = config_naves.get(nave, {}).get("icono", "🚀")
            nombre = config_naves.get(nave, {}).get("nombre", nave)
            texto += f"   {icono} {nombre}: {cantidad}\n"
        texto += "\n"
    
    # Mostrar historial reciente
    if puntos_data.get("historial"):
        texto += f"📋 <b>ÚLTIMAS ACTIVIDADES:</b>\n"
        for entry in puntos_data["historial"][-5:]:
            try:
                fecha = datetime.fromisoformat(entry["fecha"]).strftime("%d/%m %H:%M")
                texto += f"   • {fecha}: +{entry['puntos']} pts (Total: {entry['total_acumulado']})\n"
            except:
                pass
        texto += "\n"
    
    texto += f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    
    keyboard = [
        [InlineKeyboardButton("◀️ VOLVER", callback_data="menu_guerra")],
        [InlineKeyboardButton("🏠 MENÚ PRINCIPAL", callback_data="menu_principal")]
    ]
    
    await query.edit_message_text(
        text=texto,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

@requiere_login
async def ranking_global_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🌍 Muestra el ranking global de jugadores y alianzas"""
    query = update.callback_query
    await query.answer()
    
    ranking_jugadores = obtener_ranking_global()
    ranking_alianzas = obtener_ranking_alianzas()
    
    texto = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"🌍 <b>RANKING GLOBAL DE GUERRA</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
    )
    
    # Ranking de jugadores
    texto += f"🏆 <b>TOP 10 JUGADORES:</b>\n"
    texto += f"━━━━━━━━━━━━━━━━━━━\n"
    for i, jugador in enumerate(ranking_jugadores[:10], 1):
        medalla = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        texto += f"{medalla} {jugador['nombre']}: {abreviar_numero(jugador['puntos'])} pts\n"
        if i == 1:
            texto += f"   ⚔️ Alianza: {jugador['alianza']}\n"
    texto += "\n"
    
    # Ranking de alianzas
    texto += f"🏰 <b>TOP 10 ALIANZAS:</b>\n"
    texto += f"━━━━━━━━━━━━━━━━━━━\n"
    for i, alianza in enumerate(ranking_alianzas[:10], 1):
        medalla = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        texto += f"{medalla} {alianza['nombre']}: {abreviar_numero(alianza['puntos'])} pts\n"
    
    texto += f"\n🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    
    keyboard = [
        [InlineKeyboardButton("◀️ VOLVER", callback_data="menu_guerra")],
        [InlineKeyboardButton("🏠 MENÚ PRINCIPAL", callback_data="menu_principal")]
    ]
    
    await query.edit_message_text(
        text=texto,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

# ================= HANDLERS DE ENVÍO DE FLOTAS (TODOS VEN) =================

@requiere_login
async def enviar_flotas_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🚀 Menú para enviar flotas a la guerra"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    username_tag = AuthSystem.obtener_username(user_id)
    
    # Verificar temporada activa
    temporada = obtener_estado_temporada()
    if not temporada["activa"]:
        await query.edit_message_text(
            text=(
                f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
                f"🚀 <b>ENVIAR FLOTAS</b> - {username_tag}\n"
                f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
                f"❌ No hay una temporada de guerra activa.\n\n"
                f"Espera a que el administrador inicie una nueva temporada."
            ),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ VOLVER", callback_data="menu_guerra")
            ]])
        )
        return
    
    # Obtener flota del usuario
    flota_usuario = obtener_flota_usuario(user_id)
    config_naves = obtener_config_naves()
    mis_puntos = obtener_puntos_usuario(user_id)
    naves_en_guerra = mis_puntos.get("naves_enviadas", {})
    
    texto = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"🚀 <b>ENVIAR FLOTAS A LA GUERRA</b> - {username_tag}\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"📋 <b>TUS NAVES DISPONIBLES:</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
    )
    
    naves_disponibles = {}
    for nave_id, config in config_naves.items():
        cantidad = flota_usuario.get(nave_id, 0)
        en_guerra = naves_en_guerra.get(nave_id, 0)
        if cantidad > 0:
            naves_disponibles[nave_id] = {
                "cantidad": cantidad,
                "en_guerra": en_guerra,
                "nombre": config.get("nombre", nave_id),
                "icono": config.get("icono", "🚀"),
                "consumo": config.get("consumo", 20)
            }
            texto += f"{config.get('icono', '🚀')} <b>{config.get('nombre', nave_id)}</b>\n"
            texto += f"   ├ Disponibles: {cantidad}\n"
            texto += f"   └ En guerra: {en_guerra}\n"
    
    if not naves_disponibles:
        texto += "❌ No tienes naves disponibles para enviar.\n"
    
    texto += f"\n⚡ <b>Consumo por nave:</b>\n"
    for nave_id, info in naves_disponibles.items():
        texto += f"   {info['icono']} {info['nombre']}: {info['consumo']} deuterio\n"
    
    texto += f"\n🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
    texto += f"<i>Selecciona una nave para enviar:</i>"
    
    keyboard = []
    
    # Botones para cada tipo de nave
    for nave_id, info in naves_disponibles.items():
        if info["cantidad"] > 0:
            keyboard.append([
                InlineKeyboardButton(
                    f"{info['icono']} {info['nombre']} ({info['cantidad']} disp)",
                    callback_data=f"guerra_enviar_nave_{nave_id}"
                )
            ])
    
    keyboard.append([InlineKeyboardButton("◀️ CANCELAR", callback_data="menu_guerra")])
    
    await query.edit_message_text(
        text=texto,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

@requiere_login
async def seleccionar_nave_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🎯 Selecciona una nave para enviar"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    nave_id = query.data.replace("guerra_enviar_nave_", "")
    
    # Guardar nave en contexto
    context.user_data['nave_seleccionada'] = nave_id
    
    flota_usuario = obtener_flota_usuario(user_id)
    config_naves = obtener_config_naves()
    mis_puntos = obtener_puntos_usuario(user_id)
    naves_en_guerra = mis_puntos.get("naves_enviadas", {})
    
    cantidad_disponible = flota_usuario.get(nave_id, 0)
    en_guerra = naves_en_guerra.get(nave_id, 0)
    config = config_naves.get(nave_id, {"nombre": nave_id, "icono": "🚀", "consumo": 20})
    
    texto = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"🚀 <b>ENVIAR {config.get('icono', '🚀')} {config.get('nombre', nave_id)}</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"📊 <b>Disponibles:</b> {cantidad_disponible}\n"
        f"⚔️ <b>Ya en guerra:</b> {en_guerra}\n"
        f"⚡ <b>Consumo:</b> {config.get('consumo', 20)} deuterio por nave\n\n"
        f"<b>Escribe la cantidad que deseas enviar (1-{cantidad_disponible}):</b>\n\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    )
    
    keyboard = [[InlineKeyboardButton("◀️ CANCELAR", callback_data="guerra_enviar_flotas")]]
    
    await query.edit_message_text(
        text=texto,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )
    
    context.user_data['esperando_cantidad'] = True
    return SELECCIONANDO_CANTIDAD

async def recibir_cantidad_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📝 Recibe la cantidad de naves a enviar"""
    user_id = update.effective_user.id
    
    if not context.user_data.get('esperando_cantidad'):
        return ConversationHandler.END
    
    try:
        cantidad = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("❌ Por favor, ingresa un número válido.")
        return SELECCIONANDO_CANTIDAD
    
    nave_id = context.user_data.get('nave_seleccionada')
    if not nave_id:
        await update.message.reply_text("❌ Error: nave no seleccionada.")
        return ConversationHandler.END
    
    flota_usuario = obtener_flota_usuario(user_id)
    cantidad_disponible = flota_usuario.get(nave_id, 0)
    
    if cantidad <= 0 or cantidad > cantidad_disponible:
        await update.message.reply_text(f"❌ La cantidad debe ser entre 1 y {cantidad_disponible}.")
        return SELECCIONANDO_CANTIDAD
    
    # Crear diccionario de naves a enviar
    naves_enviar = {nave_id: cantidad}
    
    # Verificar recursos
    recursos_ok, mensaje = verificar_recursos_suficientes(user_id, naves_enviar)
    if not recursos_ok:
        await update.message.reply_text(mensaje)
        return SELECCIONANDO_CANTIDAD
    
    # Descontar recursos
    descontar_recursos(user_id, naves_enviar)
    
    # Registrar naves enviadas
    registrar_naves_enviadas(user_id, naves_enviar)
    
    config_naves = obtener_config_naves()
    config = config_naves.get(nave_id, {"nombre": nave_id, "icono": "🚀"})
    
    texto = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"✅ <b>NAVES ENVIADAS CORRECTAMENTE</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"{config.get('icono', '🚀')} <b>{config.get('nombre', nave_id)}:</b> {cantidad}\n"
        f"⚡ <b>Deuterio consumido:</b> {calcular_consumo_deuterio(naves_enviar)}\n\n"
        f"¡Buena suerte en la guerra, comandante!\n\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    )
    
    keyboard = [
        [InlineKeyboardButton("🚀 SEGUIR ENVIANDO", callback_data="guerra_enviar_flotas")],
        [InlineKeyboardButton("⚔️ VOLVER A GUERRA", callback_data="menu_guerra")]
    ]
    
    await update.message.reply_text(
        text=texto,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )
    
    # Limpiar contexto
    context.user_data.pop('esperando_cantidad', None)
    context.user_data.pop('nave_seleccionada', None)
    
    return ConversationHandler.END

# ================= HANDLERS DE ADMIN DE ALIANZA =================

@requiere_login
async def admin_guerra_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """⚙️ Panel de administración de guerra (solo admins de alianza)"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    alianza_id, alianza_datos = obtener_alianza_usuario(user_id)
    
    if not es_admin_alianza(user_id, alianza_id):
        await query.answer("❌ No tienes permisos de administrador", show_alert=True)
        return
    
    batallas = obtener_batallas_alianza(alianza_id)
    batallas_activas = [b for b in batallas if b.get("estado") == "en_curso"]
    todos_puntos = obtener_todos_puntos_alianza(alianza_id)
    
    texto = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"⚙️ <b>ADMINISTRACIÓN DE GUERRA</b> - {alianza_datos.get('nombre', 'ALIANZA')}\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"📊 <b>ESTADÍSTICAS:</b>\n"
        f"   ├ Miembros: {len(todos_puntos)}\n"
        f"   ├ Puntos totales: {abreviar_numero(sum(m['puntos'] for m in todos_puntos))}\n"
        f"   ├ Naves en guerra: {sum(m['naves_enviadas'] for m in todos_puntos)}\n"
        f"   └ Batallas activas: {len(batallas_activas)}\n\n"
    )
    
    if batallas_activas:
        texto += f"⚔️ <b>BATALLAS ACTIVAS:</b>\n"
        for batalla in batallas_activas:
            es_atacante = batalla["atacante_id"] == alianza_id
            rival = batalla["defensor_nombre"] if es_atacante else batalla["atacante_nombre"]
            try:
                fecha_fin = datetime.fromisoformat(batalla["fin"])
                tiempo = formatear_tiempo(max(0, int((fecha_fin - datetime.now()).total_seconds())))
                texto += f"   • vs {rival}: {tiempo} restantes\n"
            except:
                texto += f"   • vs {rival}\n"
        texto += "\n"
    
    texto += f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    
    keyboard = [
        [InlineKeyboardButton("⚔️ BUSCAR RIVAL", callback_data="guerra_buscar")],
        [InlineKeyboardButton("📋 REPORTE COMPLETO", callback_data="guerra_reporte")],
        [InlineKeyboardButton("◀️ VOLVER", callback_data="menu_guerra")]
    ]
    
    await query.edit_message_text(
        text=texto,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

@requiere_login
async def buscar_rival_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🔍 Busca rivales para la guerra (solo admins)"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    alianza_id, alianza_datos = obtener_alianza_usuario(user_id)
    
    if not es_admin_alianza(user_id, alianza_id):
        await query.answer("❌ No tienes permisos", show_alert=True)
        return
    
    # Verificar temporada activa
    temporada = obtener_estado_temporada()
    if not temporada["activa"]:
        await query.edit_message_text(
            text="❌ No hay una temporada de guerra activa.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ VOLVER", callback_data="menu_guerra")
            ]])
        )
        return
    
    # Calcular daño de la alianza actual
    daño_total = calcular_daño_total_alianza(alianza_id)
    miembros = obtener_miembros_alianza(alianza_id)
    num_miembros = len(miembros)
    
    alianza_actual = {
        "id": alianza_id,
        "nombre": alianza_datos.get("nombre", "Alianza"),
        "daño_total": daño_total,
        "miembros_activos": num_miembros
    }
    
    # Buscar rivales
    config = obtener_configuracion_guerra()
    rivales = seleccionar_rivales(alianza_actual)
    
    if not rivales:
        await query.edit_message_text(
            text=(
                f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
                f"⚔️ <b>BUSCAR RIVAL</b>\n"
                f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
                f"Tu alianza: {alianza_actual['nombre']}\n"
                f"Daño total: {abreviar_numero(daño_total)}\n\n"
                f"❌ No se encontraron rivales dentro del rango ±{config['rango_emparejamiento']*100}%.\n\n"
                f"Intenta más tarde cuando haya más alianzas disponibles."
            ),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ VOLVER", callback_data="menu_guerra")
            ]])
        )
        return
    
    # Guardar rivales en contexto
    context.user_data['rivales'] = rivales
    
    texto = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"⚔️ <b>SELECCIONAR RIVAL</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"Tu alianza: {alianza_actual['nombre']}\n"
        f"Daño total: {abreviar_numero(daño_total)}\n"
        f"Rango: ±{config['rango_emparejamiento']*100}%\n\n"
        f"Rivales encontrados ({len(rivales)}):\n\n"
    )
    
    keyboard = []
    for rival in rivales:
        diff = ((rival['daño_total'] / daño_total) - 1) * 100
        signo = "+" if diff > 0 else ""
        texto += f"🏰 <b>{rival['nombre']}</b> [{rival['etiqueta']}]\n"
        texto += f"   💥 Daño: {abreviar_numero(rival['daño_total'])} ({signo}{diff:.1f}%)\n"
        texto += f"   👥 Miembros: {rival['miembros_activos']}\n\n"
        
        keyboard.append([InlineKeyboardButton(
            f"⚔️ ATACAR {rival['nombre']}",
            callback_data=f"guerra_atacar_{rival['id']}"
        )])
    
    texto += f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    keyboard.append([InlineKeyboardButton("◀️ CANCELAR", callback_data="menu_guerra")])
    
    await query.edit_message_text(
        text=texto,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

@requiere_login
async def iniciar_guerra_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """⚔️ Inicia una guerra contra el rival seleccionado"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    rival_id = data.replace("guerra_atacar_", "")
    
    alianza_id, alianza_datos = obtener_alianza_usuario(user_id)
    
    if not es_admin_alianza(user_id, alianza_id):
        await query.answer("❌ No tienes permisos", show_alert=True)
        return ConversationHandler.END
    
    # Obtener datos del rival
    rivales = context.user_data.get('rivales', [])
    rival_data = None
    for r in rivales:
        if r["id"] == rival_id:
            rival_data = r
            break
    
    if not rival_data:
        await query.edit_message_text(
            text="❌ Rival no encontrado. Intenta buscar de nuevo.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ VOLVER", callback_data="menu_guerra")
            ]])
        )
        return ConversationHandler.END
    
    # Calcular daño de la alianza actual
    daño_atacante = calcular_daño_total_alianza(alianza_id)
    
    alianza_atacante = {
        "id": alianza_id,
        "nombre": alianza_datos.get("nombre", "Alianza"),
        "daño_total": daño_atacante
    }
    
    # Iniciar batalla
    batalla = iniciar_batalla(alianza_atacante, rival_data)
    
    # Guardar en contexto
    context.user_data['batalla_actual'] = batalla
    
    config = obtener_configuracion_guerra()
    
    texto = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"⚔️ <b>¡GUERRA INICIADA!</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"🏰 <b>{alianza_atacante['nombre']}</b>\n"
        f"   vs\n"
        f"🏰 <b>{rival_data['nombre']}</b>\n\n"
        f"📅 <b>Inicio:</b> {batalla['inicio']}\n"
        f"⏱️ <b>Duración:</b> {config['duracion_horas']} horas\n"
        f"⏱️ <b>Finaliza:</b> {batalla['fin'][:16]}\n\n"
        f"💥 <b>Daño:</b>\n"
        f"   • Tu alianza: {abreviar_numero(daño_atacante)}\n"
        f"   • Rival: {abreviar_numero(rival_data['daño_total'])}\n\n"
        f"🌦️ <b>Clima:</b> {batalla['clima']}\n\n"
        f"<i>Los miembros pueden enviar sus flotas durante las próximas {config['duracion_horas']} horas.</i>\n\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    )
    
    keyboard = [
        [InlineKeyboardButton("🚀 ENVIAR MIS FLOTAS", callback_data="guerra_enviar_flotas")],
        [InlineKeyboardButton("📋 ADMIN GUERRA", callback_data="guerra_admin_panel")],
        [InlineKeyboardButton("◀️ VOLVER", callback_data="menu_guerra")]
    ]
    
    await query.edit_message_text(
        text=texto,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )
    
    # Notificar a todos los miembros
    miembros = obtener_miembros_alianza(alianza_id)
    for uid_str in miembros.keys():
        try:
            await context.bot.send_message(
                chat_id=int(uid_str),
                text=(
                    f"⚔️ <b>¡GUERRA DECLARADA!</b>\n\n"
                    f"Tu alianza <b>{alianza_atacante['nombre']}</b> ha declarado la guerra a "
                    f"<b>{rival_data['nombre']}</b>.\n\n"
                    f"⏱️ Duración: {config['duracion_horas']} horas\n"
                    f"🚀 Envía tus flotas para apoyar a la alianza."
                ),
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🚀 ENVIAR FLOTAS", callback_data="guerra_enviar_flotas")
                ]])
            )
        except:
            pass
    
    return ConversationHandler.END

@requiere_login
async def reporte_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📋 Muestra reporte completo de la guerra"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    alianza_id, alianza_datos = obtener_alianza_usuario(user_id)
    
    if not es_admin_alianza(user_id, alianza_id):
        await query.answer("❌ No tienes permisos", show_alert=True)
        return
    
    todos_puntos = obtener_todos_puntos_alianza(alianza_id)
    batallas = obtener_batallas_alianza(alianza_id)
    
    texto = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"📋 <b>REPORTE DE GUERRA</b> - {alianza_datos.get('nombre', 'ALIANZA')}\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
    )
    
    # Naves por miembro
    texto += f"🚀 <b>NAVES EN GUERRA POR MIEMBRO:</b>\n"
    texto += f"━━━━━━━━━━━━━━━━━━━\n"
    config_naves = obtener_config_naves()
    
    for miembro in todos_puntos:
        if miembro["naves_enviadas"] > 0:
            texto += f"👤 {miembro['nombre']}: {miembro['naves_enviadas']} naves (⭐ {abreviar_numero(miembro['puntos'])} pts)\n"
            
            # Detalle de naves
            detalle = miembro.get("detalle_naves", {})
            for nave, cant in detalle.items():
                icono = config_naves.get(nave, {}).get("icono", "🚀")
                texto += f"   {icono} {nave}: {cant}\n"
    
    texto += f"\n⚔️ <b>HISTORIAL DE BATALLAS:</b>\n"
    texto += f"━━━━━━━━━━━━━━━━━━━\n"
    
    for batalla in batallas[:5]:
        es_atacante = batalla["atacante_id"] == alianza_id
        rival = batalla["defensor_nombre"] if es_atacante else batalla["atacante_nombre"]
        estado = "✅ Finalizada" if batalla["estado"] != "en_curso" else "⚔️ En curso"
        texto += f"• vs {rival}: {estado}\n"
    
    texto += f"\n🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    
    keyboard = [[InlineKeyboardButton("◀️ VOLVER", callback_data="guerra_admin_panel")]]
    
    await query.edit_message_text(
        text=texto,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

# ================= HANDLERS DE ADMIN GLOBAL (PANEL /ADMIN) =================

@requiere_admin
async def config_guerra_global_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """⚔️ Menú de configuración global de guerra (solo admin principal)"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if user_id != AuthSystem.ADMIN_USER_ID:  # Solo admin principal
        await query.answer("❌ Solo el admin principal puede acceder", show_alert=True)
        return
    
    temporada = obtener_estado_temporada()
    config = obtener_configuracion_guerra()
    ranking_jugadores = obtener_ranking_global()
    ranking_alianzas = obtener_ranking_alianzas()
    
    texto = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"⚔️ <b>CONFIGURACIÓN GLOBAL DE GUERRA</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"📅 <b>TEMPORADA ACTUAL</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
    )
    
    if temporada["activa"]:
        tiempo_restante = temporada["tiempo_restante"]
        texto += f"📌 Nombre: {temporada['nombre']}\n"
        texto += f"⏱️ Inicio: {temporada['fecha_inicio'][:16] if temporada['fecha_inicio'] else 'N/A'}\n"
        texto += f"⏱️ Fin: {temporada['fecha_fin'][:16] if temporada['fecha_fin'] else 'N/A'}\n"
        if tiempo_restante:
            texto += f"⏱️ Restante: {formatear_tiempo(tiempo_restante)}\n"
    else:
        texto += f"⏸️ No hay temporada activa\n"
    
    texto += f"\n⚙️ <b>CONFIGURACIÓN</b>\n"
    texto += f"━━━━━━━━━━━━━━━━━━━\n"
    texto += f"⏱️ Duración guerra: {config['duracion_horas']} horas\n"
    texto += f"🎯 Rango emparejamiento: ±{config['rango_emparejamiento']*100}%\n"
    texto += f"👥 Mínimo miembros: {config['minimo_miembros']}\n"
    texto += f"⚔️ Máx asaltos: {config['max_asaltos']}\n\n"
    
    texto += f"📊 <b>ESTADÍSTICAS GLOBALES</b>\n"
    texto += f"━━━━━━━━━━━━━━━━━━━\n"
    texto += f"🏆 Top jugador: {ranking_jugadores[0]['nombre'] if ranking_jugadores else 'N/A'} ({abreviar_numero(ranking_jugadores[0]['puntos'] if ranking_jugadores else 0)} pts)\n"
    texto += f"🏰 Top alianza: {ranking_alianzas[0]['nombre'] if ranking_alianzas else 'N/A'} ({abreviar_numero(ranking_alianzas[0]['puntos'] if ranking_alianzas else 0)} pts)\n"
    texto += f"👥 Jugadores activos: {len(ranking_jugadores)}\n"
    texto += f"🏰 Alianzas participantes: {len(ranking_alianzas)}\n\n"
    
    texto += f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    
    keyboard = []
    
    if not temporada["activa"]:
        keyboard.append([InlineKeyboardButton("🎬 INICIAR TEMPORADA", callback_data="admin_guerra_iniciar_temp")])
    else:
        keyboard.append([InlineKeyboardButton("🔚 CERRAR TEMPORADA", callback_data="admin_guerra_cerrar_temp")])
    
    keyboard.append([InlineKeyboardButton("📊 VER ESTADÍSTICAS", callback_data="admin_guerra_estadisticas")])
    keyboard.append([InlineKeyboardButton("⚙️ AJUSTES", callback_data="admin_guerra_ajustes")])
    keyboard.append([InlineKeyboardButton("◀️ VOLVER", callback_data="menu_admin")])
    
    await query.edit_message_text(
        text=texto,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

@requiere_admin
async def iniciar_temporada_global_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🎬 Inicia el proceso para crear nueva temporada global"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if user_id != AuthSystem.ADMIN_USER_ID:
        await query.answer("❌ Solo el admin principal", show_alert=True)
        return
    
    texto = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"🎬 <b>INICIAR NUEVA TEMPORADA GLOBAL</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"⚠️ <b>AL INICIAR NUEVA TEMPORADA:</b>\n"
        f"   • Todos los puntos de guerra se resetearán a 0\n"
        f"   • Las batallas activas continuarán\n"
        f"   • El historial anterior se guardará\n\n"
        f"📌 <b>Escribe el nombre de la temporada:</b>\n\n"
        f"<i>Ejemplo: 'Guerra de Invierno 2026'</i>\n\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    )
    
    keyboard = [[InlineKeyboardButton("❌ CANCELAR", callback_data="admin_guerra")]]
    
    await query.edit_message_text(
        text=texto,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )
    
    context.user_data['esperando_nombre_temporada_global'] = True
    return NOMBRE_TEMPORADA

async def recibir_nombre_temporada_global(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📝 Recibe el nombre de la temporada global y la inicia"""
    user_id = update.effective_user.id
    
    if not context.user_data.get('esperando_nombre_temporada_global'):
        return ConversationHandler.END
    
    if user_id != AuthSystem.ADMIN_USER_ID:
        await update.message.reply_text("❌ No autorizado")
        return ConversationHandler.END
    
    nombre = update.message.text.strip()
    
    if len(nombre) < 3 or len(nombre) > 50:
        await update.message.reply_text("❌ El nombre debe tener entre 3 y 50 caracteres.")
        return NOMBRE_TEMPORADA
    
    # Iniciar temporada
    exito = iniciar_temporada_global(nombre)
    
    if exito:
        config = obtener_configuracion_guerra()
        texto = (
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
            f"✅ <b>TEMPORADA INICIADA CORRECTAMENTE</b>\n"
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
            f"📅 <b>Nombre:</b> {nombre}\n"
            f"⏱️ <b>Duración:</b> {config['duracion_horas']} horas\n"
            f"📊 <b>Puntos reiniciados</b>\n\n"
            f"¡Que comience la guerra!\n\n"
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
        )
    else:
        texto = "❌ Error al iniciar la temporada"
    
    keyboard = [[InlineKeyboardButton("⚔️ IR A CONFIGURACIÓN", callback_data="admin_guerra")]]
    
    await update.message.reply_text(
        text=texto,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )
    
    context.user_data.pop('esperando_nombre_temporada_global', None)
    return ConversationHandler.END

@requiere_admin
async def cerrar_temporada_global_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🔚 Cierra la temporada actual"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if user_id != AuthSystem.ADMIN_USER_ID:
        await query.answer("❌ Solo el admin principal", show_alert=True)
        return
    
    resultado = cerrar_temporada_global()
    
    if resultado["exito"]:
        texto = (
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
            f"✅ <b>TEMPORADA CERRADA</b>\n"
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
            f"📅 <b>Temporada:</b> {resultado['historial']['nombre']}\n"
            f"📊 <b>Puntos totales:</b> {abreviar_numero(sum(u['puntos'] for u in resultado['historial']['usuarios'].values()))}\n"
            f"👥 <b>Participantes:</b> {len(resultado['historial']['usuarios'])}\n\n"
            f"✅ Historial guardado correctamente.\n\n"
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
        )
    else:
        texto = f"❌ {resultado['mensaje']}"
    
    keyboard = [[InlineKeyboardButton("◀️ VOLVER", callback_data="admin_guerra")]]
    
    await query.edit_message_text(
        text=texto,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

@requiere_admin
async def estadisticas_globales_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📊 Muestra estadísticas globales detalladas"""
    query = update.callback_query
    await query.answer()
    
    ranking_jugadores = obtener_ranking_global()
    ranking_alianzas = obtener_ranking_alianzas()
    temporada = obtener_estado_temporada()
    
    texto = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"📊 <b>ESTADÍSTICAS GLOBALES DE GUERRA</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"📅 <b>TEMPORADA ACTUAL:</b> {temporada['nombre'] if temporada['activa'] else 'Sin temporada'}\n\n"
    )
    
    # Top 10 jugadores
    texto += f"🏆 <b>TOP 10 JUGADORES:</b>\n"
    texto += f"━━━━━━━━━━━━━━━━━━━\n"
    for i, jugador in enumerate(ranking_jugadores[:10], 1):
        medalla = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        texto += f"{medalla} {jugador['nombre']}: {abreviar_numero(jugador['puntos'])} pts\n"
        texto += f"   ⚔️ Alianza: {jugador['alianza']}\n"
    texto += "\n"
    
    # Top 10 alianzas
    texto += f"🏰 <b>TOP 10 ALIANZAS:</b>\n"
    texto += f"━━━━━━━━━━━━━━━━━━━\n"
    for i, alianza in enumerate(ranking_alianzas[:10], 1):
        medalla = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        texto += f"{medalla} {alianza['nombre']}: {abreviar_numero(alianza['puntos'])} pts\n"
    
    texto += f"\n📊 <b>TOTALES:</b>\n"
    texto += f"━━━━━━━━━━━━━━━━━━━\n"
    texto += f"👥 Jugadores activos: {len(ranking_jugadores)}\n"
    texto += f"🏰 Alianzas participantes: {len(ranking_alianzas)}\n"
    texto += f"💥 Puntos totales: {abreviar_numero(sum(j['puntos'] for j in ranking_jugadores))}\n\n"
    
    texto += f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    
    keyboard = [[InlineKeyboardButton("◀️ VOLVER", callback_data="admin_guerra")]]
    
    await query.edit_message_text(
        text=texto,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

@requiere_admin
async def ajustes_guerra_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """⚙️ Ajustes de configuración de guerra"""
    query = update.callback_query
    await query.answer()
    
    config = obtener_configuracion_guerra()
    
    texto = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"⚙️ <b>AJUSTES DE GUERRA</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"Configuración actual:\n\n"
        f"⏱️ <b>Duración de guerra:</b> {config['duracion_horas']} horas\n"
        f"🎯 <b>Rango de emparejamiento:</b> ±{config['rango_emparejamiento']*100}%\n"
        f"👥 <b>Mínimo miembros:</b> {config['minimo_miembros']}\n"
        f"⚔️ <b>Máximo asaltos:</b> {config['max_asaltos']}\n\n"
        f"<i>Próximamente: edición de configuración</i>\n\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    )
    
    keyboard = [[InlineKeyboardButton("◀️ VOLVER", callback_data="admin_guerra")]]
    
    await query.edit_message_text(
        text=texto,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

# ================= CALLBACK HANDLER PRINCIPAL =================

async def guerra_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🎯 Manejador principal para todos los callbacks de guerra"""
    query = update.callback_query
    data = query.data
    
    # Menús principales
    if data == "menu_guerra":
        await menu_guerra(update, context)
    
    # Todos los miembros
    elif data == "guerra_mis_puntos":
        await mis_puntos_handler(update, context)
    elif data == "guerra_ranking_global":
        await ranking_global_handler(update, context)
    elif data == "guerra_enviar_flotas":
        return await enviar_flotas_menu(update, context)
    elif data.startswith("guerra_enviar_nave_"):
        return await seleccionar_nave_handler(update, context)
    
    # Admins de alianza
    elif data == "guerra_admin_panel":
        await admin_guerra_panel(update, context)
    elif data == "guerra_buscar":
        return await buscar_rival_handler(update, context)
    elif data.startswith("guerra_atacar_"):
        return await iniciar_guerra_handler(update, context)
    elif data == "guerra_reporte":
        await reporte_handler(update, context)
    
    # Admin global (panel /admin)
    elif data == "admin_guerra":
        await config_guerra_global_menu(update, context)
    elif data == "admin_guerra_iniciar_temp":
        return await iniciar_temporada_global_handler(update, context)
    elif data == "admin_guerra_cerrar_temp":
        await cerrar_temporada_global_handler(update, context)
    elif data == "admin_guerra_estadisticas":
        await estadisticas_globales_handler(update, context)
    elif data == "admin_guerra_ajustes":
        await ajustes_guerra_handler(update, context)
    
    return ConversationHandler.END

# ================= CONVERSATION HANDLERS =================

def obtener_conversation_handlers_guerra():
    """🔄 Retorna los ConversationHandlers para guerra"""
    
    # Handler para enviar flotas
    enviar_flotas_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(enviar_flotas_menu, pattern="^guerra_enviar_flotas$"),
            CallbackQueryHandler(seleccionar_nave_handler, pattern="^guerra_enviar_nave_")
        ],
        states={
            SELECCIONANDO_CANTIDAD: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_cantidad_handler)],
        },
        fallbacks=[CommandHandler("cancelar", lambda u,c: ConversationHandler.END)],
        name="guerra_enviar_flotas",
        persistent=False
    )
    
    # Handler para buscar rival
    buscar_rival_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(buscar_rival_handler, pattern="^guerra_buscar$")],
        states={
            # No hay estados adicionales, todo se maneja por callbacks
        },
        fallbacks=[CommandHandler("cancelar", lambda u,c: ConversationHandler.END)],
        name="guerra_buscar_rival",
        persistent=False
    )
    
    # Handler para iniciar guerra
    iniciar_guerra_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(iniciar_guerra_handler, pattern="^guerra_atacar_")],
        states={
            # No hay estados adicionales
        },
        fallbacks=[CommandHandler("cancelar", lambda u,c: ConversationHandler.END)],
        name="guerra_iniciar",
        persistent=False
    )
    
    # Handler para temporada global
    temporada_global_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(iniciar_temporada_global_handler, pattern="^admin_guerra_iniciar_temp$")],
        states={
            NOMBRE_TEMPORADA: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_nombre_temporada_global)],
        },
        fallbacks=[CommandHandler("cancelar", lambda u,c: ConversationHandler.END)],
        name="guerra_temporada_global",
        persistent=False
    )
    
    return [enviar_flotas_conv, buscar_rival_conv, iniciar_guerra_conv, temporada_global_conv]

# ================= EXPORTAR =================

__all__ = [
    'guerra_callback_handler',
    'obtener_conversation_handlers_guerra',
    'menu_guerra',
    'config_guerra_global_menu'
]

# Inicializar puntos de guerra al cargar el módulo
inicializar_puntos_guerra()
