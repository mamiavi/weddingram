// Upload
// Set options for compresion
const options = { 
    maxSizeMB: 5, 
    fileType: 'image/webp', //seems to do nothing
}
const newExtension = 'webp';

// Get the token to call the protected API
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
const csrftoken = getCookie('csrftoken');

const fileInput = document.getElementById('upload-photo');

fileInput.addEventListener('change', async function () {
    const files = fileInput.files;
    if (files.length === 0) return;

    const isValidMimeType = file =>
        file.type.startsWith('image/') || file.type.startsWith('video/');

    const invalidFiles = [...files].filter(file => !isValidMimeType(file));
    if (invalidFiles.length > 0) {
        alert("Solo puedes subir archivos de imagen o video.");
        fileInput.value = '';  // Reset file input
        return;
    }

    const totalSize = [...files].reduce((sum, file) => sum + file.size, 0);
    const maxSize = 250 * 1024 * 1024; // 500MB

    if (totalSize > maxSize) {
        alert("El tamaño total de los archivos no puede exceder de 500MB.");
        fileInput.value = ''; // Reset the input
        return;
    }

    // Add some kind of uploading animation

    await Promise.all([...files].map(uploadFile));

    window.location.href = '/gallery';

});

async function uploadFile(file) {
    let uploadFile = file;
    let newName = file.name;

    if (file.type.startsWith('image/')) {
        const compressedBlob = await imageCompression(file, options);
        newName = file.name.replace(/\.\w+$/, `.${newExtension}`);
        uploadFile = new File([compressedBlob], newName, { type: compressedBlob.type });
    }

    // Get the URL to upload the file
    const formData = new FormData();
    formData.append('file_name', newName);
    const resURL = await fetch('/get_upload_url/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrftoken
        },
        credentials: 'same-origin',
        body: formData
    });

    const {pload, public_url, key} = await resURL.json();

    // Upload file to storage
    const data = new FormData();
    if (pload.fields) {
        Object.entries(pload.fields).forEach(([k, v]) => data.append(k, v));
    }
    data.append('file', uploadFile);

    await fetch(pload.url, {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrftoken
        },
        body: data
    });

    // Notify BE to store the S3 URL in the db
    if (public_url) {
        const formData = new FormData();
        formData.append('key', key);
        await fetch('/save_file_url/', {
            method: 'POST',
            headers: {
            'X-CSRFToken': csrftoken
            },
            body: formData
        });
    }

}