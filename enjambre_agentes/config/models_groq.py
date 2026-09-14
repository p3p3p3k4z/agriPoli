import urllib.request
import json
from my_keys import GROQ_API_KEY

print("Consultando directamente a la API de Groq...\n")

url = "https://api.groq.com/openai/v1/models"
req = urllib.request.Request(url)

req.add_header("Authorization", f"Bearer {GROQ_API_KEY}")
req.add_header("Accept", "application/json")

try:
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode('utf-8'))
        
        print("Modelos de Groq disponibles para ti:")
        for model in data.get("data", []):
            print(f"- {model['id']}")
                
except Exception as e:
    print(f"Error al consultar la API de Groq: {e}")
