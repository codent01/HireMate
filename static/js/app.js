// HireMate - Frontend JavaScript

// Page loading bar for instant feedback on navigation
(function() {
    const loader = document.createElement('div');
    loader.className = 'page-loader';
    document.body.prepend(loader);

    document.addEventListener('click', function(e) {
        const link = e.target.closest('a[href]');
        if (!link) return;
        const href = link.getAttribute('href');
        if (!href || href.startsWith('#') || href.startsWith('javascript:') ||
            link.target === '_blank' || e.ctrlKey || e.metaKey) return;
        if (href.startsWith('http') && !href.startsWith(location.origin)) return;
        loader.className = 'page-loader loading';
    });

    window.addEventListener('beforeunload', function() {
        loader.className = 'page-loader done';
    });
})();

// Keyboard shortcut: Ctrl+K / Cmd+K -> jump to Find Jobs search
document.addEventListener('keydown', function(e) {
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        if (window.location.pathname !== '/jobs') {
            window.location.href = '/jobs';
        } else {
            var input = document.querySelector('input[type="text"][placeholder*="job"]') ||
                        document.querySelector('input[type="text"][x-model="query"]');
            if (input) input.focus();
        }
    }
});

// Toast notifications
function showToast(message, type = 'success') {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `toast ${type === 'error' ? 'error' : ''}`;
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(10px)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 2700);
}
