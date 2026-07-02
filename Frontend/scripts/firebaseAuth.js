// Import the functions you need from the SDKs you need
import { initializeApp } from "https://www.gstatic.com/firebasejs/12.15.0/firebase-app.js";
import {getAuth} from "https://www.gstatic.com/firebasejs/12.15.0/firebase-auth.js";
// TODO: Add SDKs for Firebase products that you want to use
// https://firebase.google.com/docs/web/setup#available-libraries

// Your web app's Firebase configuration
// For Firebase JS SDK v7.20.0 and later, measurementId is optional
const firebaseConfig = {
  apiKey: "AIzaSyBQodnDhu8tsGd2uhF6-i_UXvZ-NoB12tM",  // All important keys are secured on firebase server. It is meant to be public.
  authDomain: "campuspay-a6f65.firebaseapp.com",
  projectId: "campuspay-a6f65",
  storageBucket: "campuspay-a6f65.firebasestorage.app",
  messagingSenderId: "375452860116",
  appId: "1:375452860116:web:6664309b3a1e0cd7638541",
  measurementId: "G-FZ1N6MR5JT"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);