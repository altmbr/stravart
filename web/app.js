// State management
const state = {
    isAuthenticated: false,
    activities: [],
    selectedActivity: null,
    generatedImageUrl: null
};

// DOM elements
const elements = {
    authSection: document.getElementById('auth-section'),
    authStatus: document.getElementById('auth-status'),
    connectBtn: document.getElementById('connect-btn'),
    activitiesSection: document.getElementById('activities-section'),
    activitiesList: document.getElementById('activities-list'),
    artworkSection: document.getElementById('artwork-section'),
    loadingSpinner: document.getElementById('loading-spinner'),
    artworkImage: document.getElementById('artwork-image'),
    artworkActions: document.getElementById('artwork-actions'),
    downloadBtn: document.getElementById('download-btn'),
    newArtworkBtn: document.getElementById('new-artwork-btn'),
    errorMessage: document.getElementById('error-message')
};

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    checkAuthStatus();
    setupEventListeners();
});

// Event listeners
function setupEventListeners() {
    elements.connectBtn.addEventListener('click', handleConnect);
    elements.downloadBtn.addEventListener('click', handleDownload);
    elements.newArtworkBtn.addEventListener('click', handleNewArtwork);
}

// Authentication
async function checkAuthStatus() {
    try {
        const response = await fetch('/api/auth/status');
        const data = await response.json();
        
        if (data.authenticated) {
            state.isAuthenticated = true;
            updateAuthUI(true);
            loadActivities();
        } else {
            updateAuthUI(false);
        }
    } catch (error) {
        console.error('Error checking auth status:', error);
        updateAuthUI(false);
    }
}

function updateAuthUI(isAuthenticated) {
    if (isAuthenticated) {
        elements.authStatus.textContent = 'Connected to Strava';
        elements.authStatus.classList.add('connected');
        elements.connectBtn.classList.add('hidden');
        elements.activitiesSection.classList.remove('hidden');
    } else {
        elements.authStatus.textContent = 'Not connected';
        elements.authStatus.classList.remove('connected');
        elements.connectBtn.classList.remove('hidden');
        elements.activitiesSection.classList.add('hidden');
    }
}

async function handleConnect() {
    try {
        // In a real implementation, this would redirect to Strava OAuth
        // For now, we'll use a mock authentication
        const response = await fetch('/api/auth/connect', {
            method: 'POST'
        });
        
        if (response.ok) {
            state.isAuthenticated = true;
            updateAuthUI(true);
            loadActivities();
        } else {
            showError('Failed to connect to Strava');
        }
    } catch (error) {
        console.error('Error connecting to Strava:', error);
        showError('Failed to connect to Strava');
    }
}

// Activities
async function loadActivities() {
    try {
        const response = await fetch('/api/activities');
        const activities = await response.json();
        
        state.activities = activities;
        renderActivities(activities);
    } catch (error) {
        console.error('Error loading activities:', error);
        showError('Failed to load activities');
    }
}

function renderActivities(activities) {
    elements.activitiesList.innerHTML = '';
    
    activities.forEach((activity, index) => {
        const card = createActivityCard(activity, index);
        elements.activitiesList.appendChild(card);
    });
    
    // Add generate button
    const generateBtn = document.createElement('button');
    generateBtn.className = 'btn btn-primary generate-btn';
    generateBtn.textContent = 'Generate Artwork';
    generateBtn.disabled = true;
    generateBtn.addEventListener('click', handleGenerateArtwork);
    elements.activitiesList.appendChild(generateBtn);
}

function createActivityCard(activity, index) {
    const card = document.createElement('div');
    card.className = 'activity-card';
    card.dataset.index = index;
    
    const date = new Date(activity.date).toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric'
    });
    
    card.innerHTML = `
        <div class="activity-header">
            <div class="activity-title">${activity.name}</div>
            <div class="activity-date">${date}</div>
        </div>
        <div class="activity-stats">
            <div class="stat">
                <div class="stat-value">${activity.distance}</div>
                <div class="stat-label">miles</div>
            </div>
            <div class="stat">
                <div class="stat-value">${activity.duration}</div>
                <div class="stat-label">time</div>
            </div>
            <div class="stat">
                <div class="stat-value">${activity.pace}</div>
                <div class="stat-label">min/mile</div>
            </div>
        </div>
    `;
    
    card.addEventListener('click', () => selectActivity(index));
    
    return card;
}

function selectActivity(index) {
    // Clear previous selection
    document.querySelectorAll('.activity-card').forEach(card => {
        card.classList.remove('selected');
    });
    
    // Select new activity
    const selectedCard = document.querySelector(`[data-index="${index}"]`);
    selectedCard.classList.add('selected');
    
    state.selectedActivity = state.activities[index];
    
    // Enable generate button
    const generateBtn = document.querySelector('.generate-btn');
    generateBtn.disabled = false;
}

// Artwork generation
async function handleGenerateArtwork() {
    if (!state.selectedActivity) return;
    
    // Show loading state
    elements.artworkSection.classList.remove('hidden');
    elements.loadingSpinner.classList.remove('hidden');
    elements.artworkImage.classList.add('hidden');
    elements.artworkActions.classList.add('hidden');
    hideError();
    
    try {
        const response = await fetch('/api/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                activityId: state.selectedActivity.id
            })
        });
        
        if (!response.ok) throw new Error('Failed to generate artwork');
        
        const data = await response.json();
        state.generatedImageUrl = data.imageUrl;
        
        // Show generated image
        elements.artworkImage.src = data.imageUrl;
        elements.artworkImage.onload = () => {
            elements.loadingSpinner.classList.add('hidden');
            elements.artworkImage.classList.remove('hidden');
            elements.artworkActions.classList.remove('hidden');
        };
    } catch (error) {
        console.error('Error generating artwork:', error);
        elements.loadingSpinner.classList.add('hidden');
        showError('Failed to generate artwork. Please try again.');
    }
}

// Download and actions
function handleDownload() {
    if (!state.generatedImageUrl) return;
    
    const link = document.createElement('a');
    link.href = state.generatedImageUrl;
    link.download = `strava-run-art-${state.selectedActivity.id}.png`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

function handleNewArtwork() {
    // Reset state
    state.selectedActivity = null;
    state.generatedImageUrl = null;
    
    // Hide artwork section
    elements.artworkSection.classList.add('hidden');
    
    // Clear activity selection
    document.querySelectorAll('.activity-card').forEach(card => {
        card.classList.remove('selected');
    });
    
    // Disable generate button
    const generateBtn = document.querySelector('.generate-btn');
    generateBtn.disabled = true;
    
    // Scroll to activities
    elements.activitiesSection.scrollIntoView({ behavior: 'smooth' });
}

// Error handling
function showError(message) {
    elements.errorMessage.textContent = message;
    elements.errorMessage.classList.remove('hidden');
}

function hideError() {
    elements.errorMessage.classList.add('hidden');
}

// Mock data for development
const mockActivities = [
    {
        id: 1,
        name: "Morning Run",
        date: new Date().toISOString(),
        distance: "5.2",
        duration: "42:15",
        pace: "8:07"
    },
    {
        id: 2,
        name: "Interval Training",
        date: new Date(Date.now() - 86400000).toISOString(),
        distance: "3.1",
        duration: "25:30",
        pace: "8:14"
    },
    {
        id: 3,
        name: "Long Run",
        date: new Date(Date.now() - 172800000).toISOString(),
        distance: "10.0",
        duration: "1:22:45",
        pace: "8:17"
    }
];

// For development: use mock data if API is not available
if (window.location.hostname === 'localhost' && window.location.port !== '5001') {
    state.isAuthenticated = true;
    updateAuthUI(true);
    state.activities = mockActivities;
    renderActivities(mockActivities);
}