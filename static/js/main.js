document.addEventListener('DOMContentLoaded', () => {
    // Initialize Lenis Smooth Scroll
    const lenis = new Lenis({
        duration: 1.4,
        easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
        direction: 'vertical',
        gestureDirection: 'vertical',
        smooth: true,
        mouseMultiplier: 1,
        smoothTouch: false,
        touchMultiplier: 2,
        infinite: false,
    });

    function raf(time) {
        lenis.raf(time);
        requestAnimationFrame(raf);
    }

    requestAnimationFrame(raf);

    // Register GSAP Plugins
    gsap.registerPlugin(ScrollTrigger, Flip);

    // Global ScrollTrigger defaults
    ScrollTrigger.defaults({
        toggleActions: 'play none none reverse',
        markers: false
    });

    // Splitting.js
    Splitting();

    // Reveal Animations
    const revealText = document.querySelectorAll('.reveal-text');
    revealText.forEach(el => {
        const chars = el.querySelectorAll('.char');
        gsap.from(chars, {
            y: 100,
            opacity: 0,
            duration: 1,
            stagger: 0.02,
            ease: 'power4.out',
            delay: 1.5 // After preloader
        });
    });

    // Section Eyebrows
    gsap.utils.toArray('.label.accent-color').forEach(label => {
        gsap.from(label, {
            scrollTrigger: {
                trigger: label,
                start: 'top 90%',
            },
            x: -20,
            opacity: 0,
            duration: 1,
            ease: 'power3.out'
        });
    });

    // Card Entrances
    gsap.utils.toArray('.card').forEach(card => {
        gsap.from(card, {
            scrollTrigger: {
                trigger: card,
                start: 'top 95%',
            },
            y: 40,
            opacity: 0,
            duration: 1.2,
            ease: 'expo.out'
        });
    });

    console.log('LexBridge Core & Motion Initialized');
});
