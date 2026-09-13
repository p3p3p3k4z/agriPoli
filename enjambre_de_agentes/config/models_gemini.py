import urllib.request
import json
from my_keys import GEMINI_API_KEY

print("Consultando directamente a la API de Google...\n")

url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_API_KEY}"
req = urllib.request.Request(url)

try:
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode('utf-8'))
        
        print("Modelos disponibles para generación de texto (Chat):")
        for model in data.get("models", []):
            if "generateContent" in model.get("supportedGenerationMethods", []):
                print(f"- {model['name'].replace('models/', '')}")
                
        print("\nModelos disponibles para Embeddings:")
        for model in data.get("models", []):
            if "embedContent" in model.get("supportedGenerationMethods", []):
                print(f"- {model['name'].replace('models/', '')}")
                
except Exception as e:
    print(f"Error al consultar la API: {e}")
