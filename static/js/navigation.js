class Navigation {
    constructor() {
        this.nav = document.querySelector('.navbar');
        this.init();
    }

    init() {
        window.addEventListener('scroll', () => {
            if (window.scrollY > 80) {
                this.nav.classList.add('scrolled');
            } else {
                this.nav.classList.remove('scrolled');
            }
        });

        // Mobile Menu logic would go here
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new Navigation();
});
