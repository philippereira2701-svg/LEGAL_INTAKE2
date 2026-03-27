class MagneticButton {
    constructor() {
        this.buttons = document.querySelectorAll('.btn-primary, .nav-logo');
        if (window.matchMedia('(hover: hover)').matches) {
            this.init();
        }
    }

    init() {
        this.buttons.forEach(btn => {
            btn.addEventListener('mousemove', (e) => {
                const rect = btn.getBoundingClientRect();
                const x = e.clientX - rect.left - rect.width / 2;
                const y = e.clientY - rect.top - rect.height / 2;

                gsap.to(btn, {
                    x: x * 0.3,
                    y: y * 0.3,
                    duration: 0.6,
                    ease: 'power2.out'
                });
            });

            btn.addEventListener('mouseleave', () => {
                gsap.to(btn, {
                    x: 0,
                    y: 0,
                    duration: 0.8,
                    ease: 'elastic.out(1, 0.3)'
                });
            });
        });
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new MagneticButton();
});
