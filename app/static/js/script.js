// Enhanced Pollution Check App JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Initialize form handling
    initFormValidation();
    initFormDependencies(); // Call this after validation setup

    // Initialize dashboard animations
    initDashboardAnimations();

    // Initialize chart interactions
    initChartInteractions();
});

// Form validation with visual feedback
function initFormValidation() {
    const forms = document.querySelectorAll('form');
    console.log(`Found ${forms.length} forms.`); // Debug log

    forms.forEach(form => {
        const inputs = form.querySelectorAll('input[required], select[required]');
        console.log(`Found ${inputs.length} required inputs/selects in a form.`); // Debug log

        inputs.forEach(input => {
            input.addEventListener('blur', function() {
                validateInput(this);
            });
            input.addEventListener('change', function() { // Also validate on change for selects
                validateInput(this);
            });

            // Initial validation state if field has value on load
            if (input.value && !(input.type === 'select-one' && input.selectedIndex === 0 && input.options[0].disabled)) {
                validateInput(input);
            } else {
                // Ensure fields start without validation classes unless pre-filled correctly
                 input.classList.remove('is-valid', 'is-invalid');
            }
        });

        form.addEventListener('submit', function(e) {
            console.log("Form submit event triggered."); // Debug log
            let isFormValid = true;

            inputs.forEach(input => {
                if (!validateInput(input)) {
                    isFormValid = false;
                    console.log(`Input invalid: ${input.id || input.name}`); // Debug log
                }
            });

            if (!isFormValid) {
                e.preventDefault(); // Stop submission
                console.log("Form submission prevented due to invalid fields."); // Debug log
                showFormError("Please fill all required fields correctly before submitting.");
            } else {
                console.log("Form is valid, applying loading state."); // Debug log
                // Add loading state
                form.classList.add('loading');
                const submitBtn = form.querySelector('button[type="submit"]');
                if (submitBtn) {
                    // Disable button and show spinner (handled by CSS loading state)
                    submitBtn.disabled = true;
                    // If you want to change text (optional, CSS handles spinner):
                    // submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processing...';
                }
                // Note: In a real app, you wouldn't use setTimeout here. The loading state
                // would be removed upon receiving a response from the server.
            }
        });
    });
}

// Validate a single input
function validateInput(input) {
    let isValid = true;
    const feedbackElement = input.parentElement.querySelector('.invalid-feedback'); // More robust selector

    if (input.hasAttribute('required')) {
        if (!input.value) {
            isValid = false;
        } else if (input.type === 'select-one' && input.selectedIndex === 0 && input.options[0].disabled) {
             // Check specifically if the disabled placeholder is selected
             isValid = false;
        }
        // Add more specific validation rules here if needed (e.g., regex for vehicle number)
    }

    if (isValid) {
        input.classList.remove('is-invalid');
        input.classList.add('is-valid');
        if (feedbackElement) {
            // feedbackElement.textContent = ''; // Optionally clear error message
        }
    } else {
        input.classList.remove('is-valid');
        input.classList.add('is-invalid');
        // Optionally set specific error messages
        // if (feedbackElement) {
        //     feedbackElement.textContent = input.validationMessage || 'This field is required.';
        // }
    }
    return isValid;
}


// Display a general form error message (e.g., for submission failure)
function showFormError(message) {
    let alertContainer = document.querySelector('.form-alert-container');
    // Create a container if it doesn't exist, typically above the form
    if (!alertContainer) {
        alertContainer = document.createElement('div');
        alertContainer.className = 'form-alert-container mb-3'; // Add margin bottom
        const form = document.querySelector('form');
        if (form) {
             form.parentNode.insertBefore(alertContainer, form);
        }
    }

    // Remove existing alert first
    const existingAlert = alertContainer.querySelector('.alert-form-error');
    if (existingAlert) {
        existingAlert.remove();
    }

    // Create the new alert
    const alert = document.createElement('div');
    alert.className = 'alert alert-danger alert-dismissible fade show alert-form-error';
    alert.setAttribute('role', 'alert');
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    alertContainer.appendChild(alert);

    // Optional: Auto dismiss after some time
    // setTimeout(() => {
    //     const bsAlert = bootstrap.Alert.getOrCreateInstance(alert); // Use getOrCreateInstance
    //     if (bsAlert) {
    //         bsAlert.close();
    //     }
    // }, 5000);
}


// Handle form dependencies (Vehicle Type based on Wheels)
function initFormDependencies() {
    const wheelsSelect = document.getElementById('wheels');
    const vehicleTypeSelect = document.getElementById('vehicle_type');

    if (wheelsSelect && vehicleTypeSelect) {
        console.log("Initializing form dependencies. Initial wheels value:", wheelsSelect.value); // Debug

        // Event listener for when wheels selection changes
        wheelsSelect.addEventListener('change', function() {
            updateVehicleTypeOptions(this.value);
            // Reset validation state of vehicle type when wheels change
            vehicleTypeSelect.classList.remove('is-valid', 'is-invalid');
            vehicleTypeSelect.selectedIndex = 0; // Reset selection to placeholder
            validateInput(vehicleTypeSelect); // Re-validate (will likely be invalid now)
        });

        // Initial update on page load if a value is already selected
        if (wheelsSelect.value) {
            updateVehicleTypeOptions(wheelsSelect.value);
            // If vehicle_type also had a value (from server-side repopulation), validate it
            if (vehicleTypeSelect.value) {
                validateInput(vehicleTypeSelect);
            }
        } else {
             // If no wheels selected initially, ensure vehicle type is cleared and placeholder shown
             updateVehicleTypeOptions(''); // Pass empty value
        }
    } else {
        if (!wheelsSelect) console.error("Wheels select element ('#wheels') not found!");
        if (!vehicleTypeSelect) console.error("Vehicle Type select element ('#vehicle_type') not found!");
    }
}

// --- REVISED FUNCTION using DOM methods ---
function updateVehicleTypeOptions(wheelsValue) {
    const vehicleTypeSelect = document.getElementById('vehicle_type');
    console.log("Updating vehicle type options for wheels:", wheelsValue); // Debug log

    if (vehicleTypeSelect) {
        // Store the currently selected value *before* clearing, if any
        const previouslySelectedValue = vehicleTypeSelect.value;

        // --- Clear existing options (keeping the placeholder) ---
        while (vehicleTypeSelect.options.length > 1) {
            vehicleTypeSelect.remove(1); // Remove the second option repeatedly
        }

        // --- Add New Options using DOM methods ---
        function addOption(value, text) {
            const option = document.createElement('option');
            option.value = value;
            option.textContent = text;
            vehicleTypeSelect.appendChild(option);
            console.log("Added option:", value, text); // Debug log
        }

        // Reset selection to placeholder (index 0) initially
        vehicleTypeSelect.selectedIndex = 0;
        vehicleTypeSelect.disabled = true; // Disable initially

        // Add options based on the selected number of wheels
        if (wheelsValue === '2') {
            addOption('petrol', 'Petrol');
            vehicleTypeSelect.disabled = false; // Enable the select
            // Auto-select 'petrol' for 2-wheelers
            vehicleTypeSelect.value = 'petrol';
            console.log("Auto-selected 'petrol' for 2W.");
            // Since it's auto-selected, mark as valid immediately
             validateInput(vehicleTypeSelect); // Validate the auto-selected value

        } else if (wheelsValue === '3' || wheelsValue === '4') {
            addOption('petrol', 'Petrol');
            addOption('diesel', 'Diesel');
             vehicleTypeSelect.disabled = false; // Enable the select
            // Try to restore previous selection if it's valid for 3/4 wheelers
            if (previouslySelectedValue && (previouslySelectedValue === 'petrol' || previouslySelectedValue === 'diesel')) {
                vehicleTypeSelect.value = previouslySelectedValue;
                console.log("Restored previous selection:", previouslySelectedValue);
                // Re-validate if restored
                validateInput(vehicleTypeSelect);
            } else {
                 // If no previous valid selection, leave placeholder selected
                 vehicleTypeSelect.selectedIndex = 0;
                 vehicleTypeSelect.classList.remove('is-valid', 'is-invalid');
            }
        } else {
            // If wheelsValue is empty or invalid, keep placeholder and disable
            console.log("No valid wheels value ('', null, etc.), keeping only placeholder and disabling.");
            vehicleTypeSelect.selectedIndex = 0;
            vehicleTypeSelect.disabled = true;
            vehicleTypeSelect.classList.remove('is-valid', 'is-invalid');
        }
    } else {
        console.error("Cannot update options: Vehicle Type select element not found!");
    }
}


// Dashboard animations (cards, numbers)
function initDashboardAnimations() {
    // Animate dashboard cards on load using Intersection Observer for performance
    const cards = document.querySelectorAll('.card, .summary-card'); // Include summary cards too
    const cardObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach((entry, index) => {
            if (entry.isIntersecting) {
                // Add delay based on index for staggered effect
                entry.target.style.transitionDelay = `${index * 50}ms`; // 50ms delay per card
                entry.target.classList.add('fade-in-up');
                observer.unobserve(entry.target); // Stop observing once animated
            }
        });
    }, { threshold: 0.1 }); // Trigger when 10% of the card is visible

    cards.forEach(card => {
        card.classList.add('observed'); // Add class to set initial state (opacity 0, transform)
        cardObserver.observe(card);
    });

    // Animate numbers in Total Sales card
    const totalSalesEl = document.querySelector('.summary-card .card-body h3.card-title');
    if (totalSalesEl && totalSalesEl.textContent.includes('₹')) {
        const numValue = parseFloat(totalSalesEl.textContent.replace(/[^0-9.]+/g, "")); // Allow decimals
        if (!isNaN(numValue) && numValue > 0) {
            // Animate from 0 to the actual value
            animateValue(totalSalesEl, 0, numValue, 1500);
        } else if (numValue === 0) {
             // Ensure zero is formatted correctly if animation isn't needed
             totalSalesEl.textContent = `₹ 0.00`;
        }
    }
}

// Helper for number animation
function animateValue(element, start, end, duration) {
    let startTimestamp = null;
    const prefix = '₹ ';
    const decimalPlaces = 2; // For currency

    const step = (timestamp) => {
        if (!startTimestamp) startTimestamp = timestamp;
        const progress = Math.min((timestamp - startTimestamp) / duration, 1);
        // Calculate value, potentially non-integer for currency
        const currentVal = progress * (end - start) + start;
        // Format to fixed decimal places
        element.textContent = `${prefix}${currentVal.toFixed(decimalPlaces)}`;

        if (progress < 1) {
            window.requestAnimationFrame(step);
        } else {
             // Ensure final value is exact and formatted
             element.textContent = `${prefix}${end.toFixed(decimalPlaces)}`;
        }
    };

    window.requestAnimationFrame(step);
}

// Chart interactions (basic hover effect)
function initChartInteractions() {
    // Animate charts on load using Intersection Observer
    const chartImages = document.querySelectorAll('.chart-container img');
    const chartObserver = new IntersectionObserver((entries, observer) => {
         entries.forEach((entry, index) => {
            if (entry.isIntersecting) {
                entry.target.style.transitionDelay = `${100 + index * 100}ms`; // Delay after cards
                entry.target.classList.add('fade-in-scale');
                observer.unobserve(entry.target); // Stop observing once animated
            }
        });
    }, { threshold: 0.2 }); // Trigger when 20% visible

    chartImages.forEach(img => {
         img.classList.add('observed-chart'); // Initial state for animation

        // Add hover effect (already in CSS, just ensure JS doesn't interfere if not needed)
        // img.addEventListener('mouseenter', function() {
        //     this.style.transform = 'scale(1.05)';
        // });
        // img.addEventListener('mouseleave', function() {
        //     this.style.transform = 'scale(1)';
        // });

        chartObserver.observe(img); // Observe for load animation
    });
}

// Add CSS rules for observed elements if not already in style.css
// (Usually better to define these in CSS)
/* Example CSS for animations (should be in style.css):
.observed {
  opacity: 0;
  transform: translateY(20px);
  transition: opacity 0.6s ease-out, transform 0.6s ease-out;
}
.observed.fade-in-up {
  opacity: 1;
  transform: translateY(0);
}
.observed-chart {
  opacity: 0;
  transform: scale(0.95);
  transition: opacity 0.6s ease-out, transform 0.6s ease-out;
}
.observed-chart.fade-in-scale {
  opacity: 1;
  transform: scale(1);
}
*/