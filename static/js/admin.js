/**
 * Djobea AI Admin Panel JavaScript
 * Handles client-side functionality for the admin interface
 */

class DjobeaAdmin {
    constructor() {
        this.init();
        this.setupEventListeners();
        this.startAutoRefresh();
    }

    init() {
        console.log('Djobea AI Admin Panel initialized');
        this.setupFormValidation();
        this.setupTooltips();
        this.setupConfirmationDialogs();
    }

    setupEventListeners() {
        // Provider form validation
        const addProviderForm = document.querySelector('#addProviderModal form');
        if (addProviderForm) {
            addProviderForm.addEventListener('submit', this.validateProviderForm.bind(this));
        }

        // Auto-refresh controls
        const refreshButton = document.createElement('button');
        refreshButton.className = 'btn btn-outline-secondary btn-sm me-2';
        refreshButton.innerHTML = '<i class="fas fa-sync-alt"></i> Actualiser';
        refreshButton.addEventListener('click', () => this.refreshPage());

        // Add refresh button to navigation if not exists
        const navbar = document.querySelector('.navbar .container');
        if (navbar && !document.querySelector('#refresh-btn')) {
            refreshButton.id = 'refresh-btn';
            navbar.appendChild(refreshButton);
        }

        // Handle provider status toggle confirmations
        const statusForms = document.querySelectorAll('form[action*="/toggle-status"]');
        statusForms.forEach(form => {
            form.addEventListener('submit', this.confirmStatusToggle.bind(this));
        });

        // Handle request cancellation confirmations
        const cancelForms = document.querySelectorAll('form[action*="/cancel"]');
        cancelForms.forEach(form => {
            form.addEventListener('submit', this.confirmCancellation.bind(this));
        });

        // Search and filter functionality
        this.setupSearch();
        this.setupFilters();
    }

    setupFormValidation() {
        // Phone number validation for Cameroon
        const phoneInputs = document.querySelectorAll('input[name="whatsapp_id"], input[name="phone_number"]');
        phoneInputs.forEach(input => {
            input.addEventListener('input', this.validateCameroonPhone.bind(this));
        });

        // Service validation
        const servicesInput = document.querySelector('input[name="services"]');
        if (servicesInput) {
            servicesInput.addEventListener('input', this.validateServices.bind(this));
        }
    }

    validateProviderForm(event) {
        const form = event.target;
        const formData = new FormData(form);
        
        // Validate WhatsApp ID
        const whatsappId = formData.get('whatsapp_id');
        if (!this.isValidCameroonPhone(whatsappId)) {
            event.preventDefault();
            this.showError('Numéro WhatsApp invalide. Format attendu: +237XXXXXXXXX');
            return false;
        }

        // Validate phone number
        const phoneNumber = formData.get('phone_number');
        if (!this.isValidCameroonPhone(phoneNumber)) {
            event.preventDefault();
            this.showError('Numéro de téléphone invalide. Format attendu: +237XXXXXXXXX');
            return false;
        }

        // Validate services
        const services = formData.get('services');
        const validServices = ['plomberie', 'électricité', 'réparation électroménager'];
        const serviceList = services.split(',').map(s => s.trim().toLowerCase());
        
        const invalidServices = serviceList.filter(service => !validServices.includes(service));
        if (invalidServices.length > 0) {
            event.preventDefault();
            this.showError(`Services non supportés: ${invalidServices.join(', ')}. Services disponibles: ${validServices.join(', ')}`);
            return false;
        }

        // Show loading state
        this.showLoading(form);
        return true;
    }

    validateCameroonPhone(event) {
        const input = event.target;
        const value = input.value;
        
        if (value && !this.isValidCameroonPhone(value)) {
            input.classList.add('is-invalid');
            this.showFieldError(input, 'Format invalide. Utilisez +237XXXXXXXXX');
        } else {
            input.classList.remove('is-invalid');
            this.hideFieldError(input);
        }
    }

    isValidCameroonPhone(phone) {
        // Remove spaces and special characters
        const cleanPhone = phone.replace(/[\s\-\(\)]/g, '');
        
        // Check Cameroon phone number patterns
        const patterns = [
            /^\+237[67]\d{8}$/,  // International format
            /^237[67]\d{8}$/,    // Without +
            /^[67]\d{8}$/        // Local format
        ];
        
        return patterns.some(pattern => pattern.test(cleanPhone));
    }

    validateServices(event) {
        const input = event.target;
        const validServices = ['plomberie', 'électricité', 'réparation électroménager'];
        const services = input.value.split(',').map(s => s.trim().toLowerCase());
        
        const invalidServices = services.filter(service => 
            service && !validServices.includes(service)
        );
        
        if (invalidServices.length > 0) {
            input.classList.add('is-invalid');
            this.showFieldError(input, `Services non supportés: ${invalidServices.join(', ')}`);
        } else {
            input.classList.remove('is-invalid');
            this.hideFieldError(input);
        }
    }

    setupTooltips() {
        // Initialize Bootstrap tooltips
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }

    setupConfirmationDialogs() {
        // Add confirmation for destructive actions
        const destructiveButtons = document.querySelectorAll('[onclick*="confirm"]');
        destructiveButtons.forEach(button => {
            const originalOnclick = button.getAttribute('onclick');
            button.removeAttribute('onclick');
            button.addEventListener('click', (e) => {
                e.preventDefault();
                const confirmed = confirm('Êtes-vous sûr de vouloir effectuer cette action ?');
                if (confirmed) {
                    eval(originalOnclick);
                }
            });
        });
    }

    confirmStatusToggle(event) {
        const form = event.target;
        const action = form.action;
        
        let message = 'Confirmer le changement de statut ?';
        if (action.includes('toggle-status')) {
            message = 'Changer le statut actif/inactif du prestataire ?';
        } else if (action.includes('toggle-availability')) {
            message = 'Changer la disponibilité du prestataire ?';
        }
        
        if (!confirm(message)) {
            event.preventDefault();
            return false;
        }
        
        this.showLoading(form);
        return true;
    }

    confirmCancellation(event) {
        const message = 'Êtes-vous sûr de vouloir annuler cette demande ? Cette action est irréversible.';
        if (!confirm(message)) {
            event.preventDefault();
            return false;
        }
        
        this.showLoading(event.target);
        return true;
    }

    setupSearch() {
        // Add search functionality to tables
        const searchInputs = document.querySelectorAll('.search-input');
        searchInputs.forEach(input => {
            input.addEventListener('input', this.debounce(this.performSearch.bind(this), 300));
        });

        // Create search input for providers table
        const providersTable = document.querySelector('.card:has(table) .card-header');
        if (providersTable && !document.querySelector('#provider-search')) {
            const searchDiv = document.createElement('div');
            searchDiv.className = 'mt-2';
            searchDiv.innerHTML = `
                <input type="text" id="provider-search" class="form-control search-input" 
                       placeholder="Rechercher un prestataire...">
            `;
            providersTable.appendChild(searchDiv);
            
            document.getElementById('provider-search').addEventListener('input', 
                this.debounce(this.searchProviders.bind(this), 300)
            );
        }
    }

    searchProviders(event) {
        const searchTerm = event.target.value.toLowerCase();
        const rows = document.querySelectorAll('tbody tr');
        
        rows.forEach(row => {
            const text = row.textContent.toLowerCase();
            if (text.includes(searchTerm) || searchTerm === '') {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        });
    }

    setupFilters() {
        // Status filter for requests
        const statusTabs = document.querySelectorAll('.nav-tabs .nav-link');
        statusTabs.forEach(tab => {
            tab.addEventListener('click', (e) => {
                // Update active tab styling
                statusTabs.forEach(t => t.classList.remove('active'));
                e.target.classList.add('active');
            });
        });
    }

    startAutoRefresh() {
        // Auto-refresh dashboard every 30 seconds
        if (window.location.pathname === '/admin' || window.location.pathname === '/admin/') {
            setInterval(() => {
                this.refreshStats();
            }, 30000);
        }
    }

    async refreshStats() {
        try {
            const response = await fetch('/admin', {
                headers: {
                    'Accept': 'application/json'
                }
            });
            
            if (response.ok) {
                // Update only the stats cards without full page reload
                this.updateStatsDisplay();
            }
        } catch (error) {
            console.error('Error refreshing stats:', error);
        }
    }

    updateStatsDisplay() {
        // Add visual indication of last update
        const lastUpdate = document.getElementById('last-update');
        if (!lastUpdate) {
            const updateIndicator = document.createElement('small');
            updateIndicator.id = 'last-update';
            updateIndicator.className = 'text-muted';
            updateIndicator.textContent = `Dernière mise à jour: ${new Date().toLocaleTimeString()}`;
            
            const header = document.querySelector('h1');
            if (header) {
                header.parentElement.appendChild(updateIndicator);
            }
        } else {
            lastUpdate.textContent = `Dernière mise à jour: ${new Date().toLocaleTimeString()}`;
        }
    }

    refreshPage() {
        // Show loading indicator
        const refreshBtn = document.getElementById('refresh-btn');
        if (refreshBtn) {
            const originalContent = refreshBtn.innerHTML;
            refreshBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Actualisation...';
            refreshBtn.disabled = true;
            
            setTimeout(() => {
                window.location.reload();
            }, 500);
        } else {
            window.location.reload();
        }
    }

    showLoading(form) {
        const submitBtn = form.querySelector('button[type="submit"]');
        if (submitBtn) {
            const originalContent = submitBtn.innerHTML;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Traitement...';
            submitBtn.disabled = true;
            
            // Store original content for potential restoration
            submitBtn.dataset.originalContent = originalContent;
        }
    }

    showError(message) {
        // Create or update error alert
        let errorAlert = document.getElementById('error-alert');
        if (!errorAlert) {
            errorAlert = document.createElement('div');
            errorAlert.id = 'error-alert';
            errorAlert.className = 'alert alert-danger alert-dismissible fade show';
            errorAlert.innerHTML = `
                <i class="fas fa-exclamation-triangle"></i>
                <span class="error-message">${message}</span>
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `;
            
            const container = document.querySelector('.container');
            if (container) {
                container.insertBefore(errorAlert, container.firstChild);
            }
        } else {
            errorAlert.querySelector('.error-message').textContent = message;
        }
        
        // Auto-hide after 5 seconds
        setTimeout(() => {
            if (errorAlert) {
                errorAlert.remove();
            }
        }, 5000);
    }

    showSuccess(message) {
        const successAlert = document.createElement('div');
        successAlert.className = 'alert alert-success alert-dismissible fade show';
        successAlert.innerHTML = `
            <i class="fas fa-check-circle"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        const container = document.querySelector('.container');
        if (container) {
            container.insertBefore(successAlert, container.firstChild);
        }
        
        setTimeout(() => successAlert.remove(), 3000);
    }

    showFieldError(input, message) {
        // Remove existing error
        this.hideFieldError(input);
        
        const errorDiv = document.createElement('div');
        errorDiv.className = 'invalid-feedback';
        errorDiv.textContent = message;
        
        input.parentElement.appendChild(errorDiv);
    }

    hideFieldError(input) {
        const existingError = input.parentElement.querySelector('.invalid-feedback');
        if (existingError) {
            existingError.remove();
        }
    }

    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    performSearch(event) {
        const searchTerm = event.target.value.toLowerCase();
        const table = event.target.closest('.card').querySelector('table tbody');
        
        if (table) {
            const rows = table.querySelectorAll('tr');
            rows.forEach(row => {
                const text = row.textContent.toLowerCase();
                row.style.display = text.includes(searchTerm) || searchTerm === '' ? '' : 'none';
            });
        }
    }

    // Utility methods for real-time notifications
    showNotification(title, message, type = 'info') {
        // Create notification toast
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white bg-${type} border-0`;
        toast.setAttribute('role', 'alert');
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    <strong>${title}</strong><br>
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" 
                        data-bs-dismiss="toast"></button>
            </div>
        `;
        
        // Create toast container if it doesn't exist
        let toastContainer = document.getElementById('toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.id = 'toast-container';
            toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
            document.body.appendChild(toastContainer);
        }
        
        toastContainer.appendChild(toast);
        
        // Initialize and show toast
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
        
        // Remove from DOM after hiding
        toast.addEventListener('hidden.bs.toast', () => {
            toast.remove();
        });
    }

    // Format currency for Cameroon (XAF)
    formatCurrency(amount) {
        return new Intl.NumberFormat('fr-CM', {
            style: 'currency',
            currency: 'XAF'
        }).format(amount);
    }

    // Format phone number display
    formatPhoneDisplay(phone) {
        if (phone.startsWith('+237')) {
            return phone.replace(/(\+237)(\d{1})(\d{2})(\d{2})(\d{2})(\d{2})/, '$1 $2 $3 $4 $5 $6');
        }
        return phone;
    }

    // Export data functionality
    exportToCSV(tableId, filename) {
        const table = document.getElementById(tableId);
        if (!table) return;
        
        let csv = [];
        const rows = table.querySelectorAll('tr');
        
        rows.forEach(row => {
            const cells = row.querySelectorAll('th, td');
            const rowData = Array.from(cells).map(cell => {
                return '"' + cell.textContent.replace(/"/g, '""') + '"';
            });
            csv.push(rowData.join(','));
        });
        
        const csvContent = csv.join('\n');
        const blob = new Blob([csvContent], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = filename || 'export.csv';
        a.click();
        
        window.URL.revokeObjectURL(url);
    }
}

// Initialize admin panel when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new DjobeaAdmin();
});

// Global utility functions
window.DjobeaUtils = {
    formatPhone: (phone) => {
        if (phone.startsWith('+237')) {
            return phone.replace(/(\+237)(\d{1})(\d{2})(\d{2})(\d{2})(\d{2})/, '$1 $2 $3 $4 $5 $6');
        }
        return phone;
    },
    
    formatDate: (dateString) => {
        const date = new Date(dateString);
        return date.toLocaleDateString('fr-FR', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    },
    
    getStatusBadge: (status) => {
        const badges = {
            'en attente': 'warning',
            'assignée': 'info',
            'en cours': 'primary',
            'terminée': 'success',
            'annulée': 'danger'
        };
        return badges[status] || 'secondary';
    }
};

// Service Worker registration for offline functionality (optional)
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/static/js/sw.js')
            .then((registration) => {
                console.log('SW registered: ', registration);
            })
            .catch((registrationError) => {
                console.log('SW registration failed: ', registrationError);
            });
    });
}
