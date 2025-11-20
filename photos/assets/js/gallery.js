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