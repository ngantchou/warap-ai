// Djobea AI Landing Page JavaScript - Bootstrap Compatible

document.addEventListener('DOMContentLoaded', function() {
    // Chat widget functionality
    const widget = document.getElementById('whatsapp-widget');
    const chatToggle = document.getElementById('chat-toggle');
    const notificationBadge = document.getElementById('notification-badge');
    const userInput = document.getElementById('user-input');
    const chatMessages = document.getElementById('chat-messages');

    let isWidgetOpen = false;
    let conversationStarted = false;

    // Initialize chat widget
    function initWidget() {
        if (widget) {
            widget.style.display = 'block';
        }
        
        // Show initial notification
        if (notificationBadge) {
            notificationBadge.style.display = 'flex';
        }
        
        // Auto-show welcome message after 3 seconds
        setTimeout(() => {
            if (!conversationStarted && notificationBadge) {
                notificationBadge.innerHTML = '💬';
                notificationBadge.style.animation = 'pulse 2s infinite';
            }
        }, 3000);
    }

    // Toggle chat widget
    function toggleChat() {
        if (!widget) return;
        
        isWidgetOpen = !isWidgetOpen;
        
        if (isWidgetOpen) {
            widget.classList.add('active');
            if (notificationBadge) {
                notificationBadge.style.display = 'none';
            }
            if (userInput) {
                userInput.focus();
            }
        } else {
            widget.classList.remove('active');
        }
    }

    // Close chat widget
    function closeChat(event) {
        if (event) {
            event.stopPropagation();
        }
        if (widget) {
            widget.classList.remove('active');
            isWidgetOpen = false;
        }
    }

    // Add message to chat
    function addChatMessage(message, isUser = false) {
        if (!chatMessages) return;
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${isUser ? 'user-message' : 'bot-message'}`;
        
        const bubbleDiv = document.createElement('div');
        bubbleDiv.className = 'message-bubble';
        bubbleDiv.textContent = message;
        
        const timeDiv = document.createElement('small');
        timeDiv.className = 'message-time';
        timeDiv.textContent = new Date().toLocaleTimeString('fr-FR', { 
            hour: '2-digit', 
            minute: '2-digit' 
        });
        
        messageDiv.appendChild(bubbleDiv);
        messageDiv.appendChild(timeDiv);
        chatMessages.appendChild(messageDiv);
        
        // Scroll to bottom
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // Send message
    function sendMessage() {
        if (!userInput) return;
        
        const message = userInput.value.trim();
        if (!message) return;
        
        // Add user message
        addChatMessage(message, true);
        userInput.value = '';
        conversationStarted = true;
        
        // Simulate bot response
        setTimeout(() => {
            const responses = [
                'Je comprends votre demande. Laissez-moi vous aider à trouver le bon prestataire.',
                'Parfait ! Je recherche des professionnels disponibles dans votre zone.',
                'Merci pour ces informations. Je vais traiter votre demande immédiatement.',
                'Excellent ! Je vous connecte avec un spécialiste qualifié.',
                'Dans quel quartier de Douala êtes-vous situé ?',
                'Pouvez-vous me donner plus de détails sur le problème ?'
            ];
            const randomResponse = responses[Math.floor(Math.random() * responses.length)];
            addChatMessage(randomResponse);
        }, 1000 + Math.random() * 2000);
    }

    // Handle service selection
    function selectService(service) {
        const serviceMessages = {
            'plomberie': 'J\'ai besoin d\'un plombier pour une fuite d\'eau',
            'électricité': 'J\'ai un problème électrique chez moi',
            'électroménager': 'Mon électroménager est en panne'
        };
        
        if (userInput && serviceMessages[service]) {
            userInput.value = serviceMessages[service];
            sendMessage();
        }
    }

    // Handle key press
    function handleKeyPress(event) {
        if (event.key === 'Enter') {
            sendMessage();
        }
    }

    // Open WhatsApp chat
    function openWhatsAppChat() {
        const message = encodeURIComponent('Bonjour, j\'aimerais utiliser Djobea AI pour trouver un prestataire de services.');
        const whatsappURL = `https://wa.me/237000000000?text=${message}`;
        window.open(whatsappURL, '_blank');
    }

    // Open demo chat
    function openDemoChat() {
        toggleChat();
        if (!conversationStarted) {
            setTimeout(() => {
                addChatMessage('Bonjour ! 👋 Comment puis-je vous aider avec vos services à domicile ?');
            }, 500);
        }
    }

    // Smooth scrolling for navigation
    function initSmoothScrolling() {
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function (e) {
                e.preventDefault();
                const target = document.querySelector(this.getAttribute('href'));
                if (target) {
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            });
        });
    }

    // Header scroll effect
    function initHeaderEffect() {
        const navbar = document.querySelector('.navbar');
        if (!navbar) return;
        
        window.addEventListener('scroll', function() {
            if (window.scrollY > 50) {
                navbar.classList.add('scrolled');
                navbar.style.background = 'rgba(255, 255, 255, 0.98)';
                navbar.style.backdropFilter = 'blur(10px)';
            } else {
                navbar.classList.remove('scrolled');
                navbar.style.background = '';
                navbar.style.backdropFilter = '';
            }
        });
    }

    // Add CSS animation for notification badge
    function addNotificationAnimation() {
        const style = document.createElement('style');
        style.textContent = `
            @keyframes pulse {
                0% { transform: scale(1); }
                50% { transform: scale(1.1); }
                100% { transform: scale(1); }
            }
        `;
        document.head.appendChild(style);
    }

    // Event listeners
    if (chatToggle) {
        chatToggle.addEventListener('click', toggleChat);
    }

    if (userInput) {
        userInput.addEventListener('keypress', handleKeyPress);
    }

    // Global functions for HTML onclick handlers
    window.toggleChat = toggleChat;
    window.closeChat = closeChat;
    window.sendMessage = sendMessage;
    window.selectService = selectService;
    window.handleKeyPress = handleKeyPress;
    window.openWhatsAppChat = openWhatsAppChat;
    window.openDemoChat = openDemoChat;

    // Initialize everything
    initWidget();
    initSmoothScrolling();
    initHeaderEffect();
    addNotificationAnimation();

    console.log("Djobea AI Landing Page initialized successfully");
});