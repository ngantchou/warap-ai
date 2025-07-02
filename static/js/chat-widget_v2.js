/**
 * Djobea AI Chat Widget V2 - WhatsApp-style Chat with Real API Integration
 * Provides seamless chat experience connected to the conversation manager
 */

(function() {
    'use strict';

    // ===== CONFIGURATION =====
    const CONFIG = {
        apiEndpoint: '/webhook/chat',
        sessionStorageKey: 'djobeai_chat_session',
        maxRetries: 3,
        retryDelay: 1000,
        typingDelay: 1000,
        messageDelay: 500,
        maxMessageLength: 1000,
        sessionTimeout: 30 * 60 * 1000, // 30 minutes
        autoScrollDelay: 100
    };

    // ===== STATE MANAGEMENT =====
    const state = {
        isOpen: false,
        isTyping: false,
        sessionId: null,
        phoneNumber: null,
        messageHistory: [],
        currentRequestId: null,
        retryCount: 0,
        lastActivity: Date.now(),
        conversationStarted: false,
        phoneCollected: false
    };

    // ===== DOM ELEMENTS =====
    const elements = {
        widget: document.getElementById('chat-widget'),
        toggle: document.getElementById('chat-toggle'),
        window: document.getElementById('chat-window'),
        messages: document.getElementById('chat-messages'),
        input: document.getElementById('message-input'),
        sendBtn: document.querySelector('.send-btn'),
        notificationBadge: document.getElementById('notification-badge'),
        quickReplies: document.querySelector('.quick-replies')
    };

    // ===== UTILITIES =====
    const utils = {
        // Generate unique session ID
        generateSessionId() {
            return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        },

        // Get or create session ID
        getSessionId() {
            if (!state.sessionId) {
                state.sessionId = localStorage.getItem(CONFIG.sessionStorageKey) || this.generateSessionId();
                localStorage.setItem(CONFIG.sessionStorageKey, state.sessionId);
            }
            return state.sessionId;
        },

        // Format timestamp
        formatTime(date = new Date()) {
            return date.toLocaleTimeString('fr-FR', { 
                hour: '2-digit', 
                minute: '2-digit' 
            });
        },

        // Sanitize HTML to prevent XSS while allowing safe formatting
        sanitizeHtml(text) {
            // Allow safe HTML tags for message formatting
            const allowedTags = ['br', 'strong', 'b', 'em', 'i', 'u', 'p', 'div', 'span'];
            
            // First convert newlines to <br> tags
            text = text.replace(/\n/g, '<br>');
            
            // Create a temporary div to parse HTML
            const div = document.createElement('div');
            div.innerHTML = text;
            
            // Remove any potentially dangerous tags and attributes
            const allElements = div.querySelectorAll('*');
            allElements.forEach(element => {
                if (!allowedTags.includes(element.tagName.toLowerCase())) {
                    // Replace dangerous tags with their text content
                    element.outerHTML = element.textContent || element.innerText || '';
                } else {
                    // Remove all attributes except safe ones
                    const attributes = Array.from(element.attributes);
                    attributes.forEach(attr => {
                        if (!['class', 'style'].includes(attr.name.toLowerCase())) {
                            element.removeAttribute(attr.name);
                        }
                    });
                }
            });
            
            return div.innerHTML;
        },

        // Auto-resize textarea
        autoResize(element) {
            element.style.height = 'auto';
            element.style.height = (element.scrollHeight) + 'px';
        },

        // Scroll to bottom
        scrollToBottom() {
            setTimeout(() => {
                elements.messages.scrollTop = elements.messages.scrollHeight;
            }, CONFIG.autoScrollDelay);
        },

        // Check if session is expired
        isSessionExpired() {
            return Date.now() - state.lastActivity > CONFIG.sessionTimeout;
        },

        // Update last activity
        updateActivity() {
            state.lastActivity = Date.now();
        },

        // Play notification sound (optional)
        playNotificationSound() {
            try {
                const audio = new Audio('/static/sounds/notification.mp3');
                audio.volume = 0.3;
                audio.play().catch(() => {}); // Ignore errors
            } catch (e) {
                // Ignore audio errors
            }
        },

        // Vibrate on mobile (if supported)
        vibrate() {
            if ('vibrate' in navigator) {
                navigator.vibrate([100, 50, 100]);
            }
        }
    };

    // ===== MESSAGE HANDLING =====
    const messageHandler = {
        // Create message element
        createMessageElement(content, isUser = false, time = null, buttons = []) {
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${isUser ? 'message--sent' : 'message--received'}`;
            
            const contentDiv = document.createElement('div');
            contentDiv.className = 'message__content';
            contentDiv.innerHTML = utils.sanitizeHtml(content);
            
            // Add buttons if provided
            if (buttons && buttons.length > 0 && !isUser) {
                const buttonsDiv = document.createElement('div');
                buttonsDiv.className = 'message-buttons';
                buttonsDiv.style.cssText = 'margin-top: 10px; display: flex; flex-wrap: wrap; gap: 5px;';
                
                buttons.forEach(button => {
                    const buttonElement = document.createElement('button');
                    buttonElement.textContent = button.text;
                    buttonElement.className = this.getButtonClass(button.style || 'primary');
                    buttonElement.style.cssText = 'padding: 8px 15px; border: none; border-radius: 15px; cursor: pointer; font-size: 13px; flex-shrink: 0;';
                    
                    buttonElement.onclick = () => {
                        this.handleButtonClick(button.value, button.action || 'select', buttonElement);
                    };
                    
                    buttonsDiv.appendChild(buttonElement);
                });
                
                contentDiv.appendChild(buttonsDiv);
            }
            
            const timeDiv = document.createElement('div');
            timeDiv.className = 'message__time';
            timeDiv.textContent = time || utils.formatTime();
            
            messageDiv.appendChild(contentDiv);
            messageDiv.appendChild(timeDiv);
            
            return messageDiv;
        },

        // Get button CSS class based on style
        getButtonClass(style) {
            switch(style) {
                case 'primary': return 'btn-primary';
                case 'secondary': return 'btn-secondary';
                case 'success': return 'btn-success';
                case 'danger': return 'btn-danger';
                default: return 'btn-primary';
            }
        },

        // Handle button click
        handleButtonClick(value, action, buttonElement) {
            // Disable all buttons in the same message to prevent double-clicking
            const messageButtons = buttonElement.parentElement.querySelectorAll('button');
            messageButtons.forEach(btn => {
                btn.disabled = true;
                btn.style.opacity = '0.6';
            });
            
            // Highlight selected button
            buttonElement.style.backgroundColor = '#25D366';
            buttonElement.style.color = 'white';
            
            // Send button value as message
            this.sendButtonMessage(value, action);
        },

        // Send button selection as message
        sendButtonMessage(value, action) {
            // Add user message showing their selection
            const buttonText = value.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());
            this.addMessage(buttonText, true, false);
            
            // Send to backend with button_value parameter
            chatApi.sendMessage('', value);
        },

        // Add message to chat
        addMessage(content, isUser = false, animate = true, buttons = []) {
            const messageElement = this.createMessageElement(content, isUser, null, buttons);
            
            if (animate) {
                messageElement.style.opacity = '0';
                messageElement.style.transform = 'translateY(20px)';
            }
            
            elements.messages.appendChild(messageElement);
            
            if (animate) {
                requestAnimationFrame(() => {
                    messageElement.style.transition = 'all 0.3s ease';
                    messageElement.style.opacity = '1';
                    messageElement.style.transform = 'translateY(0)';
                });
            }
            
            // Store in history
            state.messageHistory.push({
                content,
                isUser,
                timestamp: Date.now()
            });
            
            utils.scrollToBottom();
            return messageElement;
        },

        // Show typing indicator
        showTyping() {
            if (state.isTyping) return;
            
            state.isTyping = true;
            const typingDiv = document.createElement('div');
            typingDiv.className = 'typing-indicator';
            typingDiv.id = 'typing-indicator';
            
            for (let i = 0; i < 3; i++) {
                const dot = document.createElement('div');
                dot.className = 'dot';
                typingDiv.appendChild(dot);
            }
            
            elements.messages.appendChild(typingDiv);
            utils.scrollToBottom();
        },

        // Hide typing indicator
        hideTyping() {
            if (!state.isTyping) return;
            
            state.isTyping = false;
            const typingIndicator = document.getElementById('typing-indicator');
            if (typingIndicator) {
                typingIndicator.remove();
            }
        },

        // Clear messages
        clearMessages() {
            state.messageHistory = [];
            state.conversationStarted = false;
            
            // Check if we already have a phone number from localStorage
            if (state.phoneCollected) {
                this.showChatInterface();
            } else {
                state.phoneCollected = false;
                this.showPhoneNumberInput();
            }
        },
        
        // Show phone number input interface
        showPhoneNumberInput() {
            console.log('DEBUG: showPhoneNumberInput() called');
            console.log('DEBUG: elements.messages exists:', !!elements.messages);
            elements.messages.innerHTML = `
                <div class="message message--received">
                    <div class="message__content">
                        Bonjour! 👋 Bienvenue sur Djobea AI.<br><br>
                        Pour mieux vous aider, veuillez entrer votre numéro de téléphone:
                        <div class="phone-input-container" style="margin-top: 15px;">
                            <input type="tel" 
                                   id="phone-input" 
                                   placeholder="Ex: 693123456 ou 237693123456"
                                   style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 20px; outline: none; font-size: 14px;"
                                   maxlength="15">
                            <button onclick="submitPhoneNumber()" 
                                    style="margin-top: 10px; width: 100%; padding: 10px; background: #25D366; color: white; border: none; border-radius: 20px; cursor: pointer;">
                                Continuer
                            </button>
                            <button onclick="clearPhoneNumber()" 
                                    style="margin-top: 5px; width: 100%; padding: 5px; background: #dc3545; color: white; border: none; border-radius: 15px; cursor: pointer; font-size: 12px;">
                                🧹 Clear & Reset (for testing)
                            </button>
                        </div>
                    </div>
                    <div class="message__time">Maintenant</div>
                </div>
            `;
            
            // Focus on input and add enter key handler
            setTimeout(() => {
                const phoneInput = document.getElementById('phone-input');
                if (phoneInput) {
                    phoneInput.focus();
                    phoneInput.addEventListener('keypress', (e) => {
                        if (e.key === 'Enter') {
                            window.submitPhoneNumber();
                        }
                    });
                    
                    // Auto-format phone number as user types
                    phoneInput.addEventListener('input', (e) => {
                        let value = e.target.value.replace(/\D/g, ''); // Remove non-digits
                        if (value.length > 0 && !value.startsWith('237')) {
                            if (value.length <= 9) {
                                value = '237' + value;
                            }
                        }
                        e.target.value = value;
                    });
                }
            }, 100);
        },
        
        // Show chat interface after phone number is collected
        showChatInterface() {
            elements.messages.innerHTML = `
                <div class="message message--received">
                    <div class="message__content">
                        Merci ! Je suis maintenant connecté à votre compte WhatsApp.<br>
                        Comment puis-je vous aider aujourd'hui?
                    </div>
                    <div class="message__time">Maintenant</div>
                </div>
                
                <div class="quick-replies">
                    <button class="quick-reply" onclick="sendQuickReply('J\\\'ai un problème de plomberie')">
                        🔧 Plomberie
                    </button>
                    <button class="quick-reply" onclick="sendQuickReply('J\\\'ai un problème électrique')">
                        ⚡ Électricité
                    </button>
                    <button class="quick-reply" onclick="sendQuickReply('Mon électroménager ne marche pas')">
                        🔨 Électroménager
                    </button>
                </div>
            `;
            
            state.phoneCollected = true;
            state.conversationStarted = true;
        },

        // Process message with line breaks
        processMessage(text) {
            return text.replace(/\n/g, '<br>');
        }
    };

    // ===== API COMMUNICATION =====
    const api = {
        // Send message to backend
        async sendMessage(message, buttonValue = null) {
            const payload = {
                message: message.trim(),
                session_id: utils.getSessionId(),
                phone_number: state.phoneNumber,
                source: 'web_chat',
                timestamp: new Date().toISOString(),
                conversation_history: state.messageHistory.slice(-10), // Last 10 messages for context
                button_value: buttonValue // Add button value for step management
            };

            try {
                const response = await fetch(CONFIG.apiEndpoint, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Accept': 'application/json'
                    },
                    body: JSON.stringify(payload)
                });

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }

                const data = await response.json();
                return this.processApiResponse(data);
            } catch (error) {
                console.error('API Error:', error);
                throw error;
            }
        },

        // Process API response
        processApiResponse(data) {
            const response = {
                message: data.response || data.message || '',
                sessionId: data.session_id || data.user_id,
                requestComplete: data.request_complete || false,
                requestId: data.request_id || null,
                suggestions: data.suggestions || [],
                needsInfo: data.needs_info || [],
                status: data.status || 'active',
                buttons: data.buttons || [],
                systemAction: data.system_action || null,
                nextStep: data.next_step || null
            };

            // Update session if provided
            if (response.sessionId) {
                state.sessionId = response.sessionId;
                localStorage.setItem(CONFIG.sessionStorageKey, response.sessionId);
            }

            // Update current request ID
            if (response.requestId) {
                state.currentRequestId = response.requestId;
            }

            return response;
        },

        // Handle API errors with retry logic
        async sendWithRetry(message) {
            for (let attempt = 0; attempt < CONFIG.maxRetries; attempt++) {
                try {
                    state.retryCount = attempt;
                    const response = await this.sendMessage(message);
                    state.retryCount = 0;
                    return response;
                } catch (error) {
                    console.log(`Attempt ${attempt + 1} failed:`, error.message);
                    
                    if (attempt === CONFIG.maxRetries - 1) {
                        throw error;
                    }
                    
                    // Wait before retry
                    await new Promise(resolve => 
                        setTimeout(resolve, CONFIG.retryDelay * (attempt + 1))
                    );
                }
            }
        }
    };

    // ===== CHAT FUNCTIONALITY =====
    const chat = {
        // Send user message
        async sendUserMessage(message) {
            if (!message.trim()) return;
            
            // Check if phone number is collected first
            if (!state.phoneCollected || !state.phoneNumber) {
                console.log('DEBUG: Phone not collected, showing phone input instead of sending message');
                console.log('DEBUG: phoneCollected:', state.phoneCollected, 'phoneNumber:', state.phoneNumber);
                messageHandler.showPhoneNumberInput();
                return;
            }
            
            // Validate message length
            if (message.length > CONFIG.maxMessageLength) {
                this.showError('Message trop long. Veuillez raccourcir votre message.');
                return;
            }

            utils.updateActivity();
            
            // Add user message to chat
            messageHandler.addMessage(message, true);
            
            // Clear input
            elements.input.value = '';
            utils.autoResize(elements.input);
            
            // Show typing indicator
            messageHandler.showTyping();
            
            // Hide quick replies after first message
            if (!state.conversationStarted) {
                const quickReplies = elements.messages.querySelector('.quick-replies');
                if (quickReplies) {
                    quickReplies.style.display = 'none';
                }
                state.conversationStarted = true;
            }

            try {
                // Send to API
                const response = await api.sendWithRetry(message);
                
                // Add small delay to make it feel more natural
                await new Promise(resolve => setTimeout(resolve, CONFIG.typingDelay));
                
                messageHandler.hideTyping();
                
                if (response.message) {
                    const processedMessage = messageHandler.processMessage(response.message);
                    messageHandler.addMessage(processedMessage, false, true, response.buttons || []);
                    
                    // Play notification sound if window is not visible
                    if (document.hidden) {
                        utils.playNotificationSound();
                        utils.vibrate();
                    }
                }
                
                // Handle suggestions or additional actions
                this.handleResponseActions(response);
                
            } catch (error) {
                messageHandler.hideTyping();
                this.handleError(error);
            }
        },

        // Handle response actions (suggestions, quick replies, etc.)
        handleResponseActions(response) {
            // Show suggestions as quick replies
            if (response.suggestions && response.suggestions.length > 0) {
                this.showSuggestions(response.suggestions);
            }
            
            // Handle request completion
            if (response.requestComplete) {
                this.handleRequestComplete(response);
            }
            
            // Update notification badge if chat is closed
            if (!state.isOpen) {
                this.showNotification();
            }
        },

        // Show suggestions as quick reply buttons
        showSuggestions(suggestions) {
            const suggestionsDiv = document.createElement('div');
            suggestionsDiv.className = 'quick-replies';
            
            suggestions.slice(0, 3).forEach(suggestion => {
                const button = document.createElement('button');
                button.className = 'quick-reply';
                button.textContent = suggestion;
                button.onclick = () => {
                    sendQuickReply(suggestion);
                    suggestionsDiv.remove();
                };
                suggestionsDiv.appendChild(button);
            });
            
            elements.messages.appendChild(suggestionsDiv);
            utils.scrollToBottom();
        },

        // Handle request completion
        handleRequestComplete(response) {
            console.log('Request completed:', response.requestId);
            
            // Could add special UI for completed requests
            const completionDiv = document.createElement('div');
            completionDiv.className = 'request-completion';
            completionDiv.innerHTML = `
                <div class="completion-message">
                    ✅ Votre demande a été traitée avec succès!
                    ${response.requestId ? `<br><small>Référence: #${response.requestId}</small>` : ''}
                </div>
            `;
            
            elements.messages.appendChild(completionDiv);
            utils.scrollToBottom();
        },

        // Handle errors
        handleError(error) {
            console.error('Chat error:', error);
            
            let errorMessage = 'Désolé, une erreur est survenue. ';
            
            if (error.message.includes('network') || error.message.includes('fetch')) {
                errorMessage += 'Vérifiez votre connexion internet.';
            } else if (error.message.includes('500')) {
                errorMessage += 'Nos serveurs rencontrent un problème temporaire.';
            } else {
                errorMessage += 'Veuillez réessayer dans quelques instants.';
            }
            
            // Add WhatsApp fallback
            errorMessage += '<br><br>En attendant, vous pouvez nous contacter directement sur WhatsApp.';
            
            const errorDiv = document.createElement('div');
            errorDiv.className = 'error-message';
            errorDiv.innerHTML = `
                <div class="message message--received error">
                    <div class="message__content">
                        ${errorMessage}
                        <br><br>
                        <button class="btn btn--whatsapp btn--small" onclick="openWhatsApp('${error.lastMessage || 'Bonjour, j\'ai besoin d\'aide'}')">
                            <i class="fab fa-whatsapp"></i> Continuer sur WhatsApp
                        </button>
                    </div>
                    <div class="message__time">${utils.formatTime()}</div>
                </div>
            `;
            
            elements.messages.appendChild(errorDiv);
            utils.scrollToBottom();
        },

        // Show simple error
        showError(message) {
            const errorDiv = document.createElement('div');
            errorDiv.className = 'error-message';
            errorDiv.innerHTML = `
                <div class="message message--received error">
                    <div class="message__content">${message}</div>
                    <div class="message__time">${utils.formatTime()}</div>
                </div>
            `;
            
            elements.messages.appendChild(errorDiv);
            utils.scrollToBottom();
            
            // Remove error after 5 seconds
            setTimeout(() => {
                if (errorDiv.parentNode) {
                    errorDiv.remove();
                }
            }, 5000);
        },

        // Show notification badge
        showNotification() {
            if (elements.notificationBadge) {
                elements.notificationBadge.style.display = 'flex';
                elements.notificationBadge.textContent = '1';
            }
        },

        // Hide notification badge
        hideNotification() {
            if (elements.notificationBadge) {
                elements.notificationBadge.style.display = 'none';
            }
        }
    };

    // ===== WIDGET CONTROLS =====
    const controls = {
        // Toggle chat widget
        toggle() {
            console.log('Toggle clicked - current state:', state.isOpen);
            state.isOpen = !state.isOpen;
            
            if (state.isOpen) {
                console.log('Opening chat widget');
                this.open();
            } else {
                console.log('Closing chat widget');
                this.close();
            }
        },

        // Open chat widget
        open() {
            console.log('DEBUG: Opening chat widget...');
            state.isOpen = true;
            elements.window.classList.add('active');
            chat.hideNotification();
            utils.updateActivity();
            
            // Check if we need to collect phone number first
            console.log('DEBUG: Open widget - phoneCollected:', state.phoneCollected, 'phoneNumber:', state.phoneNumber);
            if (!state.phoneCollected || !state.phoneNumber) {
                console.log('DEBUG: Phone not collected, calling messageHandler.showPhoneNumberInput()');
                setTimeout(() => {
                    messageHandler.showPhoneNumberInput();
                    console.log('DEBUG: Phone input should now be displayed');
                }, 100);
            } else {
                console.log('DEBUG: Phone already collected, focusing on input');
                elements.input.focus();
            }
            
            // Analytics
            if (typeof analytics !== 'undefined') {
                analytics.track('chat_widget_opened');
            }
            
            // Check if session expired
            if (utils.isSessionExpired()) {
                this.resetSession();
            }
        },

        // Close chat widget
        close() {
            state.isOpen = false;
            elements.window.classList.remove('active');
            
            // Analytics
            if (typeof analytics !== 'undefined') {
                analytics.track('chat_widget_closed', {
                    message_count: state.messageHistory.length,
                    session_duration: Date.now() - state.lastActivity
                });
            }
        },

        // Reset session
        resetSession() {
            state.sessionId = utils.generateSessionId();
            localStorage.setItem(CONFIG.sessionStorageKey, state.sessionId);
            messageHandler.clearMessages();
            
            messageHandler.addMessage(
                'Votre session a expiré. Je suis prêt à vous aider avec une nouvelle conversation! 😊',
                false
            );
        }
    };

    // ===== EVENT HANDLERS =====
    const events = {
        // Initialize event listeners
        init() {
            // Toggle button
            if (elements.toggle) {
                console.log('Adding click event to toggle button');
                elements.toggle.addEventListener('click', controls.toggle.bind(controls));
                
                // Also add debugging event to test
                elements.toggle.addEventListener('click', function() {
                    console.log('Raw click event detected on toggle');
                });
            } else {
                console.log('Toggle element not found!');
            }

            // Send button
            if (elements.sendBtn) {
                elements.sendBtn.addEventListener('click', this.handleSend);
            }

            // Input field
            if (elements.input) {
                elements.input.addEventListener('keypress', this.handleKeyPress);
                elements.input.addEventListener('input', this.handleInput);
                elements.input.addEventListener('focus', utils.updateActivity);
            }

            // Close on outside click
            document.addEventListener('click', this.handleOutsideClick);

            // Handle page visibility change
            document.addEventListener('visibilitychange', this.handleVisibilityChange);

            // Handle page unload
            window.addEventListener('beforeunload', this.handlePageUnload);

            // Session timeout check
            setInterval(this.checkSessionTimeout, 60000); // Check every minute
        },

        // Handle send button click
        handleSend(e) {
            e.preventDefault();
            const message = elements.input.value.trim();
            if (message) {
                chat.sendUserMessage(message);
            }
        },

        // Handle input key press
        handleKeyPress(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                events.handleSend(e);
            }
        },

        // Handle input changes
        handleInput(e) {
            utils.autoResize(e.target);
            utils.updateActivity();
        },

        // Handle outside click
        handleOutsideClick(e) {
            if (state.isOpen && 
                elements.widget && 
                !elements.widget.contains(e.target)) {
                // Optional: don't auto-close on outside click
                // controls.close();
            }
        },

        // Handle page visibility change
        handleVisibilityChange() {
            if (!document.hidden && state.isOpen) {
                chat.hideNotification();
            }
        },

        // Handle page unload
        handlePageUnload() {
            // Save state if needed
            if (typeof analytics !== 'undefined') {
                analytics.track('page_unload', {
                    chat_open: state.isOpen,
                    message_count: state.messageHistory.length
                });
            }
        },

        // Check session timeout
        checkSessionTimeout() {
            if (utils.isSessionExpired() && state.isOpen) {
                controls.resetSession();
            }
        }
    };

    // ===== GLOBAL FUNCTIONS =====
    window.toggleChatWidget = function() {
        controls.toggle();
    };

    window.sendQuickReply = function(message) {
        if (!state.isOpen) {
            controls.open();
        }
        setTimeout(() => {
            chat.sendUserMessage(message);
        }, 200);
    };

    window.startServiceChat = function(serviceType) {
        const messages = {
            'plomberie': 'J\'ai un problème de plomberie. Pouvez-vous m\'aider?',
            'électricité': 'J\'ai un problème électrique. Pouvez-vous m\'aider?',
            'électroménager': 'Mon électroménager ne fonctionne pas. Pouvez-vous m\'aider?'
        };
        
        const message = messages[serviceType] || messages['plomberie'];
        
        if (!state.isOpen) {
            controls.open();
        }
        
        setTimeout(() => {
            chat.sendUserMessage(message);
        }, 500);
    };

    // Phone number submission function
    window.submitPhoneNumber = function() {
        const phoneInput = document.getElementById('phone-input');
        if (!phoneInput) return;
        
        const phoneNumber = phoneInput.value.trim();
        
        // Validate phone number
        if (!phoneNumber) {
            alert('Veuillez entrer votre numéro de téléphone.');
            return;
        }
        
        // Basic Cameroon phone number validation
        const cleanPhone = phoneNumber.replace(/\D/g, '');
        if (cleanPhone.length < 9 || cleanPhone.length > 15) {
            alert('Numéro de téléphone invalide. Format: 693123456 ou 237693123456');
            return;
        }
        
        // Store phone number in state
        state.phoneNumber = cleanPhone.startsWith('237') ? cleanPhone : '237' + cleanPhone;
        state.phoneCollected = true;
        
        // Show confirmation message and proceed to chat
        messageHandler.addMessage(`Numéro enregistré: ${state.phoneNumber}`, true);
        messageHandler.showChatInterface();
        
        // Save to localStorage for session persistence
        localStorage.setItem('djobea_phone_number', state.phoneNumber);
        
        console.log('Phone number collected:', state.phoneNumber);
    };

    // Function to clear phone number and restart
    window.clearPhoneNumber = function() {
        localStorage.removeItem('djobea_phone_number');
        state.phoneNumber = null;
        state.phoneCollected = false;
        messageHandler.clearMessages();
        console.log('Phone number cleared, showing input again');
    };

    // ===== INITIALIZATION =====
    function init() {
        // Wait for DOM to be ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', init);
            return;
        }

        try {
            // Check if elements exist
            if (!elements.widget) {
                console.log('Chat widget elements not found');
                return;
            }

            // Debug: Log element existence
            console.log('Toggle element found:', !!elements.toggle);
            console.log('Widget element found:', !!elements.widget);
            console.log('Window element found:', !!elements.window);

            // Initialize components
            events.init();
            
            // Initialize session
            utils.getSessionId();
            
            // Check for existing phone number
            const savedPhone = localStorage.getItem('djobea_phone_number');
            console.log('DEBUG: Checking for saved phone number:', savedPhone);
            if (savedPhone) {
                state.phoneNumber = savedPhone;
                state.phoneCollected = true;
                console.log('Restored phone number from storage:', savedPhone);
            } else {
                // Clear phone collected status for new sessions
                state.phoneCollected = false;
                state.phoneNumber = null;
                console.log('No phone number found, will prompt user on next open');
            }
            console.log('DEBUG: Final state after init - phoneCollected:', state.phoneCollected, 'phoneNumber:', state.phoneNumber);
            
            // Show initial notification
            setTimeout(() => {
                if (!state.isOpen) {
                    chat.showNotification();
                }
            }, 5000); // Show after 5 seconds

            console.log('Chat widget initialized successfully');
            
            // Analytics
            if (typeof analytics !== 'undefined') {
                analytics.track('chat_widget_initialized', {
                    session_id: state.sessionId
                });
            }
        } catch (error) {
            console.error('Error initializing chat widget:', error);
        }
    }

    // Start initialization
    init();

    // ===== CSS INJECTION FOR ERROR STYLES =====
    const style = document.createElement('style');
    style.textContent = `
        .error-message .message.error .message__content {
            background: #FEF2F2 !important;
            border-left: 4px solid #EF4444;
            color: #DC2626;
        }
        
        .request-completion {
            text-align: center;
            margin: 1rem 0;
        }
        
        .completion-message {
            background: #F0FDF4;
            border: 1px solid #22C55E;
            border-radius: 0.5rem;
            padding: 1rem;
            color: #166534;
            font-weight: 500;
        }
        
        .btn--small {
            padding: 0.5rem 1rem;
            font-size: 0.75rem;
        }
        
        .typing-indicator {
            display: flex;
            gap: 0.25rem;
            padding: 1rem;
            background: white;
            border-radius: 1rem;
            width: 60px;
            margin-bottom: 1rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        
        .typing-indicator .dot {
            width: 8px;
            height: 8px;
            background: #9CA3AF;
            border-radius: 50%;
            animation: typing 1.4s infinite ease-in-out;
        }
        
        .typing-indicator .dot:nth-child(2) {
            animation-delay: 0.2s;
        }
        
        .typing-indicator .dot:nth-child(3) {
            animation-delay: 0.4s;
        }
        
        @keyframes typing {
            0%, 60%, 100% {
                transform: translateY(0);
            }
            30% {
                transform: translateY(-10px);
            }
        }
    `;
    document.head.appendChild(style);

})();