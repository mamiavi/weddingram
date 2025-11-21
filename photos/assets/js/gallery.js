// Gallery
const lightbox = document.getElementById('lightbox');
const addButton = document.getElementById('add-button');
const closeBtn = document.getElementById('closeBtn');
const galleryImages = document.querySelectorAll('.gallery-img');
const galleryVideos = document.querySelectorAll('.gallery-video');

let swiper = null;

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

function resetVideos() {
    const allVideos = document.querySelectorAll('.swiper-slide video');
    allVideos.forEach(video => {
        video.pause();
        video.currentTime = 0;
        video.load();
    });
}

function openLightbox(index) {
    lightbox.classList.add('active');
    addButton.classList.add('hidden');

    resetVideos();

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
            },
        }
    });
    } else {
    swiper.slideTo(index, 0);
    }

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

window.addEventListener('popstate', (e) => {
    if (lightbox.classList.contains('active')) {
    closeLightbox();
    }
});

lightbox.addEventListener('click', (e) => {
    if (e.target === lightbox) {
    closeLightbox();
    }
});

let selectionMode = false;
let selectedItems = new Set();

const galleryItems = document.querySelectorAll('.gallery-item');
const selectionBar = document.getElementById('selection-bar');
const downloadSelectedBtn = document.getElementById('download-selected-btn');
const selectAllBtn = document.getElementById('select-all-btn');
const cancelSelectBtn = document.getElementById('cancel-select-btn');

let longPressTimer = null;
let longPressTriggered = false;

galleryItems.forEach(item => {
    const media = item.querySelector('.gallery-media');

    // Right-click = selection mode
    media.addEventListener('contextmenu', (e) => {
        e.preventDefault();
        enterSelectionMode();
        toggleItem(item);
    });

    // Touch start: begin long press detection
    media.addEventListener('touchstart', () => {
        longPressTriggered = false;

        longPressTimer = setTimeout(() => {
            longPressTriggered = true;
            enterSelectionMode();
            toggleItem(item);
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

// Enter selection mode
function enterSelectionMode() {
    if (selectionMode) return;
    selectionMode = true;
    selectionBar.classList.remove('hidden');
    downloadSelectedBtn.classList.remove('hidden');
    addButton.classList.add('hidden');
}

// Toggle an item
function toggleItem(item) {
    const key = item.dataset.key;
    if (item.classList.contains('selected')) {
        item.classList.remove('selected');
        selectedItems.delete(key);
    } else {
        item.classList.add('selected');
        selectedItems.add(key);
    }
}

// Select all
selectAllBtn.addEventListener('click', () => {
    galleryItems.forEach(item => {
        if (!item.classList.contains('selected')) {
            toggleItem(item);
        }
    });
});

// Exit selection mode
cancelSelectBtn.addEventListener('click', exitSelectionMode);

function exitSelectionMode() {
    selectionMode = false;
    selectionBar.classList.add('hidden');
    downloadSelectedBtn.classList.add('hidden');
    addButton.classList.remove('hidden');

    selectedItems.clear();
    galleryItems.forEach(item => item.classList.remove('selected'));
}