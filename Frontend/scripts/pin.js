import { getToken } from "./auth.js";

// Configuration
const PIN_LENGTH = 4;
const API_BASE_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? 'http://localhost:8000'
    : 'https://campuspay.pxxl.run';

// Haptic Feedback Support for iOS
const triggerHaptic = (type = 'light') => {
    if (navigator.vibrate) {
        switch (type) {
            case 'light':
                navigator.vibrate(10);
                break;
            case 'medium':
                navigator.vibrate(20);
                break;
            case 'heavy':
                navigator.vibrate([30, 10, 30]);
                break;
            case 'error':
                navigator.vibrate([50, 50, 50]);
                break;
            default:
                navigator.vibrate(10);
        }
    }
};

// App State
let currentPin = "";
let isSubmitting = false;
let userToken = null;

// Initialize on DOM Ready
document.addEventListener("DOMContentLoaded", async () => {
    // Authentication Check
    userToken = await getToken();
    if (!userToken) {
        console.log("No authenticated token, redirecting to index.html...");
        window.location.href = "index.html";
        return;
    }

    // Initialize UI
    initializeUI();
});

function initializeUI() {
    // DOM Elements
    const pinBoxes = document.querySelectorAll(".pin-box");
    const numberKeys = document.querySelectorAll(".keypad-grid .key:not(.backspace-key)");
    const backspaceKey = document.querySelector(".backspace-key");
    const setPinBtn = document.querySelector("#set-pin-btn");

    // Prevent text selection and improve touch experience
    document.querySelectorAll(".key, .pin-box").forEach(el => {
        el.addEventListener("selectstart", e => e.preventDefault());
        el.addEventListener("contextmenu", e => e.preventDefault());
    });

    /**
     * Update PIN Display UI
     */
    function updatePinDisplay() {
        pinBoxes.forEach((box, index) => {
            const isEmpty = index >= currentPin.length;
            box.textContent = isEmpty ? "" : currentPin[index];
            box.classList.toggle("filled", !isEmpty);
            
            // Announce to screen readers
            if (!isEmpty) {
                box.setAttribute("aria-label", `Digit ${index + 1}`);
            }
        });

        // Update button state
        const isPinComplete = currentPin.length === PIN_LENGTH;
        setPinBtn.disabled = !isPinComplete;
        setPinBtn.classList.toggle("active", isPinComplete);
        
        if (isPinComplete) {
            setPinBtn.setAttribute("aria-label", "Confirm PIN");
            triggerHaptic('light');
        }
    }

    /**
     * Handle Number Key Input
     */
    numberKeys.forEach(key => {
        const handleKeyPress = () => {
            if (currentPin.length < PIN_LENGTH && !isSubmitting) {
                currentPin += key.getAttribute("data-key");
                triggerHaptic('light');
                updatePinDisplay();
            }
        };

        // Mouse and Touch Events
        key.addEventListener("click", handleKeyPress);
        key.addEventListener("touchend", (e) => {
            e.preventDefault();
            handleKeyPress();
        });
    });

    /**
     * Handle Backspace/Delete
     */
    backspaceKey.addEventListener("click", () => {
        if (currentPin.length > 0 && !isSubmitting) {
            currentPin = currentPin.slice(0, -1);
            triggerHaptic('light');
            updatePinDisplay();
        }
    });

    backspaceKey.addEventListener("touchend", (e) => {
        e.preventDefault();
        if (currentPin.length > 0 && !isSubmitting) {
            currentPin = currentPin.slice(0, -1);
            triggerHaptic('light');
            updatePinDisplay();
        }
    });

    /**
     * Handle PIN Submission
     */
    setPinBtn.addEventListener("click", async () => {
        if (currentPin.length === PIN_LENGTH && !isSubmitting) {
            await submitPin();
        }
    });

    // Allow Enter key as alternative submit
    document.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && currentPin.length === PIN_LENGTH && !isSubmitting) {
            submitPin();
        }
    });

    /**
     * Submit PIN to Backend
     */
    async function submitPin() {
        isSubmitting = true;
        const originalText = setPinBtn.textContent;
        
        try {
            // Show loading state
            setPinBtn.disabled = true;
            setPinBtn.classList.add("loading");
            setPinBtn.textContent = "Setting PIN...";
            setPinBtn.setAttribute("aria-busy", "true");
            triggerHaptic('medium');

            // Send to backend
            const response = await fetch(`${API_BASE_URL}/api/profile/set-pin`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${userToken}`
                },
                body: JSON.stringify({ pin: currentPin }),
                signal: AbortSignal.timeout(10000) // 10 second timeout
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || `Error setting PIN (${response.status})`);
            }

            // Success
            console.log("✓ PIN set successfully");
            triggerHaptic('heavy');
            setPinBtn.textContent = "✓ PIN Set!";
            
            // Wait briefly for visual feedback, then redirect
            await new Promise(resolve => setTimeout(resolve, 1000));
            window.location.href = "profile.html";

        } catch (error) {
            console.error("PIN submission error:", error);
            isSubmitting = false;
            
            // Restore button state
            setPinBtn.textContent = originalText;
            setPinBtn.disabled = false;
            setPinBtn.classList.remove("loading");
            setPinBtn.setAttribute("aria-busy", "false");
            triggerHaptic('error');

            // Show error message
            const errorMessage = error.message || "Failed to set PIN. Please try again.";
            showErrorNotification(errorMessage);
            
            // Clear PIN for retry
            currentPin = "";
            updatePinDisplay();
        }
    }
}

/**
 * Show Error Notification
 */
function showErrorNotification(message) {
    // Create notification element
    const notification = document.createElement("div");
    notification.className = "error-notification";
    notification.setAttribute("role", "alert");
    notification.setAttribute("aria-live", "polite");
    notification.textContent = message;
    
    document.body.appendChild(notification);

    // Style the notification
    const style = document.createElement("style");
    style.textContent = `
        .error-notification {
            position: fixed;
            bottom: 20px;
            left: 20px;
            right: 20px;
            background-color: #dc2626;
            color: white;
            padding: 16px;
            border-radius: 8px;
            font-size: 14px;
            line-height: 1.5;
            box-shadow: 0 4px 12px rgba(220, 38, 38, 0.3);
            animation: slideUp 0.3s ease-out;
            z-index: 1000;
        }
        @keyframes slideUp {
            from { transform: translateY(100px); opacity: 0; }
            to { transform: translateY(0); opacity: 1; }
        }
    `;
    document.head.appendChild(style);

    // Auto-remove after 5 seconds
    setTimeout(() => {
        notification.style.animation = "slideDown 0.3s ease-out forwards";
        setTimeout(() => notification.remove(), 300);
    }, 5000);
}