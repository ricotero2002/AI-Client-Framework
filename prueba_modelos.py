from google import genai
from config import Config

api_key = Config.get_api_key("gemini")
client = genai.Client(api_key=api_key)

print("List of models that support generateContent:\n")
for m in client.models.list():
    for action in m.supported_actions:
        if action == "generateContent":
            print(m.name)