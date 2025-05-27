// active_downloads.js
// This script handles the display and cancellation of active download sessions.

let activeDownloadsInterval = null; // For refreshing active downloads list

// Helper function to format elapsed time
function formatElapsedTime(startTime) {
    const elapsed = Math.floor((Date.now() - new Date(startTime).getTime()) / 1000);
    const hour = Math.floor(elapsed / 3600).toString().padStart(2, '0');
    const min = Math.floor((elapsed % 3600) / 60).toString().padStart(2, '0');
    const sec = (elapsed % 60).toString().padStart(2, '0');
    return `${hour}:${min}:${sec}`;
}

// Function to fetch and display active download sessions
async function fetchActiveDownloads() {
    const activeDownloadsList = document.getElementById('active-downloads-list');
    if (!activeDownloadsList) return;

    try {
        // Assuming fetchData and showNotification are available globally or passed in
        const data = await fetchData('/download/get-active-sessions');
        activeDownloadsList.innerHTML = ''; // Clear existing rows

        if (data && Array.isArray(data.active_sessions) && data.active_sessions.length > 0) {
            data.active_sessions.forEach(session => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${session.config_name || 'N/A'}</td>
                    <td>${session.session_id}</td>
                    <td>${new Date(session.created_at).toLocaleString()}</td>
                    <td>${formatElapsedTime(session.created_at)}</td>
                    <td>${session.status}</td>
                    <td><button class="cancel-active-download-btn delete-button" data-session-id="${session.session_id}" title="Cancel this active download session"><i class="fas fa-times"></i> Cancel</button></td>
                `;
                activeDownloadsList.appendChild(tr);
            });
            // Attach event listeners to new cancel buttons
            activeDownloadsList.querySelectorAll('.cancel-active-download-btn').forEach(button => {
                button.addEventListener('click', handleCancelSession);
            });
        } else {
            activeDownloadsList.innerHTML = '<tr><td colspan="6" class="subtext">No active downloads.</td></tr>';
        }
    } catch (error) {
        console.error("Error fetching active downloads:", error);
        activeDownloadsList.innerHTML = `<tr><td colspan="6" class="error-message">Failed to load active downloads: ${error.message}</td></tr>`;
    }
}

// Function to handle cancellation of a session
async function handleCancelSession(event) {
    const button = event.target.closest('.cancel-active-download-btn');
    if (!button) return;

    const sessionId = button.dataset.sessionId;
    if (!sessionId) {
        console.error("Session ID not found for cancellation.");
        showNotification("Error: Session ID missing for cancellation.", "error");
        return;
    }

    if (!confirm(`Are you sure you want to cancel download session ${sessionId}?`)) {
        return;
    }

    button.disabled = true; // Disable button to prevent multiple clicks
    button.textContent = 'Cancelling...';

    try {
        const result = await fetchData(`/download/cancel-active-session/${sessionId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
        });

        if (result && result.status === 'success') {
            showNotification(result.message || `Session ${sessionId} cancellation initiated.`, 'success');
            // Immediately refresh the list to reflect the change
            fetchActiveDownloads();
        } else {
            const errorMsg = result?.message || 'Failed to cancel session.';
            showNotification(errorMsg, 'error');
            button.disabled = false; // Re-enable on error
            button.innerHTML = '<i class="fas fa-times"></i> Cancel';
        }
    } catch (error) {
        console.error("Error cancelling session:", error);
        showNotification(`Failed to cancel session ${sessionId}: ${error.message}`, 'error');
        button.disabled = false; // Re-enable on error
        button.innerHTML = '<i class="fas fa-times"></i> Cancel';
    }
}

// Functions to add/remove active sessions from the in-memory list (for immediate UI update)
// These are simplified as the main source of truth will be the backend API
let activeSessions = []; // This will be managed by the backend API, but keep for local tracking if needed

function addActiveSession(sessionId, startTime, reports) {
    // This function might not be strictly necessary if fetchActiveDownloads is called frequently
    // But it can provide immediate feedback
    activeSessions.push({ sessionId, startTime, reports, status: 'started' });
    // No need to render here, fetchActiveDownloads will do it
}

function removeActiveSession(sessionId) {
    // This function might not be strictly necessary if fetchActiveDownloads is called frequently
    activeSessions = activeSessions.filter(s => s.sessionId !== sessionId);
    // No need to render here, fetchActiveDownloads will do it
}

// Expose functions to the global scope if needed by other scripts (e.g., script.js)
window.fetchActiveDownloads = fetchActiveDownloads;
window.handleCancelSession = handleCancelSession;
window.activeDownloadsInterval = activeDownloadsInterval; // Expose for management
window.addActiveSession = addActiveSession; // Expose for handleDownloadFormSubmit
window.removeActiveSession = removeActiveSession; // Expose for handleDownloadFormSubmit
