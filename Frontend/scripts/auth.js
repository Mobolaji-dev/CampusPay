import {auth} from "./firebaseAuth.js";
import { signInWithEmailAndPassword, createUserWithEmailAndPassword, onAuthStateChanged } from "https://www.gstatic.com/firebasejs/12.15.0/firebase-auth.js";


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



if (loginForm) {
  loginForm.addEventListener("submit", async(e) => {
    e.preventDefault();
    const email = loginForm["login-email"].value;
    const password = loginForm["login-password"].value; 

    loginbtn.classList.add('loading')

    try {
      const userCredential = await signInWithEmailAndPassword(auth, email, password);
      // Signed in
      const user = userCredential.user;
      const token = await user.getIdToken(true);


      console.log("User signed in:", user);
    
      localStorage.setItem('token', token);
      localStorage.setItem('uid', user.uid);
      loginbtn.classList.remove('loading');

      window.location.href = "dashboard.html"
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
    const fullname = signupForm["fullName"].value;

    signupbtn.classList.add('loading')

    try {
      const userCredential = await createUserWithEmailAndPassword(auth, email, password)
      // Signed up
      
      const user = userCredential.user;
      const token = await user.getIdToken(true);

      localStorage.setItem('token', token);
      localStorage.setItem('uid', user.uid);
      signupbtn.classList.remove('loading');

      await fetch('https://campuspay.pxxl.run/auth/sync', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          fullname: fullname,
        })
      });

      window.location.href = "dashboard.html"
      
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






