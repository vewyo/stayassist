class RasaAPI {
    constructor() {
        this.baseUrl = '/api/send_message';
        this.maxRetries = 2;
        this.retryDelay = 1000; // 1 second
        this.defaultTimeout = 15000; // 15 seconds (increased from 10)
        
        // Keep track of pending requests to avoid duplicates
        this.pendingRequests = new Map();
        
        // Add connection status tracking
        this.isConnected = true;
        this.lastCheckTime = Date.now();
        this.connectionCheckInterval = setInterval(() => this.checkAvailability(), 30000);
        
        // Initialize by checking connection
        this.checkAvailability();
    }

    /**
     * Send a message to Rasa with improved error handling and retry logic
     * @param {string} message - The message to send
     * @param {Object} context - The context to send
     * @param {Object} options - Additional options
     * @returns {Promise<Object>} - The Rasa response
     */
    async sendMessage(message, context = {}, options = {}) {
        // If we know the server is down, fail fast
        if (!this.isConnected && Date.now() - this.lastCheckTime < 5000) {
            console.warn('Rasa server appears to be down, skipping request');
            return this.createErrorResponse(
                "Server connection issue", 
                "I'm sorry, I'm having trouble connecting to my backend service. Please try again in a few moments.",
                context
            );
        }
        
        // Generate a request ID based on message and context to avoid duplicates
        const requestId = this.generateRequestId(message, context);
        
        // If an identical request is already pending, wait for that one
        if (this.pendingRequests.has(requestId)) {
            console.log('Duplicate request detected, waiting for existing request to complete');
            return await this.pendingRequests.get(requestId);
        }
        
        // Create a promise for this request
        const requestPromise = this._executeRequest(message, context, options);
        
        // Store the promise
        this.pendingRequests.set(requestId, requestPromise);
        
        // Clean up after completion
        requestPromise.finally(() => {
            this.pendingRequests.delete(requestId);
        });
        
        return requestPromise;
    }
    
    /**
     * Execute the actual request to the Rasa server
     * @private
     */
    async _executeRequest(message, context = {}, options = {}) {
        const timeout = this.defaultTimeout;
        
        let retries = 0;
        let lastError = null;

        while (retries <= this.maxRetries) {
            try {
                // Create AbortController for timeout
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), timeout);

                console.log(`Sending request to Rasa: ${message.substring(0, 30)}${message.length > 30 ? '...' : ''}`);
                const startTime = Date.now();
                
                const response = await fetch(this.baseUrl, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ 
                        message: message, 
                        context: context 
                    }),
                    signal: controller.signal
                });

                // Clear timeout
                clearTimeout(timeoutId);
                
                // Log request time for performance monitoring
                const requestTime = Date.now() - startTime;
                console.log(`Rasa request completed in ${requestTime}ms`);
                
                // Server is connected if we got here
                this.isConnected = true;
                this.lastCheckTime = Date.now();

                if (!response.ok) {
                    throw new Error(`Server responded with ${response.status}: ${response.statusText}`);
                }

                return await response.json();
            } catch (error) {
                lastError = error;
                
                // Mark server as disconnected if we couldn't reach it
                if (error.name === 'AbortError' || error.message.includes('NetworkError')) {
                    this.isConnected = false;
                    this.lastCheckTime = Date.now();
                }
                
                // Don't retry if it's not a timeout or network error
                if (error.name !== 'AbortError' && !error.message.includes('NetworkError')) {
                    break;
                }
                
                console.warn(`Attempt ${retries + 1} failed: ${error.message}. Retrying...`);
                retries++;
                
                // Only wait if we're going to retry
                if (retries <= this.maxRetries) {
                    await new Promise(resolve => setTimeout(resolve, this.retryDelay));
                }
            }
        }

        console.error('All retries failed:', lastError);
        
        // Return a graceful error response
        return this.createErrorResponse(
            lastError.message,
            "I'm sorry, I encountered a problem communicating with my backend. Please try again later.",
            context
        );
    }
    
    /**
     * Create a standardized error response
     * @private
     */
    createErrorResponse(errorMessage, userMessage, context) {
        return {
            error: errorMessage,
            messages: [{
                text: userMessage
            }],
            context: context
        };
    }
    
    /**
     * Generate a request ID to detect duplicate requests
     * @private
     */
    generateRequestId(message, context) {
        // Simple implementation - in a real app you might want to use a hash function
        return `${message.substring(0, 50)}_${Date.now()}`;
    }

    /**
     * Check if the Rasa server is available
     * @returns {Promise<boolean>} - True if available
     */
    async checkAvailability() {
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 3000); // 3 second timeout
            
            const response = await fetch('/api/check_rasa', {
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);
            
            const wasConnected = this.isConnected;
            this.isConnected = response.ok;
            this.lastCheckTime = Date.now();
            
            // If connection state changed, log it
            if (wasConnected !== this.isConnected) {
                if (this.isConnected) {
                    console.log('Rasa server connection restored');
                } else {
                    console.warn('Rasa server connection lost');
                }
            }
            
            if (!response.ok) {
                return false;
            }
            
            const data = await response.json();
            return data.status === 'available';
        } catch (error) {
            this.isConnected = false;
            this.lastCheckTime = Date.now();
            console.error('Error checking Rasa availability:', error);
            return false;
        }
    }
    
    /**
     * Clean up resources when the API is no longer needed
     */
    destroy() {
        if (this.connectionCheckInterval) {
            clearInterval(this.connectionCheckInterval);
        }
    }
}

// Create a singleton instance
window.rasaAPI = new RasaAPI();
console.log('Rasa API helper initialized');

// Clean up when window unloads
window.addEventListener('unload', () => {
    if (window.rasaAPI) {
        window.rasaAPI.destroy();
    }
});
