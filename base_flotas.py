#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#██████╗ ███████╗████████╗██████╗  █████╗ ██╗     ███████╗
#██╔══██╗██╔════╝╚══██╔══╝██╔══██╗██╔══██╗██║     ██╔════╝
#██████╔╝███████╗   ██║   ██████╔╝███████║██║     ███████╗
#██╔══██╗╚════██║   ██║   ██╔══██╗██╔══██║██║     ╚════██║
#██║  ██║███████║   ██║   ██║  ██║██║  ██║███████╗███████║
#╚═╝  ╚═╝╚══════╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚══════╝

#🚀 ASTRO.IO v2.4.0 🚀
#✈️ base_flotas.py - SISTEMA DE FLOTAS Y MISIONES ESPACIALES
#============================================================
#✅ MISMO ESTILO que menú principal
#✅ Separadores con 🌀
#✅ Animaciones y barras de progreso mejoradas
#============================================================

import os
import json
import logging
import random
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from login import AuthSystem, requiere_login
from database import load_json, save_json
from utils import abreviar_numero
from recursos import actualizar_recursos_tiempo, guardar_recursos_usuario

logger = logging.getLogger(__name__)

# ================= CONSTANTES =================
DATA_DIR = "data"

# 🏠 BASE DE DATOS 1 - NAVES DISPONIBLES EN BASE
FLOTA_USUARIO_FILE = os.path.join(DATA_DIR, "flota_usuario.json")

# ✈️ BASE DE DATOS 2 - NAVES EN VUELO (MISIONES ACTIVAS)
MISIONES_FLOTA_FILE = os.path.join(DATA_DIR, "misiones_flota.json")

# 💀 BASE DE DATOS 3 - HISTORIAL DE BAJAS
BAJAS_FLOTA_FILE = os.path.join(DATA_DIR, "bajas_flota.json")

# 🌍 BASE DE DATOS DE COORDENADAS
GALAXIA_FILE = os.path.join(DATA_DIR, "galaxia.json")

# ================= CONFIGURACIÓN DE NAVES =================
# IMPORTAMOS LA CONFIGURACIÓN DESDE flota.py
try:
    from flota import CONFIG_NAVES
except ImportError:
    # Configuración de respaldo por si flota.py no existe
    CONFIG_NAVES = {
        "cazador_ligero": {
            "nombre": "Cazador Ligero",
            "icono": "🚀",
            "ataque": 50,
            "escudo": 10,
            "velocidad": 100,
            "consumo": 20,
            "capacidad": 5000
        },
        "cazador_pesado": {
            "nombre": "Cazador Pesado",
            "icono": "⚔️",
            "ataque": 150,
            "escudo": 25,
            "velocidad": 80,
            "consumo": 30,
            "capacidad": 10000
        },
        "crucero": {
            "nombre": "Crucero",
            "icono": "⚡",
            "ataque": 250,
            "escudo": 50,
            "velocidad": 90,
            "consumo": 35,
            "capacidad": 15000
        },
        "nave_batalla": {
            "nombre": "Nave de Batalla",
            "icono": "💥",
            "ataque": 1000,
            "escudo": 200,
            "velocidad": 70,
            "consumo": 150,
            "capacidad": 75000
        }
    }

# ================= PROBABILIDADES DE EVENTOS =================
PROBABILIDADES = {
    "explosion": 0.25,      # 25% - Todas las naves destruidas
    "ataque_pirata": 0.15,  # 15% - 50% naves destruidas
    "perdidos": 0.20,       # 20% - Sin botín, naves intactas
    "recursos": 0.20,       # 20% - Encuentran recursos (1k-5k)
    "escombros": 0.15,      # 15% - Encuentran naves (10-20)
    "materia_oscura": 0.05  # 5%  - Encuentran MO (50-250)
}

# ================= FUNCIONES DE LECTURA/ESCRITURA =================

def obtener_flota_base(user_id: int) -> dict:
    """🏠 Obtiene naves disponibles en base"""
    user_id_str = str(user_id)
    data = load_json(FLOTA_USUARIO_FILE) or {}
    return data.get(user_id_str, {})

def guardar_flota_base(user_id: int, flota: dict) -> bool:
    """💾 Guarda naves en base"""
    user_id_str = str(user_id)
    data = load_json(FLOTA_USUARIO_FILE) or {}
    data[user_id_str] = flota
    return save_json(FLOTA_USUARIO_FILE, data)

def obtener_misiones_activas(user_id: int = None) -> dict:
    """✈️ Obtiene misiones activas"""
    data = load_json(MISIONES_FLOTA_FILE) or {}
    if user_id:
        # Filtrar misiones donde el usuario es atacante o defensor
        misiones_usuario = {}
        for mid, mision in data.items():
            if mision.get("atacante") == user_id or mision.get("defensor") == user_id:
                misiones_usuario[mid] = mision
        return misiones_usuario
    return data

def guardar_mision(mision_id: str, mision_data: dict) -> bool:
    """💾 Guarda una misión"""
    data = load_json(MISIONES_FLOTA_FILE) or {}
    data[mision_id] = mision_data
    return save_json(MISIONES_FLOTA_FILE, data)

def eliminar_mision(mision_id: str) -> bool:
    """🗑️ Elimina una misión completada"""
    data = load_json(MISIONES_FLOTA_FILE) or {}
    if mision_id in data:
        del data[mision_id]
        return save_json(MISIONES_FLOTA_FILE, data)
    return True

def registrar_baja(user_id: int, mision_id: str, naves_perdidas: dict) -> bool:
    """💀 Registra naves destruidas en el historial"""
    user_id_str = str(user_id)
    data = load_json(BAJAS_FLOTA_FILE) or {}
    
    if user_id_str not in data:
        data[user_id_str] = []
    
    data[user_id_str].append({
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "mision_id": mision_id,
        "naves": naves_perdidas,
        "total": sum(naves_perdidas.values())
    })
    
    # Mantener solo últimas 50 bajas
    if len(data[user_id_str]) > 50:
        data[user_id_str] = data[user_id_str][-50:]
    
    return save_json(BAJAS_FLOTA_FILE, data)

def obtener_coordenadas(user_id: int) -> dict:
    """🌍 Obtiene coordenadas del jugador"""
    user_id_str = str(user_id)
    data = load_json(GALAXIA_FILE) or {}
    
    if user_id_str not in data:
        # Coordenadas por defecto
        data[user_id_str] = {
            "galaxia": 1,
            "sistema": 150,
            "planeta": 8,
            "nombre": "Planeta Principal"
        }
        save_json(GALAXIA_FILE, data)
    
    return data[user_id_str]

def actualizar_coordenadas(user_id: int, galaxia: int, sistema: int, planeta: int) -> bool:
    """💾 Actualiza coordenadas del jugador"""
    user_id_str = str(user_id)
    data = load_json(GALAXIA_FILE) or {}
    
    data[user_id_str] = {
        "galaxia": galaxia,
        "sistema": sistema,
        "planeta": planeta,
        "nombre": f"Planeta {galaxia}:{sistema}:{planeta}"
    }
    
    return save_json(GALAXIA_FILE, data)

# ================= FUNCIONES DE CÁLCULO =================

def calcular_distancia(origen: dict, destino: dict) -> int:
    """📏 Calcula distancia entre dos puntos"""
    dif_galaxia = abs(origen["galaxia"] - destino["galaxia"]) * 20000
    dif_sistema = abs(origen["sistema"] - destino["sistema"]) * 100
    dif_planeta = abs(origen["planeta"] - destino["planeta"]) * 5
    
    return dif_galaxia + dif_sistema + dif_planeta

def calcular_tiempo_vuelo(distancia: int, velocidad_base: int = 100) -> int:
    """⏱️ Calcula tiempo de vuelo en segundos"""
    tiempo = int(distancia * 0.1)  # 0.1 segundos por unidad de distancia
    return max(30, tiempo)  # Mínimo 30 segundos

def calcular_consumo_deuterio(distancia: int, naves: dict) -> int:
    """⚡ Calcula consumo de deuterio para la misión"""
    consumo_total = 0
    for nave, cantidad in naves.items():
        if nave in CONFIG_NAVES:
            consumo_base = CONFIG_NAVES[nave].get("consumo", 20)
            consumo_total += consumo_base * cantidad * (distancia / 1000)
    return int(consumo_total)

def calcular_poder_flota(naves: dict) -> dict:
    """⚔️ Calcula poder de ataque y escudo de una flota"""
    ataque = 0
    escudo = 0
    for nave, cantidad in naves.items():
        if nave in CONFIG_NAVES:
            ataque += CONFIG_NAVES[nave]["ataque"] * cantidad
            escudo += CONFIG_NAVES[nave]["escudo"] * cantidad
    return {"ataque": ataque, "escudo": escudo}

# ================= 🚀 ENVÍO DE MISIÓN =================

def enviar_mision(user_id: int, tipo: str, destino_id: int, naves: dict) -> tuple:
    """
    🚀 ENVÍA UNA MISIÓN - FLUJO COMPLETO
    1. ✅ Verificar naves disponibles en flota_usuario.json
    2. ✅ Verificar deuterio suficiente
    3. 💰 DESCONTAR deuterio de recursos.json
    4. 🏠 DESCONTAR naves de flota_usuario.json
    5. ✈️ AGREGAR naves a misiones_flota.json
    6. 📨 Enviar alerta al defensor (si es ataque)
    """
    user_id_str = str(user_id)
    destino_str = str(destino_id)
    
    # ========== 1. VERIFICAR NAVES DISPONIBLES ==========
    flota_base = obtener_flota_base(user_id)
    
    for nave, cantidad in naves.items():
        if flota_base.get(nave, 0) < cantidad:
            return False, f"❌ No tienes suficientes {nave}. Disponibles: {flota_base.get(nave, 0)}"
    
    # ========== 2. CALCULAR DISTANCIA Y CONSUMO ==========
    origen_coords = obtener_coordenadas(user_id)
    destino_coords = obtener_coordenadas(destino_id)
    
    distancia = calcular_distancia(origen_coords, destino_coords)
    tiempo_vuelo = calcular_tiempo_vuelo(distancia)
    consumo_deuterio = calcular_consumo_deuterio(distancia, naves)
    
    # ========== 3. VERIFICAR DEUTERIO ==========
    from recursos import obtener_recursos_usuario
    recursos = obtener_recursos_usuario(user_id)
    
    if recursos.get("deuterio", 0) < consumo_deuterio:
        return False, f"❌ No tienes suficiente deuterio. Necesitas: {abreviar_numero(consumo_deuterio)}"
    
    # ========== 4. 💰 DESCONTAR DEUTERIO ==========
    recursos["deuterio"] = recursos.get("deuterio", 0) - consumo_deuterio
    guardar_recursos_usuario(user_id, recursos)
    
    # ========== 5. 🏠 DESCONTAR NAVES DE BASE ==========
    for nave, cantidad in naves.items():
        flota_base[nave] = flota_base.get(nave, 0) - cantidad
    
    guardar_flota_base(user_id, flota_base)
    
    # ========== 6. ✈️ CREAR MISIÓN ==========
    ahora = datetime.now()
    fin = ahora + timedelta(seconds=tiempo_vuelo)
    mision_id = f"mision_{int(ahora.timestamp())}"
    
    mision_data = {
        "id": mision_id,
        "tipo": tipo,
        "atacante": user_id,
        "atacante_username": AuthSystem.obtener_username(user_id),
        "defensor": destino_id,
        "defensor_username": AuthSystem.obtener_username(destino_id),
        "origen": origen_coords,
        "destino": destino_coords,
        "naves": naves.copy(),
        "distancia": distancia,
        "tiempo_vuelo": tiempo_vuelo,
        "inicio": ahora.strftime("%Y-%m-%d %H:%M:%S"),
        "fin": fin.strftime("%Y-%m-%d %H:%M:%S"),
        "deuterio_consumido": consumo_deuterio,
        "estado": "en_vuelo",
        "alerta_enviada": False
    }
    
    guardar_mision(mision_id, mision_data)
    
    # ========== 7. LOG ==========
    username = AuthSystem.obtener_username(user_id)
    logger.info(f"🚀 {username} envió misión {tipo} a {destino_id} - {len(naves)} naves")
    
    return True, (mision_id, mision_data)

# ================= ⚔️ CÁLCULO DE BATALLA =================

def calcular_batalla(mision: dict) -> dict:
    """
    ⚔️ CALCULA EL RESULTADO DE UNA BATALLA
    Retorna: {
        "resultado": "victoria_atacante" | "victoria_defensor" | "empate",
        "bajas_atacante": {...},
        "bajas_defensor": {...},
        "supervivientes_atacante": {...},
        "supervivientes_defensor": {...},
        "botin": {"metal": 0, "cristal": 0, "deuterio": 0}
    }
    """
    naves_atacante = mision["naves"]
    
    # Obtener defensas y naves del defensor
    from defensa import obtener_defensas_usuario
    from flota import obtener_flota_usuario
    
    defensor_id = mision["defensor"]
    naves_defensor = obtener_flota_base(defensor_id)
    defensas = obtener_defensas_usuario(defensor_id)
    
    # Calcular poder
    poder_atacante = calcular_poder_flota(naves_atacante)["ataque"]
    poder_defensor = calcular_poder_flota(naves_defensor)["ataque"]
    poder_defensas = sum(defensas.values()) * 20  # 20 puntos de ataque por defensa
    
    poder_total_defensor = poder_defensor + poder_defensas
    diferencia = poder_atacante - poder_total_defensor
    
    # Determinar resultado
    if diferencia > 500:
        # Victoria aplastante del atacante
        bajas_atacante = 0.2  # 20% bajas
        bajas_defensor = 0.8  # 80% bajas
        botin_factor = 0.5    # 50% de los recursos
        resultado = "victoria_atacante"
    elif diferencia > 0:
        # Victoria del atacante
        bajas_atacante = 0.3  # 30% bajas
        bajas_defensor = 0.6  # 60% bajas
        botin_factor = 0.3    # 30% de los recursos
        resultado = "victoria_atacante"
    elif diferencia < -500:
        # Victoria aplastante del defensor
        bajas_atacante = 0.8  # 80% bajas
        bajas_defensor = 0.2  # 20% bajas
        botin_factor = 0      # 0% botín
        resultado = "victoria_defensor"
    elif diferencia < 0:
        # Victoria del defensor
        bajas_atacante = 0.6  # 60% bajas
        bajas_defensor = 0.3  # 30% bajas
        botin_factor = 0      # 0% botín
        resultado = "victoria_defensor"
    else:
        # Empate
        bajas_atacante = 0.5  # 50% bajas
        bajas_defensor = 0.5  # 50% bajas
        botin_factor = 0      # 0% botín
        resultado = "empate"
    
    # Calcular bajas
    bajas_atacante_dict = {}
    supervivientes_atacante_dict = {}
    
    for nave, cantidad in naves_atacante.items():
        bajas = int(cantidad * bajas_atacante)
        if bajas < 1 and cantidad > 0:
            bajas = 1  # Mínimo 1 baja si hay naves
        bajas = min(bajas, cantidad)
        bajas_atacante_dict[nave] = bajas
        supervivientes_atacante_dict[nave] = cantidad - bajas
    
    # Calcular bajas del defensor (naves)
    bajas_defensor_dict = {}
    supervivientes_defensor_dict = {}
    
    for nave, cantidad in naves_defensor.items():
        bajas = int(cantidad * bajas_defensor)
        if bajas < 1 and cantidad > 0:
            bajas = 1
        bajas = min(bajas, cantidad)
        bajas_defensor_dict[nave] = bajas
        supervivientes_defensor_dict[nave] = cantidad - bajas
    
    # Calcular botín
    from recursos import obtener_recursos_usuario
    recursos_defensor = obtener_recursos_usuario(defensor_id)
    
    botin = {}
    if botin_factor > 0:
        botin["metal"] = int(recursos_defensor.get("metal", 0) * botin_factor * 0.1)  # 10% de los recursos disponibles
        botin["cristal"] = int(recursos_defensor.get("cristal", 0) * botin_factor * 0.1)
        botin["deuterio"] = int(recursos_defensor.get("deuterio", 0) * botin_factor * 0.1)
    
    return {
        "resultado": resultado,
        "bajas_atacante": bajas_atacante_dict,
        "bajas_defensor": bajas_defensor_dict,
        "supervivientes_atacante": supervivientes_atacante_dict,
        "supervivientes_defensor": supervivientes_defensor_dict,
        "botin": botin,
        "poder_atacante": poder_atacante,
        "poder_defensor": poder_total_defensor
    }

# ================= ⏰ PROCESAR MISIONES COMPLETADAS =================

def procesar_misiones_completadas() -> list:
    """
    ⏰ PROCESA TODAS LAS MISIONES QUE HAN LLEGADO A SU DESTINO
    """
    misiones = load_json(MISIONES_FLOTA_FILE) or {}
    ahora = datetime.now()
    completadas = []
    
    for mision_id, mision in list(misiones.items()):
        try:
            fin = datetime.strptime(mision["fin"], "%Y-%m-%d %H:%M:%S")
            
            if ahora >= fin:
                if mision["tipo"] == "ataque":
                    # ⚔️ PROCESAR BATALLA
                    resultado = calcular_batalla(mision)
                    
                    # 💀 REGISTRAR BAJAS DEL ATACANTE
                    if resultado["bajas_atacante"]:
                        registrar_baja(
                            mision["atacante"],
                            mision_id,
                            resultado["bajas_atacante"]
                        )
                    
                    # 💀 REGISTRAR BAJAS DEL DEFENSOR
                    if resultado["bajas_defensor"]:
                        registrar_baja(
                            mision["defensor"],
                            mision_id,
                            resultado["bajas_defensor"]
                        )
                    
                    # ✨ DEVOLVER NAVES SUPERVIVIENTES AL ATACANTE
                    if resultado["supervivientes_atacante"]:
                        flota_atacante = obtener_flota_base(mision["atacante"])
                        for nave, cantidad in resultado["supervivientes_atacante"].items():
                            if cantidad > 0:
                                flota_atacante[nave] = flota_atacante.get(nave, 0) + cantidad
                        guardar_flota_base(mision["atacante"], flota_atacante)
                    
                    # ✨ DEVOLVER NAVES SUPERVIVIENTES AL DEFENSOR
                    if resultado["supervivientes_defensor"]:
                        flota_defensor = obtener_flota_base(mision["defensor"])
                        for nave, cantidad in resultado["supervivientes_defensor"].items():
                            if cantidad > 0:
                                flota_defensor[nave] = flota_defensor.get(nave, 0) + cantidad
                        guardar_flota_base(mision["defensor"], flota_defensor)
                    
                    # 💰 TRANSFERIR BOTÍN AL ATACANTE
                    if resultado["botin"] and resultado["resultado"].startswith("victoria_atacante"):
                        from recursos import obtener_recursos_usuario, guardar_recursos_usuario
                        recursos_atacante = obtener_recursos_usuario(mision["atacante"])
                        recursos_defensor = obtener_recursos_usuario(mision["defensor"])
                        
                        for recurso, cantidad in resultado["botin"].items():
                            if cantidad > 0:
                                recursos_atacante[recurso] = recursos_atacante.get(recurso, 0) + cantidad
                                recursos_defensor[recurso] = max(0, recursos_defensor.get(recurso, 0) - cantidad)
                        
                        guardar_recursos_usuario(mision["atacante"], recursos_atacante)
                        guardar_recursos_usuario(mision["defensor"], recursos_defensor)
                    
                    # 🗑️ ELIMINAR MISIÓN
                    eliminar_mision(mision_id)
                    completadas.append((mision_id, mision, resultado))
                
                elif mision["tipo"] == "expedicion":
                    # 🛰️ PROCESAR EXPEDICIÓN CON EVENTOS ALEATORIOS
                    resultado = procesar_expedicion(mision)
                    
                    # ✨ DEVOLVER NAVES SUPERVIVIENTES
                    if resultado["supervivientes"]:
                        flota_atacante = obtener_flota_base(mision["atacante"])
                        for nave, cantidad in resultado["supervivientes"].items():
                            if cantidad > 0:
                                flota_atacante[nave] = flota_atacante.get(nave, 0) + cantidad
                        guardar_flota_base(mision["atacante"], flota_atacante)
                    
                    # 💀 REGISTRAR BAJAS
                    if resultado["bajas"]:
                        registrar_baja(
                            mision["atacante"],
                            mision_id,
                            resultado["bajas"]
                        )
                    
                    # 💰 AÑADIR RECURSOS ENCONTRADOS
                    if resultado.get("recursos"):
                        from recursos import obtener_recursos_usuario, guardar_recursos_usuario
                        recursos = obtener_recursos_usuario(mision["atacante"])
                        for recurso, cantidad in resultado["recursos"].items():
                            recursos[recurso] = recursos.get(recurso, 0) + cantidad
                        guardar_recursos_usuario(mision["atacante"], recursos)
                    
                    # 🗑️ ELIMINAR MISIÓN
                    eliminar_mision(mision_id)
                    completadas.append((mision_id, mision, resultado))
        
        except Exception as e:
            logger.error(f"❌ Error procesando misión {mision_id}: {e}")
    
    return completadas

# ================= 🛰️ PROCESAR EXPEDICIÓN CON EVENTOS =================

def procesar_expedicion(mision: dict) -> dict:
    """
    🛰️ PROCESA UNA EXPEDICIÓN CON EVENTOS ALEATORIOS
    """
    naves = mision["naves"]
    total_naves = sum(naves.values())
    
    # SELECCIONAR EVENTO ALEATORIO
    rand = random.random()
    acumulado = 0
    
    for evento, prob in PROBABILIDADES.items():
        acumulado += prob
        if rand <= acumulado:
            break
    
    # ===== 1. 💥 EXPLOSIÓN DE MOTORES (25%) =====
    if evento == "explosion":
        return {
            "evento": "explosion",
            "nombre": "💥 Explosión de Motores",
            "bajas": naves.copy(),  # Todas las naves destruidas
            "supervivientes": {},
            "recursos": {},
            "mensaje": "💥 ¡EXPLOSIÓN DE MOTORES! Todas las naves fueron destruidas."
        }
    
    # ===== 2. 🛸 ATAQUE PIRATA (15%) =====
    elif evento == "ataque_pirata":
        bajas = {}
        supervivientes = {}
        for nave, cantidad in naves.items():
            perdidas = int(cantidad * 0.5)  # 50% destruidas
            if perdidas < 1 and cantidad > 0:
                perdidas = 1
            bajas[nave] = perdidas
            supervivientes[nave] = cantidad - perdidas
        
        return {
            "evento": "ataque_pirata",
            "nombre": "🛸 Ataque Pirata",
            "bajas": bajas,
            "supervivientes": supervivientes,
            "recursos": {},
            "mensaje": "🛸 ¡ATAQUE PIRATA! Perdiste el 50% de tu flota."
        }
    
    # ===== 3. 🧭 PERDIDOS EN EL ESPACIO (20%) =====
    elif evento == "perdidos":
        return {
            "evento": "perdidos",
            "nombre": "🧭 Perdidos en el Espacio",
            "bajas": {},
            "supervivientes": naves.copy(),  # Todas las naves intactas
            "recursos": {},
            "mensaje": "🧭 PERDIDOS EN EL ESPACIO. Las naves regresan sin botín."
        }
    
    # ===== 4. 💎 RECURSOS ENCONTRADOS (20%) =====
    elif evento == "recursos":
        metal = random.randint(1000, 5000)
        cristal = random.randint(1000, 5000)
        deuterio = random.randint(500, 2500)
        
        return {
            "evento": "recursos",
            "nombre": "💎 Recursos Encontrados",
            "bajas": {},
            "supervivientes": naves.copy(),  # Todas las naves intactas
            "recursos": {
                "metal": metal,
                "cristal": cristal,
                "deuterio": deuterio
            },
            "mensaje": f"💎 ¡RECURSOS ENCONTRADOS! +{abreviar_numero(metal)} Metal, +{abreviar_numero(cristal)} Cristal, +{abreviar_numero(deuterio)} Deuterio."
        }
    
    # ===== 5. ⚙️ ESCOMBROS DE BATALLA (15%) =====
    elif evento == "escombros":
        naves_recuperadas = {}
        num_naves = random.randint(10, 20)
        
        # Distribuir naves aleatoriamente
        for _ in range(num_naves):
            nave_aleatoria = random.choice(list(CONFIG_NAVES.keys()))
            naves_recuperadas[nave_aleatoria] = naves_recuperadas.get(nave_aleatoria, 0) + 1
        
        return {
            "evento": "escombros",
            "nombre": "⚙️ Escombros de Batalla",
            "bajas": {},
            "supervivientes": naves.copy(),  # Naves originales intactas
            "naves_recuperadas": naves_recuperadas,  # + naves encontradas
            "recursos": {},
            "mensaje": f"⚙️ ¡NAVES ABANDONADAS! Recuperaste {num_naves} naves."
        }
    
    # ===== 6. 🌑 MATERIA OSCURA (5%) =====
    elif evento == "materia_oscura":
        mo = random.randint(50, 250)
        
        return {
            "evento": "materia_oscura",
            "nombre": "🌑 Materia Oscura",
            "bajas": {},
            "supervivientes": naves.copy(),
            "recursos": {
                "materia_oscura": mo
            },
            "mensaje": f"🌑 ¡MATERIA OSCURA! Encontraste {mo} unidades."
        }
    
    # Fallback
    return {
        "evento": "perdidos",
        "nombre": "🧭 Perdidos en el Espacio",
        "bajas": {},
        "supervivientes": naves.copy(),
        "recursos": {},
        "mensaje": "🧭 Misión completada sin incidentes."
    }

# ================= 🎬 ANIMACIÓN DE VUELO =================

def generar_animacion_vuelo(progreso: float, ida: bool = True) -> str:
    """
    🎬 GENERA ANIMACIÓN DE VUELO
    progreso: 0.0 a 1.0
    ida: True = yendo, False = regresando
    """
    barra = 20  # caracteres
    pos = int(progreso * barra)
    
    if ida:  # YENDO (hacia la derecha)
        if pos >= barra - 1:
            return "🌍 " + "─" * barra + " 🚀 [DESTINO]"
        else:
            return "🌍 " + "─" * pos + "🚀" + "─" * (barra - pos - 1) + " 🌍"
    else:    # REGRESANDO (hacia la izquierda)
        if pos >= barra - 1:
            return "🚀 " + "─" * barra + " 🌍 [BASE]"
        else:
            return "🌍 " + "─" * (barra - pos - 1) + "🚀" + "─" * pos + " 🌍"

def generar_barra_progreso(progreso: float, ancho: int = 10) -> str:
    """📊 Genera barra de progreso visual [██░░]"""
    lleno = int(progreso * ancho)
    vacio = ancho - lleno
    return "[" + "█" * lleno + "░" * vacio + "]"

# ================= 📋 REPORTES =================

async def reporte_misiones_activas(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int = None):
    """✈️ Muestra todas las misiones activas del usuario"""
    if not user_id:
        user_id = update.effective_user.id
    
    username_tag = AuthSystem.obtener_username(user_id)
    misiones = obtener_misiones_activas(user_id)
    
    if not misiones:
        mensaje = (
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
            f"✈️ <b>FLOTAS EN VUELO</b> - {username_tag}\n"
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
            f"📭 No tienes misiones activas.\n\n"
            f"🚀 Usa 'Enviar Misión' para comenzar.\n\n"
            f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
        )
        
        keyboard = [[InlineKeyboardButton("🚀 ENVIAR MISIÓN", callback_data="flota_enviar")]]
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                text=mensaje,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="HTML"
            )
        return
    
    ahora = datetime.now()
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"✈️ <b>FLOTAS EN VUELO</b> - {username_tag}\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"📊 {len(misiones)} misiones activas\n\n"
    )
    
    for idx, (mision_id, mision) in enumerate(list(misiones.items())[:5], 1):
        fin = datetime.strptime(mision["fin"], "%Y-%m-%d %H:%M:%S")
        segundos_restantes = max(0, (fin - ahora).total_seconds())
        minutos = int(segundos_restantes // 60)
        segundos = int(segundos_restantes % 60)
        progreso = 1 - (segundos_restantes / mision["tiempo_vuelo"])
        
        # Determinar si es ida o regreso
        es_ida = mision.get("estado") == "en_vuelo"
        
        animacion = generar_animacion_vuelo(progreso, es_ida)
        barra = generar_barra_progreso(progreso)
        
        if mision["tipo"] == "ataque":
            icono = "⚔️"
            destino = f"@{mision['defensor_username']}"
        else:
            icono = "🛰️"
            destino = f"[{mision['destino']['galaxia']}:{mision['destino']['sistema']}:{mision['destino']['planeta']}]"
        
        mensaje += f"\n{idx}. {icono} <b>{mision['tipo'].upper()}</b>\n"
        mensaje += f"   <code>{animacion}</code>\n"
        mensaje += f"   ⏱️ {minutos:02d}:{segundos:02d} • {barra} {int(progreso*100)}%\n"
        mensaje += f"   🎯 Destino: {destino}\n"
        mensaje += f"   🚀 Naves: {sum(mision['naves'].values())}\n\n"
    
    mensaje += f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    
    keyboard = [
        [InlineKeyboardButton("🔄 REFRESCAR", callback_data="flota_misiones")],
        [InlineKeyboardButton("🚀 NUEVA MISIÓN", callback_data="flota_enviar")],
        [InlineKeyboardButton("❌ CANCELAR MISIÓN", callback_data="flota_cancelar")],
        [InlineKeyboardButton("◀️ VOLVER", callback_data="menu_flota")]
    ]
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text=mensaje,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )

async def reporte_historial_bajas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """💀 Muestra historial de naves perdidas"""
    user_id = update.effective_user.id
    username_tag = AuthSystem.obtener_username(user_id)
    
    data = load_json(BAJAS_FLOTA_FILE) or {}
    bajas_usuario = data.get(str(user_id), [])
    
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"💀 <b>HISTORIAL DE BAJAS</b> - {username_tag}\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
    )
    
    if not bajas_usuario:
        mensaje += "📭 No has perdido naves en combate.\n\n"
    else:
        total_bajas = sum(b["total"] for b in bajas_usuario)
        mensaje += f"📊 <b>TOTAL NAVES PERDIDAS:</b> {total_bajas}\n\n"
        
        for baja in bajas_usuario[-10:]:  # Últimas 10
            fecha = baja["fecha"][:16]
            mensaje += f"📅 <b>{fecha}</b>\n"
            for nave, cantidad in baja["naves"].items():
                if cantidad > 0:
                    icono = CONFIG_NAVES.get(nave, {}).get("icono", "🚀")
                    nombre = CONFIG_NAVES.get(nave, {}).get("nombre", nave)
                    mensaje += f"   {icono} {cantidad}x {nombre}\n"
            mensaje += "\n"
    
    mensaje += f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    
    keyboard = [
        [InlineKeyboardButton("◀️ VOLVER A FLOTA", callback_data="menu_flota")],
        [InlineKeyboardButton("🏠 MENÚ PRINCIPAL", callback_data="menu_principal")]
    ]
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text=mensaje,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )

# ================= 🤖 HANDLERS DE TELEGRAM =================

@requiere_login
async def menu_flota_principal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🚀 Menú principal de flota"""
    query = update.callback_query
    if not query:
        logger.error("❌ menu_flota_principal sin callback_query")
        return
    
    await query.answer()
    user_id = query.from_user.id
    username_tag = AuthSystem.obtener_username(user_id)
    
    # Procesar misiones completadas
    procesar_misiones_completadas()
    
    # Obtener datos
    from recursos import obtener_recursos_usuario
    recursos = obtener_recursos_usuario(user_id)
    flota_base = obtener_flota_base(user_id)
    misiones = obtener_misiones_activas(user_id)
    
    total_naves = sum(flota_base.values())
    
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"🚀 <b>COMANDO DE FLOTA</b> - {username_tag}\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"💰 <b>RECURSOS:</b>\n"
        f"🔩 Metal: {abreviar_numero(recursos.get('metal', 0))}\n"
        f"💎 Cristal: {abreviar_numero(recursos.get('cristal', 0))}\n"
        f"🧪 Deuterio: {abreviar_numero(recursos.get('deuterio', 0))}\n\n"
        f"📊 <b>FLOTA EN BASE:</b> {total_naves} naves\n"
        f"✈️ <b>MISIONES ACTIVAS:</b> {len(misiones)}\n\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    )
    
    keyboard = [
        [InlineKeyboardButton("🚀 ENVIAR MISIÓN", callback_data="flota_enviar")],
        [InlineKeyboardButton("✈️ FLOTAS EN VUELO", callback_data="flota_misiones")],
        [InlineKeyboardButton("📊 ESTADÍSTICAS", callback_data="flota_estadisticas")],
        [InlineKeyboardButton("💀 HISTORIAL DE BAJAS", callback_data="flota_bajas")],
        [InlineKeyboardButton("🏠 MENÚ PRINCIPAL", callback_data="menu_principal")]
    ]
    
    await query.edit_message_text(
        text=mensaje,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

# ================= EXPORTAR =================

__all__ = [
    'menu_flota_principal',
    'reporte_misiones_activas',
    'reporte_historial_bajas',
    'enviar_mision',
    'procesar_misiones_completadas',
    'obtener_flota_base',
    'obtener_misiones_activas'
]
