// Gallery
const lightbox = document.getElementById('lightbox');
const addButton = document.getElementById('add-button');
const closeBtn = document.getElementById('closeBtn');
const galleryImages = document.querySelectorAll('.gallery-img');

let swiper = null;

galleryImages.forEach(img => {
    img.addEventListener('click', () => {
    const index = parseInt(img.dataset.index, 10);
    openLightbox(index);
    });
});

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