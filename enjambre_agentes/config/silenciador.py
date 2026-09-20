"""
Módulo de silenciamiento centralizado de advertencias (warnings) y logs ruidosos.
Garantiza una salida limpia en terminal suprimiendo warnings de librerías externas
(fontTools, pypdf, pdfminer, google, langchain, pydantic, urllib3).
"""
import os
import sys
import warnings
import logging

def silenciar_todo():
    """Suprime warnings a nivel de intérprete y eleva el umbral de logging para librerías ruidosas."""
    # 1. Variables de entorno del sistema
    os.environ["PYTHONWARNINGS"] = "ignore"
    os.environ["GRPC_VERBOSITY"] = "ERROR"
    os.environ["GLOG_minloglevel"] = "2"

    # 2. Filtro global de warnings de Python
    warnings.filterwarnings("ignore")
    warnings.simplefilter("ignore")

    # 3. Silenciar loggers específicos de librerías externas ruidosas
    loggers_a_silenciar = [
        "fontTools",
        "fontTools.cffLib",
        "fontTools.subset",
        "pypdf",
        "pdfminer",
        "pdfminer.pdfinterp",
        "pdfminer.pdfdocument",
        "pdfminer.psparser",
        "urllib3",
        "urllib3.connectionpool",
        "google",
        "google.genai",
        "google.generativeai",
        "langchain",
        "langchain_core",
        "langchain_community",
        "langchain_google_genai",
        "PIL",
        "sentence_transformers",
        "transformers",
    ]

    for nombre_logger in loggers_a_silenciar:
        logger = logging.getLogger(nombre_logger)
        logger.setLevel(logging.ERROR)
        logger.propagate = False

# Ejecutar automáticamente al ser importado
silenciar_todo()
