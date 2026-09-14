import urllib.request
import json
from my_keys import COHERE_API_KEY

print("Consultando directamente a la API de Cohere...\n")

url = "https://api.cohere.com/v1/models"
req = urllib.request.Request(url)

# A diferencia de Google, Cohere pide la llave en los "Headers" de la petición
req.add_header("Authorization", f"Bearer {COHERE_API_KEY}")
req.add_header("Accept", "application/json")

try:
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode('utf-8'))
        
        print("Modelos de Cohere disponibles para ti:")
        for model in data.get("models", []):
            # Filtramos para que solo muestre los modelos compatibles con chat
            if "chat" in model.get("endpoints", []):
                print(f"- {model['name']}")
                
except Exception as e:
    print(f"Error al consultar la API de Cohere: {e}")
