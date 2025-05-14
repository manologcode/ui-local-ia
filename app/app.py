from flask import Flask, render_template, request, jsonify, request
import os
import sys
import time
from werkzeug.utils import secure_filename
from ollama import OllamaClient
from update_podcast import create_episode
import requests
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)
# Configuración
UPLOAD_FOLDER = '/app/static/uploads'
AUDIO_FOLDER = '/app/static/audio'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
ALLOWED_AUDIO_EXTENSIONS = {'mp3', 'wav', 'ogg'} # Added allowed audio extensions

# URLs de los servicios
OLLAMA_API_URL = os.environ.get('OLLAMA_API_URL', 'http://localhost:11434/api/generate')
XTTS_API_URL = os.environ.get('XTTS_API_URL', 'http://localhost:5008')
WHISPER_API_URL = os.environ.get('WHISPER_API_URL', 'http://localhost:5090')



PODCAST_TOKEN = os.environ.get('PODCAST_TOKEN', 'your_super_secret_token')
PODCAST_ID = os.environ.get('PODCAST_ID', 1)

# Asegúrate de que existe el directorio para las imágenes subidas
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(AUDIO_FOLDER, exist_ok=True) # Ensure audio directory exists

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Limitar tamaño a 16MB

# Inicializar el cliente de Ollama
ollama_client = OllamaClient()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def allowed_audio_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_AUDIO_EXTENSIONS

def check_service_connection(url, timeout=5):
    """Verifica si un servicio está disponible"""
    try:
        response = requests.get(url, timeout=timeout)
        return response.status_code == 200
    except:
        return False

def get_available_services():
    """Obtiene el estado de todos los servicios"""

    return {
        'ollama': check_service_connection(OLLAMA_API_URL),
        'xtts': check_service_connection(XTTS_API_URL),

        'whisper': check_service_connection(WHISPER_API_URL)
    }

@app.route('/')
def index():
    """Página principal con diferentes interacciones"""
    services_status = get_available_services()
    return render_template('index.html', services_status=services_status)

@app.route('/generate-text', methods=['GET', 'POST'])
def generate_text():
    """Endpoint para generar texto"""
    respuesta = None
    available_models = ollama_client.list_models()
    modelos_dict = {model: model for model in available_models} # Create a dictionary for the template

    if request.method == 'POST':
        # Obtener datos del formulario
        prompt = request.form.get('prompt', '')
        # Use the first available model as default if none is selected
        modelo_seleccionado = request.form.get('modelo', available_models[0] if available_models else None)

        if modelo_seleccionado:
            # Generar respuesta usando el cliente de Ollama
            respuesta = ollama_client.generate_response(prompt, modelo_seleccionado)
        else:
            respuesta = "Error: No models available from Ollama."


    return render_template('generate_text.html',
                         modelos=modelos_dict,
                         respuesta=respuesta)

@app.route('/text-to-audio', methods=['GET', 'POST'])
def text_to_audio():
    """Endpoint para convertir texto a audio"""
    xtts_api_url = os.environ.get('XTTS_API_URL', 'http://localhost:5008')
    # Construct the base URL for the Flask app
    # This assumes the app is accessed via the host and port it's running on
    # In a production environment, this might need to be more sophisticated
    api_base_url = f"http://{request.host}"
    return render_template('text_to_audio.html', xtts_api_url=xtts_api_url, api_base_url=api_base_url)

@app.route('/check-audio-status/<task_id>')
def check_audio_status(task_id):
    """Endpoint para verificar el estado de la generación de audio"""
    try:
        response = requests.get(f'{XTTS_API_URL}/status/{task_id}')
        if response.status_code == 200:
            status_data = response.json()
            if status_data.get('status') == 'completed':
                # Si está completado, obtener el audio
                audio_data = response.content
                audio_filename = f"audio_{int(time.time())}.mp3"
                audio_path = os.path.join('static', 'audio', audio_filename)

                # Asegurarse de que existe el directorio
                os.makedirs(os.path.dirname(audio_path), exist_ok=True)

                # Guardar el archivo
                with open(audio_path, 'wb') as f:
                    f.write(audio_data)

                return jsonify({
                    'status': 'completed',
                    'audio_url': f"/static/audio/{audio_filename}"
                })
            elif status_data.get('status') == 'failed':
                return jsonify({
                    'status': 'failed',
                    'error': 'Error en la generación del audio'
                })
            else:
                return jsonify({
                    'status': 'processing',
                    'message': 'El audio está siendo generado'
                })
        else:
            return jsonify({
                'status': 'error',
                'error': f"Error al verificar el estado: {response.status_code}"
            })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        })

@app.route('/image-to-text', methods=['GET', 'POST'])
def image_to_text():
    """Endpoint para convertir imágenes a texto"""
    respuesta = None
    imagen_subida = None
    error_message = None
    available_models = ollama_client.list_models()
    modelos_dict = {model: model for model in available_models} # Create a dictionary for the template

    if request.method == 'POST':
        # Obtener datos del formulario
        prompt = request.form.get('prompt', '')
        # Use the first available model as default if none is selected
        modelo_seleccionado = request.form.get('modelo', available_models[0] if available_models else None)

        # Obtener la ruta de la imagen subida
        imagen_subida = request.form.get('imagen_subida')

        if imagen_subida and modelo_seleccionado:
            # Construir la ruta completa
            filepath = os.path.join('/app','static', imagen_subida)
            # If we are using a multimodal model, prepare the image
            if os.path.exists(filepath):
                try:
                    respuesta = ollama_client.generate_response(prompt, modelo_seleccionado, filepath)
                except requests.exceptions.ConnectionError:
                    error_message = "Error de conexión: No se pudo conectar al servidor de Ollama. Por favor, verifica que el servidor esté en funcionamiento."
                    print(error_message, file=sys.stderr)
                except requests.exceptions.Timeout:
                    error_message = "Error de tiempo de espera: El servidor tardó demasiado en responder. Por favor, intenta de nuevo."
                    print(error_message, file=sys.stderr)
                except Exception as e:
                    error_message = f"Error inesperado: {str(e)}"
                    print(error_message, file=sys.stderr)
            else:
                error_message = "Error: No se ha encontrado la imagen en la ruta especificada."
                print(error_message, file=sys.stderr)
        elif not imagen_subida:
            error_message = "Error: No se ha subido ninguna imagen."
            print(error_message, file=sys.stderr)
        elif not modelo_seleccionado:
             error_message = "Error: No models available from Ollama."
             print(error_message, file=sys.stderr)


    return render_template('image_to_text.html',
                         modelos=modelos_dict,
                         respuesta=respuesta,
                         imagen_subida=imagen_subida,
                         error_message=error_message)

@app.route('/upload-image', methods=['POST'])
def upload_image():
    """Endpoint para subir imágenes de forma asíncrona"""
    if 'imagen' not in request.files:
        return jsonify({'success': False, 'error': 'No se encontró ninguna imagen'}), 400

    file = request.files['imagen']

    if file.filename == '':
        return jsonify({'success': False, 'error': 'No se seleccionó ninguna imagen'}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        imagen_subida = os.path.join('uploads', filename)

        return jsonify({'success': True, 'imagen_subida': imagen_subida}), 200

    return jsonify({'success': False, 'error': 'Tipo de archivo no permitido'}), 400

@app.route('/audio-to-text', methods=['GET', 'POST'])
def audio_to_text():
    """Endpoint for audio to text transcription"""
    transcription = None
    error_message = None

    if request.method == 'POST':
        if 'audioFile' not in request.files:
            error_message = "No audio file part in the request."
        else:
            file = request.files['audioFile']
            if file.filename == '':
                error_message = "No selected file."
            else:
                try:
                    # Send the audio file to the Whisper service
                    files = {'file': (file.filename, file.stream, file.content_type)}
                    whisper_url = 'http://192.168.1.69:5090/'
                    response = requests.post(whisper_url, files=files)

                    if response.status_code == 200:
                        transcription = response.json().get('text', 'No transcription received.')
                    else:
                        error_message = f"Error from Whisper service: {response.status_code} - {response.text}"
                except requests.exceptions.ConnectionError:
                    error_message = "Connection error: Could not connect to the Whisper service. Please ensure the service is running."
                except requests.exceptions.Timeout:
                    error_message = "Timeout error: The Whisper service took too long to respond. Please try again."
                except Exception as e:
                    error_message = f"An unexpected error occurred: {str(e)}"

    return render_template('audio_to_text.html',
                           transcription=transcription,
                           error_message=error_message)

@app.route('/upload-podcast', methods=['POST'])
def upload_podcast():
    """Endpoint to receive podcast metadata and trigger episode creation"""
    # Get JSON data from the request body
    data = request.get_json()

    if not data:
        return jsonify({'success': False, 'error': 'No JSON data received'}), 400

    text = data.get('text', '')
    title = data.get('title', '')
    mp3_url = data.get('mp3_url', '')

    if not mp3_url:
        return jsonify({'success': False, 'error': 'No mp3_url provided'}), 400

    try:
        response = requests.get(mp3_url, stream=True)
        response.raise_for_status()  # Raise an HTTPError for bad responses (4xx or 5xx)

        # Generate a unique filename
        timestamp = int(time.time())
        audio_filename = f"downloaded_audio_{timestamp}.mp3"
        file_path = os.path.join('/app', 'static', 'audio', audio_filename)

        # Ensure the directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # Save the downloaded file
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

    except requests.exceptions.RequestException as e:
        app.logger.error(f"Error downloading audio file: {e}")
        return jsonify({'success': False, 'error': f'Error downloading audio file: {e}'}), 500

    # Use the local file path for the episode creation
    data={ "token": PODCAST_TOKEN,
           "podcast_id": PODCAST_ID, # Assuming a fixed podcast_id for now
           "title": title,
           "description":text,
           "audio_filepath": file_path}

    # app.logger.info("----------------")
    # app.logger.info(data)

    episode_data = create_episode(**data)
    if episode_data:
        print("Episode created successfully:")
        print(episode_data)
    else:
        print("Failed to create episode.")

    # Construct the relative path for the response
    relative_mp3_path = os.path.join('static', 'audio', audio_filename)

    return jsonify({
        'success': True,
        'title': title,
        'mp3_path': relative_mp3_path
    }), 200




if __name__ == '__main__':
    # Configurar para que la aplicación sea accesible desde otros contenedores
    app.run(debug=True, host='0.0.0.0')
