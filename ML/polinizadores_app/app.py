# app.py
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse, StreamingResponse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.tree import DecisionTreeClassifier
from sklearn.preprocessing import MultiLabelBinarizer
import io


from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Predicción de Polinizadores en México")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # "*" permite todas las conexiones (útil para desarrollo)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cargar datos 
df = pd.read_csv("/data/polinizadores_mexico.csv")
df['PolinizadoresLista'] = df['Polinizadores'].apply(lambda x: x.split(", "))

df_plantas = pd.read_csv("/data/plantas_polinizadoras.csv")  
df_plantas['PlantasLista'] = df_plantas['NombreComún'].apply(lambda x: [x])  


# Codificar etiquetas múltiples 
mlb = MultiLabelBinarizer()
y_multi = mlb.fit_transform(df['PolinizadoresLista'])

# Variables de entrada (X) 
X = df[['TemperaturaPromedio', 'AltitudPromedio']]

# Entrenar modelo multi-etiqueta 
modelo = DecisionTreeClassifier(max_depth=4, random_state=0)
modelo.fit(X, y_multi)

# Endpoint para predicción 
@app.get("/polinizadores/")
def predecir_polinizadores(
    temperatura: float = Query(..., description="Temperatura promedio del estado (°C)"),
    altitud: float = Query(..., description="Altitud promedio del estado (m)"),
    grafica: bool = Query(False, description="Si es True, devuelve la gráfica como imagen")
):
    nuevo_estado = [[temperatura, altitud]]
    prediccion = modelo.predict(nuevo_estado)[0]
    polinizadores_predichos = [mlb.classes_[i] for i, val in enumerate(prediccion) if val == 1]

    if grafica:
        # Generar gráfica 
        fig, ax = plt.subplots(figsize=(10,7))
        colors = ['blue','green','orange','purple']

        for i, especie in enumerate(mlb.classes_):
            indices_reales = [idx for idx, val in enumerate(y_multi[:,i]) if val == 1]
            ax.scatter(df.loc[indices_reales, 'TemperaturaPromedio'],
                       df.loc[indices_reales, 'AltitudPromedio'],
                       label=f"{especie} (real)",
                       s=70, edgecolor='black', color=colors[i])
            
            if especie in polinizadores_predichos:
                ax.scatter(nuevo_estado[0][0], nuevo_estado[0][1],
                           label=f"{especie} (predicho)",
                           color=colors[i], marker='x', s=200)

        ax.set_title("Predicción de Polinizadores según condiciones ambientales", fontsize=14)
        ax.set_xlabel("Temperatura promedio (°C)")
        ax.set_ylabel("Altitud promedio (m)")
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        ax.grid(True)

        buf = io.BytesIO()
        plt.tight_layout()
        fig.savefig(buf, format='png')
        buf.seek(0)
        plt.close(fig)
        return StreamingResponse(buf, media_type="image/png")

    return JSONResponse(content={"polinizadores_predichos": polinizadores_predichos})

@app.get("/floraEndemica/")
def predecir_flora(
    temperatura: float = Query(..., description="Temperatura promedio del estado (°C)"),
    humedad: float = Query(..., description="Humedad relativa promedio (%)"),
    altitud: float = Query(..., description="Altitud promedio del estado (m)"),
    grafica: bool = Query(False, description="Si es True, devuelve la gráfica como imagen")
):
    df_temp = df_plantas.copy()

    # Limpiar espacios y convertir columnas numéricas
    for col in [
        "TemperaturaMin", "TemperaturaMax",
        "HumedadMin", "HumedadMax",
        "AltitudMin", "AltitudMax",
        "TemperaturaPromedio", "AltitudPromedio"
    ]:
        df_temp[col] = pd.to_numeric(df_temp[col].astype(str).str.strip(), errors="coerce")

    # Filtro flexible (± tolerancia)
    tolerancia_temp = 2.0
    tolerancia_alt = 200.0
    tolerancia_hum = 10.0

    plantas_pred = df_temp[
        (df_temp["TemperaturaMin"] - tolerancia_temp <= temperatura) &
        (df_temp["TemperaturaMax"] + tolerancia_temp >= temperatura) &
        (df_temp["HumedadMin"] - tolerancia_hum <= humedad) &
        (df_temp["HumedadMax"] + tolerancia_hum >= humedad) &
        (df_temp["AltitudMin"] - tolerancia_alt <= altitud) &
        (df_temp["AltitudMax"] + tolerancia_alt >= altitud)
    ]

    # Si no encuentra ninguna
    if plantas_pred.empty:
        return JSONResponse(content={
            "mensaje": "No se encontraron plantas aptas para esas condiciones.",
        })

    # Si se solicito grafica
    if grafica:
        fig, ax = plt.subplots(figsize=(10,7))
        ax.scatter(
            df_temp["TemperaturaPromedio"],
            df_temp["AltitudPromedio"],
            s=70, color='green', alpha=0.6, label="Todas las plantas", edgecolor='black'
        )

        for _, fila in plantas_pred.iterrows():
            ax.scatter(
                fila["TemperaturaPromedio"],
                fila["AltitudPromedio"],
                label=f"{fila['NombreComún']} (apta)",
                color='orange', marker='x', s=200
            )

        ax.set_title("Plantas endémicas posibles según condiciones", fontsize=14)
        ax.set_xlabel("Temperatura promedio (°C)")
        ax.set_ylabel("Altitud promedio (m)")
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        ax.grid(True)

        buf = io.BytesIO()
        plt.tight_layout()
        fig.savefig(buf, format="png")
        buf.seek(0)
        plt.close(fig)
        return StreamingResponse(buf, media_type="image/png")

    return JSONResponse(content={
        "plantas_predichas": plantas_pred[[
            "Estado", "NombreComún", "NombreCientifico", "Familia",
            "TipoFlora", "TemperaturaMin", "TemperaturaMax",
            "HumedadMin", "HumedadMax", "AltitudMin", "AltitudMax"
        ]].to_dict(orient="records")
    })