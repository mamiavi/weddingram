const csrftoken = getCookie('csrftoken');

// --- DOM Elements ---
const lightbox = document.getElementById('lightbox');
const addButton = document.getElementById('add-button');
const closeBtn = document.getElementById('closeBtn');
const galleryItems = document.querySelectorAll('.gallery-item');
const selectionBar = document.getElementById('selection-bar');
const downloadSelectedBtn = document.getElementById('download-selected-btn');
const selectAllBtn = document.getElementById('select-all-btn');
const cancelSelectBtn = document.getElementById('cancel-select-btn');
const downloadOverlay = document.getElementById('download-overlay');

// --- Lightbox ---
let swiper = null;

function loadSlideVideo(index) {
    const slide = document.querySelectorAll('.swiper-slide')[index];
    if (!slide) return;
    const video = slide.querySelector('video');
    if (video && !video.src && video.dataset.src) {
        video.src = video.dataset.src;
    }
}

function resetVideos() {
    const allVideos = document.querySelectorAll('.swiper-slide video');
    allVideos.forEach(video => {
        video.pause();
        video.currentTime = 0;
    });
}
function openLightbox(index) {
    lightbox.classList.add('active');
    addButton.classList.add('hidden');

    if (!swiper) {
    swiper = new Swiper('.swiper', {
        initialSlide: index,
        loop: false,
        navigation: {
        nextEl: '.swiper-button-next',
        prevEl: '.swiper-button-prev',
        },
        pagination: {
        el: '.swiper-pagination',
        clickable: true,
        },
        on: {
            slideChange: () => {
                resetVideos();
                loadSlideVideo(swiper.activeIndex);
            },
        }
    });
    } else {
    swiper.slideTo(index, 0);
    }
    loadSlideVideo(index)
    history.pushState({ lightboxOpen: true }, '');
}
function closeLightbox() {
    lightbox.classList.remove('active');
    addButton.classList.remove('hidden');
    if (history.state?.lightboxOpen) {
    history.back();
    }
    resetVideos();
}
closeBtn.addEventListener('click', closeLightbox);

window.addEventListener('popstate', () => {
    if (lightbox.classList.contains('active')) {
    closeLightbox();
    }
});

lightbox.addEventListener('click', (e) => {
    if (e.target === lightbox) {
    closeLightbox();
    }
});

// --- Select Mode ---
let selectionMode = false;
let selectedItems = new Set();
let longPressTimer = null;
let longPressTriggered = false;

galleryItems.forEach(item => {
    const media = item.querySelector('.gallery-media');

    // Right-click = selection mode
    media.addEventListener('contextmenu', (e) => {
        e.preventDefault();
        enterSelectionMode();
        selectItem(item);
    });

    // Touch start: begin long press detection
    media.addEventListener('touchstart', () => {
        longPressTriggered = false;

        longPressTimer = setTimeout(() => {
            longPressTriggered = true;
            enterSelectionMode();
            selectItem(item);
        }, 450);
    });

    // Touch end: cancel long-press timer
    media.addEventListener('touchend', () => {
        clearTimeout(longPressTimer);
    });

    // Click / tap
    media.addEventListener('click', (e) => {
        if (longPressTriggered) {
            // long-press already handled, block click
            e.stopPropagation();
            return;
        }

        if (selectionMode) {
            e.stopPropagation();
            toggleItem(item);
        } else {
            // Normal click → open lightbox
            const index = parseInt(media.dataset.index, 10);
            openLightbox(index);
        }
    });
});
function enterSelectionMode() {
    if (selectionMode) return;
    selectionMode = true;
    selectionBar.classList.remove('hidden');
    downloadSelectedBtn.classList.remove('hidden');
    addButton.classList.add('hidden');
}
function exitSelectionMode() {
    selectionMode = false;
    selectionBar.classList.add('hidden');
    downloadSelectedBtn.classList.add('hidden');
    addButton.classList.remove('hidden');

    selectedItems.clear();
    galleryItems.forEach(item => item.classList.remove('selected'));
}
function selectItem(item) {
    const key = item.dataset.id;
    if (!item.classList.contains('selected')) {
        item.classList.add('selected');
        selectedItems.add(key);
    }
}
function toggleItem(item) {
    const key = item.dataset.id;
    if (item.classList.contains('selected')) {
        item.classList.remove('selected');
        selectedItems.delete(key);
    } else {
        item.classList.add('selected');
        selectedItems.add(key);
    }
}
selectAllBtn.addEventListener('click', () => {
    galleryItems.forEach(item => {
        if (!item.classList.contains('selected')) {
            toggleItem(item);
        }
    });
});
cancelSelectBtn.addEventListener('click', exitSelectionMode);

// --- Download Selected ---
downloadSelectedBtn.addEventListener('click', async function () {
    if (selectedItems.size === 0) return;

    showDownloadOverlay();

    const formData = new FormData();
    [...selectedItems].forEach(id => formData.append('file_ids[]', id));

    try {
        const response = await fetch('/download_selected_zip/', {
            method: 'POST',
            headers: { 'X-CSRFToken': csrftoken },
            body: formData,
        });

        const contentType = response.headers.get('Content-Type') || '';

        if (contentType.includes('application/json')) {
            // Production: Lambda returned a presigned S3 URL
            const data = await response.json();
            if (data.error) {
                alert(data.error);
                return;
            }
            window.location.href = data.download_url;
        } else {
            // Local dev: server returned the zip file directly
            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'selected_files.zip';
            document.body.appendChild(a);
            a.click();
            a.remove();
            URL.revokeObjectURL(url);
        }
    } catch (err) {
        alert('Error al preparar la descarga. Inténtalo de nuevo.');
        console.error(err);
    } finally {
        hideDownloadOverlay();
    }
});

// --- Lightbox triggers for gallery media (images/videos) ---
const galleryImages = document.querySelectorAll('.gallery-img');
const galleryVideos = document.querySelectorAll('.gallery-video');
galleryImages.forEach(img => {
    img.addEventListener('click', () => {
    const index = parseInt(img.dataset.index, 10);
    openLightbox(index);
    });
});

galleryVideos.forEach(vid => {
    vid.addEventListener('click', () => {
    const index = parseInt(vid.dataset.index, 10);
    openLightbox(index);
    });
});

// --- Download animation ---
function showDownloadOverlay() {
    downloadOverlay.classList.remove('hidden');
}

function hideDownloadOverlay() {
    downloadOverlay.classList.add('hidden');
}

