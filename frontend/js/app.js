// Global voice-related variables and functions
let recognition = null;
let isListening = false;
let synth = window.speechSynthesis;
let isSpeaking = false;

/**
 * Toggle speech recognition
 */
function toggleSpeechRecognition() {
    if (isListening) {
        recognition.stop();
    } else {
        // Clear any existing text
        document.querySelector('.chat-input textarea').value = '';
        recognition.start();
    }
}

speakTextQueue = [];

/**
 * Speak text using text-to-speech
 * @param {string} text - Text to be spoken
 */
function speakText(text) {
    if (isSpeaking) {
        speakTextQueue.push(text);
        return;
    }

    // Cancel any ongoing speech
    synth.cancel();
    
    // Get checkbox state directly from DOM
    const autoReadCheckbox = document.getElementById('autoReadResponses');
    
    // Only continue if auto-read is enabled
    if (!autoReadCheckbox || !autoReadCheckbox.checked) return;

    isSpeaking = true;
    
    // Clean text of HTML tags
    const cleanText = text.replace(/<[^>]*>?/gm, '');
    
    // Create a new utterance
    const utterance = new SpeechSynthesisUtterance(cleanText);
    
    // Try to get the most natural FEMALE human-like voice
    // Priority: Natural female voices > Neural female > Premium female > Default female
    let voices = synth.getVoices();
    let preferredVoice = null;
    
    // Priority 1: Most natural FEMALE human-sounding voices (best quality)
    // These female voices sound most like real humans
    preferredVoice = voices.find(voice => 
        (voice.name.includes('Samantha') && voice.lang.startsWith('en')) ||  // macOS - very natural female
        (voice.name.includes('Karen') && voice.lang.startsWith('en')) ||     // macOS - natural female
        (voice.name.includes('Victoria') && voice.lang.startsWith('en')) ||  // macOS - natural female
        (voice.name.includes('Fiona') && voice.lang.startsWith('en')) ||     // macOS - natural female
        (voice.name.includes('Tessa') && voice.lang.startsWith('en')) ||     // macOS - natural female
        (voice.name.includes('Moira') && voice.lang.startsWith('en')) ||     // macOS - natural female
        (voice.name.includes('Kate') && voice.lang.startsWith('en')) ||      // macOS - natural female
        (voice.name.includes('Google') && voice.name.includes('US') && (voice.name.includes('Neural') || voice.name.includes('Wavenet')) && (voice.gender === 'female' || voice.name.toLowerCase().includes('female'))) || // Google Neural/Wavenet female
        (voice.name.includes('Microsoft') && (voice.name.includes('Zira') || voice.name.includes('Aria') || voice.name.includes('Jenny'))) || // Microsoft natural female voices
        (voice.name.includes('Amazon Polly') && (voice.gender === 'female' || voice.name.toLowerCase().includes('female'))) || // AWS Polly female
        (voice.name.includes('ElevenLabs') && (voice.gender === 'female' || voice.name.toLowerCase().includes('female')))   // ElevenLabs female
    );
    
    // Priority 2: Any Neural/Premium FEMALE voices (very natural)
    if (!preferredVoice) {
        preferredVoice = voices.find(voice => 
            (voice.name.includes('Neural') || voice.name.includes('Premium') || voice.name.includes('Enhanced') || voice.name.includes('Wavenet')) &&
            (voice.gender === 'female' || voice.name.toLowerCase().includes('female') || voice.lang.startsWith('en'))
        );
    }
    
    // Priority 3: Google US FEMALE voices (usually better quality)
    if (!preferredVoice) {
        preferredVoice = voices.find(voice => 
            voice.name.includes('Google') && 
            voice.name.includes('US') &&
            (voice.gender === 'female' || voice.name.toLowerCase().includes('female'))
        );
    }
    
    // Priority 4: Microsoft natural FEMALE voices
    if (!preferredVoice) {
        preferredVoice = voices.find(voice => 
            voice.name.includes('Microsoft') && 
            (voice.name.includes('Zira') || voice.name.includes('Aria') || voice.name.includes('Jenny') || voice.name.includes('Catherine'))
        );
    }
    
    // Priority 5: Any Google FEMALE voice (fallback)
    if (!preferredVoice) {
        preferredVoice = voices.find(voice => 
            voice.name.includes('Google') &&
            (voice.gender === 'female' || voice.name.toLowerCase().includes('female'))
        );
    }
    
    // Priority 6: Any US English FEMALE voice (explicitly female)
    if (!preferredVoice) {
        preferredVoice = voices.find(voice => 
            voice.lang.startsWith('en-US') && 
            (voice.name.includes('Female') || voice.gender === 'female' || 
             voice.name.toLowerCase().includes('woman') || voice.name.toLowerCase().includes('girl'))
        );
    }
    
    // Priority 7: macOS default female voices (last resort for female)
    if (!preferredVoice) {
        preferredVoice = voices.find(voice => 
            voice.lang.startsWith('en') && 
            (voice.name.includes('Samantha') || voice.name.includes('Karen') || voice.name.includes('Victoria') || 
             voice.name.includes('Fiona') || voice.name.includes('Tessa') || voice.name.includes('Moira'))
        );
    }
    
    if (preferredVoice) {
        utterance.voice = preferredVoice;
        console.log('Using FEMALE voice:', preferredVoice.name, preferredVoice.lang, 'Gender:', preferredVoice.gender);
    } else {
        console.warn('No preferred FEMALE voice found, using default');
    }
    
    utterance.lang = 'en-US';
    // Optimized for VERY natural, human-like FEMALE speech (minimal AI/robotic sound)
    utterance.rate = 0.75;   // Even slower pace (0.75 = 75% speed) - very natural, relaxed conversation
    utterance.pitch = 0.88;  // Lower pitch (0.88 = 88% pitch) - deeper, warmer, more human-like
    utterance.volume = 0.92; // Softer volume (0.92) - gentle, less robotic, more intimate
    
    utterance.onstart = () => {
        console.log('Speaking with voice:', utterance.voice ? utterance.voice.name : 'Default voice');
    };
    
    utterance.onend = () => {
        isSpeaking = false;

        if (speakTextQueue.length > 0) {
            const nextText = speakTextQueue.shift();
            speakText(nextText);
        }
    };
    
    utterance.onerror = (event) => {
        console.error('Speech synthesis error', event);
        isSpeaking = false;
    };
    
    // Speak the text
    synth.speak(utterance);
}

// Make the functions available globally
window.toggleSpeechRecognition = toggleSpeechRecognition;
window.speakText = speakText;

document.addEventListener('DOMContentLoaded', () => {
    // Check if required dependencies are loaded
    if (!window.DB) {
        console.error('DB not initialized. Please check db.js is loaded correctly.');
        alert('Application failed to initialize database. Please refresh the page or contact support.');
        return;
    }

    // DOM Elements
    const chatMessages = document.querySelector('.chat-messages');
    const chatInput = document.querySelector('.chat-input textarea');
    const sendButton = document.querySelector('.send-button');
    const micButton = document.querySelector('.mic-button');
    const voiceIndicator = document.querySelector('.voice-indicator');
    const voiceControls = document.querySelector('.voice-controls');
    const clearButton = document.querySelector('.btn-clear');
    const humanSupportButton = document.querySelector('.cta-human');

    const RESET_HISTORY_ON_LOAD = true;

    // State
    let isTyping = false;
    let conversationContext = {};
    let hasConversationStarted = false;

    // Initialize
    chatInput.focus();
    scrollToBottom();
    resetConversationState();
    initChatbot();

    // Event Listeners
    chatInput.addEventListener('input', autoResizeTextarea);
    chatInput.addEventListener('keydown', handleInputKeydown);
    sendButton.addEventListener('click', sendMessage);
    clearButton.addEventListener('click', clearChat);

    // Initialize the voices as soon as possible
    function initVoices() {
        return new Promise((resolve) => {
            if (synth.getVoices().length > 0) {
                resolve(synth.getVoices());
                return;
            }
            
            synth.onvoiceschanged = () => {
                resolve(synth.getVoices());
            };
        });
    }
    
    // Initialize voices
    initVoices().then(voices => {
        console.log('Available voices:', voices.map(v => v.name).join(', '));
    });
    
    // Initialize speech recognition if supported
    if ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window) {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = true;
        recognition.lang = 'en-US';

        recognition.onstart = () => {
            isListening = true;
            micButton.classList.add('listening');
            voiceIndicator.style.display = 'block';
        };

        recognition.onresult = (event) => {
            const transcript = Array.from(event.results)
                .map(result => result[0])
                .map(result => result.transcript)
                .join('');
            
            chatInput.value = transcript;
            autoResizeTextarea();
        };

        recognition.onend = () => {
            isListening = false;
            micButton.classList.remove('listening');
            voiceIndicator.style.display = 'none';
            
            // If we have content, send after a short delay to allow user to see what was recognized
            if (chatInput.value.trim()) {
                setTimeout(() => {
                    sendMessage();
                }, 1000);
            }
        };

        recognition.onerror = (event) => {
            console.error('Speech recognition error', event.error);
            isListening = false;
            micButton.classList.remove('listening');
            voiceIndicator.style.display = 'none';
        };

        // Add event listener for the mic button
        micButton.addEventListener('click', toggleSpeechRecognition);
        
        // Show voice controls since speech is supported
        if (voiceIndicator) {
            voiceIndicator.style.display = 'flex';
            console.log('Voice controls should be visible');
        }
    } else {
        // Hide mic button if speech recognition is not supported
        if (micButton) micButton.style.display = 'none';
        if (voiceIndicator) voiceIndicator.style.display = 'none';
        console.warn('Speech recognition not supported in this browser');
    }

    /**
     * Initialize Chatbot and its services
     */
    async function initChatbot() {
        try {
            console.log('Initializing Chatbot...');
            
            if (RESET_HISTORY_ON_LOAD) {
                await resetStoredConversations(true);
                conversationContext = {};
                console.log('Cleared stored conversations for a fresh session.');
            } else {
                // Load previous conversations for context
                const conversations = await loadRecentConversations();
                conversations.forEach((conversation) => {
                    addMessageToChat(conversation.sender, conversation.message, Date.parse(conversation.timestamp), false);
                });
            }

            // Show automatic greeting when chatbot starts (only if no previous messages)
            setTimeout(() => {
                const existingMessages = document.querySelectorAll('.message');
                if (existingMessages.length === 0) {
                    const greetingTimestamp = new Date();
                    addMessageToChat('bot', 'Welcome to StayAssist. How can I assist you today?', greetingTimestamp);
                    
                    // Save greeting to database
                    if (window.DB && window.DB.saveConversation) {
                        window.DB.saveConversation({
                            sender: 'bot',
                            message: 'Welcome to StayAssist. How can I assist you today?',
                            context: conversationContext,
                            timestamp: greetingTimestamp.toISOString()
                        });
                    }
                }
            }, 300); // Small delay to ensure everything is initialized

            console.log('Chatbot initialization complete');
        } catch (error) {
            console.error('Error initializing Chatbot:', error);
        }
    }


    /**
     * Load recent conversations from the database
     */
    async function loadRecentConversations() {
        try {
            const conversations = (await window.DB.getConversations())
                .sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));

            // Only load the last 10 conversations if there are any
            if (conversations && conversations.length > 0) {
                const recentConversations = conversations.slice(-10);

                // Update context with historical data
                conversationContext.history = recentConversations;
                console.log('Loaded conversation history for context:', conversationContext);
            }

            return conversations;
        } catch (error) {
            console.error('Error loading conversations:', error);
        }
    }

    /**
     * Auto-resize textarea as user types
     */
    function autoResizeTextarea() {
        chatInput.style.height = 'auto';
        chatInput.style.height = chatInput.scrollHeight + 'px';
    }

    /**
     * Handle keydown in the textarea (e.g., Enter to send)
     */
    function handleInputKeydown(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    }

    /**
     * Send user message and get bot response
     */
    function sendMessage() {
        const message = chatInput.value.trim();
        if (!message) return;

        // Current timestamp
        const timestamp = new Date();

        // Mark that the conversation has started so CTA can appear
        markConversationStarted();

        // Add user message to chat
        addMessageToChat('user', message, timestamp);

        // Save user message to database
        window.DB.saveConversation({
            sender: 'user',
            message: message,
            context: conversationContext,
            timestamp: timestamp.toISOString() // Explicit timestamp
        });

        // Clear input
        chatInput.value = '';
        chatInput.style.height = 'auto';

        // Show typing indicator
        showTypingIndicator();

        // Reset booking slots in context when starting a new booking
        const messageLower = message.toLowerCase().trim();
        const bookingPhrases = ['book a room', 'book room', 'i want to book', 'reserve a room', 'make a reservation', 'reserve', 'booking'];
        if (bookingPhrases.some(phrase => messageLower.includes(phrase))) {
            console.log('Detected new booking request, resetting booking slots in frontend context');
            if (!conversationContext.slots) {
                conversationContext.slots = {};
            }
            conversationContext.slots.guests = null;
            conversationContext.slots.room_type = null;
            conversationContext.slots.arrival_date = null;
            conversationContext.slots.departure_date = null;
            conversationContext.slots.nights = null;
            conversationContext.slots.rooms = null;
            conversationContext.slots.payment_option = null;
        }

        // Send message to Python backend and get response
        fetch('/api/send_message', { 
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ message: message, context: conversationContext })
        })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`Server responded with ${response.status}: ${response.statusText}`);
                }
                return response.json();
            })
            .then(data => {
                console.log("Response from Rasa:", data); // Debug: log the response
                console.log("Response from Rasa (stringified):", JSON.stringify(data, null, 2)); // Full response
                const responseTimestamp = new Date();
                hideTypingIndicator();

                try {
                // Check if data is in the expected format
                if (data.fallback_response) {
                    // Handle fallback response (error case)
                        if (Array.isArray(data.fallback_response) && data.fallback_response.length > 0) {
                            addMessageToChat('bot', data.fallback_response[0].text || 'I apologize, but I encountered an issue processing your request.', responseTimestamp);
                        } else {
                            addMessageToChat('bot', 'I apologize, but I encountered an issue processing your request. Please try again.', responseTimestamp);
                        }
                    return;
                }

                // Process Rasa response
                handleRasaResponse(data, responseTimestamp);
                } catch (error) {
                    console.error('Error processing Rasa response:', error);
                    addMessageToChat('bot', 'I apologize, but I encountered an issue processing your request. Please try again.', responseTimestamp);
                }
            })
            .catch(error => {
                const errorTimestamp = new Date();
                console.error('Error getting response from Rasa:', error);
                hideTypingIndicator();
                addMessageToChat('bot', 'Sorry, I encountered a network error. Please try again later.', errorTimestamp);
            });
    }

    /**
     * Handle Rasa response and perform actions based on it
     * @param {Object} response - Response from Rasa backend
     * @param {Date} timestamp - Timestamp when response was received
     */
    function handleRasaResponse(response, timestamp) {
        if (!response) {
            console.log('Empty response received (this might be OK if confirmation was already shown)');
            // Don't show error message if this is from date confirmation
            // The confirmation message is already displayed
            return;
        }

        console.log("Processing response:", response);
        console.log("Response messages:", response.messages || response);
        
        // Debug: Log each message in detail
        const messages = response.messages || (Array.isArray(response) ? response : []);
        messages.forEach((msg, index) => {
            console.log(`Message ${index}:`, msg);
            console.log(`Message ${index} json_message:`, msg.json_message);
        });
        
        // Track seen messages to prevent duplicates
        const seenMessages = new Set();
        let messageAdded = false;
        let allMessages = [];
        
        // Collect all messages first
        if (Array.isArray(response)) {
            response.forEach(message => {
                // Skip empty messages and calendar widget messages (they're handled separately)
                if (message && message.text && typeof message.text === 'string' && message.text.trim() && 
                    !(message.json_message && message.json_message.type === 'calendar')) {
                    allMessages.push(message.text.trim());
                }
                // Check for calendar widget (skip if text is empty to avoid duplicate messages)
                if (message && message.json_message && message.json_message.type === 'calendar') {
                    console.log('Found calendar widget in array response:', message.json_message);
                    try {
                        addCalendarWidget(message.json_message, timestamp);
                        // Don't set messageAdded to true if text is empty, to avoid showing empty message
                        if (message.text && message.text.trim()) {
                            messageAdded = true;
                        }
                    } catch (calendarError) {
                        console.error('Error adding calendar widget:', calendarError);
                        // Don't fail completely, just log the error
                    }
                }
            });
        } else if (response.messages && Array.isArray(response.messages)) {
            response.messages.forEach(message => {
                // Skip empty messages and calendar widget messages (they're handled separately)
                if (message && message.text && typeof message.text === 'string' && message.text.trim() && 
                    !(message.json_message && message.json_message.type === 'calendar')) {
                    allMessages.push(message.text.trim());
                }
                // Check for calendar widget (skip if text is empty to avoid duplicate messages)
                if (message && message.json_message && message.json_message.type === 'calendar') {
                    console.log('Found calendar widget in messages array:', message.json_message);
                    try {
                        addCalendarWidget(message.json_message, timestamp);
                        // Don't set messageAdded to true if text is empty, to avoid showing empty message
                        if (message.text && message.text.trim()) {
                            messageAdded = true;
                        }
                    } catch (calendarError) {
                        console.error('Error adding calendar widget:', calendarError);
                        // Don't fail completely, just log the error
                    }
                }
            });
        }
        
        // Filter out duplicate or very similar messages
        // Check if we already have a greeting in the chat
        const existingGreeting = Array.from(document.querySelectorAll('.message-text')).some(msg => {
            const text = msg.textContent.toLowerCase();
            return text.includes('welcome to stayassist') && text.includes('how can i assist');
        });
        
        // CRITICAL: Filter out "Let's continue with book room" messages - these are unwanted
        allMessages = allMessages.filter(msg => {
            const msgLower = msg.toLowerCase();
            // Filter out "Let's continue" messages (including "Let's continue with book room")
            if (msgLower.includes("let's continue") || msgLower.includes("lets continue") || 
                msgLower.includes("let's continue with") || msgLower.includes("lets continue with") ||
                msgLower.includes("let's continue with book") || msgLower.includes("lets continue with book")) {
                console.log('Filtered out unwanted "Let\'s continue" message:', msg);
                return false;
            }
            // Also filter out messages that appear right after the information sufficient question
            // These are unwanted LLM responses
            if (msgLower.includes("continue") && (msgLower.includes("book") || msgLower.includes("booking"))) {
                console.log('Filtered out unwanted continue/booking message:', msg);
                return false;
            }
            return true;
        });
        
        // CRITICAL: Filter out fallback messages when they appear after "I hope I've provided you with sufficient information"
        // Check if previous message was the information sufficient question (both in DOM and in current response)
        const previousMessages = Array.from(document.querySelectorAll('.message-text')).slice(-5);
        const hasInfoQuestionInDOM = previousMessages.some(prevMsg => {
            const prevText = prevMsg.textContent.toLowerCase();
            return prevText.includes("i hope i've provided you with sufficient information") ||
                   prevText.includes("is there anything else you'd like to know") ||
                   prevText.includes("shall we continue with your booking");
        });
        
        // Also check if the current response contains the info question
        const hasInfoQuestionInResponse = allMessages.some(msg => {
            const msgLower = msg.toLowerCase();
            return msgLower.includes("i hope i've provided you with sufficient information") ||
                   msgLower.includes("is there anything else you'd like to know") ||
                   msgLower.includes("shall we continue with your booking");
        });
        
        const hasInfoQuestion = hasInfoQuestionInDOM || hasInfoQuestionInResponse;
        
        // Filter out fallback messages
        const fallbackPhrases = [
            "i'm sorry i am unable to understand you",
            "could you please rephrase",
            "i'm sorry",
            "unable to understand",
            "please rephrase",
            "utter_ask_rephrase"
        ];
        
        allMessages = allMessages.filter(msg => {
            const msgLower = msg.toLowerCase();
            const msgNormalized = msgLower.trim();
            
            // ALWAYS filter "placeholder" messages - these are internal Rasa messages
            // Check both exact match and if it contains "placeholder"
            if (msgNormalized === "placeholder" || msgNormalized.includes("placeholder")) {
                console.log('🚫 Filtered out placeholder message:', msg);
                return false;
            }
            
            const isFallback = fallbackPhrases.some(phrase => msgLower.includes(phrase));
            
            // ALWAYS filter fallback if info question was asked (in DOM or in response)
            if (isFallback && hasInfoQuestion) {
                console.log('🚫 Filtered out fallback message after info question:', msg);
                return false;
            }
            
            // Also filter fallback if it appears right after "Great! Let's continue" in the same response
            const msgIndex = allMessages.indexOf(msg);
            if (msgIndex > 0) {
                const prevMsgInResponse = allMessages[msgIndex - 1].toLowerCase();
                if (prevMsgInResponse.includes("great") && prevMsgInResponse.includes("continue") && isFallback) {
                    console.log('🚫 Filtered out fallback message after "Great! Let\'s continue":', msg);
                    return false;
                }
            }
            
            return true;
        });
        
        // Filter out "What else can I help you with?" if it appears after "Great! Let's continue with your booking."
        // This is a fallback response that shouldn't appear when we're continuing a booking flow
        if (allMessages.length >= 2) {
            const firstMsg = allMessages[0].toLowerCase();
            const secondMsg = allMessages[1].toLowerCase();
            if (firstMsg.includes("great") && firstMsg.includes("continue") && 
                (secondMsg.includes("what else") || secondMsg.includes("how can i assist") || secondMsg.includes("how can i help"))) {
                // Remove the fallback message
                console.log('Filtered out fallback message after "continue":', allMessages[1]);
                allMessages = [allMessages[0]];
            }
        }
        
        // Filter out "What else can I help you with?" after booking summaries
        const bookingSummaryIndicators = ["booking reference", "booking summary", "your booking reference is"];
        const hasBookingSummary = allMessages.some(msg => {
            const msgLower = msg.toLowerCase();
            return bookingSummaryIndicators.some(indicator => msgLower.includes(indicator));
        });
        if (hasBookingSummary) {
            allMessages = allMessages.filter(msg => {
                const msgLower = msg.toLowerCase();
                const isHelpMessage = msgLower.includes("what else can i help") || 
                                    msgLower.includes("how can i assist") || 
                                    msgLower.includes("how can i help");
                if (isHelpMessage) {
                    console.log('🚫 Frontend: Filtered "What else can I help" after booking summary:', msg);
                    return false;
                }
                return true;
            });
        }
        
        // Filter exact duplicates (case-insensitive)
        const uniqueMessages = [];
        const seenNormalized = new Set();
        allMessages.forEach(msg => {
            const normalized = msg.toLowerCase().trim();
            if (!seenNormalized.has(normalized)) {
                seenNormalized.add(normalized);
                uniqueMessages.push(msg);
            } else {
                console.log('🚫 Frontend: Filtered duplicate message:', msg);
            }
        });
        allMessages = uniqueMessages;
        
        // If we have multiple messages and the first one is a greeting, only show the first one
        if (allMessages.length > 1) {
            const firstMessage = allMessages[0].toLowerCase();
            // Check if first message is a greeting
            if (firstMessage.includes('welcome') || firstMessage.includes('how can i assist') || firstMessage.includes('how can i help')) {
                // Only show the first message (the greeting)
                allMessages = [allMessages[0]];
            }
        }
        
        // CRITICAL: Filter duplicate "For how many guests?" messages
        const guestsQuestionCount = allMessages.filter(msg => 
            msg.toLowerCase().includes("for how many guests")
        ).length;
        if (guestsQuestionCount > 1) {
            // Keep only the first occurrence
            let foundFirst = false;
            allMessages = allMessages.filter(msg => {
                if (msg.toLowerCase().includes("for how many guests")) {
                    if (!foundFirst) {
                        foundFirst = true;
                        return true;
                    }
                    console.log('🚫 Frontend: Filtered duplicate "For how many guests?":', msg);
                    return false;
                }
                return true;
            });
        }
        
        // If there's already a greeting in the chat and we're getting another greeting, filter it out
        if (existingGreeting) {
            allMessages = allMessages.filter(msg => {
                const msgLower = msg.toLowerCase();
                return !(msgLower.includes('welcome to stayassist') && msgLower.includes('how can i assist'));
            });
        }
        
        // Display the filtered messages
        allMessages.forEach(messageText => {
            addMessageToChat('bot', messageText, timestamp);
            messageAdded = true;

                    // Save bot response to database
            try {
                if (window.DB && window.DB.saveConversation) {
                    window.DB.saveConversation({
                        sender: 'bot',
                        message: messageText,
                        context: response.context || conversationContext,
                        timestamp: timestamp.toISOString()
                    });
                }
            } catch (dbError) {
                console.error('Error saving to database:', dbError);
            }
        });
        
        if (messageAdded) {
            // Process actions from Rasa
            if (response.actions && Array.isArray(response.actions) && response.actions.length > 0) {
                response.actions.forEach(action => {
                    try {
                        executeAction(action, response.context);
                    } catch (actionError) {
                        console.error('Error executing action:', actionError);
                    }
                });
            }

            // Update conversation context
            if (response.context && typeof response.context === 'object') {
                try {
                    conversationContext = {
                        ...conversationContext,
                        ...response.context
                    };
                } catch (contextError) {
                    console.error('Error updating context:', contextError);
                }
            }
            return;
        }

        // Process actions from Rasa
        if (response.actions && Array.isArray(response.actions) && response.actions.length > 0) {
            response.actions.forEach(action => {
                try {
                executeAction(action, response.context);
                } catch (actionError) {
                    console.error('Error executing action:', actionError);
                }
            });
        }

        // Update conversation context
        if (response.context && typeof response.context === 'object') {
            try {
            conversationContext = {
                ...conversationContext,
                ...response.context
            };
            } catch (contextError) {
                console.error('Error updating context:', contextError);
            }
        }
        
            // If no response was processed, check if it's a greeting and provide a fallback
            if (!messageAdded && (!response.actions || !Array.isArray(response.actions) || response.actions.length === 0)) {
                // Check if the last user message contains date information (from calendar confirmation)
                const lastUserMessage = document.querySelectorAll('.user-message .message-text');
                let isDateConfirmation = false;
                if (lastUserMessage.length > 0) {
                    const lastText = lastUserMessage[lastUserMessage.length - 1].textContent.toLowerCase().trim();
                    // Check if it's a date confirmation message
                    if (lastText.includes('arrival date:') && lastText.includes('departure date:')) {
                        isDateConfirmation = true;
                    }
                }
                
                // If it's a date confirmation, don't show fallback - the confirmation is already shown
                if (isDateConfirmation) {
                    console.log('Date confirmation detected, skipping fallback message');
                    return;
                }
                
                // Check the last user message to see if it's a greeting
                if (lastUserMessage.length > 0) {
                    const lastText = lastUserMessage[lastUserMessage.length - 1].textContent.toLowerCase().trim();
                    const greetingWords = ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening', 'greetings', 'hallo'];
                    const isGreeting = greetingWords.some(word => lastText.includes(word));
                    
                    if (isGreeting) {
                        // If it's a greeting, provide a friendly greeting response instead of fallback
                        addMessageToChat('bot', "Hello! How can I help you today?", timestamp);
                        return;
                    }
                }
                // For non-greetings, show the fallback message
            addMessageToChat('bot', "I'm processing your request. Please give me a moment.", timestamp);
        }
    }

    /**
     * Execute actions received from Rasa
     * @param {Object} action - Action to execute
     * @param {Object} context - Context for the action
     */
    function executeAction(action, context) {
        switch (action.name) {
            default:
                console.log('Unknown action:', action.name);
        }
    }

    /**
     * Add calendar widget to chat with support for date range selection
     * @param {Object} calendarData - Calendar data from Rasa (with mode: "arrival" or "departure")
     * @param {Date} timestamp - Timestamp for the message
     */
    function addCalendarWidget(calendarData, timestamp) {
        console.log('addCalendarWidget called with:', calendarData, timestamp);
        // Create bot message container
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', 'bot-message');

        const avatarDiv = document.createElement('div');
        avatarDiv.classList.add('message-avatar');
        const avatarIcon = document.createElement('i');
        avatarIcon.classList.add('fa-solid', 'fa-robot');
        avatarDiv.appendChild(avatarIcon);
        messageDiv.appendChild(avatarDiv);

        const contentDiv = document.createElement('div');
        contentDiv.classList.add('message-content');

        // Add calendar widget
        const calendarWidget = document.createElement('div');
        calendarWidget.classList.add('calendar-widget');

        const calendarHeader = document.createElement('div');
        calendarHeader.classList.add('calendar-header');
        
        // Previous month button
        const prevButton = document.createElement('button');
        prevButton.classList.add('calendar-nav-button', 'calendar-prev');
        prevButton.innerHTML = '<i class="fa-solid fa-chevron-left"></i>';
        prevButton.setAttribute('aria-label', 'Previous month');
        calendarHeader.appendChild(prevButton);
        
        const monthYear = document.createElement('div');
        monthYear.classList.add('calendar-month-year');
        
        // Create dates grid FIRST before defining updateCalendar
        const datesGrid = document.createElement('div');
        datesGrid.classList.add('calendar-dates');
        
        const today = new Date();
        const currentMonth = today.getMonth();
        const currentYear = today.getYear() + 1900;
        
        const monthNames = ['January', 'February', 'March', 'April', 'May', 'June',
                          'July', 'August', 'September', 'October', 'November', 'December'];
        
        let displayMonth = currentMonth;
        let displayYear = currentYear;
        
        // Store selected dates for booking mode
        let selectedArrivalDate = null;
        let selectedDepartureDate = null;
        
        // Function to update calendar display
        function updateCalendar() {
            monthYear.textContent = `${monthNames[displayMonth]} ${displayYear}`;
            
            // Clear existing dates
            datesGrid.innerHTML = '';
            
            // Get first day of month and number of days
            const firstDay = new Date(displayYear, displayMonth, 1).getDay();
            const daysInMonth = new Date(displayYear, displayMonth + 1, 0).getDate();
            const minDate = calendarData.min_date ? new Date(calendarData.min_date) : today;

            // Add empty cells for days before month starts
            for (let i = 0; i < firstDay; i++) {
                const emptyCell = document.createElement('div');
                emptyCell.classList.add('calendar-date', 'empty');
                datesGrid.appendChild(emptyCell);
            }

            // Add date cells
            for (let day = 1; day <= daysInMonth; day++) {
                const dateCell = document.createElement('div');
                dateCell.classList.add('calendar-date');
                dateCell.textContent = day;

                const cellDate = new Date(displayYear, displayMonth, day);
                cellDate.setHours(0, 0, 0, 0);
                const todayDate = new Date(today);
                todayDate.setHours(0, 0, 0, 0);
                const minDateOnly = new Date(minDate);
                minDateOnly.setHours(0, 0, 0, 0);

                // Mark today
                if (cellDate.getTime() === todayDate.getTime()) {
                    dateCell.classList.add('today');
                }

                // Disable past dates or dates before min_date
                if (cellDate < minDateOnly) {
                    dateCell.classList.add('disabled');
                } else {
                    // Check if arrival_date is set and we're in departure mode
                    if (calendarData.mode === 'departure' && calendarData.arrival_date) {
                        // Parse arrival date to compare
                        const arrivalDate = new Date(calendarData.arrival_date);
                        arrivalDate.setHours(0, 0, 0, 0);
                        // Departure must be after arrival
                        if (cellDate <= arrivalDate) {
                            dateCell.classList.add('disabled');
                        }
                    }
                    
                    // In booking mode, handle both dates
                    if (calendarData.mode === 'booking') {
                        // Mark selected arrival date
                        if (selectedArrivalDate && cellDate.getTime() === selectedArrivalDate.getTime()) {
                            dateCell.classList.add('selected', 'arrival');
                        }
                        // Mark selected departure date
                        if (selectedDepartureDate && cellDate.getTime() === selectedDepartureDate.getTime()) {
                            dateCell.classList.add('selected', 'departure');
                        }
                        // Mark dates in range (between arrival and departure)
                        if (selectedArrivalDate && selectedDepartureDate) {
                            if (cellDate > selectedArrivalDate && cellDate < selectedDepartureDate) {
                                dateCell.classList.add('in-range');
                            }
                        }
                        // Disable dates before arrival if arrival is selected
                        if (selectedArrivalDate && cellDate < selectedArrivalDate) {
                            dateCell.classList.add('disabled');
                        }
                    }
                    
                    // Only add click handler if not disabled
                    if (!dateCell.classList.contains('disabled')) {
                        // Add click handler
                        dateCell.addEventListener('click', () => {
                            if (calendarData.mode === 'booking') {
                                // Booking mode: handle both dates
                                if (!selectedArrivalDate || (selectedArrivalDate && selectedDepartureDate)) {
                                    // Start new selection: set arrival
                                    selectedArrivalDate = new Date(cellDate);
                                    selectedDepartureDate = null;
                                    // Clear all selections
                                    datesGrid.querySelectorAll('.calendar-date').forEach(cell => {
                                        cell.classList.remove('selected', 'arrival', 'departure', 'in-range');
                                    });
                                    dateCell.classList.add('selected', 'arrival');
                                } else if (selectedArrivalDate && !selectedDepartureDate) {
                                    // Set departure
                                    if (cellDate > selectedArrivalDate) {
                                        selectedDepartureDate = new Date(cellDate);
                                        dateCell.classList.add('selected', 'departure');
                                        // Mark range
                                        datesGrid.querySelectorAll('.calendar-date').forEach(cell => {
                                            const cellDay = parseInt(cell.textContent);
                                            if (cellDay && !cell.classList.contains('empty')) {
                                                const cellDateCheck = new Date(displayYear, displayMonth, cellDay);
                                                cellDateCheck.setHours(0, 0, 0, 0);
                                                if (cellDateCheck > selectedArrivalDate && cellDateCheck < selectedDepartureDate) {
                                                    cell.classList.add('in-range');
                                                }
                                            }
                                        });
                                        
                                        // Show confirm button when both dates are selected
                                        if (selectedArrivalDate && selectedDepartureDate) {
                                            confirmContainer.style.display = 'block';
                                        }
                                    } else {
                                        // Invalid: departure must be after arrival
                                        alert('Departure date must be after arrival date');
                                    }
                                }
                            } else {
                                // Single date mode (arrival or departure)
                                // Remove selected class from all dates
                                datesGrid.querySelectorAll('.calendar-date').forEach(cell => {
                                    cell.classList.remove('selected');
                                });
                                // Add selected class to clicked date
                                dateCell.classList.add('selected');
                                
                                // Format date and send to Rasa
                                const selectedDate = cellDate.toLocaleDateString('en-GB', {
                                    day: 'numeric',
                                    month: 'long',
                                    year: 'numeric'
                                });
                                
                                // Send date to Rasa
                                sendToRasa(selectedDate);
                            }
                        });
                    }
                }

                datesGrid.appendChild(dateCell);
            }
        }
        
        // Initial calendar render
        updateCalendar();
        
        // Navigation buttons
        prevButton.addEventListener('click', () => {
            displayMonth--;
            if (displayMonth < 0) {
                displayMonth = 11;
                displayYear--;
            }
            updateCalendar();
        });
        
        // Next month button
        const nextButton = document.createElement('button');
        nextButton.classList.add('calendar-nav-button', 'calendar-next');
        nextButton.innerHTML = '<i class="fa-solid fa-chevron-right"></i>';
        nextButton.setAttribute('aria-label', 'Next month');
        nextButton.addEventListener('click', () => {
            displayMonth++;
            if (displayMonth > 11) {
                displayMonth = 0;
                displayYear++;
            }
            updateCalendar();
        });
        
        monthYear.textContent = `${monthNames[displayMonth]} ${displayYear}`;
        calendarHeader.appendChild(monthYear);
        calendarHeader.appendChild(nextButton);
        calendarWidget.appendChild(calendarHeader);

        // Days header (static, doesn't change)
        const daysHeader = document.createElement('div');
        daysHeader.classList.add('calendar-days-header');
        const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
        dayNames.forEach(day => {
            const dayName = document.createElement('div');
            dayName.classList.add('calendar-day-name');
            dayName.textContent = day;
            daysHeader.appendChild(dayName);
        });
        calendarWidget.appendChild(daysHeader);

        // Dates grid is already created above, just append it
        calendarWidget.appendChild(datesGrid);
        
        // Create confirm button container (initially hidden)
        const confirmContainer = document.createElement('div');
        confirmContainer.classList.add('calendar-confirm-container');
        confirmContainer.style.display = 'none';
        confirmContainer.id = 'calendar-confirm-' + Date.now();
        
        const confirmButton = document.createElement('button');
        confirmButton.classList.add('calendar-confirm-button');
        confirmButton.textContent = 'Confirm';
        confirmButton.addEventListener('click', () => {
            if (selectedArrivalDate && selectedDepartureDate) {
                const arrivalStr = selectedArrivalDate.toLocaleDateString('en-GB', {
                    day: 'numeric',
                    month: 'long',
                    year: 'numeric'
                });
                const departureStr = selectedDepartureDate.toLocaleDateString('en-GB', {
                    day: 'numeric',
                    month: 'long',
                    year: 'numeric'
                });
                
                // Send both dates together in one message to Rasa
                // Format: "arrival date: [date], departure date: [date]"
                const combinedMessage = `arrival date: ${arrivalStr}, departure date: ${departureStr}`;
                
                // Show user message first
                const userTimestamp = new Date();
                addMessageToChat('user', combinedMessage, userTimestamp);
                
                // Then show bot confirmation message IMMEDIATELY (before sending to Rasa)
                const confirmMessage = `Arrival date: ${arrivalStr}\nDeparture date: ${departureStr}\n\nThe arrival and departure dates are available.`;
                const botTimestamp = new Date();
                addMessageToChat('bot', confirmMessage, botTimestamp);
                
                // Then send to Rasa (but skip adding user message since we already showed it)
                // Use a small delay to ensure the bot message is shown first
                setTimeout(() => {
                    sendToRasaWithoutUserMessage(combinedMessage);
                }, 200);
                
                // Hide confirm button
                confirmContainer.style.display = 'none';
            }
        });
        confirmContainer.appendChild(confirmButton);
        calendarWidget.appendChild(confirmContainer);
        
        // confirmContainer is available in the click handler scope above
        
        contentDiv.appendChild(calendarWidget);

        // Add timestamp
        const timeDiv = document.createElement('div');
        timeDiv.classList.add('message-time');
        timeDiv.textContent = formatTimestamp(timestamp);
        contentDiv.appendChild(timeDiv);

        messageDiv.appendChild(contentDiv);
        chatMessages.appendChild(messageDiv);
        scrollToBottom();
    }

    /**
     * Format timestamp to human-readable string
     * @param {Date} timestamp - The timestamp to format
     * @returns {string} - Formatted timestamp string
     */
    function formatTimestamp(timestamp) {
        // If it's not a Date object, try to convert it
        if (!(timestamp instanceof Date)) {
            timestamp = new Date(timestamp);
        }

        // Check if timestamp is today
        const now = new Date();
        const isToday = timestamp.toDateString() === now.toDateString();

        // Format options
        const timeOptions = { hour: '2-digit', minute: '2-digit' };
        const dateTimeOptions = {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        };

        // If it's today, just show the time, otherwise show date and time
        return timestamp.toLocaleString(undefined, isToday ? timeOptions : dateTimeOptions);
    }

    /**
     * Add a message to the chat
     */
    function addMessageToChat(sender, text, timestamp = new Date(), newMessage = true) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message');
        messageDiv.classList.add(sender === 'user' ? 'user-message' : 'bot-message');

        const avatarDiv = document.createElement('div');
        avatarDiv.classList.add('message-avatar');

        const avatarIcon = document.createElement('i');
        avatarIcon.classList.add('fa-solid');
        avatarIcon.classList.add(sender === 'user' ? 'fa-user' : 'fa-robot');

        avatarDiv.appendChild(avatarIcon);
        messageDiv.appendChild(avatarDiv);

        const contentDiv = document.createElement('div');
        contentDiv.classList.add('message-content');

        const textDiv = document.createElement('div');
        textDiv.classList.add('message-text');

        // Format the text content properly
        // Check if the text contains HTML and handle accordingly
        if (/<[a-z][\s\S]*>/i.test(text)) {
            // If the text contains HTML, set it as innerHTML
            textDiv.innerHTML = text;
        } else {
            // Convert plain text to HTML with line breaks and formatting
            const formattedText = text
                .replace(/\n/g, '<br>')
                .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                .replace(/\*(.*?)\*/g, '<em>$1</em>')
                .replace(/```(.*?)/gs, '<pre><code>$1</code></pre>')
                .replace(/`(.*?)`/g, '<code>$1</code>');
            textDiv.innerHTML = formattedText;
        }

        const timeDiv = document.createElement('div');
        timeDiv.classList.add('message-time');
        timeDiv.textContent = formatTimestamp(timestamp);

        contentDiv.appendChild(textDiv);
        contentDiv.appendChild(timeDiv);
        messageDiv.appendChild(contentDiv);

        chatMessages.appendChild(messageDiv);
        scrollToBottom();

        // If it's a bot message, read it out loud
        if (sender === 'bot' && newMessage) {
            window.speakText(text);
        }
    }

    /**
     * Show typing indicator
     */
    function showTypingIndicator() {
        if (isTyping) return;

        isTyping = true;
        const typingDiv = document.createElement('div');
        typingDiv.classList.add('message', 'bot-message', 'typing-message');

        const avatarDiv = document.createElement('div');
        avatarDiv.classList.add('message-avatar');

        const avatarIcon = document.createElement('i');
        avatarIcon.classList.add('fa-solid', 'fa-robot');

        avatarDiv.appendChild(avatarIcon);
        typingDiv.appendChild(avatarDiv);

        const contentDiv = document.createElement('div');
        contentDiv.classList.add('message-content');

        const textDiv = document.createElement('div');
        textDiv.classList.add('message-text');

        const typingIndicator = document.createElement('div');
        typingIndicator.classList.add('typing-indicator');

        for (let i = 0; i < 3; i++) {
            const dot = document.createElement('div');
            dot.classList.add('typing-dot');
            typingIndicator.appendChild(dot);
        }

        textDiv.appendChild(typingIndicator);
        contentDiv.appendChild(textDiv);
        typingDiv.appendChild(contentDiv);

        chatMessages.appendChild(typingDiv);
        scrollToBottom();
    }

    /**
     * Hide typing indicator
     */
    function hideTypingIndicator() {
        const typingMessage = document.querySelector('.typing-message');
        if (typingMessage) {
            typingMessage.remove();
        }
        isTyping = false;
    }

    /**
     * Clear chat messages with confirmation
     */
    function clearChat() {
        // Show a confirmation dialog
        const confirmClear = confirm("Are you sure you want to clear the chat history? This action cannot be undone.");

        if (confirmClear) {
            const messages = Array.from(document.querySelectorAll('.message'));
            messages.forEach(msg => msg.remove());

            // Clear conversations from database
            resetStoredConversations();

            // Reset conversation context
            conversationContext = {};
            resetConversationState();
        }
    }

    /**
     * Clear conversations from the database
     */
    async function resetStoredConversations(silent = false) {
        try {
            if (window.DB?.db?.conversations) {
                await window.DB.db.conversations.clear();
                if (!silent) {
                    console.log('Deleted all conversations from database');
                }
            } else if (!silent) {
                console.warn('Database not initialized, nothing to clear.');
            }
        } catch (error) {
            if (!silent) {
                console.error('Error clearing conversations from database:', error);
            }
        }
    }

    /**
     * Scroll to bottom of chat messages
     */
    function scrollToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    // Helper function for LLM action buttons to send messages to Rasa
    function sendToRasa(message) {
        // Create a timestamp
        const timestamp = new Date();

        // Mark conversation started if triggered via helper button
        markConversationStarted();
        
        // Show message in chat
        addMessageToChat('user', message, timestamp);
        
        // Show typing indicator
        showTypingIndicator();
        
        // Send to Rasa
        fetch('/api/send_message', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ message: message, context: conversationContext })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`Server responded with ${response.status}: ${response.statusText}`);
            }
            return response.json();
        })
        .then(data => {
            const responseTimestamp = new Date();
            hideTypingIndicator();
            
            // Process response
            handleRasaResponse(data, responseTimestamp);
        })
        .catch(error => {
            console.error('Error communicating with Rasa:', error);
            hideTypingIndicator();
            addMessageToChat('bot', 'Sorry, I encountered an error processing that request.', new Date());
        });
    }

    // Helper function to send to Rasa without adding user message (already shown)
    function sendToRasaWithoutUserMessage(message) {
        // Mark conversation started if triggered via helper button
        markConversationStarted();
        
        // Show typing indicator
        showTypingIndicator();
        
        // Send to Rasa
        fetch('/api/send_message', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ message: message, context: conversationContext })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`Server responded with ${response.status}: ${response.statusText}`);
            }
            return response.json();
        })
        .then(data => {
            const responseTimestamp = new Date();
            hideTypingIndicator();
            
            // Check if data is valid - if empty or invalid, don't show error since confirmation is already shown
            if (!data || (!data.messages && !data.actions && !data.error)) {
                console.log('Empty or minimal response from Rasa (this is OK for date confirmations):', data);
                // Don't show error - the confirmation message is already displayed
                return;
            }
            
            // Process response
            handleRasaResponse(data, responseTimestamp);
        })
        .catch(error => {
            console.error('Error communicating with Rasa (without user message):', error);
            hideTypingIndicator();
            // Don't show error message - the confirmation message is already displayed
            // Just log the error for debugging
        });
    }

    function markConversationStarted() {
        if (hasConversationStarted) return;
        hasConversationStarted = true;
        setHumanButtonVisibility(true);
    }

    function resetConversationState() {
        hasConversationStarted = false;
        setHumanButtonVisibility(false);
    }

    function setHumanButtonVisibility(visible) {
        if (!humanSupportButton) return;
        humanSupportButton.style.display = visible ? 'block' : 'none';
    }

    window.sendToRasa = sendToRasa;
});


// Make the function available globally
window.speakText = speakText;