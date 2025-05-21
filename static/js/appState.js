// appState.js - Quản lý trạng thái ứng dụng
class AppState {
    constructor() {
        this.currentPanel = localStorage.getItem('currentPanel') || 'main-download-panel';
        this.initialize();
    }

    initialize() {
        console.log('Initializing AppState...');
        this.panels = document.querySelectorAll('.main-panel');
        this.navLinks = document.querySelectorAll('.sidebar-link[data-target]');
        
        // Khởi tạo sự kiện cho các liên kết điều hướng
        this.setupEventListeners();

        // Khôi phục trạng thái trước đó
        this.switchPanel(this.currentPanel, false);
    }

    setupEventListeners() {
        // Xử lý sự kiện click cho các liên kết điều hướng
        document.addEventListener('click', (e) => {
            // Tìm phần tử được click có class sidebar-link
            let targetElement = e.target.closest('.sidebar-link[data-target]');
            
            if (targetElement) {
                e.preventDefault();
                const targetPanel = targetElement.getAttribute('data-target');
                console.log('Navigation link clicked, target:', targetPanel);
                this.switchPanel(targetPanel);
                this.updateActiveLink(targetElement);
            }
        });
    }

    switchPanel(panelId, saveState = true) {
        console.log('Switching to panel:', panelId);
        
        // Ẩn tất cả các panel
        this.panels = document.querySelectorAll('.main-panel');
        this.panels.forEach(panel => {
            if (panel.id === panelId) {
                panel.style.display = 'block';
                console.log('Showing panel:', panelId);
            } else {
                panel.style.display = 'none';
            }
        });

        // Cập nhật tiêu đề
        const titleElement = document.getElementById('section-title');
        if (titleElement) {
            const activeLink = document.querySelector(`.sidebar-link[data-target="${panelId}"]`);
            if (activeLink) {
                const linkText = activeLink.querySelector('span')?.textContent || 'Dashboard';
                titleElement.textContent = linkText;
            }
        }

        // Lưu trạng thái nếu cần
        if (saveState && panelId) {
            this.currentPanel = panelId;
            localStorage.setItem('currentPanel', panelId);
            console.log('Saved current panel:', panelId);
        }

        // Kích hoạt sự kiện khi chuyển tab
        this.dispatchPanelChange(panelId);
    }

    updateActiveLink(clickedLink) {
        if (!clickedLink) return;
        
        // Xóa class active khỏi tất cả các liên kết
        this.navLinks.forEach(link => {
            link.classList.remove('active');
        });

        // Thêm class active vào liên kết được chọn
        if (clickedLink.classList.contains('sidebar-link')) {
            clickedLink.classList.add('active');
        } else {
            const parentLink = clickedLink.closest('.sidebar-link');
            if (parentLink) {
                parentLink.classList.add('active');
            }
        }
    }

    dispatchPanelChange(panelId) {
        console.log('Dispatching panel change event for:', panelId);
        // Tạo sự kiện tùy chỉnh khi chuyển tab
        const event = new CustomEvent('panelChanged', {
            detail: { panelId }
        });
        window.dispatchEvent(event);
    }
}

// Khởi tạo khi DOM đã tải xong
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM fully loaded, initializing AppState...');
    window.appState = new AppState();
});
