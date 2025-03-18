// Smooth Scrolling for internal links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener("click", function (e) {
        e.preventDefault();
        document.querySelector(this.getAttribute("href")).scrollIntoView({
            behavior: "smooth",
            block: "start"
        });
    });
});

// Modal for Account Deletion Confirmation
const deleteAccountButton = document.getElementById('delete-account-btn');
const deleteAccountModal = document.getElementById('delete-account-modal');
const cancelDeleteBtn = document.getElementById('cancel-delete');
const confirmDeleteBtn = document.getElementById('confirm-delete');

if (deleteAccountButton) {
    deleteAccountButton.addEventListener('click', () => {
        deleteAccountModal.style.display = 'block'; // Show confirmation modal
    });

    cancelDeleteBtn.addEventListener('click', () => {
        deleteAccountModal.style.display = 'none'; // Hide modal when cancelled
    });

    confirmDeleteBtn.addEventListener('click', () => {
        // Simulate account deletion action here
        alert('Account has been deleted!');
        deleteAccountModal.style.display = 'none'; // Hide modal after action
    });
}

// Show/Hide Password Toggle Functionality
const passwordToggle = document.querySelectorAll('.password-toggle');
passwordToggle.forEach((toggle) => {
    toggle.addEventListener('click', (e) => {
        const passwordField = e.target.previousElementSibling;
        if (passwordField.type === 'password') {
            passwordField.type = 'text';
            e.target.textContent = 'Hide Password';
        } else {
            passwordField.type = 'password';
            e.target.textContent = 'Show Password';
        }
    });
});

// Update Favorite Books Section with Animations
const favoriteBooksContainer = document.getElementById('favorite-books-list');
if (favoriteBooksContainer) {
    const addBookButton = document.getElementById('add-book-btn');
    addBookButton.addEventListener('click', () => {
        const newBook = document.createElement('li');
        newBook.classList.add('list-group-item');
        newBook.innerHTML = `
            <strong>New Book Title</strong> by Author Name
            <small class="text-muted">Added just now</small><br>
            <img src="https://via.placeholder.com/50" alt="New Book" width="50"><br>
            <p>New book description...</p>
        `;
        favoriteBooksContainer.appendChild(newBook);
        newBook.style.animation = 'fadeIn 1s ease-out';
    });
}

// Input Validation
const profileForm = document.getElementById('profile-form');
if (profileForm) {
    profileForm.addEventListener('submit', (e) => {
        const nameInput = document.getElementById('name-input');
        const emailInput = document.getElementById('email-input');
        let valid = true;

        // Clear previous errors
        document.querySelectorAll('.error-message').forEach(msg => msg.remove());

        // Name validation
        if (!nameInput.value.trim()) {
            valid = false;
            const error = document.createElement('div');
            error.classList.add('error-message');
            error.textContent = 'Name is required!';
            nameInput.parentElement.appendChild(error);
        }

        // Email validation (basic)
        const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
        if (!emailRegex.test(emailInput.value.trim())) {
            valid = false;
            const error = document.createElement('div');
            error.classList.add('error-message');
            error.textContent = 'Please enter a valid email address.';
            emailInput.parentElement.appendChild(error);
        }

        if (!valid) {
            e.preventDefault(); // Prevent form submission if not valid
        }
    });
}

// Sticky Navbar
const navbar = document.getElementById('navbar');
if (navbar) {
    window.onscroll = function () {
        if (window.pageYOffset > 100) {
            navbar.classList.add('sticky');
        } else {
            navbar.classList.remove('sticky');
        }
    };
}

// Utility to close the modal when clicked outside
window.onclick = function (event) {
    if (event.target === deleteAccountModal) {
        deleteAccountModal.style.display = 'none';
    }
};

// Fade-In Animation for Favorite Books and Reading History
const fadeInElements = document.querySelectorAll('.fade-in');
window.addEventListener('scroll', () => {
    fadeInElements.forEach(element => {
        if (element.getBoundingClientRect().top < window.innerHeight) {
            element.classList.add('fade-in-visible');
        }
    });
});

// CSS for Fade-In Effect
const style = document.createElement('style');
style.innerHTML = `
    @keyframes fadeIn {
        0% { opacity: 0; }
        100% { opacity: 1; }
    }

    .fade-in {
        opacity: 0;
        animation: fadeIn 1s ease-out forwards;
    }

    .fade-in-visible {
        opacity: 1;
    }

    .error-message {
        color: red;
        font-size: 0.9rem;
        margin-top: 5px;
    }
`;
document.head.appendChild(style);
