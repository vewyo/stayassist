(function () {
    // Initialize Dexie
    const db = new Dexie('chatbot');

    // Define database schema
    db.version(1).stores({
        conversations: '++id, timestamp, sender, message, context',
    });

    /**
     * Save a conversation to the database
     * @param {Object} conversationData - Conversation data to save
     * @returns {Promise} - Promise that resolves with the new conversation ID
     */
    async function saveConversation(conversationData) {
        try {
            const id = await db.conversations.add({
                ...conversationData,
                timestamp: new Date().toISOString()
            });
            console.log(`Conversation saved with ID: ${id}`);
            return id;
        } catch (error) {
            console.error('Error saving conversation:', error);
            throw error;
        }
    }

    /**
     * Get all conversations
     * @returns {Promise} - Promise that resolves with an array of conversations
     */
    async function getConversations() {
        try {
            return await db.conversations.toArray();
        } catch (error) {
            console.error('Error fetching conversations:', error);
            throw error;
        }
    }

    // Export functions to global scope to ensure they're accessible
    window.DB = {
        saveConversation,
        getConversations,
        db
    };

    // Log that initialization is complete
    console.log('DB initialized successfully');
})();
