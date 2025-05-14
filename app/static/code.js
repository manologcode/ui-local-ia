// Elementos DOM
const dropArea = document.getElementById('drop-area');
const fileInput = document.getElementById('imagen');
const previewContainer = document.getElementById('preview-container');
const previewImage = document.getElementById('preview-image');
const submitBtn = document.getElementById('submit-btn');
const uploadLoader = document.getElementById('upload-loader');
const uploadStatusContainer = document.getElementById('upload-status-container');
const uploadStatusMessage = document.getElementById('upload-status-message');
const serverPreviewContainer = document.getElementById('server-preview-container');

// Si hay una imagen ya subida, activar el botón de envío
if (document.getElementById('imagen_subida')) {
    submitBtn.disabled = false;
}

// Prevenir comportamiento predeterminado del navegador para eventos de arrastrar y soltar
['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
    dropArea.addEventListener(eventName, preventDefaults, false);
});

function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
}

// Destacar el área de soltar cuando se arrastra un archivo
['dragenter', 'dragover'].forEach(eventName => {
    dropArea.addEventListener(eventName, highlight, false);
});

['dragleave', 'drop'].forEach(eventName => {
    dropArea.addEventListener(eventName, unhighlight, false);
});

function highlight() {
    dropArea.style.borderColor = 'var(--primary-color)';
    dropArea.style.backgroundColor = 'rgba(67, 97, 238, 0.05)';
}

function unhighlight() {
    dropArea.style.borderColor = '';
    dropArea.style.backgroundColor = '';
}

// Manejar archivos soltados
dropArea.addEventListener('drop', handleDrop, false);

function handleDrop(e) {
    const dt = e.dataTransfer;
    const files = dt.files;

    if (files.length) {
        fileInput.files = files;
        uploadImage(files[0]);
    }
}

// Manejar archivos seleccionados
fileInput.addEventListener('change', function() {
    if (fileInput.files && fileInput.files[0]) {
        uploadImage(fileInput.files[0]);
    }
});

// Manejar imágenes pegadas
dropArea.addEventListener('paste', handlePaste, false);

function handlePaste(e) {
    const items = (e.clipboardData || window.clipboardData).items;
    let blob = null;

    for (let i = 0; i < items.length; i++) {
        if (items[i].type.indexOf('image') === 0) {
            blob = items[i].getAsFile();
            break;
        }
    }

    if (blob) {
        uploadImage(blob);
    } else {
        showUploadStatus('Por favor, pega solo imágenes', 'error');
    }
}

// Función para mostrar la vista previa de la imagen
function showPreview(file) {
    if (!file.type.match('image.*')) {
        showUploadStatus('Por favor, selecciona solo archivos de imagen', 'error');
        return;
    }

    const reader = new FileReader();

    reader.onload = function(e) {
        previewImage.src = e.target.result;
        previewContainer.style.display = 'block';

        // Ocultar la vista previa del servidor si existe
        if (serverPreviewContainer) {
            serverPreviewContainer.style.display = 'none';
        }
    }

    reader.readAsDataURL(file);
}

// Función para subir la imagen al servidor
function uploadImage(file) {
    if (!file.type.match('image.*')) {
        showUploadStatus('Por favor, selecciona solo archivos de imagen', 'error');
        return;
    }

    // Mostrar cargador
    uploadLoader.style.display = 'flex';

    // Crear un FormData para enviar la imagen
    const formData = new FormData();
    formData.append('imagen', file);

    // Enviar la imagen al servidor usando fetch API
    fetch('/upload-image', {
        method: 'POST',
        body: formData
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Error al subir la imagen');
        }
        return response.json();
    })
    .then(data => {
        // Ocultar cargador
        uploadLoader.style.display = 'none';

        if (data.success) {
            // Mostrar la imagen subida
            showPreview(file);

            // Mostrar mensaje de éxito
            showUploadStatus('Imagen subida correctamente', 'success');

            // Guardar la ruta de la imagen en un input oculto
            const hiddenInput = document.createElement('input');
            hiddenInput.type = 'hidden';
            hiddenInput.name = 'imagen_subida';
            hiddenInput.value = data.imagen_subida;
            document.getElementById('ollama-form').appendChild(hiddenInput);

            // Activar el botón de envío
            submitBtn.disabled = false;
        } else {
            showUploadStatus(data.error || 'Error al subir la imagen', 'error');
        }
    })
    .catch(error => {
        // Ocultar cargador
        uploadLoader.style.display = 'none';

        // Mostrar error
        showUploadStatus(error.message, 'error');
    });
}

// Función para mostrar mensaje de estado
function showUploadStatus(message, status) {
    uploadStatusContainer.style.display = 'block';
    uploadStatusMessage.textContent = message;

    // Eliminar todas las clases de estado
    uploadStatusContainer.classList.remove('success', 'error');

    // Añadir la clase de estado correspondiente
    if (status) {
        uploadStatusContainer.classList.add(status);
    }

    // Ocultar el mensaje después de 5 segundos
    setTimeout(() => {
        uploadStatusContainer.style.display = 'none';
    }, 5000);
}

// Si hay una respuesta del formulario, desplazarse hasta ella
if (document.querySelector('.response-container')) {
    document.querySelector('.response-container').scrollIntoView({ behavior: 'smooth' });
}
