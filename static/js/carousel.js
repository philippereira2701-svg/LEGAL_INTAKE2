class TestimonialCarousel {
    constructor() {
        this.container = document.querySelector('.testimonial-quote');
        this.author = document.querySelector('.author-name');
        this.location = document.querySelector('.author-location');
        this.prevBtn = document.querySelector('.prev-testimonial');
        this.nextBtn = document.querySelector('.next-testimonial');
        
        this.testimonials = [
            {
                quote: "After my accident, I was lost. LexBridge matched me with David in minutes. He won my case in 4 months and I received $2.4M in settlement.",
                author: "Jennifer R.",
                location: "Los Angeles, CA"
            },
            {
                quote: "The custody battle was terrifying. Sarah Chen guided us through every step. My children are now safe, and I can't imagine going through this without LexBridge.",
                author: "Michael T.",
                location: "Austin, TX"
            },
            {
                quote: "As a first-generation immigrant, navigating the legal system felt impossible. LexBridge connected me with an attorney who changed everything.",
                author: "Ana M.",
                location: "Miami, FL"
            }
        ];
        
        this.currentIndex = 0;
        this.init();
    }

    init() {
        if (!this.container) return;

        this.prevBtn.addEventListener('click', () => this.show(this.currentIndex - 1));
        this.nextBtn.addEventListener('click', () => this.show(this.currentIndex + 1));
        
        this.updateUI();
    }

    show(index) {
        if (index < 0) index = this.testimonials.length - 1;
        if (index >= this.testimonials.length) index = 0;
        
        const tl = gsap.timeline();
        tl.to([this.container, this.author, this.location], {
            opacity: 0,
            y: -10,
            duration: 0.3,
            onComplete: () => {
                this.currentIndex = index;
                this.updateUI();
                gsap.to([this.container, this.author, this.location], {
                    opacity: 1,
                    y: 0,
                    duration: 0.5,
                    stagger: 0.1
                });
            }
        });
    }

    updateUI() {
        const t = this.testimonials[this.currentIndex];
        this.container.textContent = t.quote;
        this.author.textContent = t.author;
        this.location.textContent = t.location;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new TestimonialCarousel();
});
