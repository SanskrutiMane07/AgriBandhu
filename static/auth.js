// Check login before accessing features
function checkLogin(page){
    let isLoggedIn = localStorage.getItem("userLoggedIn");

    if(isLoggedIn){
        window.location.href = page;
    } else {
        alert("Please login first!");
        window.location.href = "login.html";
    }
}

// Login
function loginUser(event){
    event.preventDefault();

    let username = document.getElementById("username").value;
    let password = document.getElementById("password").value;

    if(username && password){
        localStorage.setItem("userLoggedIn", true);
        alert("Login Successful!");
        window.location.href = "index.html";
    }
}

// Register
function registerUser(event){
    event.preventDefault();
    alert("Registered Successfully!");
    window.location.href = "login.html";
}

// Logout
function logoutUser(){
    localStorage.removeItem("userLoggedIn");
    alert("Logged out!");
    window.location.href = "index.html";
}

// Navbar control
window.onload = function(){
    let isLoggedIn = localStorage.getItem("userLoggedIn");

    let loginNav = document.getElementById("loginNav");
    let registerNav = document.getElementById("registerNav");
    let logoutNav = document.getElementById("logoutNav");

    if(isLoggedIn){
        if(loginNav) loginNav.style.display = "none";
        if(registerNav) registerNav.style.display = "none";
        if(logoutNav) logoutNav.style.display = "block";
    }
}