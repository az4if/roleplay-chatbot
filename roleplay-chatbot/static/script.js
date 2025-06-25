document.addEventListener('DOMContentLoaded', () => {
    // Elements
    const wikiUrlInput = document.getElementById('wiki-url');
    const setCharacterBtn = document.getElementById('set-character');
    const setupContainer = document.getElementById('setup-container');
    const chatContainer = document.getElementById('chat-container');
    const characterImg = document.getElementById('character-img');
    const characterNameEl = document.getElementById('character-name');
    const speechStyleEl = document.getElementById('speech-style');
    const clearHistoryBtn = document.getElementById('clear-history');
    const chatHistory = document.getElementById('chat-history');
    const userInput = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');
    const emojiBtn = document.getElementById('emoji-btn');
    const typingIndicator = document.getElementById('typing-indicator');
    const modelStatusEl = document.getElementById('model-status');
    const lastInferenceTimeEl = document.getElementById('last-inference-time');
    const lastDurationEl = document.getElementById('last-duration');
    const inferenceCountEl = document.getElementById('inference-count');
    
    // Model status monitoring
    function checkModelStatus() {
        fetch('/status')
            .then(response => response.json())
            .then(data => {
                if (data.model_loaded) {
                    modelStatusEl.className = 'status-indicator loaded';
                    modelStatusEl.innerHTML = '<div class="status-dot"></div> <span>Model Ready</span>';
                } else if (data.model_loading) {
                    modelStatusEl.className = 'status-indicator loading';
                    modelStatusEl.innerHTML = '<div class="status-dot"></div> <span>Loading Model...</span>';
                } else if (data.error) {
                    modelStatusEl.className = 'status-indicator error';
                    modelStatusEl.innerHTML = `<div class="status-dot"></div> <span>Error: ${data.error.substring(0, 50)}</span>`;
                }
                
                // Update inference stats
                if (data.last_inference_time) {
                    const timeDiff = Math.floor((Date.now()/1000 - data.last_inference_time) * 1000);
                    lastInferenceTimeEl.textContent = formatTimeDiff(timeDiff);
                }
                
                if (data.last_inference_duration) {
                    lastDurationEl.textContent = `${(data.last_inference_duration).toFixed(2)}s`;
                }
                
                inferenceCountEl.textContent = data.inference_count || '0';
            });
    }
    
    // Format time difference for display
    function formatTimeDiff(ms) {
        const seconds = Math.floor(ms / 1000);
        if (seconds < 60) return `${seconds} seconds ago`;
        const minutes = Math.floor(seconds / 60);
        return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
    }
    
    // Check model status every 5 seconds
    setInterval(checkModelStatus, 5000);
    checkModelStatus(); // Initial check
    
    // Set character from wiki URL
    setCharacterBtn.addEventListener('click', async () => {
        const url = wikiUrlInput.value;
        if (!url) {
            addSystemMessage("Please enter a valid wiki URL");
            return;
        }
        
        setCharacterBtn.disabled = true;
        setCharacterBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Loading...';
        
        try {
            const response = await fetch('/set_character', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: `wiki_url=${encodeURIComponent(url)}`
            });
            
            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    // Update character info
                    characterNameEl.textContent = data.name;
                    speechStyleEl.querySelector('span').textContent = data.speech_style || "Speech style not detected";
                    
                    // Set character image if available
                    if (data.image_url) {
                        characterImg.src = data.image_url;
                    } else {
                        characterImg.src = "{{ url_for('static', filename='icons/icon.jpg') }}";
                    }
                    
                    // Smooth transition to chat interface
                    setupContainer.style.opacity = "1";
                    setupContainer.style.transform = "scale(1)";
                    
                    setTimeout(() => {
                        setupContainer.style.opacity = "0";
                        setupContainer.style.transform = "scale(0.95)";
                        
                        setTimeout(() => {
                            setupContainer.classList.add('hidden');
                            chatContainer.classList.add('visible');
                            
                            // Animation for chat container
                            chatContainer.style.opacity = "0";
                            chatContainer.style.transform = "translateY(20px)";
                            
                            setTimeout(() => {
                                chatContainer.style.opacity = "1";
                                chatContainer.style.transform = "translateY(0)";
                                addSystemMessage(`Character "${data.name}" loaded. Start chatting!`);
                                window.characterName = data.name;
                                userInput.focus();
                            }, 50);
                        }, 300);
                    }, 200);
                } else {
                    throw new Error(data.error || 'Failed to load character');
                }
            } else {
                const error = await response.text();
                throw new Error(error);
            }
        } catch (error) {
            console.error('Error setting character:', error);
            addSystemMessage(`Error: ${error.message || 'Failed to load character'}`);
        } finally {
            setCharacterBtn.disabled = false;
            setCharacterBtn.innerHTML = '<i class="fas fa-play"></i> Load Character';
        }
    });
    
    // Clear chat history
    clearHistoryBtn.addEventListener('click', async () => {
        const response = await fetch('/clear_history', {
            method: 'POST'
        });
        
        if (response.ok) {
            chatHistory.innerHTML = '';
            addSystemMessage('Chat history cleared');
        }
    });
    
    // Send message
    sendBtn.addEventListener('click', sendMessage);
    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });
    
    // Emoji button placeholder
    emojiBtn.addEventListener('click', () => {
        userInput.value += ' 😊';
        userInput.focus();
    });
    
    async function sendMessage() {
        const message = userInput.value.trim();
        if (!message || !window.characterName) return;
        
        // Add user message to chat
        addMessage("You", message, 'user-message');
        userInput.value = '';
        userInput.disabled = true;
        sendBtn.disabled = true;
        
        // Show typing indicator
        typingIndicator.classList.add('visible');
        
        try {
            // Use streaming
            const eventSource = new EventSource(`/chat?message=${encodeURIComponent(message)}`);
            let fullResponse = '';
            let messageDiv = null;
            
            eventSource.onmessage = (event) => {
                if (event.data) {
                    fullResponse += event.data;
                    
                    if (!messageDiv) {
                        // Create message container for bot response
                        messageDiv = document.createElement('div');
                        messageDiv.classList.add('message', 'bot-message');
                        messageDiv.innerHTML = `<strong>${window.characterName}:</strong> <span id="bot-response">${fullResponse}</span>`;
                        chatHistory.appendChild(messageDiv);
                    } else {
                        // Update existing response
                        document.getElementById('bot-response').textContent = fullResponse;
                    }
                    
                    // Scroll to bottom
                    chatHistory.scrollTop = chatHistory.scrollHeight;
                }
            };
            
            eventSource.onerror = () => {
                eventSource.close();
                typingIndicator.classList.remove('visible');
                userInput.disabled = false;
                sendBtn.disabled = false;
                
                // Update history after completion
                if (fullResponse) {
                    const history = JSON.parse(sessionStorage.getItem('chat_history') || '[]');
                    history.push({
                        user: message,
                        bot: fullResponse
                    });
                    sessionStorage.setItem('chat_history', JSON.stringify(history));
                }
            };
        } catch (error) {
            console.error('Error sending message:', error);
            addSystemMessage('Error communicating with server');
            typingIndicator.classList.remove('visible');
            userInput.disabled = false;
            sendBtn.disabled = false;
        }
    }
    
    function addMessage(sender, text, className) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', className);
        messageDiv.innerHTML = `<strong>${sender}:</strong> ${text}`;
        chatHistory.appendChild(messageDiv);
        chatHistory.scrollTop = chatHistory.scrollHeight;
        
        // Add animation effect
        messageDiv.style.opacity = '0';
        messageDiv.style.transform = 'translateY(10px)';
        setTimeout(() => {
            messageDiv.style.transition = 'opacity 0.3s, transform 0.3s';
            messageDiv.style.opacity = '1';
            messageDiv.style.transform = 'translateY(0)';
        }, 10);
    }
    
    function addSystemMessage(text) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', 'system-message');
        messageDiv.textContent = text;
        chatHistory.appendChild(messageDiv);
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }
    
    // Initialize
    addSystemMessage("Welcome to AI Character Roleplay! Enter a character wiki URL to begin.");
    
    // Add CSS transitions
    setupContainer.style.transition = 'all 0.3s ease';
    chatContainer.style.transition = 'all 0.4s ease';
});