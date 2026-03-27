class Preloader {
    constructor() {
        this.overlay = document.querySelector('.preloader-overlay');
        this.wordmark = document.querySelector('.preloader-wordmark');
        this.subtext = document.querySelector('.preloader-subtext');
        this.counter = document.querySelector('.preloader-counter');
        
        this.init();
    }

    init() {
        const tl = gsap.timeline({
            onComplete: () => {
                document.body.classList.remove('loading');
            }
        });

        tl.to(this.wordmark, {
            opacity: 1,
            duration: 1.2,
            ease: 'power3.out'
        })
        .from(this.subtext, {
            y: 20,
            opacity: 0,
            duration: 0.8,
            ease: 'power3.out'
        }, '-=0.4')
        .to({}, { duration: 1 }) // Wait
        .to('.preloader-panel.left', {
            yPercent: -100,
            duration: 1.1,
            ease: 'power4.inOut'
        })
        .to('.preloader-panel.right', {
            yPercent: 100,
            duration: 1.1,
            ease: 'power4.inOut'
        }, '-=1.1')
        .to(this.overlay, {
            display: 'none'
        });
    }
}

// Add loading class to body
document.body.classList.add('loading');
window.addEventListener('load', () => {
    new Preloader();
});
