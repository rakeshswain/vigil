// DOM Elements
const chatMessages = document.getElementById('chatMessages');
const userInput = document.getElementById('userInput');
const sendBtn = document.getElementById('sendBtn');
const webAgentBtn = document.getElementById('webAgentBtn');
const apiAgentBtn = document.getElementById('apiAgentBtn');
const resultsContent = document.getElementById('resultsContent');
const clearResultsBtn = document.getElementById('clearResultsBtn');
const statusDot = document.getElementById('statusDot');
const statusText = document.getElementById('statusText');

// State
let currentAgent = 'web'; // 'web' or 'api'
let isProcessing = false;
let messageId = 0;

// Event Listeners
document.addEventListener('DOMContentLoaded', initializeApp);
sendBtn.addEventListener('click', handleSendMessage);
userInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSendMessage();
    }
});
webAgentBtn.addEventListener('click', () => switchAgent('web'));
apiAgentBtn.addEventListener('click', () => switchAgent('api'));
clearResultsBtn.addEventListener('click', clearResults);

// Initialize the application
function initializeApp() {
    checkServerStatus();
    setInterval(checkServerStatus, 30000); // Check every 30 seconds
    
    // Focus the input field
    userInput.focus();
}

// Switch between agents
function switchAgent(agent) {
    currentAgent = agent;
    
    // Update UI
    if (agent === 'web') {
        webAgentBtn.classList.add('active');
        apiAgentBtn.classList.remove('active');
    } else {
        webAgentBtn.classList.remove('active');
        apiAgentBtn.classList.add('active');
    }
    
    // Add system message about agent switch
    addMessage({
        type: 'system',
        content: `Switched to ${agent === 'web' ? 'Web Testing Agent' : 'API Testing Agent'}`
    });
}

// Handle sending a message
function handleSendMessage() {
    const message = userInput.value.trim();
    
    if (message && !isProcessing) {
        // Add user message to chat
        addMessage({
            type: 'user',
            content: message
        });
        
        // Clear input
        userInput.value = '';
        
        // Set processing state
        isProcessing = true;
        updateStatus(true, 'Processing...');
        
        // Send to backend
        sendToBackend(message);
    }
}

// Add a message to the chat
function addMessage(message) {
    const messageId = Date.now();
    const messageElement = document.createElement('div');
    messageElement.classList.add('message', message.type);
    messageElement.id = `message-${messageId}`;
    
    const contentElement = document.createElement('div');
    contentElement.classList.add('message-content');
    
    // Handle different content types
    if (typeof message.content === 'string') {
        // Convert markdown-like syntax to HTML
        contentElement.innerHTML = formatMessage(message.content);
    } else if (Array.isArray(message.content)) {
        // Handle step-by-step content
        message.content.forEach(step => {
            const stepElement = document.createElement('p');
            stepElement.innerHTML = formatMessage(step);
            contentElement.appendChild(stepElement);
        });
    }
    
    messageElement.appendChild(contentElement);
    chatMessages.appendChild(messageElement);
    
    // Scroll to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;
    
    return messageId;
}

// Format message with markdown-like syntax
function formatMessage(text) {
    // Convert code blocks
    text = text.replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>');
    
    // Convert inline code
    text = text.replace(/`([^`]+)`/g, '<code>$1</code>');
    
    // Convert bold text
    text = text.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    
    // Convert italic text
    text = text.replace(/\*([^*]+)\*/g, '<em>$1</em>');
    
    // Convert URLs to links
    text = text.replace(
        /(\b(https?|ftp|file):\/\/[-A-Z0-9+&@#\/%?=~_|!:,.;]*[-A-Z0-9+&@#\/%=~_|])/ig,
        '<a href="$1" target="_blank">$1</a>'
    );
    
    // Convert line breaks
    text = text.replace(/\n/g, '<br>');
    
    return text;
}

// Send message to backend
async function sendToBackend(message) {
    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message,
                agent: currentAgent
            })
        });
        
        if (!response.ok) {
            throw new Error(`Server responded with status: ${response.status}`);
        }
        
        // For streaming responses
        const reader = response.body.getReader();
        let partialResponse = '';
        let responseMessageId = null;
        
        while (true) {
            const { done, value } = await reader.read();
            
            if (done) {
                break;
            }
            
            // Convert the chunk to text
            const chunk = new TextDecoder().decode(value);
            partialResponse += chunk;
            
            try {
                // Try to parse the accumulated JSON
                const data = JSON.parse(partialResponse);
                
                // Handle the response
                if (!responseMessageId) {
                    // First chunk, create the message
                    responseMessageId = addMessage({
                        type: 'system',
                        content: data.message || 'Processing your request...'
                    });
                } else {
                    // Update existing message
                    updateMessage(responseMessageId, data.message);
                }
                
                // Handle test results if present
                if (data.results) {
                    addTestResult(data.results);
                }
                
                // Reset for the next chunk
                partialResponse = '';
            } catch (e) {
                // Incomplete JSON, continue accumulating
            }
        }
        
        // If we never got a valid response
        if (!responseMessageId) {
            addMessage({
                type: 'error',
                content: 'Failed to get a response from the server.'
            });
        }
        
    } catch (error) {
        console.error('Error sending message:', error);
        
        addMessage({
            type: 'error',
            content: `Error: ${error.message}`
        });
    } finally {
        // Reset processing state
        isProcessing = false;
        updateStatus(true, 'Connected');
    }
}

// Update an existing message
function updateMessage(messageId, content) {
    const messageElement = document.getElementById(`message-${messageId}`);
    if (messageElement) {
        const contentElement = messageElement.querySelector('.message-content');
        if (contentElement) {
            contentElement.innerHTML = formatMessage(content);
        }
    }
}

// Add test result to the results panel
function addTestResult(result) {
    // Remove "no results" message if present
    const noResults = resultsContent.querySelector('.no-results');
    if (noResults) {
        noResults.remove();
    }
    
    // Create result element
    const resultElement = document.createElement('div');
    resultElement.classList.add('test-result');
    
    if (result.status) {
        resultElement.classList.add(result.status.toLowerCase());
    }
    
    // Add title
    const titleElement = document.createElement('h3');
    titleElement.innerHTML = `
        <i class="fas fa-${result.status === 'PASS' ? 'check-circle' : 'times-circle'}"></i>
        ${result.title || 'Test Result'}
    `;
    resultElement.appendChild(titleElement);
    
    // Add description if present
    if (result.description) {
        const descElement = document.createElement('p');
        descElement.textContent = result.description;
        resultElement.appendChild(descElement);
    }
    
    // Add steps if present
    if (result.steps && result.steps.length > 0) {
        const stepsElement = document.createElement('div');
        stepsElement.classList.add('test-steps');
        
        result.steps.forEach(step => {
            const stepElement = document.createElement('div');
            stepElement.classList.add('test-step');
            
            const statusElement = document.createElement('span');
            statusElement.classList.add('test-step-status');
            statusElement.innerHTML = step.status === 'PASS' ? 
                '<i class="fas fa-check text-success"></i>' : 
                '<i class="fas fa-times text-danger"></i>';
            
            const textElement = document.createElement('span');
            textElement.textContent = step.description;
            
            stepElement.appendChild(statusElement);
            stepElement.appendChild(textElement);
            stepsElement.appendChild(stepElement);
        });
        
        resultElement.appendChild(stepsElement);
    }
    
    // Add screenshot if present
    if (result.screenshot) {
        const imgElement = document.createElement('img');
        imgElement.src = result.screenshot;
        imgElement.alt = 'Test Screenshot';
        imgElement.classList.add('test-screenshot');
        resultElement.appendChild(imgElement);
    }
    
    // Add to results panel
    resultsContent.prepend(resultElement);
}

// Clear all test results
function clearResults() {
    resultsContent.innerHTML = '<div class="no-results">No test results yet</div>';
}

// Check server status
async function checkServerStatus() {
    try {
        const response = await fetch('/api/status');
        
        if (response.ok) {
            updateStatus(true, 'Connected');
        } else {
            updateStatus(false, 'Server Error');
        }
    } catch (error) {
        updateStatus(false, 'Disconnected');
    }
}

// Update status indicator
function updateStatus(isOnline, message) {
    statusDot.className = `status-dot ${isOnline ? 'online' : 'offline'}`;
    statusText.textContent = message || (isOnline ? 'Connected' : 'Disconnected');
}

// Mock function for development - remove in production
function mockBackendResponse() {
    setTimeout(() => {
        addMessage({
            type: 'system',
            content: 'I\'ll test the login form at example.com for you. Starting the test now...'
        });
        
        setTimeout(() => {
            addTestResult({
                title: 'Login Form Test',
                status: 'PASS',
                description: 'Tested login form functionality at example.com',
                steps: [
                    { status: 'PASS', description: 'Navigated to example.com/login' },
                    { status: 'PASS', description: 'Found login form elements' },
                    { status: 'PASS', description: 'Entered test credentials' },
                    { status: 'PASS', description: 'Submitted form' },
                    { status: 'PASS', description: 'Verified successful login' }
                ],
                screenshot: 'https://via.placeholder.com/800x600.png?text=Login+Test+Screenshot'
            });
            
            isProcessing = false;
            updateStatus(true, 'Connected');
        }, 2000);
    }, 1000);
}
