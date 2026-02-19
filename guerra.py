#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#⚔️ guerra.py - SISTEMA DE GUERRA DE ALIANZAS
#===================================================
#✅ Menú principal con botón de entrada
#✅ Selección automática de rivales por rango ±5% de daño
#✅ Validación de miembros activos (mínimo 3)
#✅ Batalla por asaltos con daño fijo de armas
#✅ Tecnología máxima de la alianza aplicada globalmente
#✅ Clima aleatorio que afecta coeficientes
#✅ PUNTOS POR FLOTAS DESTRUIDAS - Cada nave destruida otorga sus puntos de flota
#✅ Persistencia en JSON
#✅ Notificaciones a todos los miembros
#===================================================

import os
import json
import logging
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, ConversationHandler

from login import AuthSystem, requiere_login
from database import load_json, save_json
from utils import abreviar_numero

logger = logging.getLogger(__name__)

# ================= CONSTANTES =================
DATA_DIR = "data"
ALIANZA_DATOS_FILE = os.path.join(DATA_DIR, "alianza_datos.json")
ALIANZA_MIEMBROS_FILE = os.path.join(DATA_DIR, "alianza_miembros.json")
ALIANZA_BANCO_FILE = os.path.join(DATA_DIR, "alianza_banco.json")
GUERRAS_FILE = os.path.join(DATA_DIR, "guerras.json")
HISTORIAL_GUERRAS_FILE = os.path.join(DATA_DIR, "historial_guerras.json")
RECURSOS_FILE = os.path.join(DATA_DIR, "recursos.json")
INVESTIGACIONES_USUARIO_FILE = os.path.join(DATA_DIR, "investigaciones_usuario.json")
FLOTA_USUARIO_FILE = os.path.join(DATA_DIR, "flota_usuario.json")
DEFENSA_USUARIO_FILE = os.path.join(DATA_DIR, "defensa_usuario.json")
PUNTUACION_FILE = os.path.join(DATA_DIR, "puntuacion.json")

# Estados para ConversationHandler
SELECCIONANDO_RIVAL, EN_BATALLA = range(2)

# ================= CONFIGURACIÓN DE ARMAS Y TECNOLOGÍAS =================

CONFIG_GUERRA = {
  "versión": "1.0.0",
  "fecha_actualización": "2026-02-18",
  
  "armas": {
    "misil_basico": {
      "nombre": "Misil Básico",
      "icono": "🚀",
      "descripción": "Proyectil de rastreo térmico. Efecto balanceado contra todo tipo de blindaje.",
      "daño_base": 10,
      "coeficientes": {
        "escudo": 1.0,
        "blindaje": 1.0,
        "casco": 1.0
      },
      "tecnología_requerida": "propulsion_basica",
      "nivel_requerido": 1,
      "consumo_energia": 5,
      "cadencia": 1.0
    },
    "misil_mejorado": {
      "nombre": "Misil Mejorado",
      "icono": "🚀✨",
      "descripción": "Sistema de guiado mejorado. Mayor precisión contra todo tipo de objetivos.",
      "daño_base": 15,
      "coeficientes": {
        "escudo": 1.2,
        "blindaje": 1.2,
        "casco": 1.2
      },
      "tecnología_requerida": "propulsion_mejorada",
      "nivel_requerido": 5,
      "consumo_energia": 8,
      "cadencia": 1.0
    },
    "laser_basico": {
      "nombre": "Láser Básico",
      "icono": "⚡",
      "descripción": "Rayo de energía continua. Penetra blindaje pero es menos efectivo contra escudos.",
      "daño_base": 10,
      "coeficientes": {
        "escudo": 0.5,
        "blindaje": 2.0,
        "casco": 1.0
      },
      "tecnología_requerida": "tecnologia_laser",
      "nivel_requerido": 1,
      "consumo_energia": 8,
      "cadencia": 0.8
    },
    "laser_pesado": {
      "nombre": "Láser Pesado",
      "icono": "⚡🔫",
      "descripción": "Cañón láser de alta potencia. Devastador contra blindaje pesado.",
      "daño_base": 20,
      "coeficientes": {
        "escudo": 0.3,
        "blindaje": 2.5,
        "casco": 1.2
      },
      "tecnología_requerida": "tecnologia_laser",
      "nivel_requerido": 8,
      "consumo_energia": 15,
      "cadencia": 0.6
    },
    "balistico_basico": {
      "nombre": "Cañón Balístico",
      "icono": "💥",
      "descripción": "Proyectil de alto calibre. Ideal para destruir escudos.",
      "daño_base": 10,
      "coeficientes": {
        "escudo": 2.0,
        "blindaje": 0.5,
        "casco": 1.0
      },
      "tecnología_requerida": "tecnologia_balistica",
      "nivel_requerido": 1,
      "consumo_energia": 6,
      "cadencia": 0.7
    },
    "balistico_perforante": {
      "nombre": "Cañón Perforante",
      "icono": "💥🔨",
      "descripción": "Munición de núcleo duro. Atraviesa escudos y blindaje.",
      "daño_base": 15,
      "coeficientes": {
        "escudo": 1.5,
        "blindaje": 1.5,
        "casco": 1.0
      },
      "tecnología_requerida": "tecnologia_balistica",
      "nivel_requerido": 6,
      "consumo_energia": 10,
      "cadencia": 0.5
    },
    "ionico": {
      "nombre": "Cañón Iónico",
      "icono": "⚡🌀",
      "descripción": "Descarga de iones. Neutraliza escudos electrónicamente.",
      "daño_base": 8,
      "coeficientes": {
        "escudo": 3.0,
        "blindaje": 0.2,
        "casco": 0.5
      },
      "tecnología_requerida": "tecnologia_iones",
      "nivel_requerido": 4,
      "consumo_energia": 12,
      "cadencia": 0.4
    },
    "plasma": {
      "nombre": "Cañón de Plasma",
      "icono": "☢️",
      "descripción": "Proyectil de plasma supercaliente. Daño masivo contra todo.",
      "daño_base": 25,
      "coeficientes": {
        "escudo": 1.5,
        "blindaje": 1.5,
        "casco": 2.0
      },
      "tecnología_requerida": "tecnologia_plasma",
      "nivel_requerido": 10,
      "consumo_energia": 25,
      "cadencia": 0.3
    }
  },

  "tecnologías": {
    "propulsion_basica": {
      "nombre": "Propulsión Básica",
      "icono": "🚀",
      "descripción": "Tecnología fundamental de motores.",
      "nivel_maximo": 10,
      "bonificaciones": {
        "velocidad": "2% por nivel",
        "evasión": "1% por nivel"
      }
    },
    "propulsion_mejorada": {
      "nombre": "Propulsión Mejorada",
      "icono": "🚀✨",
      "descripción": "Sistemas de propulsión avanzados.",
      "requisitos": {"propulsion_basica": 5},
      "nivel_maximo": 10,
      "bonificaciones": {
        "velocidad": "3% por nivel",
        "evasión": "2% por nivel"
      }
    },
    "tecnologia_laser": {
      "nombre": "Tecnología Láser",
      "icono": "⚡",
      "descripción": "Investigación en armas de energía dirigida.",
      "nivel_maximo": 10,
      "bonificaciones": {
        "daño_laser": "5% por nivel",
        "penetración_blindaje": "3% por nivel"
      }
    },
    "tecnologia_balistica": {
      "nombre": "Tecnología Balística",
      "icono": "💥",
      "descripción": "Mejora en proyectiles cinéticos.",
      "nivel_maximo": 10,
      "bonificaciones": {
        "daño_balistico": "5% por nivel",
        "penetración_escudo": "3% por nivel"
      }
    },
    "tecnologia_iones": {
      "nombre": "Tecnología Iónica",
      "icono": "⚡🌀",
      "descripción": "Armas que afectan sistemas electrónicos.",
      "requisitos": {"tecnologia_laser": 3, "tecnologia_energia": 4},
      "nivel_maximo": 8,
      "bonificaciones": {
        "daño_ionico": "7% por nivel",
        "desactivación_escudos": "2% por nivel"
      }
    },
    "tecnologia_plasma": {
      "nombre": "Tecnología de Plasma",
      "icono": "☢️",
      "descripción": "La cúspide de la tecnología de armas.",
      "requisitos": {"tecnologia_laser": 8, "tecnologia_balistica": 6, "tecnologia_iones": 5},
      "nivel_maximo": 5,
      "bonificaciones": {
        "daño_plasma": "10% por nivel",
        "daño_critico": "5% por nivel"
      }
    },
    "tecnologia_energia": {
      "nombre": "Tecnología Energética",
      "icono": "🔋",
      "descripción": "Optimización de sistemas de energía.",
      "nivel_maximo": 15,
      "bonificaciones": {
        "produccion_energia": "5% por nivel",
        "eficiencia_armas": "3% por nivel"
      }
    },
    "tecnologia_escudos": {
      "nombre": "Tecnología de Escudos",
      "icono": "🛡️",
      "descripción": "Mejora en generadores de escudos.",
      "requisitos": {"tecnologia_energia": 5},
      "nivel_maximo": 12,
      "bonificaciones": {
        "resistencia_escudo": "6% por nivel",
        "recarga_escudo": "4% por nivel"
      }
    },
    "tecnologia_blindaje": {
      "nombre": "Tecnología de Blindaje",
      "icono": "🧱",
      "descripción": "Aleaciones y materiales compuestos.",
      "requisitos": {"tecnologia_energia": 3},
      "nivel_maximo": 12,
      "bonificaciones": {
        "resistencia_blindaje": "5% por nivel",
        "integridad_casco": "3% por nivel"
      }
    }
  },

  "climas_batalla": {
    "normal": {
      "nombre": "Clima Normal",
      "icono": "☀️",
      "coeficientes": {
        "misil": 1.0,
        "laser": 1.0,
        "balistico": 1.0,
        "ionico": 1.0,
        "plasma": 1.0
      }
    },
    "tormenta_ionica": {
      "nombre": "Tormenta Iónica",
      "icono": "⚡🌩️",
      "coeficientes": {
        "misil": 0.7,
        "laser": 1.3,
        "balistico": 0.8,
        "ionico": 1.5,
        "plasma": 0.9
      }
    },
    "lluvia_meteoritos": {
      "nombre": "Lluvia de Meteoritos",
      "icono": "💫🌠",
      "coeficientes": {
        "misil": 1.2,
        "laser": 0.8,
        "balistico": 1.4,
        "ionico": 0.6,
        "plasma": 0.7
      }
    },
    "campo_gravitatorio": {
      "nombre": "Campo Gravitatorio",
      "icono": "🌀🌌",
      "coeficientes": {
        "misil": 1.1,
        "laser": 0.9,
        "balistico": 1.3,
        "ionico": 0.8,
        "plasma": 1.2
      }
    },
    "viento_solar": {
      "nombre": "Viento Solar",
      "icono": "☀️💨",
      "coeficientes": {
        "misil": 0.9,
        "laser": 1.2,
        "balistico": 0.8,
        "ionico": 1.1,
        "plasma": 1.3
      }
    }
  },

  "posiciones_naves": {
    "vanguardia": {
      "nombre": "Vanguardia",
      "icono": "⚔️",
      "probabilidad_ataque": 0.4,
      "probabilidad_defensa": 0.3,
      "descripción": "Primera línea de ataque. Mayor daño, menor defensa."
    },
    "centro": {
      "nombre": "Centro",
      "icono": "🎯",
      "probabilidad_ataque": 0.35,
      "probabilidad_defensa": 0.35,
      "descripción": "Equilibrio entre ataque y defensa."
    },
    "retaguardia": {
      "nombre": "Retaguardia",
      "icono": "🛡️",
      "probabilidad_ataque": 0.25,
      "probabilidad_defensa": 0.4,
      "descripción": "Última línea de defensa. Mayor protección."
    }
  },

  "pesos_puntuacion": {
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
  },

  "reglas_batalla": {
    "duracion_maxima_asaltos": 10,
    "minimo_miembros_alianza": 3,
    "rango_emparejamiento": 0.05,
    "factor_supervivencia": {
      "vanguardia": 0.7,
      "centro": 0.8,
      "retaguardia": 0.9
    }
  }
}

# ================= FUNCIONES AUXILIARES DE ALIANZA =================

def obtener_alianza_usuario(user_id: int) -> tuple:
    """Obtiene la alianza de un usuario"""
    user_id_str = str(user_id)
    miembros_data = load_json(ALIANZA_MIEMBROS_FILE) or {}
    
    for alianza_id, miembros in miembros_data.items():
        if user_id_str in miembros:
            datos = load_json(ALIANZA_DATOS_FILE) or {}
            return alianza_id, datos.get(alianza_id, {})
    
    return None, None

def obtener_miembros_alianza(alianza_id: str) -> dict:
    """Obtiene los miembros de una alianza"""
    miembros_data = load_json(ALIANZA_MIEMBROS_FILE) or {}
    return miembros_data.get(alianza_id, {})

def es_admin_alianza(user_id: int, alianza_id: str) -> bool:
    """Verifica si el usuario es admin de la alianza"""
    from alianza import es_admin_alianza
    return es_admin_alianza(user_id, alianza_id)

# ================= FUNCIONES DE TECNOLOGÍA =================

def obtener_nivel_maximo_tecnologia_alianza(alianza_id: str, tecnologia: str) -> int:
    """
    Obtiene el nivel MÁXIMO de una tecnología entre todos los miembros de la alianza.
    En guerra de alianzas, se aplica el nivel más alto de cualquier miembro.
    """
    miembros = obtener_miembros_alianza(alianza_id)
    nivel_maximo = 0
    
    investigaciones_data = load_json(INVESTIGACIONES_USUARIO_FILE) or {}
    
    for uid_str in miembros.keys():
        user_id = int(uid_str)
        user_invest = investigaciones_data.get(str(user_id), {})
        nivel = user_invest.get(tecnologia, 0)
        if nivel > nivel_maximo:
            nivel_maximo = nivel
    
    return nivel_maximo

def obtener_tecnologias_alianza(alianza_id: str) -> dict:
    """Obtiene todas las tecnologías de la alianza (nivel máximo por cada una)"""
    miembros = obtener_miembros_alianza(alianza_id)
    tecnologias = {}
    
    investigaciones_data = load_json(INVESTIGACIONES_USUARIO_FILE) or {}
    
    for tecnologia in CONFIG_GUERRA["tecnologías"].keys():
        nivel_maximo = 0
        for uid_str in miembros.keys():
            user_id = int(uid_str)
            user_invest = investigaciones_data.get(str(user_id), {})
            nivel = user_invest.get(tecnologia, 0)
            if nivel > nivel_maximo:
                nivel_maximo = nivel
        if nivel_maximo > 0:
            tecnologias[tecnologia] = nivel_maximo
    
    return tecnologias

# ================= FUNCIONES DE PUNTUACIÓN DE NAVES =================

def obtener_puntos_nave(nave_id: str) -> int:
    """Obtiene los puntos de una nave según la configuración"""
    return CONFIG_GUERRA["pesos_puntuacion"].get(nave_id, 10)

def calcular_puntos_flota(flota: dict) -> int:
    """Calcula los puntos totales de una flota"""
    total = 0
    for posicion, naves in flota.items():
        for nave_id, data in naves.items():
            cantidad = data["cantidad"]
            puntos = obtener_puntos_nave(nave_id)
            total += puntos * cantidad
    return total

# ================= FUNCIONES DE FLOTA =================

def obtener_flota_alianza(alianza_id: str) -> dict:
    """
    Obtiene todas las naves de todos los miembros de la alianza,
    agrupadas por tipo y posición.
    """
    miembros = obtener_miembros_alianza(alianza_id)
    flota_alianza = {
        "vanguardia": {},
        "centro": {},
        "retaguardia": {}
    }
    
    flota_data = load_json(FLOTA_USUARIO_FILE) or {}
    
    from flota import CONFIG_NAVES
    
    for uid_str in miembros.keys():
        user_id = int(uid_str)
        user_flota = flota_data.get(str(user_id), {})
        
        for nave_id, cantidad in user_flota.items():
            if nave_id in CONFIG_NAVES and cantidad > 0:
                config = CONFIG_NAVES[nave_id]
                # Determinar posición (por defecto centro)
                posicion = config.get("posicion", "centro")
                if posicion not in flota_alianza:
                    posicion = "centro"
                
                if nave_id not in flota_alianza[posicion]:
                    flota_alianza[posicion][nave_id] = {
                        "cantidad": 0,
                        "nombre": config.get("nombre", nave_id),
                        "icono": config.get("icono", "🚀"),
                        "arma": config.get("arma", "misil_basico"),
                        "puntos": obtener_puntos_nave(nave_id),
                        "escudo_base": config.get("escudo", 10),
                        "blindaje_base": config.get("blindaje", 20),
                        "casco_base": config.get("casco", 30)
                    }
                flota_alianza[posicion][nave_id]["cantidad"] += cantidad
    
    return flota_alianza

# ================= FUNCIONES DE DAÑO =================

def calcular_daño_total_alianza(alianza_id: str) -> int:
    """
    Calcula el daño total de la alianza sumando el daño fijo de todas las naves.
    """
    flota = obtener_flota_alianza(alianza_id)
    daño_total = 0
    
    for posicion, naves in flota.items():
        for nave_id, data in naves.items():
            cantidad = data["cantidad"]
            arma_id = data["arma"]
            
            if arma_id in CONFIG_GUERRA["armas"]:
                arma = CONFIG_GUERRA["armas"][arma_id]
                daño_total += arma["daño_base"] * cantidad
    
    return daño_total

def calcular_daño_arma_con_tecnologia(arma_id: str, nivel_tecnologia: int, clima: str = "normal") -> dict:
    """
    Calcula el daño de un arma considerando:
    - Nivel de tecnología de la alianza (máximo)
    - Clima de la batalla
    """
    if arma_id not in CONFIG_GUERRA["armas"]:
        return {"error": "Arma no encontrada"}
    
    arma = CONFIG_GUERRA["armas"][arma_id]
    clima_config = CONFIG_GUERRA["climas_batalla"].get(clima, CONFIG_GUERRA["climas_batalla"]["normal"])
    
    # Determinar tipo de arma para coeficiente de clima
    tipo_arma = arma_id.split('_')[0]  # misil, laser, balistico, ionico, plasma
    if tipo_arma not in clima_config["coeficientes"]:
        tipo_arma = "misil"  # default
    
    coeficiente_clima = clima_config["coeficientes"][tipo_arma]
    
    # Bonificación por tecnología (5% por nivel)
    bonificacion_tecnologia = 1.0 + (nivel_tecnologia * 0.05)
    
    return {
        "daño_base": arma["daño_base"],
        "coeficientes": arma["coeficientes"],
        "daño_contra_escudo": int(arma["daño_base"] * arma["coeficientes"]["escudo"] * coeficiente_clima * bonificacion_tecnologia),
        "daño_contra_blindaje": int(arma["daño_base"] * arma["coeficientes"]["blindaje"] * coeficiente_clima * bonificacion_tecnologia),
        "daño_contra_casco": int(arma["daño_base"] * arma["coeficientes"]["casco"] * coeficiente_clima * bonificacion_tecnologia),
        "consumo_energia": arma["consumo_energia"],
        "cadencia": arma["cadencia"],
        "icono": arma["icono"],
        "nombre": arma["nombre"]
    }

def generar_clima_aleatorio() -> str:
    """Genera un clima aleatorio para la batalla"""
    climas = list(CONFIG_GUERRA["climas_batalla"].keys())
    return random.choice(climas)

# ================= FUNCIONES DE SELECCIÓN DE RIVALES =================

def obtener_todas_las_alianzas() -> list:
    """Obtiene todas las alianzas con su daño total y miembros activos"""
    datos = load_json(ALIANZA_DATOS_FILE) or {}
    miembros = load_json(ALIANZA_MIEMBROS_FILE) or {}
    
    alianzas = []
    for alianza_id, info in datos.items():
        num_miembros = len(miembros.get(alianza_id, {}))
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
    Selecciona rivales dentro del rango ±5% de daño total
    """
    rango_min = alianza["daño_total"] * (1 - CONFIG_GUERRA["reglas_batalla"]["rango_emparejamiento"])
    rango_max = alianza["daño_total"] * (1 + CONFIG_GUERRA["reglas_batalla"]["rango_emparejamiento"])
    
    todas = obtener_todas_las_alianzas()
    
    rivales = [
        rival for rival in todas
        if rival["id"] != alianza["id"]
        and rival["miembros_activos"] >= CONFIG_GUERRA["reglas_batalla"]["minimo_miembros_alianza"]
        and rango_min <= rival["daño_total"] <= rango_max
    ]
    
    # Ordenar por cercanía de daño
    rivales.sort(key=lambda x: abs(x["daño_total"] - alianza["daño_total"]))
    
    return rivales[:4]  # Máximo 4 rivales para elegir

# ================= FUNCIONES DE BATALLA =================

def calcular_bajas(daño_recibido: int, naves: dict) -> tuple:
    """
    Calcula las bajas basado en el daño recibido y los puntos de las naves.
    Retorna (bajas, puntos_perdidos, naves_sobrevivientes)
    """
    bajas = {}
    puntos_perdidos = 0
    sobrevivientes = {}
    
    # Copia de las naves para ir descontando
    naves_restantes = {}
    for nave_id, data in naves.items():
        naves_restantes[nave_id] = {
            "cantidad": data["cantidad"],
            "puntos": data["puntos"]
        }
    
    daño_restante = daño_recibido
    
    # Ordenar naves por puntos (de menor a mayor) para simular bajas
    naves_ordenadas = sorted(naves_restantes.items(), key=lambda x: x[1]["puntos"])
    
    for nave_id, data in naves_ordenadas:
        if daño_restante <= 0:
            if data["cantidad"] > 0:
                sobrevivientes[nave_id] = data["cantidad"]
            continue
        
        puntos_por_nave = data["puntos"]
        cantidad = data["cantidad"]
        
        # Calcular cuántas naves se pueden destruir con el daño restante
        naves_destruidas = min(cantidad, daño_restante // puntos_por_nave)
        if naves_destruidas > 0:
            bajas[nave_id] = naves_destruidas
            puntos_perdidos += naves_destruidas * puntos_por_nave
            daño_restante -= naves_destruidas * puntos_por_nave
            
            # Naves que sobreviven
            sobrevivientes_count = cantidad - naves_destruidas
            if sobrevivientes_count > 0:
                sobrevivientes[nave_id] = sobrevivientes_count
        else:
            # Si no se puede destruir ninguna, todas sobreviven
            if cantidad > 0:
                sobrevivientes[nave_id] = cantidad
    
    return bajas, puntos_perdidos, sobrevivientes

def iniciar_batalla(alianza_atacante: dict, alianza_defensora: dict) -> dict:
    """
    Inicia una nueva batalla entre dos alianzas
    """
    clima = generar_clima_aleatorio()
    
    # Obtener flotas iniciales
    flota_atacante = obtener_flota_alianza(alianza_atacante["id"])
    flota_defensor = obtener_flota_alianza(alianza_defensora["id"])
    
    puntos_totales_atacante = calcular_puntos_flota(flota_atacante)
    puntos_totales_defensor = calcular_puntos_flota(flota_defensor)
    
    batalla = {
        "id": f"war_{int(datetime.now().timestamp())}",
        "atacante_id": alianza_atacante["id"],
        "atacante_nombre": alianza_atacante["nombre"],
        "defensor_id": alianza_defensora["id"],
        "defensor_nombre": alianza_defensora["nombre"],
        "inicio": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "clima": clima,
        "asaltos": [],
        "resultado": None,
        "puntos_iniciales_atacante": puntos_totales_atacante,
        "puntos_iniciales_defensor": puntos_totales_defensor,
        "puntos_ganados_atacante": 0,
        "puntos_ganados_defensor": 0,
        "bajas_atacante": {},
        "bajas_defensor": {},
        "supervivientes_atacante": flota_atacante,
        "supervivientes_defensor": flota_defensor
    }
    
    # Guardar batalla
    guerras = load_json(GUERRAS_FILE) or {}
    guerras[batalla["id"]] = batalla
    save_json(GUERRAS_FILE, guerras)
    
    return batalla

def ejecutar_asalto(batalla: dict) -> dict:
    """
    Ejecuta un asalto de la batalla
    """
    # Obtener flotas supervivientes
    flota_atacante = batalla["supervivientes_atacante"]
    flota_defensor = batalla["supervivientes_defensor"]
    
    # Obtener tecnologías máximas
    tec_atacante = obtener_tecnologias_alianza(batalla["atacante_id"])
    tec_defensor = obtener_tecnologias_alianza(batalla["defensor_id"])
    
    clima = batalla["clima"]
    
    # Calcular daño por posición
    daño_atacante = {
        "vanguardia": 0,
        "centro": 0,
        "retaguardia": 0
    }
    daño_defensor = {
        "vanguardia": 0,
        "centro": 0,
        "retaguardia": 0
    }
    
    # Calcular daño del atacante
    for posicion, naves in flota_atacante.items():
        for nave_id, data in naves.items():
            cantidad = data["cantidad"]
            arma_id = data["arma"]
            tecnologia_nivel = tec_atacante.get(data.get("tecnologia_requerida", ""), 0)
            
            daño_calculado = calcular_daño_arma_con_tecnologia(arma_id, tecnologia_nivel, clima)
            
            daño_por_nave = daño_calculado["daño_contra_escudo"]  # Usamos daño contra escudo como base
            daño_atacante[posicion] += daño_por_nave * cantidad
    
    # Calcular daño del defensor
    for posicion, naves in flota_defensor.items():
        for nave_id, data in naves.items():
            cantidad = data["cantidad"]
            arma_id = data["arma"]
            tecnologia_nivel = tec_defensor.get(data.get("tecnologia_requerida", ""), 0)
            
            daño_calculado = calcular_daño_arma_con_tecnologia(arma_id, tecnologia_nivel, clima)
            
            daño_por_nave = daño_calculado["daño_contra_escudo"]
            daño_defensor[posicion] += daño_por_nave * cantidad
    
    # Aplicar daño en orden de posiciones
    # Primero las naves atacantes reciben daño del defensor
    # y viceversa (ambos se atacan simultáneamente)
    
    nuevas_flotas_atacante = {}
    nuevas_flotas_defensor = {}
    
    bajas_atacante_detalle = {}
    bajas_defensor_detalle = {}
    puntos_ganados_atacante = 0
    puntos_ganados_defensor = 0
    
    # Procesar daño recibido por el atacante
    for posicion in ["vanguardia", "centro", "retaguardia"]:
        if posicion in flota_atacante:
            daño_recibido = daño_defensor.get(posicion, 0)
            bajas, puntos, sobrevivientes = calcular_bajas(daño_recibido, flota_atacante[posicion])
            
            if bajas:
                bajas_atacante_detalle[posicion] = bajas
                puntos_ganados_defensor += puntos
            
            if sobrevivientes:
                nuevas_flotas_atacante[posicion] = sobrevivientes
    
    # Procesar daño recibido por el defensor
    for posicion in ["vanguardia", "centro", "retaguardia"]:
        if posicion in flota_defensor:
            daño_recibido = daño_atacante.get(posicion, 0)
            bajas, puntos, sobrevivientes = calcular_bajas(daño_recibido, flota_defensor[posicion])
            
            if bajas:
                bajas_defensor_detalle[posicion] = bajas
                puntos_ganados_atacante += puntos
            
            if sobrevivientes:
                nuevas_flotas_defensor[posicion] = sobrevivientes
    
    # Actualizar batalla
    batalla["supervivientes_atacante"] = nuevas_flotas_atacante
    batalla["supervivientes_defensor"] = nuevas_flotas_defensor
    
    # Acumular puntos ganados
    batalla["puntos_ganados_atacante"] = batalla.get("puntos_ganados_atacante", 0) + puntos_ganados_atacante
    batalla["puntos_ganados_defensor"] = batalla.get("puntos_ganados_defensor", 0) + puntos_ganados_defensor
    
    asalto = {
        "numero": len(batalla["asaltos"]) + 1,
        "daño_atacante": daño_atacante,
        "daño_defensor": daño_defensor,
        "bajas_atacante": bajas_atacante_detalle,
        "bajas_defensor": bajas_defensor_detalle,
        "puntos_ganados_atacante": puntos_ganados_atacante,
        "puntos_ganados_defensor": puntos_ganados_defensor,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    batalla["asaltos"].append(asalto)
    
    return batalla

# ================= FUNCIONES DE PUNTUACIÓN =================

def aplicar_puntuacion_guerra(user_id: int, puntos_ganados: int):
    """Aplica los puntos ganados en guerra a la puntuación del usuario"""
    puntuacion_data = load_json(PUNTUACION_FILE) or {}
    
    if str(user_id) not in puntuacion_data:
        puntuacion_data[str(user_id)] = {"total": 0, "flota": 0, "defensa": 0, "edificios": 0, "investigacion": 0, "recursos": 0}
    
    # Los puntos de guerra se suman al total directamente
    puntuacion_data[str(user_id)]["total"] = puntuacion_data[str(user_id)].get("total", 0) + puntos_ganados
    
    save_json(PUNTUACION_FILE, puntuacion_data)

def distribuir_puntos_guerra(batalla: dict):
    """Distribuye los puntos ganados a todos los miembros de las alianzas"""
    # Obtener miembros
    miembros_atacante = obtener_miembros_alianza(batalla["atacante_id"])
    miembros_defensor = obtener_miembros_alianza(batalla["defensor_id"])
    
    puntos_atacante = batalla["puntos_ganados_atacante"]
    puntos_defensor = batalla["puntos_ganados_defensor"]
    
    # Distribuir puntos entre atacantes
    if puntos_atacante > 0 and miembros_atacante:
        puntos_por_miembro_atacante = puntos_atacante // len(miembros_atacante)
        for uid_str in miembros_atacante.keys():
            aplicar_puntuacion_guerra(int(uid_str), puntos_por_miembro_atacante)
    
    # Distribuir puntos entre defensores
    if puntos_defensor > 0 and miembros_defensor:
        puntos_por_miembro_defensor = puntos_defensor // len(miembros_defensor)
        for uid_str in miembros_defensor.keys():
            aplicar_puntuacion_guerra(int(uid_str), puntos_por_miembro_defensor)

# ================= HANDLERS DE TELEGRAM =================

@requiere_login
async def menu_guerra(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menú principal de guerra"""
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
    
    # Obtener miembros activos
    miembros = obtener_miembros_alianza(alianza_id)
    num_miembros = len(miembros)
    
    # Calcular daño total
    daño_total = calcular_daño_total_alianza(alianza_id)
    
    texto = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"⚔️ <b>GUERRA DE ALIANZAS</b> - {username_tag}\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"🏰 <b>{alianza_datos.get('nombre', 'ALIANZA')}</b> [{alianza_id}]\n"
        f"👥 Miembros: {num_miembros}\n"
        f"💥 Daño total: {abreviar_numero(daño_total)}\n\n"
    )
    
    # Verificar requisitos
    if num_miembros < CONFIG_GUERRA["reglas_batalla"]["minimo_miembros_alianza"]:
        texto += (
            f"❌ <b>REQUISITOS NO CUMPLIDOS</b>\n"
            f"Se necesitan al menos {CONFIG_GUERRA['reglas_batalla']['minimo_miembros_alianza']} miembros activos.\n"
            f"Actualmente tienes {num_miembros}."
        )
        keyboard = [[InlineKeyboardButton("◀️ VOLVER", callback_data="menu_principal")]]
    else:
        texto += f"✅ ¡Listo para la guerra! Busca rivales dentro de tu rango."
        keyboard = [
            [InlineKeyboardButton("⚔️ BUSCAR RIVAL", callback_data="guerra_buscar")],
            [InlineKeyboardButton("📊 VER HISTORIAL", callback_data="guerra_historial")],
            [InlineKeyboardButton("◀️ VOLVER", callback_data="menu_principal")]
        ]
    
    await query.edit_message_text(
        text=texto,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

@requiere_login
async def buscar_rival(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Busca rivales para la guerra"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    alianza_id, alianza_datos = obtener_alianza_usuario(user_id)
    
    if not alianza_id:
        await query.edit_message_text(
            text="❌ No perteneces a ninguna alianza.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ VOLVER", callback_data="menu_guerra")
            ]])
        )
        return
    
    # Verificar miembros activos
    miembros = obtener_miembros_alianza(alianza_id)
    num_miembros = len(miembros)
    
    if num_miembros < CONFIG_GUERRA["reglas_batalla"]["minimo_miembros_alianza"]:
        await query.edit_message_text(
            text=(
                f"❌ <b>REQUISITOS NO CUMPLIDOS</b>\n\n"
                f"Tu alianza tiene {num_miembros} miembros.\n"
                f"Se necesitan al menos {CONFIG_GUERRA['reglas_batalla']['minimo_miembros_alianza']}."
            ),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ VOLVER", callback_data="menu_guerra")
            ]])
        )
        return
    
    # Calcular daño de la alianza actual
    daño_total = calcular_daño_total_alianza(alianza_id)
    
    alianza_actual = {
        "id": alianza_id,
        "nombre": alianza_datos.get("nombre", "Alianza"),
        "daño_total": daño_total,
        "miembros_activos": num_miembros
    }
    
    # Buscar rivales
    rivales = seleccionar_rivales(alianza_actual)
    
    if not rivales:
        await query.edit_message_text(
            text=(
                f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
                f"⚔️ <b>BUSCAR RIVAL</b>\n"
                f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
                f"Tu alianza: {alianza_actual['nombre']}\n"
                f"Daño total: {abreviar_numero(daño_total)}\n\n"
                f"❌ No se encontraron rivales dentro del rango ±5%.\n\n"
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
    
    # Crear botones
    botones = []
    for rival in rivales:
        botones.append([
            InlineKeyboardButton(
                f"⚔️ {rival['nombre']} ({abreviar_numero(rival['daño_total'])})",
                callback_data=f"guerra_atacar_{rival['id']}"
            )
        ])
    
    botones.append([InlineKeyboardButton("◀️ CANCELAR", callback_data="menu_guerra")])
    
    texto = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"⚔️ <b>SELECCIONAR RIVAL</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"Tu alianza: {alianza_actual['nombre']}\n"
        f"Daño total: {abreviar_numero(daño_total)}\n\n"
        f"Rivales encontrados ({len(rivales)}):\n\n"
        f"<i>Selecciona un rival para comenzar la batalla:</i>"
    )
    
    await query.edit_message_text(
        text=texto,
        reply_markup=InlineKeyboardMarkup(botones),
        parse_mode="HTML"
    )
    
    return SELECCIONANDO_RIVAL

@requiere_login
async def iniciar_guerra(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inicia una guerra contra el rival seleccionado"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    rival_id = data.replace("guerra_atacar_", "")
    
    alianza_id, alianza_datos = obtener_alianza_usuario(user_id)
    
    if not alianza_id:
        await query.edit_message_text(
            text="❌ No perteneces a ninguna alianza.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ VOLVER", callback_data="menu_guerra")
            ]])
        )
        return ConversationHandler.END
    
    # Verificar que el usuario tenga permisos (admin o fundador)
    from alianza import es_admin_alianza
    if not es_admin_alianza(user_id, alianza_id):
        await query.answer("❌ Solo administradores pueden iniciar guerras", show_alert=True)
        return SELECCIONANDO_RIVAL
    
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
    
    # Clima aleatorio
    clima = batalla["clima"]
    clima_info = CONFIG_GUERRA["climas_batalla"][clima]
    
    texto = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"⚔️ <b>¡GUERRA INICIADA!</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"🏰 <b>{alianza_atacante['nombre']}</b>\n"
        f"   vs\n"
        f"🏰 <b>{rival_data['nombre']}</b>\n\n"
        f"🌍 <b>Clima:</b> {clima_info['icono']} {clima_info['nombre']}\n"
        f"📅 <b>Inicio:</b> {batalla['inicio']}\n\n"
        f"💥 <b>Daño:</b>\n"
        f"   • Tu alianza: {abreviar_numero(daño_atacante)}\n"
        f"   • Rival: {abreviar_numero(rival_data['daño_total'])}\n\n"
        f"🏆 <b>PUNTOS EN JUEGO:</b>\n"
        f"   • Flota atacante: {abreviar_numero(batalla['puntos_iniciales_atacante'])} pts\n"
        f"   • Flota defensora: {abreviar_numero(batalla['puntos_iniciales_defensor'])} pts\n\n"
        f"<i>Los puntos se ganan destruyendo naves enemigas</i>\n\n"
        f"¿Preparados para el primer asalto?"
    )
    
    keyboard = [
        [InlineKeyboardButton("⚔️ EJECUTAR ASALTO 1", callback_data=f"guerra_asalto_1")],
        [InlineKeyboardButton("📊 VER DETALLES", callback_data=f"guerra_detalles")],
        [InlineKeyboardButton("◀️ RENDIRSE", callback_data="menu_guerra")]
    ]
    
    await query.edit_message_text(
        text=texto,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )
    
    return EN_BATALLA

@requiere_login
async def ejecutar_asalto_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ejecuta un asalto de la guerra"""
    query = update.callback_query
    await query.answer()
    
    batalla = context.user_data.get('batalla_actual')
    if not batalla:
        await query.edit_message_text(
            text="❌ No hay una batalla en curso.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ VOLVER", callback_data="menu_guerra")
            ]])
        )
        return ConversationHandler.END
    
    # Ejecutar asalto
    batalla = ejecutar_asalto(batalla)
    asalto_actual = batalla["asaltos"][-1]
    numero_asalto = asalto_actual["numero"]
    
    # Guardar batalla actualizada
    guerras = load_json(GUERRAS_FILE) or {}
    guerras[batalla["id"]] = batalla
    save_json(GUERRAS_FILE, guerras)
    context.user_data['batalla_actual'] = batalla
    
    texto = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"⚔️ <b>ASALTO {numero_asalto}</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"🏰 <b>{batalla['atacante_nombre']}</b> vs <b>{batalla['defensor_nombre']}</b>\n\n"
        f"📊 <b>RESULTADO DEL ASALTO:</b>\n\n"
        f"⚡ <b>Daño infligido:</b>\n"
        f"   • Vanguardia: {abreviar_numero(asalto_actual['daño_atacante']['vanguardia'])}\n"
        f"   • Centro: {abreviar_numero(asalto_actual['daño_atacante']['centro'])}\n"
        f"   • Retaguardia: {abreviar_numero(asalto_actual['daño_atacante']['retaguardia'])}\n\n"
        f"🛡️ <b>Daño recibido:</b>\n"
        f"   • Vanguardia: {abreviar_numero(asalto_actual['daño_defensor']['vanguardia'])}\n"
        f"   • Centro: {abreviar_numero(asalto_actual['daño_defensor']['centro'])}\n"
        f"   • Retaguardia: {abreviar_numero(asalto_actual['daño_defensor']['retaguardia'])}\n\n"
        f"💀 <b>BAJAS:</b>\n"
        f"   • Atacante perdió {abreviar_numero(asalto_actual['puntos_ganados_defensor'])} pts\n"
        f"   • Defensor perdió {abreviar_numero(asalto_actual['puntos_ganados_atacante'])} pts\n\n"
        f"🏆 <b>PUNTOS ACUMULADOS:</b>\n"
        f"   • Atacante: {abreviar_numero(batalla['puntos_ganados_atacante'])} pts\n"
        f"   • Defensor: {abreviar_numero(batalla['puntos_ganados_defensor'])} pts\n\n"
    )
    
    # Verificar si la batalla terminó (una flota aniquilada o máximo asaltos)
    max_asaltos = CONFIG_GUERRA["reglas_batalla"]["duracion_maxima_asaltos"]
    
    flota_atacante_vacia = all(len(v) == 0 for v in batalla["supervivientes_atacante"].values())
    flota_defensor_vacia = all(len(v) == 0 for v in batalla["supervivientes_defensor"].values())
    
    if flota_atacante_vacia or flota_defensor_vacia or numero_asalto >= max_asaltos:
        # Determinar ganador
        if flota_defensor_vacia or batalla["puntos_ganados_atacante"] > batalla["puntos_ganados_defensor"]:
            resultado = "victoria"
            ganador = batalla['atacante_nombre']
            perdedor = batalla['defensor_nombre']
            puntos_ganados = batalla["puntos_ganados_atacante"]
        else:
            resultado = "derrota"
            ganador = batalla['defensor_nombre']
            perdedor = batalla['atacante_nombre']
            puntos_ganados = batalla["puntos_ganados_defensor"]
        
        batalla["resultado"] = resultado
        
        # Distribuir puntos a los miembros
        distribuir_puntos_guerra(batalla)
        
        texto += (
            f"🏆 <b>¡BATALLA FINALIZADA!</b>\n\n"
            f"🎉 <b>GANADOR:</b> {ganador}\n"
            f"💔 <b>PERDEDOR:</b> {perdedor}\n\n"
            f"💰 Se han distribuido {abreviar_numero(puntos_ganados)} puntos entre los miembros de {ganador}."
        )
        
        keyboard = [[InlineKeyboardButton("◀️ VOLVER", callback_data="menu_guerra")]]
        
        # Notificar a los miembros
        await notificar_resultado_guerra(context, batalla)
        
    else:
        keyboard = [
            [InlineKeyboardButton(f"⚔️ SIGUIENTE ASALTO", callback_data=f"guerra_asalto_{numero_asalto+1}")],
            [InlineKeyboardButton("🏳️ RENDIRSE", callback_data="menu_guerra")]
        ]
    
    await query.edit_message_text(
        text=texto,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )
    
    return EN_BATALLA

async def notificar_resultado_guerra(context, batalla):
    """Notifica el resultado de la guerra a todos los miembros"""
    # Obtener miembros de ambas alianzas
    miembros_atacante = obtener_miembros_alianza(batalla["atacante_id"])
    miembros_defensor = obtener_miembros_alianza(batalla["defensor_id"])
    
    resultado = batalla["resultado"]
    
    if resultado == "victoria":
        texto_atacante = (
            f"🎉 <b>¡VICTORIA EN GUERRA!</b>\n\n"
            f"Tu alianza <b>{batalla['atacante_nombre']}</b> ha derrotado a "
            f"<b>{batalla['defensor_nombre']}</b>.\n\n"
            f"🏆 Puntos ganados: {abreviar_numero(batalla['puntos_ganados_atacante'])}\n\n"
            f"¡Enhorabuena comandantes!"
        )
        texto_defensor = (
            f"💔 <b>DERROTA EN GUERRA</b>\n\n"
            f"Tu alianza <b>{batalla['defensor_nombre']}</b> ha sido derrotada por "
            f"<b>{batalla['atacante_nombre']}</b>.\n\n"
            f"💔 Puntos perdidos: {abreviar_numero(batalla['puntos_ganados_atacante'])}\n\n"
            f"Ánimo, la próxima será vuestra."
        )
    else:
        texto_atacante = (
            f"💔 <b>DERROTA EN GUERRA</b>\n\n"
            f"Tu alianza <b>{batalla['atacante_nombre']}</b> ha sido derrotada por "
            f"<b>{batalla['defensor_nombre']}</b>.\n\n"
            f"💔 Puntos perdidos: {abreviar_numero(batalla['puntos_ganados_defensor'])}\n\n"
            f"Ánimo, la próxima será vuestra."
        )
        texto_defensor = (
            f"🎉 <b>¡VICTORIA EN GUERRA!</b>\n\n"
            f"Tu alianza <b>{batalla['defensor_nombre']}</b> ha derrotado a "
            f"<b>{batalla['atacante_nombre']}</b>.\n\n"
            f"🏆 Puntos ganados: {abreviar_numero(batalla['puntos_ganados_defensor'])}\n\n"
            f"¡Enhorabuena comandantes!"
        )
    
    # Notificar a atacantes
    for uid_str in miembros_atacante.keys():
        try:
            await context.bot.send_message(
                chat_id=int(uid_str),
                text=texto_atacante,
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Error notificando a {uid_str}: {e}")
    
    # Notificar a defensores
    for uid_str in miembros_defensor.keys():
        try:
            await context.bot.send_message(
                chat_id=int(uid_str),
                text=texto_defensor,
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Error notificando a {uid_str}: {e}")

# ================= CALLBACK HANDLER =================

async def guerra_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejador principal para callbacks de guerra"""
    query = update.callback_query
    data = query.data
    
    if data == "menu_guerra":
        await menu_guerra(update, context)
        return ConversationHandler.END
    elif data == "guerra_buscar":
        return await buscar_rival(update, context)
    elif data.startswith("guerra_atacar_"):
        return await iniciar_guerra(update, context)
    elif data.startswith("guerra_asalto_"):
        return await ejecutar_asalto_handler(update, context)
    elif data == "guerra_historial":
        await query.edit_message_text(
            text="📊 Función de historial en desarrollo.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ VOLVER", callback_data="menu_guerra")
            ]])
        )
    elif data == "guerra_detalles":
        await query.edit_message_text(
            text="📊 Función de detalles en desarrollo.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ VOLVER", callback_data="menu_guerra")
            ]])
        )
    
    return ConversationHandler.END

# ================= CONVERSATION HANDLER =================

guerra_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(guerra_callback_handler, pattern="^guerra_")],
    states={
        SELECCIONANDO_RIVAL: [
            CallbackQueryHandler(iniciar_guerra, pattern="^guerra_atacar_"),
            CallbackQueryHandler(menu_guerra, pattern="^menu_guerra$")
        ],
        EN_BATALLA: [
            CallbackQueryHandler(ejecutar_asalto_handler, pattern="^guerra_asalto_"),
            CallbackQueryHandler(menu_guerra, pattern="^menu_guerra$")
        ],
    },
    fallbacks=[CallbackQueryHandler(menu_guerra, pattern="^menu_guerra$")],
    name="guerra_conversacion",
    persistent=False
)

def obtener_conversation_handlers_guerra():
    """Retorna los ConversationHandlers para guerra"""
    return [guerra_conv]

# ================= EXPORTAR =================

__all__ = [
    'guerra_callback_handler',
    'obtener_conversation_handlers_guerra',
    'menu_guerra',
    'calcular_daño_total_alianza',
    'seleccionar_rivales'
]
