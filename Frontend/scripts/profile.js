import { auth } from "./firebaseAuth.js";
import { getToken, API_BASE_URL } from "./auth.js";
import { signOut } from "https://www.gstatic.com/firebasejs/12.15.0/firebase-auth.js";

document.addEventListener('DOMContentLoaded', async () => {
  const token = await getToken();
  if (!token) {
    console.log("No authenticated token, redirecting to index.html...");
    window.location.href = "index.html";
    return;
  }

  try {
    let res = await fetch(`${API_BASE_URL}/api/profile`, {
      headers: {
        "Authorization": `Bearer ${token}`,
        "Content-Type": "application/json"
      }
    });

    if (res.status === 401) {
      window.location.href = "index.html";
      return;
    }

    const profile = await res.json();


    const profileName  =  document.getElementById("profile-name");
    const email = document.getElementById("email");
    const phone = document.getElementById("phone")
    const role = document.getElementById("role");

    profileName.textContent = profile.full_name;
    email.textContent = profile.email;
    phone.textContent = profile.phone;
    role.textContent = profile.role;
    
  } catch(err) {
    console.error(err);
  }


 
});






// logout function

const logout = document.getElementById("logout-btn");

logout.addEventListener('click', () => {
  signOut(auth).then (()=> {
    window.location.href = 'index.html'
  }). catch((error) => {
    console.error(`Error logging out`, error)
  })
})
