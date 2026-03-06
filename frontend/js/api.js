const API_BASE_URL = 'http://127.0.0.1:8000/api';

// --- Theme Management ---
function initTheme() {
    const themeToggleBtn = document.getElementById('theme-toggle');
    if (!themeToggleBtn) return;

    // Check Local Storage
    if (localStorage.theme === 'dark' || (!('theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
        document.documentElement.classList.add('dark');
        themeToggleBtn.innerHTML = '<i class="fas fa-sun text-yellow-500"></i>';
    } else {
        document.documentElement.classList.remove('dark');
        themeToggleBtn.innerHTML = '<i class="fas fa-moon text-gray-700"></i>';
    }

    themeToggleBtn.addEventListener('click', () => {
        if (document.documentElement.classList.contains('dark')) {
            document.documentElement.classList.remove('dark');
            localStorage.theme = 'light';
            themeToggleBtn.innerHTML = '<i class="fas fa-moon text-gray-700"></i>';
        } else {
            document.documentElement.classList.add('dark');
            localStorage.theme = 'dark';
            themeToggleBtn.innerHTML = '<i class="fas fa-sun text-yellow-500"></i>';
        }

        // Dispatch event for charts to update colors
        window.dispatchEvent(new Event('themeChanged'));
    });
}

// --- API Helpers ---
async function fetchAPI(endpoint, options = {}) {
    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'API Request Failed');
        }

        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        showNotification('Error: ' + error.message, 'error');
        throw error;
    }
}

// --- UI Helpers ---
function showNotification(message, type = 'success') {
    // Create notification element
    const notif = document.createElement('div');
    notif.className = `fixed bottom-4 right-4 p-4 rounded-lg shadow-lg text-white font-medium z-50 transform transition-all duration-300 translate-y-10 opacity-0 flex items-center gap-2`;

    if (type === 'success') {
        notif.classList.add('bg-green-500');
        notif.innerHTML = `<i class="fas fa-check-circle"></i> ${message}`;
    } else {
        notif.classList.add('bg-red-500');
        notif.innerHTML = `<i class="fas fa-exclamation-circle"></i> ${message}`;
    }

    document.body.appendChild(notif);

    // Animate in
    setTimeout(() => {
        notif.classList.remove('translate-y-10', 'opacity-0');
    }, 10);

    // Animate out
    setTimeout(() => {
        notif.classList.add('translate-y-10', 'opacity-0');
        setTimeout(() => notif.remove(), 300);
    }, 3000);
}

// Set active sidebar link
function setActiveSidebar() {
    const currentPath = window.location.pathname.split('/').pop() || 'dashboard.html';
    document.querySelectorAll('.sidebar-link').forEach(link => {
        if (link.getAttribute('href') === currentPath) {
            link.classList.add('active', 'bg-indigo-100', 'text-indigo-600', 'border-r-4', 'border-indigo-600', 'dark:bg-indigo-900/40', 'dark:text-indigo-400');
        } else {
            link.classList.remove('active', 'bg-indigo-100', 'text-indigo-600', 'border-r-4', 'border-indigo-600', 'dark:bg-indigo-900/40', 'dark:text-indigo-400');
        }
    });
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    setActiveSidebar();
});
