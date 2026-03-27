class HorizontalScroll {
    constructor() {
        this.section = document.querySelector('#how_it_works');
        this.wrapper = this.section.querySelector('.horizontal-scroll-wrapper');
        this.progressFill = this.section.querySelector('.progress-fill');
        
        if (!this.section) return;
        this.init();
    }

    init() {
        const sections = gsap.utils.toArray('.step-section');
        
        gsap.to(sections, {
            xPercent: -100 * (sections.length - 1),
            ease: "none",
            scrollTrigger: {
                trigger: this.section,
                pin: true,
                scrub: 1.5,
                snap: 1 / (sections.length - 1),
                end: () => "+=" + this.section.offsetWidth * 3,
                onUpdate: self => {
                    this.progressFill.style.width = (self.progress * 100) + '%';
                }
            }
        });

        // Animate elements within steps on enter
        sections.forEach((step, i) => {
            gsap.from(step.querySelector('.step-card'), {
                y: 50,
                opacity: 0,
                duration: 1,
                scrollTrigger: {
                    trigger: step,
                    containerAnimation: gsap.getProperty(sections, "xPercent"),
                    start: "left center",
                    toggleActions: "play none none reverse"
                }
            });
        });
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new HorizontalScroll();
});
