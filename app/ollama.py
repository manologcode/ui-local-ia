import os
import requests
import base64
import sys

class OllamaClient:
    def __init__(self, base_api_url=None):
        """
        Inicializa el cliente de Ollama.

        Args:
            base_api_url (str, optional): URL base de la API de Ollama. Si no se proporciona,
                                   se usa la variable de entorno OLLAMA_API_URL o
                                   el valor por defecto 'http://localhost:11434'
        """
        self.base_api_url = base_api_url or os.environ.get('OLLAMA_API_URL', 'http://localhost:11434')
        self.generate_url = f'{self.base_api_url}/api/generate'
        self.tags_url = f'{self.base_api_url}/api/tags'

    def generate_response(self, prompt, modelo, imagen_path=None):

        try:
            payload = self._prepare_payload(prompt, modelo, imagen_path)
            response = requests.post(self.generate_url, json=payload)

            if response.status_code == 200:
                respuesta = response.json()
                return respuesta['response']
            else:
                return f"Error: {response.status_code} - {response.text}"

        except Exception as e:
            return f"Error en la conexión: {str(e)}"

    def _prepare_payload(self, prompt, modelo, imagen_path=None):
        payload = {
            'model': modelo,
            'prompt': prompt,
            'stream': False
        }

        if imagen_path and os.path.exists(imagen_path):
            with open( imagen_path, 'rb') as img_file:
                img_base64 = base64.b64encode(img_file.read()).decode('utf-8')
                payload['images'] = [img_base64]

        return payload

    def list_models(self):

        try:
            response = requests.get(self.tags_url)
            response.raise_for_status()  # Raise an exception for bad status codes

            data = response.json()
            models = [model['name'] for model in data.get('models', [])]
            return models

        except requests.exceptions.RequestException as e:
            print(f"Error fetching models: {e}", file=sys.stderr)
            return []
