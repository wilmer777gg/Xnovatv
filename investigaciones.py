#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#██████╗ ███████╗████████╗██████╗  █████╗ ██╗     ███████╗
#██╔══██╗██╔════╝╚══██╔══╝██╔══██╗██╔══██╗██║     ██╔════╝
#██████╔╝███████╗   ██║   ██████╔╝███████║██║     ███████╗
#██╔══██╗╚════██║   ██║   ██╔══██╗██╔══██║██║     ╚════██║
#██║  ██║███████║   ██║   ██║  ██║██║  ██║███████╗███████║
#╚═╝  ╚═╝╚══════╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚══════╝

#🚀 ASTRO.IO v2.4.0 🚀
#🔬 investigaciones.py - SISTEMA DE INVESTIGACIÓN I+D
#===========================================================
#✅ MISMO ESTILO que menú principal
#✅ Barras de progreso [██░] 3 caracteres
#✅ Formato de tiempo corto: 45m, 2h, 1h 30m
#✅ Diseño con separadores 🌀
#===========================================================

import os
import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from login import AuthSystem, requiere_login
from database import load_json, save_json
from utils import abreviar_numero
from edificios import obtener_nivel

logger = logging.getLogger(__name__)

# ================= CONSTANTES =================
DATA_DIR = "data"
RECURSOS_FILE = os.path.join(DATA_DIR, "recursos.json")
INVESTIGACIONES_FILE = os.path.join(DATA_DIR, "investigaciones.json")

# ================= 🎨 FUNCIONES VISUALES (MISMO ESTILO QUE MENÚ PRINCIPAL) =================

def barra_progreso_3c(actual: int, total: int) -> str:
    """📊 Barra de progreso de SOLO 3 caracteres [██░]"""
    if total <= 0:
        return "[░░░]"
    porcentaje = min(1.0, actual / total)
    llenos = int(porcentaje * 3)
    return "[" + "█" * llenos + "░" * (3 - llenos) + "]"

def formatear_tiempo_corto(segundos: int) -> str:
    """⏱️ Formatea tiempo en formato corto: 45s, 23m, 2h, 1h 30m"""
    if segundos < 60:
        return f"{segundos}s"
    elif segundos < 3600:
        minutos = segundos // 60
        return f"{minutos}m"
    else:
        horas = segundos // 3600
        minutos = (segundos % 3600) // 60
        if minutos == 0:
            return f"{horas}h"
        else:
            return f"{horas}h {minutos}m"

# ================= CONFIGURACIÓN DE INVESTIGACIONES =================
INVESTIGACIONES = {
    "propulsion_combustion": {
        "nombre": "Propulsión por Combustión",
        "icono": "🚀",
        "icono_corto": "🔥",
        "descripcion": "Tecnología básica de propulsión química para naves espaciales.",
        "requisitos": {"laboratorio": 1},
        "costo_base": {"metal": 1000, "cristal": 500},
        "tiempo_base": 60,
        "bonificacion": "+10% velocidad naves civiles",
        "max_nivel": 20,
        "grupo": "Propulsión",
        "orden": 1
    },
    "tecnologia_energia": {
        "nombre": "Tecnología de Energía",
        "icono": "⚡",
        "icono_corto": "🔋",
        "descripcion": "Optimización de sistemas de energía.",
        "requisitos": {"laboratorio": 1},
        "costo_base": {"metal": 800, "cristal": 400},
        "tiempo_base": 90,
        "bonificacion": "+5% producción de energía",
        "max_nivel": 20,
        "grupo": "Energía",
        "orden": 2
    },
    "tecnologia_computacion": {
        "nombre": "Tecnología de Computación",
        "icono": "💻",
        "icono_corto": "🖥️",
        "descripcion": "Avances en sistemas informáticos y IA.",
        "requisitos": {"laboratorio": 2},
        "costo_base": {"metal": 1500, "cristal": 1000},
        "tiempo_base": 150,
        "bonificacion": "+1 slot de investigación cada 5 niveles",
        "max_nivel": 10,
        "grupo": "Investigación",
        "orden": 3
    },
    "tecnologia_laser": {
        "nombre": "Tecnología Láser",
        "icono": "🔫",
        "icono_corto": "⚡",
        "descripcion": "Investigación de armas de energía dirigida.",
        "requisitos": {"laboratorio": 2, "tecnologia_energia": 3},
        "costo_base": {"metal": 2000, "cristal": 1000, "deuterio": 500},
        "tiempo_base": 120,
        "bonificacion": "+15% daño armas láser",
        "max_nivel": 15,
        "grupo": "Armamento",
        "orden": 4
    },
    "tecnologia_escudos": {
        "nombre": "Tecnología de Escudos",
        "icono": "🛡️",
        "icono_corto": "🔰",
        "descripcion": "Desarrollo de sistemas de escudos protectores.",
        "requisitos": {"laboratorio": 3, "tecnologia_laser": 2},
        "costo_base": {"metal": 2500, "cristal": 2000, "deuterio": 1000},
        "tiempo_base": 180,
        "bonificacion": "+20% potencia de escudos",
        "max_nivel": 10,
        "grupo": "Defensa",
        "orden": 5
    },
    "propulsion_impulso": {
        "nombre": "Propulsión por Impulso",
        "icono": "🌀",
        "icono_corto": "💫",
        "descripcion": "Motores de impulso para viajes interplanetarios.",
        "requisitos": {"laboratorio": 3, "propulsion_combustion": 5},
        "costo_base": {"metal": 3000, "cristal": 1500, "deuterio": 800},
        "tiempo_base": 240,
        "bonificacion": "+25% velocidad naves militares",
        "max_nivel": 15,
        "grupo": "Propulsión",
        "orden": 6
    },
    "tecnologia_iones": {
        "nombre": "Tecnología de Iones",
        "icono": "⚡",
        "icono_corto": "⚡",
        "descripcion": "Sistemas de armamento de iones avanzados.",
        "requisitos": {"laboratorio": 4, "tecnologia_laser": 5},
        "costo_base": {"metal": 4000, "cristal": 2000, "deuterio": 1000},
        "tiempo_base": 300,
        "bonificacion": "+20% daño armas iónicas",
        "max_nivel": 12,
        "grupo": "Armamento",
        "orden": 7
    },
    "tecnologia_hiperespacio": {
        "nombre": "Tecnología Hiperespacial",
        "icono": "🌌",
        "icono_corto": "✨",
        "descripcion": "Investigación para viajes a través del hiperespacio.",
        "requisitos": {"laboratorio": 6, "propulsion_impulso": 8, "tecnologia_iones": 5},
        "costo_base": {"metal": 10000, "cristal": 8000, "deuterio": 5000},
        "tiempo_base": 600,
        "bonificacion": "Desbloquea motores hiperespaciales",
        "max_nivel": 8,
        "grupo": "Avanzado",
        "orden": 8
    }
}

# ================= FUNCIONES DE LECTURA EN TIEMPO REAL =================

def inicializar_db_investigaciones():
    """📁 Inicializa el archivo de investigaciones si no existe"""
    if not os.path.exists(INVESTIGACIONES_FILE):
        estructura = {
            "usuarios": {},
            "colas": {},
            "estadisticas": {
                "total_investigaciones_iniciadas": 0,
                "total_investigaciones_completadas": 0,
                "ultima_actualizacion": datetime.now().isoformat()
            }
        }
        save_json(INVESTIGACIONES_FILE, estructura)
        return estructura
    return load_json(INVESTIGACIONES_FILE)

def obtener_datos_investigacion(user_id: int) -> dict:
    """🔬 Obtiene datos de investigación del usuario"""
    user_id_str = str(user_id)
    data = inicializar_db_investigaciones()
    
    return {
        "investigaciones": data.get("usuarios", {}).get(user_id_str, {}),
        "cola": data.get("colas", {}).get(user_id_str, [])
    }

def guardar_investigacion(user_id: int, investigaciones: dict = None, cola: list = None) -> bool:
    """💾 Guarda datos de investigación del usuario"""
    user_id_str = str(user_id)
    data = inicializar_db_investigaciones()
    
    if "usuarios" not in data:
        data["usuarios"] = {}
    if "colas" not in data:
        data["colas"] = {}
    
    if investigaciones is not None:
        data["usuarios"][user_id_str] = investigaciones
    
    if cola is not None:
        data["colas"][user_id_str] = cola
    
    data["estadisticas"]["ultima_actualizacion"] = datetime.now().isoformat()
    
    return save_json(INVESTIGACIONES_FILE, data)

def obtener_recursos(user_id: int) -> dict:
    """💰 Obtiene recursos del usuario"""
    user_id_str = str(user_id)
    recursos_data = load_json(RECURSOS_FILE) or {}
    return recursos_data.get(user_id_str, {})

def guardar_recursos(user_id: int, recursos: dict) -> bool:
    """💾 Guarda recursos del usuario"""
    user_id_str = str(user_id)
    recursos_data = load_json(RECURSOS_FILE) or {}
    recursos_data[user_id_str] = recursos
    return save_json(RECURSOS_FILE, recursos_data)

# ================= FUNCIONES DE CÁLCULO =================

def calcular_costo(tipo: str, nivel_actual: int) -> dict:
    """💰 Calcula costo para el siguiente nivel"""
    config = INVESTIGACIONES[tipo]
    costo = {}
    factor = 1.5
    
    for recurso, base in config["costo_base"].items():
        costo[recurso] = int(base * (factor ** nivel_actual))
    
    return costo

def calcular_tiempo(tipo: str, nivel_actual: int, nivel_lab: int) -> int:
    """⏱️ Calcula tiempo en segundos"""
    config = INVESTIGACIONES[tipo]
    tiempo_base = config["tiempo_base"]
    factor = 1.3
    
    tiempo = int(tiempo_base * (factor ** nivel_actual))
    
    if nivel_lab > 0:
        reduccion = 0.05 * nivel_lab
        tiempo = int(tiempo * (1 - reduccion))
    
    return max(tiempo, 10)

def calcular_slots(nivel_lab: int) -> int:
    """📊 Calcula slots de investigación disponibles"""
    return 1 + (nivel_lab // 5)

# ================= FUNCIONES DE VERIFICACIÓN =================

def verificar_requisitos(user_id: int, tipo: str) -> tuple:
    """🔍 Verifica requisitos para investigar"""
    if tipo not in INVESTIGACIONES:
        return False, "❌ Investigación no válida"
    
    config = INVESTIGACIONES[tipo]
    datos_inv = obtener_datos_investigacion(user_id)
    nivel_lab = obtener_nivel(user_id, "laboratorio")
    
    errores = []
    
    for req_tipo, req_nivel in config["requisitos"].items():
        if req_tipo == "laboratorio":
            if nivel_lab < req_nivel:
                errores.append(f"• Laboratorio: Nivel {req_nivel} (tienes: {nivel_lab})")
        else:
            nivel_actual = datos_inv["investigaciones"].get(req_tipo, 0)
            if nivel_actual < req_nivel:
                req_nombre = INVESTIGACIONES.get(req_tipo, {}).get("nombre", req_tipo)
                errores.append(f"• {req_nombre}: Nivel {req_nivel} (tienes: {nivel_actual})")
    
    if errores:
        return False, "❌ Requisitos no cumplidos:\n" + "\n".join(errores)
    
    return True, "✅ Requisitos cumplidos"

def verificar_recursos_suficientes(user_id: int, tipo: str, nivel_actual: int) -> tuple:
    """💰 Verifica recursos suficientes"""
    recursos = obtener_recursos(user_id)
    costo = calcular_costo(tipo, nivel_actual)
    
    faltantes = []
    
    for recurso, cantidad in costo.items():
        disponible = recursos.get(recurso, 0)
        if disponible < cantidad:
            icono = "🔩" if recurso == "metal" else "💎" if recurso == "cristal" else "🧪"
            faltantes.append(f"{icono} {recurso.capitalize()}: {abreviar_numero(disponible)}/{abreviar_numero(cantidad)}")
    
    if faltantes:
        return False, "❌ Recursos insuficientes:\n" + "\n".join(faltantes)
    
    return True, "✅ Recursos suficientes"

def obtener_investigaciones_desbloqueadas(user_id: int) -> dict:
    """🔓 Obtiene investigaciones que el usuario puede ver"""
    datos_inv = obtener_datos_investigacion(user_id)
    nivel_lab = obtener_nivel(user_id, "laboratorio")
    
    desbloqueadas = {}
    
    for tipo, config in INVESTIGACIONES.items():
        cumple = True
        
        # Verificar laboratorio
        req_lab = config["requisitos"].get("laboratorio", 0)
        if nivel_lab < req_lab:
            cumple = False
        
        # Verificar otros requisitos
        if cumple:
            for req_tipo, req_nivel in config["requisitos"].items():
                if req_tipo != "laboratorio":
                    nivel_actual = datos_inv["investigaciones"].get(req_tipo, 0)
                    if nivel_actual < req_nivel:
                        cumple = False
                        break
        
        if cumple:
            desbloqueadas[tipo] = config
    
    return desbloqueadas

# ================= SISTEMA DE COLAS =================

def procesar_cola(user_id: int) -> list:
    """⏳ Procesa investigaciones completadas"""
    user_id_str = str(user_id)
    data = inicializar_db_investigaciones()
    
    cola = data.get("colas", {}).get(user_id_str, [])
    if not cola:
        return []
    
    ahora = datetime.now()
    completadas = []
    cola_restante = []
    
    for item in cola:
        try:
            fin = datetime.fromisoformat(item["fin"])
            
            if ahora >= fin:
                # Investigación completada
                tipo = item["tipo"]
                nivel = item["nivel"]
                
                if user_id_str not in data["usuarios"]:
                    data["usuarios"][user_id_str] = {}
                
                data["usuarios"][user_id_str][tipo] = nivel
                data["estadisticas"]["total_investigaciones_completadas"] += 1
                
                completadas.append(item)
                logger.info(f"✅ Investigación completada: {tipo} nivel {nivel} para {AuthSystem.obtener_username(user_id)}")
            else:
                # Actualizar tiempo restante
                item["tiempo_restante"] = (fin - ahora).total_seconds()
                cola_restante.append(item)
        except Exception as e:
            logger.error(f"❌ Error procesando item: {e}")
            cola_restante.append(item)
    
    # Guardar cambios
    data["colas"][user_id_str] = cola_restante
    save_json(INVESTIGACIONES_FILE, data)
    
    return completadas

# ================= INICIAR INVESTIGACIÓN =================

def iniciar_investigacion_db(user_id: int, tipo: str) -> tuple:
    """
    🔬 INICIAR INVESTIGACIÓN - CON COLAS
    1. Lee datos en tiempo real
    2. Verifica requisitos, recursos, slots
    3. Descuenta recursos
    4. Añade a cola de investigaciones.json
    5. Guarda TODO inmediatamente
    """
    if tipo not in INVESTIGACIONES:
        return False, "❌ Investigación no válida"
    
    config = INVESTIGACIONES[tipo]
    datos_inv = obtener_datos_investigacion(user_id)
    nivel_actual = datos_inv["investigaciones"].get(tipo, 0)
    nivel_lab = obtener_nivel(user_id, "laboratorio")
    slots_max = calcular_slots(nivel_lab)
    
    # ========== VERIFICACIONES ==========
    if nivel_actual >= config["max_nivel"]:
        return False, f"🏆 Nivel máximo ({config['max_nivel']}) alcanzado"
    
    cumple_req, msg_req = verificar_requisitos(user_id, tipo)
    if not cumple_req:
        return False, msg_req
    
    cumple_rec, msg_rec = verificar_recursos_suficientes(user_id, tipo, nivel_actual)
    if not cumple_rec:
        return False, msg_rec
    
    if len(datos_inv["cola"]) >= slots_max:
        return False, f"❌ Slots llenos ({len(datos_inv['cola'])}/{slots_max})"
    
    # ========== CALCULAR COSTO Y TIEMPO ==========
    costo = calcular_costo(tipo, nivel_actual)
    tiempo = calcular_tiempo(tipo, nivel_actual, nivel_lab)
    
    # ========== 1. DESCONTAR RECURSOS ==========
    recursos = obtener_recursos(user_id)
    for recurso, cantidad in costo.items():
        recursos[recurso] = recursos.get(recurso, 0) - cantidad
    
    if not guardar_recursos(user_id, recursos):
        return False, "❌ Error al descontar recursos"
    
    # ========== 2. AÑADIR A COLA ==========
    fin = datetime.now() + timedelta(seconds=tiempo)
    
    nueva_investigacion = {
        "tipo": tipo,
        "nivel": nivel_actual + 1,
        "inicio": datetime.now().isoformat(),
        "fin": fin.isoformat(),
        "costo": costo,
        "tiempo_total": tiempo,
        "tiempo_restante": tiempo
    }
    
    data = inicializar_db_investigaciones()
    user_id_str = str(user_id)
    
    if user_id_str not in data["colas"]:
        data["colas"][user_id_str] = []
    
    data["colas"][user_id_str].append(nueva_investigacion)
    data["estadisticas"]["total_investigaciones_iniciadas"] += 1
    
    if not save_json(INVESTIGACIONES_FILE, data):
        return False, "❌ Error al guardar investigación"
    
    # ========== 3. LOG ==========
    username = AuthSystem.obtener_username(user_id)
    logger.info(f"✅ {username} inició investigación: {config['nombre']} nivel {nivel_actual + 1}")
    
    # ========== 4. MENSAJE ==========
    tiempo_str = formatear_tiempo_corto(tiempo)
    
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"🔬 <b>INVESTIGACIÓN INICIADA</b>\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"{config['icono']} {config['nombre']}\n"
        f"├ Nivel objetivo: {nivel_actual + 1}\n"
        f"├ Tiempo: {tiempo_str}\n"
        f"├ Finaliza: {fin.strftime('%H:%M:%S')}\n"
        f"└ Slots: {len(data['colas'][user_id_str])}/{slots_max}\n\n"
        f"💰 Recursos descontados correctamente.\n\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    )
    
    return True, mensaje

# ================= MENÚ PRINCIPAL DE INVESTIGACIONES =================

@requiere_login
async def menu_investigaciones_principal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🔬 Menú principal de investigaciones - SIEMPRE edita el mensaje actual"""
    query = update.callback_query
    if not query:
        logger.error("❌ menu_investigaciones_principal sin callback_query")
        return
    
    await query.answer()
    user_id = query.from_user.id
    
    # ========== PROCESAR COLAS ==========
    procesar_cola(user_id)
    
    # ========== LEER DATOS EN TIEMPO REAL ==========
    recursos = obtener_recursos(user_id)
    datos_inv = obtener_datos_investigacion(user_id)
    nivel_lab = obtener_nivel(user_id, "laboratorio")
    slots_max = calcular_slots(nivel_lab)
    username_tag = AuthSystem.obtener_username(user_id)
    
    # Obtener investigaciones desbloqueadas
    desbloqueadas = obtener_investigaciones_desbloqueadas(user_id)
    
    # ========== CONSTRUIR MENSAJE ==========
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"🔬 <b>LABORATORIO DE INVESTIGACIÓN</b> - {username_tag}\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"💰 <b>RECURSOS:</b>\n"
        f"🔩 Metal: {abreviar_numero(recursos.get('metal', 0))}\n"
        f"💎 Cristal: {abreviar_numero(recursos.get('cristal', 0))}\n"
        f"🧪 Deuterio: {abreviar_numero(recursos.get('deuterio', 0))}\n\n"
        f"🏛️ <b>LABORATORIO:</b> Nivel {nivel_lab}\n"
        f"📊 <b>SLOTS:</b> {len(datos_inv['cola'])}/{slots_max}\n\n"
    )
    
    # Mostrar investigaciones en curso
    if datos_inv["cola"]:
        mensaje += f"⏳ <b>INVESTIGACIONES EN CURSO:</b>\n"
        ahora = datetime.now()
        for idx, item in enumerate(datos_inv["cola"][:3], 1):
            tipo = item["tipo"]
            nivel = item["nivel"]
            config = INVESTIGACIONES.get(tipo, {})
            nombre = config.get("nombre", tipo)
            
            fin = datetime.fromisoformat(item["fin"])
            segundos = max(0, (fin - ahora).total_seconds())
            tiempo = formatear_tiempo_corto(int(segundos))
            progreso = item["tiempo_total"] - item["tiempo_restante"]
            barra = barra_progreso_3c(progreso, item["tiempo_total"])
            
            mensaje += f"   {idx}. {config.get('icono', '🔬')} {nombre}\n"
            mensaje += f"      {barra} {tiempo} → N.{nivel}\n"
        
        if len(datos_inv["cola"]) > 3:
            mensaje += f"      ... y {len(datos_inv['cola']) - 3} más\n"
        mensaje += "\n"
    
    # Mostrar tecnologías disponibles
    mensaje += f"🔍 <b>TECNOLOGÍAS DISPONIBLES:</b>\n"
    
    if not desbloqueadas:
        mensaje += f"\n   🔒 Mejora tu Laboratorio para desbloquear tecnologías.\n\n"
    else:
        # Agrupar por grupo
        grupos = {}
        for tipo, config in desbloqueadas.items():
            grupo = config.get("grupo", "Otros")
            if grupo not in grupos:
                grupos[grupo] = []
            
            nivel_actual = datos_inv["investigaciones"].get(tipo, 0)
            grupos[grupo].append((tipo, config, nivel_actual))
        
        for grupo, items in grupos.items():
            mensaje += f"\n<b>{grupo}:</b>\n"
            for tipo, config, nivel in items[:4]:  # Máximo 4 por grupo
                icono = config.get('icono', '🔬')
                if nivel >= config["max_nivel"]:
                    estado = "🏆"
                else:
                    cumple_rec, _ = verificar_recursos_suficientes(user_id, tipo, nivel)
                    estado = "🟢" if cumple_rec else "🟡"
                mensaje += f"   {estado} {icono} {config['nombre']}: N.{nivel}/{config['max_nivel']}\n"
            if len(items) > 4:
                mensaje += f"      ... y {len(items) - 4} más\n"
    
    mensaje += f"\n🟢 Disponible | 🟡 Requiere recursos | 🏆 Máximo | 🔒 Bloqueado"
    mensaje += f"\n\n🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
    mensaje += f"<i>Selecciona una tecnología:</i>"
    
    # ========== TECLADO ==========
    keyboard = []
    
    # Ordenar investigaciones desbloqueadas
    investigaciones_ordenadas = sorted(
        desbloqueadas.items(),
        key=lambda x: x[1].get("orden", 99)
    )
    
    # Crear botones por grupos
    for tipo, config in investigaciones_ordenadas[:12]:  # Máximo 12 botones
        nivel_actual = datos_inv["investigaciones"].get(tipo, 0)
        if nivel_actual < config["max_nivel"]:
            texto = f"{config['icono']} {config['nombre'].split()[0]}"
        else:
            texto = f"🏆 {config['icono']} {config['nombre'].split()[0]}"
        
        keyboard.append([
            InlineKeyboardButton(texto, callback_data=f"investigacion_{tipo}")
        ])
    
    if not desbloqueadas:
        keyboard.append([
            InlineKeyboardButton("🔒 MEJORAR LABORATORIO", callback_data="edificio_laboratorio")
        ])
    
    # Botones de navegación
    keyboard.append([
        InlineKeyboardButton("🔄 ACTUALIZAR", callback_data="menu_investigaciones"),
        InlineKeyboardButton("◀️ VOLVER", callback_data="menu_principal")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # ========== EDITAR MENSAJE ==========
    try:
        await query.edit_message_text(
            text=mensaje,
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
        logger.info(f"✅ Menú investigaciones mostrado a {username_tag}")
    except Exception as e:
        logger.error(f"❌ Error editando menú investigaciones: {e}")

# ================= SUBMENÚ DE INVESTIGACIÓN ESPECÍFICA =================

@requiere_login
async def submenu_investigacion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🔬 Muestra detalles de una investigación específica"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    tipo = query.data.replace("investigacion_", "")
    
    if tipo not in INVESTIGACIONES:
        await query.edit_message_text("❌ Investigación no encontrada")
        return
    
    config = INVESTIGACIONES[tipo]
    
    # ========== PROCESAR COLAS ==========
    procesar_cola(user_id)
    
    # ========== LEER DATOS EN TIEMPO REAL ==========
    recursos = obtener_recursos(user_id)
    datos_inv = obtener_datos_investigacion(user_id)
    nivel_actual = datos_inv["investigaciones"].get(tipo, 0)
    nivel_lab = obtener_nivel(user_id, "laboratorio")
    slots_max = calcular_slots(nivel_lab)
    username_tag = AuthSystem.obtener_username(user_id)
    
    # Verificar desbloqueo
    desbloqueadas = obtener_investigaciones_desbloqueadas(user_id)
    esta_desbloqueada = tipo in desbloqueadas
    
    # Calcular valores
    costo_proximo = calcular_costo(tipo, nivel_actual) if nivel_actual < config["max_nivel"] else {}
    tiempo_proximo = calcular_tiempo(tipo, nivel_actual, nivel_lab) if nivel_actual < config["max_nivel"] else 0
    
    # Verificar requisitos
    cumple_req, msg_req = verificar_requisitos(user_id, tipo)
    cumple_rec, msg_rec = verificar_recursos_suficientes(user_id, tipo, nivel_actual) if nivel_actual < config["max_nivel"] else (False, "")
    
    puede_investigar = (
        esta_desbloqueada and
        nivel_actual < config["max_nivel"] and
        cumple_req and
        cumple_rec and
        len(datos_inv["cola"]) < slots_max
    )
    
    # ========== CONSTRUIR MENSAJE ==========
    mensaje = (
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n"
        f"{config['icono']} <b>{config['nombre']}</b> - {username_tag}\n"
        f"🌀 ━━━━━━━━━━━━━━━━━━━ 🌀\n\n"
        f"💰 <b>TUS RECURSOS:</b>\n"
        f"🔩 Metal: {abreviar_numero(recursos.get('metal', 0))}\n"
        f"💎 Cristal: {abreviar_numero(recursos.get('cristal', 0))}\n"
        f"🧪 Deuterio: {abreviar_numero(recursos.get('deuterio', 0))}\n\n"
        f"📊 <b>NIVEL ACTUAL:</b> {nivel_actual}/{config['max_nivel']}\n"
        f"🎯 <b>BONIFICACIÓN:</b> {config['bonificacion']}\n\n"
    )
    
    if not esta_desbloqueada:
        mensaje += f"🔒 <b>TECNOLOGÍA BLOQUEADA</b>\n\n"
        mensaje += f"<b>Requisitos:</b>\n"
        cumple, detalles = verificar_requisitos(user_id, tipo)
        mensaje += detalles + "\n\n"
    elif nivel_actual >= config["max_nivel"]:
        mensaje += f"🏆 <b>¡NIVEL MÁXIMO ALCANZADO!</b>\n\n"
    else:
        tiempo_str = formatear_tiempo_corto(tiempo_proximo)
        
        mensaje += f"📈 <b>PRÓXIMO NIVEL ({nivel_actual + 1}):</b>\n\n"
        
        mensaje += f"💰 <b>COSTO:</b>\n"
        for recurso, cantidad in costo_proximo.items():
            icono = "🔩" if recurso == "metal" else "💎" if recurso == "cristal" else "🧪"
            disponible = recursos.get(recurso, 0)
            check = "✅" if disponible >= cantidad else "❌"
            mensaje += f"   {icono} {recurso.capitalize()}: {abreviar_numero(cantidad)} {check}\n"
        
        mensaje += f"\n⏱️ <b>TIEMPO:</b> {tiempo_str}\n"
        mensaje += f"📊 <b>SLOTS:</b> {len(datos_inv['cola'])}/{slots_max}\n\n"
    
    mensaje += f"📖 <b>DESCRIPCIÓN:</b>\n{config['descripcion']}\n"
    mensaje += f"\n🌀 ━━━━━━━━━━━━━━━━━━━ 🌀"
    
    if not cumple_req and esta_desbloqueada and nivel_actual < config["max_nivel"]:
        mensaje += f"\n\n❌ {msg_req}\n"
    
    # ========== TECLADO ==========
    keyboard = []
    
    if puede_investigar:
        keyboard.append([
            InlineKeyboardButton(
                f"🔬 INVESTIGAR NIVEL {nivel_actual + 1}",
                callback_data=f"investigar_{tipo}"
            )
        ])
    elif nivel_actual >= config["max_nivel"]:
        keyboard.append([
            InlineKeyboardButton("🏆 NIVEL MÁXIMO", callback_data="noop")
        ])
    elif not esta_desbloqueada:
        keyboard.append([
            InlineKeyboardButton("🔒 BLOQUEADA", callback_data="noop")
        ])
    else:
        razon = []
        if not cumple_req:
            razon.append("REQUISITOS")
        if not cumple_rec:
            razon.append("RECURSOS")
        if len(datos_inv["cola"]) >= slots_max:
            razon.append("SLOTS")
        
        keyboard.append([
            InlineKeyboardButton(f"🔒 {', '.join(razon)}", callback_data="noop")
        ])
    
    keyboard.append([
        InlineKeyboardButton("◀️ VOLVER", callback_data="menu_investigaciones"),
        InlineKeyboardButton("🏠 MENÚ", callback_data="menu_principal")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # ========== EDITAR MENSAJE ==========
    try:
        await query.edit_message_text(
            text=mensaje,
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"❌ Error editando submenú {tipo}: {e}")

# ================= INICIAR INVESTIGACIÓN HANDLER =================

@requiere_login
async def iniciar_investigacion_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🔬 Ejecuta el inicio de investigación"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    tipo = query.data.replace("investigar_", "")
    
    exito, mensaje = iniciar_investigacion_db(user_id, tipo)
    
    username_tag = AuthSystem.obtener_username(user_id)
    
    if exito:
        logger.info(f"✅ {username_tag} inició investigación {tipo}")
        
        keyboard = [
            [InlineKeyboardButton("🔬 VER INVESTIGACIONES", callback_data="menu_investigaciones")],
            [InlineKeyboardButton("🏠 MENÚ PRINCIPAL", callback_data="menu_principal")]
        ]
        
        await query.edit_message_text(
            text=mensaje,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
    else:
        logger.warning(f"❌ {username_tag} falló investigación {tipo}: {mensaje}")
        
        keyboard = [
            [InlineKeyboardButton("🔄 REINTENTAR", callback_data=f"investigacion_{tipo}")],
            [InlineKeyboardButton("◀️ VOLVER", callback_data="menu_investigaciones")]
        ]
        
        await query.edit_message_text(
            text=f"❌ <b>ERROR</b>\n\n{mensaje}",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )

# ================= 🕐 TAREA PROGRAMADA =================

async def procesar_colas_background(context: ContextTypes.DEFAULT_TYPE):
    """🔄 Procesa todas las colas de investigación"""
    logger.info("🔄 Procesando colas de investigación...")
    data = inicializar_db_investigaciones()
    
    for user_id_str in list(data.get("colas", {}).keys()):
        try:
            user_id = int(user_id_str)
            procesar_cola(user_id)
        except Exception as e:
            logger.error(f"❌ Error procesando investigación de {user_id_str}: {e}")
    
    logger.info("✅ Colas de investigación procesadas")

# ================= EXPORTAR =================

__all__ = [
    'menu_investigaciones_principal',
    'submenu_investigacion',
    'iniciar_investigacion_handler',
    'procesar_colas_background',
    'INVESTIGACIONES',
    'obtener_datos_investigacion'
]
