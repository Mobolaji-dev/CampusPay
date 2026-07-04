document.addEventListener("DOMContentLoaded", () => {
    // 1. Select DOM Elements
    const pinBoxes = document.querySelectorAll(".pin-box");
    const keys = document.querySelectorAll(".keypad-grid .key:not(.backspace-key)"); // Select only number keys
    const backspaceKey = document.querySelector(".backspace-key");
    const setPinBtn = document.querySelector(".set-pin-btn");

    // 2. App State Variables
    let currentPin = "";
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
            const pinDataObject = getPinData();
            
            // Log the object to the console to verify it works
            console.log("Success! PIN Object:", pinDataObject);
            
            // Optional: Alert to show the user it worked
            alert(currentPin)
            
            // TODO: Add your API fetch/axios logic here
        }
    });
});