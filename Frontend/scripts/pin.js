import { getToken } from "./auth.js";


document.addEventListener("DOMContentLoaded", async () => {
    const token = await getToken();
    if (!token) {
    console.log("No authenticated token, redirecting to index.html...");
    window.location.href = "index.html";
    return;
  }
})

let currentPin = "";
document.addEventListener("DOMContentLoaded", async () => {
    // 1. Select DOM Elements
    const pinBoxes = document.querySelectorAll(".pin-box");
    const keys = document.querySelectorAll(".keypad-grid .key:not(.backspace-key)"); // Select only number keys
    const backspaceKey = document.querySelector(".backspace-key");
    const setPinBtn = document.querySelector(".set-pin-btn");

    // 2. App State Variables
    
    const PIN_LENGTH = 4;

    // 3. Update the UI based on currentPin state
    function updatePinDisplay() {
        // Fill boxes with numbers
        pinBoxes.forEach((box, index) => {
            if (index < currentPin.length) {
                box.textContent = currentPin[index]; // Shows the actual number typed
                box.classList.add("filled");
            } else {
                box.textContent = ""; // Clears the box if empty
                box.classList.remove("filled");
            }
        });

        // Toggle the button state strictly
        if (currentPin.length === PIN_LENGTH) {
            setPinBtn.disabled = false;
            setPinBtn.removeAttribute("disabled");
            setPinBtn.classList.add("active"); // Triggers CSS color change
        } else {
            setPinBtn.disabled = true;
            setPinBtn.setAttribute("disabled", "true");
            setPinBtn.classList.remove("active");
        }
    }

    // 5. Handle Number Key Clicks
    keys.forEach(key => {
        key.addEventListener("click", () => {
            if (currentPin.length < PIN_LENGTH) {
                currentPin += key.textContent.trim();
                updatePinDisplay();
            }
        });
    });

    // 6. Handle Backspace Click
    backspaceKey.addEventListener("click", () => {
        if (currentPin.length > 0) {
            currentPin = currentPin.slice(0, -1);
            updatePinDisplay();
        }
    });

    // 7. Handle Submit Button Click
    setPinBtn.addEventListener("click", () => {
        if (currentPin.length === PIN_LENGTH) {
            // Optional: Alert to show the user it worked
        }
    });

});


const pinButton = document.getElementById("set-pin-btn");
const token = await getToken();
const API_BASE_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
  ? 'http://localhost:8000'
  : 'https://campuspay.pxxl.run';

pinButton.addEventListener("click", async (e) => {
    e.preventDefault();

    const response = fetch(`${API_BASE_URL}/api/profile/set-pin`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
            pin: currentPin
        })
    });

    if(!response.ok) {
        throw new Error(`Error setting pin`)
    } else {
        console.log('PIN set successful');
        window.location.href = "profile.html";
    }
});