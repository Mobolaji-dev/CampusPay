import {auth} from "./firebaseAuth.js";
import { signInWithEmailAndPassword, createUserWithEmailAndPassword, onAuthStateChanged, updateProfile } from "https://www.gstatic.com/firebasejs/12.15.0/firebase-auth.js";


const loginForm = document.getElementById("login-form");
const signupForm = document.getElementById("signup-form");
const error = document.getElementById("popup-error");
const loginbtn = document.getElementById("login-btn");
const signupbtn = document.getElementById("signup-btn");




export async function getToken() {
  return new Promise((resolve) => {
    const unsubscribe = onAuthStateChanged(auth, async (user) => {
      unsubscribe();
      if (!user) {
        return resolve(null);
      }

      try {
        const token = await user.getIdToken(true);
        localStorage.setItem('token', token);
        localStorage.setItem('uid', user.uid);
        // Cache displayName for self-healing sync fallback
        if (user.displayName) {
          localStorage.setItem('displayName', user.displayName);
        }
        resolve(token);
      } catch (err) {
        console.error('Failed to refresh auth token:', err);
        resolve(null);
      }
    });
  });
}



export function getUid() {
  const currentUser = auth.currentUser;
  if (currentUser) return currentUser.uid;
  return localStorage.getItem('uid');
}



const API_BASE_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
  ? 'http://localhost:8000'
  : 'https://campuspay.pxxl.run';

async function syncWithBackend(token, uid, fullName = null, role = 'student', phoneNo) {
  try {
    const response = await fetch(`${API_BASE_URL}/auth/sync`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        full_name: fullName,
        role: role,
        phone: phoneNo,
      })
    });
    if (!response.ok) {
      const errText = await response.text();
      throw new Error(`Sync failed: ${errText}`);
    }
    const data = await response.json();
    console.log('Backend sync successful:', data);
    localStorage.setItem('role', data.role);
    localStorage.setItem('fullName', data.full_name);
    return data;
  } catch (error) {
    console.error('Backend sync error:', error);
    throw error;
  }
}

if (loginForm) {
  loginForm.addEventListener("submit", async(e) => {
    e.preventDefault();
    const email = loginForm["login-email"].value;
    const password = loginForm["login-password"].value; 

    loginbtn.classList.add('loading')

    try {
      const userCredential = await signInWithEmailAndPassword(auth, email, password);
      const user = userCredential.user;
      const token = await user.getIdToken(true);

      localStorage.setItem('token', token);
      localStorage.setItem('uid', user.uid);

      // Pass displayName on login so the backend can correct a fallback name.
      // Role is intentionally omitted here — for existing users, get_or_create_user
      // always returns the role they registered with, ignoring the sent role.
      const data = await syncWithBackend(token, user.uid, user.displayName || null, 'student');

      loginbtn.classList.remove('loading');

      // Store vendor-specific fields so dashboard pages don't need extra fetches
      if (data.role === 'Vendor') {
        localStorage.setItem('vendorId', data.user_id);
        localStorage.setItem('vendorName', data.full_name);
        window.location.href = "vendor-dashboard.html";
      } else {
        window.location.href = "dashboard.html";
      }
    }
      catch(err) {
      console.error("Error signing in:", err.code, err.message);
      loginbtn.classList.remove('loading');
      error.classList.add('show');
      setTimeout(() => {
        error.classList.remove('show')
      }, 1500);
    };
  })
    
};

if (signupForm) {
  signupForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    const email = signupForm["signup-email"].value;
    const password = signupForm["signup-password"].value; 
    const fullName = signupForm["fullName"].value;
    const role = signupForm["accountType"].value;
    const rawPhone = String(signupForm["phone"].value);
    const phoneNo = rawPhone.startsWith("0") ? `+234${rawPhone.slice(1)}` : `+234${rawPhone}`;
    signupbtn.classList.add('loading');

    try {
      const userCredential = await createUserWithEmailAndPassword(auth, email, password);
      // Signed up
      const user = userCredential.user;

      // Persist displayName in Firebase so future logins can pass it to the backend
      if (fullName) {
        await updateProfile(user, { displayName: fullName });
        localStorage.setItem('displayName', fullName);
      }

      const token = await user.getIdToken(true);
      console.log("User signed up:", user);
      localStorage.setItem('token', token);
      localStorage.setItem('uid', user.uid);

      await syncWithBackend(token, user.uid, fullName, role, phoneNo);

      signupbtn.classList.remove('loading');
      window.location.href = "dashboard.html";
    } 
      catch(err) {
      console.error("Error signing up:", err.code, err.message);
      signupbtn.classList.remove('loading');
      error.classList.add('show');
      setTimeout(() => {
        error.classList.remove('show')
      }, 1500);
    };
  })
};






