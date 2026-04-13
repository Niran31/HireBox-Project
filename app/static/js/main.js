/**
 * HireBox - Main JavaScript Utilities
 * Modern UI/UX Enhancement Scripts
 */

// ============================================
// 1. Mobile Menu Toggle
// ============================================
function initMobileMenu() {
    const toggle = document.querySelector('.mobile-menu-toggle');
    const menu = document.querySelector('.navbar-menu');

    if (toggle && menu) {
        toggle.addEventListener('click', () => {
            menu.classList.toggle('active');
            toggle.setAttribute('aria-expanded', menu.classList.contains('active'));
        });
    }
}

// ============================================
// 2. Toast Notifications
// ============================================
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `alert alert-${type} toast fade-in`;
    toast.style.cssText = 'position: fixed; top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    toast.innerHTML = `
    ${message}
    <button class="btn-close" onclick="this.parentElement.remove()">×</button>
  `;

    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 5000);
}

// ============================================
// 3. Copy to Clipboard
// ============================================
function copyToClipboard(text, button) {
    navigator.clipboard.writeText(text).then(() => {
        const originalText = button.textContent;
        button.textContent = 'Copied!';
        button.classList.add('btn-success');

        setTimeout(() => {
            button.textContent = originalText;
            button.classList.remove('btn-success');
        }, 2000);
    }).catch(err => {
        console.error('Failed to copy:', err);
        showToast('Failed to copy to clipboard', 'danger');
    });
}

// ============================================
// 4. File Upload Enhancement
// ============================================
function initFileUpload() {
    const fileInputs = document.querySelectorAll('input[type="file"]');

    fileInputs.forEach(input => {
        const wrapper = input.closest('.file-upload-area');
        if (!wrapper) return;

        // Drag and drop
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            wrapper.addEventListener(eventName, preventDefaults, false);
        });

        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }

        ['dragenter', 'dragover'].forEach(eventName => {
            wrapper.addEventListener(eventName, () => {
                wrapper.classList.add('dragover');
            }, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            wrapper.addEventListener(eventName, () => {
                wrapper.classList.remove('dragover');
            }, false);
        });

        wrapper.addEventListener('drop', (e) => {
            const dt = e.dataTransfer;
            const files = dt.files;
            input.files = files;
            handleFiles(files, wrapper);
        }, false);

        input.addEventListener('change', (e) => {
            handleFiles(e.target.files, wrapper);
        });
    });
}

function handleFiles(files, wrapper) {
    if (files.length > 0) {
        const fileList = Array.from(files).map(f => f.name).join(', ');
        const preview = wrapper.querySelector('.file-preview');
        if (preview) {
            preview.textContent = `Selected: ${fileList}`;
        }
    }
}

// ============================================
// 5. Form Validation Enhancement
// ============================================
function initFormValidation() {
    const forms = document.querySelectorAll('form');

    forms.forEach(form => {
        const inputs = form.querySelectorAll('input, textarea, select');

        inputs.forEach(input => {
            input.addEventListener('blur', () => {
                validateField(input);
            });

            input.addEventListener('input', () => {
                if (input.classList.contains('is-invalid')) {
                    validateField(input);
                }
            });
        });
    });
}

function validateField(field) {
    const errorSpan = field.parentElement.querySelector('.form-error');

    if (field.validity.valid) {
        field.classList.remove('is-invalid');
        if (errorSpan) errorSpan.remove();
    } else {
        field.classList.add('is-invalid');
        if (!errorSpan) {
            const error = document.createElement('span');
            error.className = 'form-error';
            error.textContent = field.validationMessage;
            field.parentElement.appendChild(error);
        }
    }
}

// ============================================
// 6. Smooth Scroll
// ============================================
function initSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                e.preventDefault();
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
}

// ============================================
// 7. Loading State Management
// ============================================
function setLoadingState(button, isLoading) {
    if (isLoading) {
        button.disabled = true;
        button.dataset.originalText = button.textContent;
        button.innerHTML = '<span class="spinner" style="width: 16px; height: 16px; border-width: 2px;"></span> Loading...';
    } else {
        button.disabled = false;
        button.textContent = button.dataset.originalText || button.textContent;
    }
}

// ============================================
// 8. Confirmation Modal
// ============================================
function confirmAction(message, callback) {
    const modal = document.createElement('div');
    modal.className = 'modal-backdrop';
    modal.style.cssText = 'position: fixed; inset: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 9999;';

    modal.innerHTML = `
    <div class="card-modern" style="max-width: 400px; margin: 20px;">
      <div class="card-body-modern">
        <h3 style="margin-bottom: 16px;">Confirm Action</h3>
        <p style="margin-bottom: 24px;">${message}</p>
        <div class="btn-group" style="justify-content: flex-end; width: 100%;">
          <button class="btn btn-secondary" onclick="this.closest('.modal-backdrop').remove()">Cancel</button>
          <button class="btn btn-danger" id="confirm-btn">Confirm</button>
        </div>
      </div>
    </div>
  `;

    document.body.appendChild(modal);

    modal.querySelector('#confirm-btn').addEventListener('click', () => {
        callback();
        modal.remove();
    });

    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.remove();
        }
    });
}

// ============================================
// 9. Auto-dismiss Alerts
// ============================================
function initAlerts() {
    const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');

    alerts.forEach(alert => {
        const closeBtn = alert.querySelector('.btn-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                alert.style.opacity = '0';
                setTimeout(() => alert.remove(), 300);
            });
        }
    });
}

// ============================================
// 10. Keyboard Navigation
// ============================================
function initKeyboardNav() {
    document.addEventListener('keydown', (e) => {
        // ESC to close modals
        if (e.key === 'Escape') {
            const modals = document.querySelectorAll('.modal-backdrop');
            modals.forEach(modal => modal.remove());
        }
    });
}

// ============================================
// 11. Table Responsive Wrapper
// ============================================
function initResponsiveTables() {
    const tables = document.querySelectorAll('.table-modern');

    tables.forEach(table => {
        if (!table.parentElement.classList.contains('table-responsive')) {
            const wrapper = document.createElement('div');
            wrapper.className = 'table-responsive';
            wrapper.style.cssText = 'overflow-x: auto; -webkit-overflow-scrolling: touch;';
            table.parentNode.insertBefore(wrapper, table);
            wrapper.appendChild(table);
        }
    });
}

// ============================================
// 12. Initialize All
// ============================================
document.addEventListener('DOMContentLoaded', () => {
    initMobileMenu();
    initFileUpload();
    initFormValidation();
    initSmoothScroll();
    initAlerts();
    initKeyboardNav();
    initResponsiveTables();

    // Add fade-in animation to main content
    const mainContent = document.querySelector('.page-content');
    if (mainContent) {
        mainContent.classList.add('fade-in');
    }
});

// Export functions for use in other scripts
window.HireBox = {
    showToast,
    copyToClipboard,
    setLoadingState,
    confirmAction
};
