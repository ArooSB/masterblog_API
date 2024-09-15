const API_BASE_URL = 'http://127.0.0.1:5004/api';  // Adjusted to your Flask backend URL

// Function to load posts and display them
function loadPosts() {
    fetch(`${API_BASE_URL}/posts`, {
        headers: {
            'Authorization': `Bearer ${localStorage.getItem('jwtToken')}`
        }
    })
    .then(response => response.json())
    .then(data => {
        const postContainer = document.getElementById('post-container');
        postContainer.innerHTML = data.map(post => `
            <div class="post">
                <h2>${post.title}</h2>
                <p>${post.content}</p>
                <button onclick="viewPost(${post.id})">Read More</button>
            </div>
        `).join('');
    })
    .catch(error => console.error('Error:', error));
}

// Function to search for posts based on a keyword
function searchPosts() {
    const keyword = document.getElementById('keyword').value;
    fetch(`${API_BASE_URL}/posts/search?title=${keyword}`, {
        headers: {
            'Authorization': `Bearer ${localStorage.getItem('jwtToken')}`
        }
    })
    .then(response => response.json())
    .then(data => {
        const postContainer = document.getElementById('post-container');
        postContainer.innerHTML = data.map(post => `
            <div class="post">
                <h2>${post.title}</h2>
                <p>${post.content}</p>
                <button onclick="viewPost(${post.id})">Read More</button>
            </div>
        `).join('');
    })
    .catch(error => console.error('Error:', error));
}

// Function to view a specific post
function viewPost(postId) {
    fetch(`${API_BASE_URL}/posts/${postId}`, {
        headers: {
            'Authorization': `Bearer ${localStorage.getItem('jwtToken')}`
        }
    })
    .then(response => response.json())
    .then(post => {
        localStorage.setItem('currentPost', JSON.stringify(post));
        window.location.href = 'blog.html';
    })
    .catch(error => console.error('Error:', error));
}

// Function to display the post details on blog.html
function displayPost() {
    const post = JSON.parse(localStorage.getItem('currentPost'));
    if (post) {
        const blogDetails = document.getElementById('blog-details');
        blogDetails.innerHTML = `
            <h1>${post.title}</h1>
            <p>${post.content}</p>
            <h2>Comments:</h2>
            <ul>
                ${post.comments.map(comment => `<li>${comment}</li>`).join('')}
            </ul>
        `;
    } else {
        window.location.href = 'home.html';
    }
}

// Function to submit a new post
function submitPost() {
    const title = document.getElementById('title').value;
    const content = document.getElementById('content').value;

    fetch(`${API_BASE_URL}/posts`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('jwtToken')}`
        },
        body: JSON.stringify({ title, content })
    })
    .then(response => response.json())
    .then(() => {
        alert('Post published successfully!');
        window.location.href = 'home.html';
    })
    .catch(error => console.error('Error:', error));
}

// Function to handle user login and store the JWT token
function loginUser() {
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;

    fetch(`${API_BASE_URL}/login`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ username, password })
    })
    .then(response => response.json())
    .then(data => {
        if (data.token) {
            localStorage.setItem('jwtToken', data.token);
            window.location.href = 'home.html';
        } else {
            alert('Login failed. Please check your credentials.');
        }
    })
    .catch(error => console.error('Error:', error));
}

// Function to handle user logout
function logoutUser() {
    localStorage.removeItem('jwtToken');
    window.location.href = 'home.html';
}

// Execute on page load for blog.html
if (window.location.pathname.endsWith('blog.html')) {
    displayPost();
}
