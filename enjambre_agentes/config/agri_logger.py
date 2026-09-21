"""
Sistema de logging y trazabilidad expresivo para el Sistema Multiagente AgriPoli.
Combina etiquetas formales en mayúsculas con kaomojis ASCII para reflejar
emociones y estados cognitivos de los agentes, garantizando una salida
limpia en texto plano sin emojis gráficos.
"""
from typing import Any

# Estilos de formato opcionales (compatibles con texto plano en terminal)
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
MAGENTA = "\033[95m"
RED = "\033[91m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

_USAR_COLORES = True


# Catálogo de Kaomojis Emocionales para Agentes Multiagente
KAOMOJIS_EMOCIONES = {
    "ALEGRIA":      "(^o^)",
    "ENTUSIASMO":   "(^_^)/",
    "CURIOSIDAD":   "(o.O)?",
    "INDAGACION":   "(・_・)?",
    "CONCENTRACION":"(˘_˘)",
    "ANALISIS":     "[._.]",
    "ASOMBRO":      "(*_*)!",
    "DESCUBRIMIENTO":"[O_O]!",
    "DETERMINACION":"(ง •̀_•́)ง",
    "TRABAJO_DURO": "(>_<)",
    "CAUTELA":      "(¬_¬)",
    "ALERTA":       "(ಠ_ಠ)",
    "EMPATIA":      "(^-^)",
    "ESCUCHA":      "( ´ ▽ ` )",
    "PREOCUPACION": "(>_<;)",
    "DESCONCIERTO": "(・_・;)",
    "ERROR":        "[X_X]",
    "FRUSTRACION":  "(T_T)",
    "CELEBRACION":  "\\(^o^)/",
    "LOGRO":        "\\(*_*)/",
    "SALUDO":       "(^-^)/",
}


def configurar_formato(colores: bool = True):
    """Activa o desactiva colores ANSI según preferencia de texto plano puro."""
    global _USAR_COLORES
    _USAR_COLORES = colores


def _fmt(tag: str, kaomoji: str, msg: str, color: str = "") -> str:
    if _USAR_COLORES and color:
        return f"{color}{BOLD}{kaomoji} {tag}{RESET} {msg}"
    return f"{kaomoji} {tag} {msg}"


def log_agente(agente: str, msg: str, kaomoji: str = "(o_o)"):
    """Registra la actividad y estado emocional de un agente principal."""
    tag = f"[AGENTE: {agente.upper()}]"
    print(_fmt(tag, kaomoji, msg, CYAN), flush=True)


def log_mini_agente(nombre: str, msg: str, kaomoji: str = "(O_O)"):
    """Registra la actividad de un mini-agente o worker paralelo."""
    tag = f"[MINI-AGENTE: {nombre.upper()}]"
    print(_fmt(tag, kaomoji, msg, MAGENTA), flush=True)


def log_herramienta(nombre: str, msg: str, kaomoji: str = "(>_<)"):
    """Registra la invocación o retorno de una herramienta."""
    tag = f"[HERRAMIENTA: {nombre}]"
    print(_fmt(tag, kaomoji, msg, YELLOW), flush=True)


def log_flujo(origen: str, destino: str, detalle: str = "", kaomoji: str = "[>_<]"):
    """Registra la comunicación y transición de estado a través de LangGraph."""
    tag = "[FLUX LANGGRAPH]"
    if detalle:
        msg = f"{origen} -> {destino} ({detalle})"
    else:
        msg = f"{origen} -> {destino}"
    print(_fmt(tag, kaomoji, msg, GREEN), flush=True)


def log_emocion(agente: str, emocion: str, msg: str):
    """Registra un cambio de estado emocional formal del agente."""
    kaomoji = KAOMOJIS_EMOCIONES.get(emocion.upper(), "(o_o)")
    tag = f"[AGENTE: {agente.upper()}] [{emocion.upper()}]"
    print(_fmt(tag, kaomoji, msg, CYAN), flush=True)


def log_ok(msg: str, kaomoji: str = "(^_^)/"):
    """Registra una operación exitosa o logro."""
    print(_fmt("[OK]", kaomoji, msg, GREEN), flush=True)


def log_info(msg: str, kaomoji: str = "(o_o)"):
    """Registra información general del sistema."""
    print(_fmt("[INFO]", kaomoji, msg, CYAN), flush=True)


def log_alerta(msg: str, kaomoji: str = "(¬_¬)"):
    """Registra una advertencia o cautela técnica."""
    print(_fmt("[ALERTA]", kaomoji, msg, YELLOW), flush=True)


def log_error(msg: str, kaomoji: str = "[X_X]"):
    """Registra un error controlado."""
    print(_fmt("[ERROR]", kaomoji, msg, RED), flush=True)

