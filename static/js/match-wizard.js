class MatchWizard {
    constructor() {
        this.modal = document.getElementById('match-modal');
        this.overlay = document.querySelector('.modal-overlay');
        this.form = document.getElementById('intake-form');
        this.steps = Array.from(document.querySelectorAll('.form-wizard-step'));
        this.currentStep = 0;
        
        this.init();
    }

    init() {
        const trigger = document.querySelectorAll('.nav-cta, .hero-search button');
        trigger.forEach(btn => {
            btn.addEventListener('click', () => this.open());
        });

        document.querySelector('.close-modal').addEventListener('click', () => this.close());
        this.overlay.addEventListener('click', () => this.close());

        this.form.addEventListener('submit', (e) => this.handleSubmit(e));
    }

    open() {
        this.modal.classList.add('active');
        this.overlay.classList.add('active');
        this.showStep(0);
        document.body.style.overflow = 'hidden';
    }

    close() {
        this.modal.classList.remove('active');
        this.overlay.classList.remove('active');
        document.body.style.overflow = '';
    }

    showStep(n) {
        this.steps.forEach((step, i) => {
            step.classList.toggle('active', i === n);
        });
        this.currentStep = n;
    }

    nextStep() {
        if (this.currentStep < this.steps.length - 1) {
            this.showStep(this.currentStep + 1);
        }
    }

    async handleSubmit(e) {
        e.preventDefault();
        const formData = new FormData(this.form);
        const data = Object.fromEntries(formData.entries());
        
        // Show loading state
        const submitBtn = this.form.querySelector('button[type="submit"]');
        const originalText = submitBtn.textContent;
        submitBtn.textContent = 'Processing...';
        submitBtn.disabled = true;

        try {
            const response = await fetch('/intake', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            const result = await response.json();
            if (result.status === 'success') {
                this.showSuccess(result.action);
            } else {
                throw new Error(result.message);
            }
        } catch (err) {
            alert('Error: ' + err.message);
        } finally {
            submitBtn.textContent = originalText;
            submitBtn.disabled = false;
        }
    }

    showSuccess(action) {
        const body = this.modal.querySelector('.modal-body');
        body.innerHTML = `
            <div class="text-center py-8">
                <div class="badge badge-success mb-4">Case Submitted</div>
                <h2 class="display-md mb-4">We've Found Your Matches.</h2>
                <p class="body-lg text-secondary mb-8">Our AI has analyzed your situation. An attorney will contact you within 60 seconds.</p>
                <div class="badge badge-gold">${action}</div>
                <button class="btn btn-primary mt-8 w-full" onclick="location.reload()">Return Home</button>
            </div>
        `;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new MatchWizard();
});
