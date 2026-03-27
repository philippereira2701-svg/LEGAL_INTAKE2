class CustomCursor {
    constructor() {
        this.cursor = document.querySelector('.custom-cursor');
        this.label = this.cursor.querySelector('.cursor-label');
        this.pos = { x: 0, y: 0 };
        this.mouse = { x: 0, y: 0 };
        this.speed = 0.15;

        this.init();
    }

    init() {
        window.addEventListener('mousemove', e => {
            this.mouse.x = e.clientX;
            this.mouse.y = e.clientY;
        });

        this.animate();
        this.handleHover();
    }

    animate() {
        this.pos.x += (this.mouse.x - this.pos.x) * this.speed;
        this.pos.y += (this.mouse.y - this.pos.y) * this.speed;

        this.cursor.style.transform = `translate3d(${this.pos.x}px, ${this.pos.y}px, 0) translate(-50%, -50%)`;

        requestAnimationFrame(() => this.animate());
    }

    handleHover() {
        const hoverables = document.querySelectorAll('a, button, .attorney-card, .chip');
        
        hoverables.forEach(el => {
            el.addEventListener('mouseenter', () => {
                this.cursor.classList.add('active');
                if (el.dataset.cursor) {
                    this.label.textContent = el.dataset.cursor;
                } else {
                    this.label.textContent = 'VIEW';
                }
            });

            el.addEventListener('mouseleave', () => {
                this.cursor.classList.remove('active');
                this.label.textContent = '';
            });
        });

        const ctas = document.querySelectorAll('.btn-primary');
        ctas.forEach(el => {
            el.addEventListener('mouseenter', () => {
                this.cursor.classList.add('cta');
                this.label.textContent = '→';
            });
            el.addEventListener('mouseleave', () => {
                this.cursor.classList.remove('cta');
            });
        });
    }
}

document.addEventListener('DOMContentLoaded', () => {
    // Only init if not on touch device
    if (window.matchMedia('(hover: hover)').matches) {
        new CustomCursor();
    }
});
