# app.py
import os
import io
import json
import base64
from fastapi import FastAPI, Query, Response
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Modo no interactivo para servidores
import matplotlib.pyplot as plt
from sklearn.tree import DecisionTreeClassifier
from sklearn.preprocessing import MultiLabelBinarizer

app = FastAPI(title="AgriPoli ML | Predicción de Polinizadores y Flora")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Polinizadores-Predichos", "X-Plantas-Predichas-Count"],
)

# Paleta Gruvbox Oficial
GRUVBOX = {
    "bg_main": "#fbf1c7",      # Gruvbox light fondo principal
    "bg_panel": "#ebdbb2",     # Gruvbox light fondo contenedor
    "bg_dark": "#282828",      # Gruvbox dark
    "text_main": "#3c3836",    # Texto principal oscuro
    "text_muted": "#7c6f64",   # Texto secundario
    "border": "#bdae93",       # Borde suave
    "border_strong": "#7c6f64",# Borde marcado
    "red": "#cc241d",
    "green": "#98971a",
    "yellow": "#d79921",
    "blue": "#458588",
    "purple": "#b16286",
    "aqua": "#689d6a",
    "orange": "#d65d0e",
}

def aplicar_estilo_gruvbox(fig, ax, titulo, xlabel, ylabel):
    fig.patch.set_facecolor(GRUVBOX["bg_main"])
    ax.set_facecolor(GRUVBOX["bg_panel"])
    for spine in ['bottom', 'left']:
        ax.spines[spine].set_color(GRUVBOX["text_main"])
        ax.spines[spine].set_linewidth(1.5)
    for spine in ['top', 'right']:
        ax.spines[spine].set_color(GRUVBOX["border"])
        ax.spines[spine].set_linewidth(1.0)
    
    ax.xaxis.label.set_color(GRUVBOX["text_main"])
    ax.xaxis.label.set_fontsize(11)
    ax.xaxis.label.set_fontweight('bold')
    
    ax.yaxis.label.set_color(GRUVBOX["text_main"])
    ax.yaxis.label.set_fontsize(11)
    ax.yaxis.label.set_fontweight('bold')
    
    ax.set_title(titulo, fontsize=13, fontweight='bold', color=GRUVBOX["text_main"], pad=14)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    
    ax.tick_params(axis='x', colors=GRUVBOX["text_main"], labelsize=9)
    ax.tick_params(axis='y', colors=GRUVBOX["text_main"], labelsize=9)
    ax.grid(True, linestyle='--', alpha=0.45, color=GRUVBOX["border_strong"])

# Rutas de datos resilientes (Docker /data o local ../data)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if os.path.exists("/data/polinizadores_mexico.csv"):
    DATA_DIR = "/data"
elif os.path.exists(os.path.join(BASE_DIR, "..", "data", "polinizadores_mexico.csv")):
    DATA_DIR = os.path.join(BASE_DIR, "..", "data")
elif os.path.exists(os.path.join(BASE_DIR, "data", "polinizadores_mexico.csv")):
    DATA_DIR = os.path.join(BASE_DIR, "data")
else:
    # Ruta absoluta al repo
    DATA_DIR = "/home/m4r10/Documents/AgriPoli/ML/data"

# Cargar datos
path_polinizadores = os.path.join(DATA_DIR, "polinizadores_mexico.csv")
path_plantas = os.path.join(DATA_DIR, "plantas_polinizadoras.csv")

df = pd.read_csv(path_polinizadores)
df['PolinizadoresLista'] = df['Polinizadores'].apply(lambda x: [p.strip() for p in x.split(",")])

df_plantas = pd.read_csv(path_plantas)
df_plantas['PlantasLista'] = df_plantas['NombreComún'].apply(lambda x: [str(x).strip()])

# Codificar etiquetas múltiples
mlb = MultiLabelBinarizer()
y_multi = mlb.fit_transform(df['PolinizadoresLista'])

# Variables de entrada (X)
X = df[['TemperaturaPromedio', 'AltitudPromedio']]

# Entrenar modelo multi-etiqueta
modelo = DecisionTreeClassifier(max_depth=4, random_state=0)
modelo.fit(X, y_multi)

@app.get("/health")
def health_check():
    return {
        "status": "online",
        "service": "AgriPoli ML Predictor",
        "data_dir": DATA_DIR,
        "polinizadores_disponibles": len(mlb.classes_),
        "plantas_disponibles": len(df_plantas)
    }

# Endpoint para predicción de polinizadores
@app.get("/polinizadores/")
def predecir_polinizadores(
    temperatura: float = Query(..., description="Temperatura promedio del estado (°C)"),
    altitud: float = Query(..., description="Altitud promedio del estado (m)"),
    grafica: bool = Query(False, description="Si es True, devuelve la gráfica como imagen"),
    formato_completo: bool = Query(False, description="Devuelve JSON con datos y gráfica en base64")
):
    nuevo_df = pd.DataFrame([[temperatura, altitud]], columns=['TemperaturaPromedio', 'AltitudPromedio'])
    prediccion = modelo.predict(nuevo_df)[0]
    polinizadores_predichos = [mlb.classes_[i] for i, val in enumerate(prediccion) if val == 1]

    if grafica or formato_completo:
        fig, ax = plt.subplots(figsize=(9, 6), dpi=150)
        gruv_colors = [
            GRUVBOX["green"], GRUVBOX["blue"], GRUVBOX["orange"], 
            GRUVBOX["purple"], GRUVBOX["yellow"], GRUVBOX["aqua"], GRUVBOX["red"]
        ]

        for i, especie in enumerate(mlb.classes_):
            indices_reales = [idx for idx, val in enumerate(y_multi[:, i]) if val == 1]
            color_sel = gruv_colors[i % len(gruv_colors)]
            ax.scatter(
                df.loc[indices_reales, 'TemperaturaPromedio'],
                df.loc[indices_reales, 'AltitudPromedio'],
                label=f"{especie} (datos)",
                s=65, edgecolor=GRUVBOX["text_main"], linewidth=0.8, color=color_sel, alpha=0.85
            )
            
            if especie in polinizadores_predichos:
                ax.scatter(
                    temperatura, altitud,
                    label=f"{especie} (predicho)",
                    color=color_sel, marker='X', s=200, edgecolor=GRUVBOX["text_main"], linewidth=1.5, zorder=5
                )

        aplicar_estilo_gruvbox(
            fig, ax,
            titulo="Distribucion de Polinizadores por Clima y Altitud",
            xlabel="Temperatura Promedio (°C)",
            ylabel="Altitud Promedio (msnm)"
        )

        leg = ax.legend(
            bbox_to_anchor=(1.02, 1), loc='upper left',
            frameon=True, facecolor=GRUVBOX["bg_main"], edgecolor=GRUVBOX["border_strong"],
            fontsize=8.5
        )
        for t in leg.get_texts():
            t.set_color(GRUVBOX["text_main"])

        buf = io.BytesIO()
        plt.tight_layout()
        fig.savefig(buf, format='png', facecolor=fig.get_facecolor(), edgecolor='none')
        buf.seek(0)
        plt.close(fig)

        if formato_completo:
            b64_img = base64.b64encode(buf.getvalue()).decode('utf-8')
            return JSONResponse(content={
                "polinizadores_predichos": polinizadores_predichos,
                "temperatura": temperatura,
                "altitud": altitud,
                "grafica_base64": f"data:image/png;base64,{b64_img}"
            })

        return StreamingResponse(
            buf, 
            media_type="image/png",
            headers={
                "X-Polinizadores-Predichos": json.dumps(polinizadores_predichos, ensure_ascii=False)
            }
        )

    return JSONResponse(content={"polinizadores_predichos": polinizadores_predichos})

@app.get("/floraEndemica/")
def predecir_flora(
    temperatura: float = Query(..., description="Temperatura promedio del estado (°C)"),
    humedad: float = Query(..., description="Humedad relativa promedio (%)"),
    altitud: float = Query(..., description="Altitud promedio del estado (m)"),
    grafica: bool = Query(False, description="Si es True, devuelve la gráfica como imagen"),
    formato_completo: bool = Query(False, description="Devuelve JSON con datos y gráfica en base64")
):
    df_temp = df_plantas.copy()

    # Limpiar espacios y convertir columnas numéricas
    for col in [
        "TemperaturaMin", "TemperaturaMax",
        "HumedadMin", "HumedadMax",
        "AltitudMin", "AltitudMax",
        "TemperaturaPromedio", "AltitudPromedio"
    ]:
        if col in df_temp.columns:
            df_temp[col] = pd.to_numeric(df_temp[col].astype(str).str.strip(), errors="coerce")

    # Filtro flexible (± tolerancia)
    tolerancia_temp = 2.5
    tolerancia_alt = 250.0
    tolerancia_hum = 12.0

    plantas_pred = df_temp[
        (df_temp["TemperaturaMin"] - tolerancia_temp <= temperatura) &
        (df_temp["TemperaturaMax"] + tolerancia_temp >= temperatura) &
        (df_temp["HumedadMin"] - tolerancia_hum <= humedad) &
        (df_temp["HumedadMax"] + tolerancia_hum >= humedad) &
        (df_temp["AltitudMin"] - tolerancia_alt <= altitud) &
        (df_temp["AltitudMax"] + tolerancia_alt >= altitud)
    ]

    registros_plantas = plantas_pred[[
        "Estado", "NombreComún", "NombreCientifico", "Familia",
        "TipoFlora", "TemperaturaMin", "TemperaturaMax",
        "HumedadMin", "HumedadMax", "AltitudMin", "AltitudMax"
    ]].to_dict(orient="records") if not plantas_pred.empty else []

    if grafica or formato_completo:
        fig, ax = plt.subplots(figsize=(9, 6), dpi=150)
        
        # Todas las especies como referencia
        ax.scatter(
            df_temp["TemperaturaPromedio"],
            df_temp["AltitudPromedio"],
            s=60, color=GRUVBOX["aqua"], alpha=0.55, 
            label="Catálogo Nacional de Flora", edgecolor=GRUVBOX["text_main"], linewidth=0.6
        )

        # Especies aptas
        if not plantas_pred.empty:
            for idx, (_, fila) in enumerate(plantas_pred.iterrows()):
                color_apt = GRUVBOX["orange"] if idx % 2 == 0 else GRUVBOX["yellow"]
                ax.scatter(
                    fila["TemperaturaPromedio"],
                    fila["AltitudPromedio"],
                    label=f"{fila['NombreComún']} (compatible)",
                    color=color_apt, marker='X', s=180, 
                    edgecolor=GRUVBOX["text_main"], linewidth=1.5, zorder=5
                )
        else:
            # Marcar el punto consultado aunque no haya match directo
            ax.scatter(
                temperatura, altitud,
                label="Condicion consultada (sin coincidencia)",
                color=GRUVBOX["red"], marker='o', s=160, 
                edgecolor=GRUVBOX["text_main"], linewidth=1.5, zorder=5
            )

        aplicar_estilo_gruvbox(
            fig, ax,
            titulo="Plantas Compatibles por Temperatura y Altitud",
            xlabel="Temperatura Promedio (°C)",
            ylabel="Altitud Promedio (msnm)"
        )

        leg = ax.legend(
            bbox_to_anchor=(1.02, 1), loc='upper left',
            frameon=True, facecolor=GRUVBOX["bg_main"], edgecolor=GRUVBOX["border_strong"],
            fontsize=8.5
        )
        for t in leg.get_texts():
            t.set_color(GRUVBOX["text_main"])

        buf = io.BytesIO()
        plt.tight_layout()
        fig.savefig(buf, format="png", facecolor=fig.get_facecolor(), edgecolor='none')
        buf.seek(0)
        plt.close(fig)

        if formato_completo:
            b64_img = base64.b64encode(buf.getvalue()).decode('utf-8')
            return JSONResponse(content={
                "plantas_predichas": registros_plantas,
                "total": len(registros_plantas),
                "temperatura": temperatura,
                "humedad": humedad,
                "altitud": altitud,
                "grafica_base64": f"data:image/png;base64,{b64_img}"
            })

        return StreamingResponse(
            buf, 
            media_type="image/png",
            headers={"X-Plantas-Predichas-Count": str(len(registros_plantas))}
        )

    if plantas_pred.empty:
        return JSONResponse(content={
            "mensaje": "No se encontraron plantas aptas para esas condiciones exactas.",
            "plantas_predichas": []
        })

    return JSONResponse(content={"plantas_predichas": registros_plantas})