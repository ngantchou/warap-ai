/**
 * Djobea AI Landing Page V2 - Main JavaScript Functionality
 * Handles navigation, smooth scrolling, animations, and user interactions
 */

(function() {
    'use strict';

    // ===== CONFIGURATION =====
    const CONFIG = {
        whatsappNumber: '+237690000000',
        animationDuration: 300,
        scrollOffset: 80,
        mobileBreakpoint: 768,
        apiEndpoint: '/api/landing/data',
        statsEndpoint: '/api/landing/stats'
    };

    // ===== DOM ELEMENTS =====
    const elements = {
        header: document.getElementById('header'),
        navToggle: document.getElementById('nav-toggle'),
        navMenu: document.getElementById('nav-menu'),
        navClose: document.getElementById('nav-close'),
        navLinks: document.querySelectorAll('.nav__link'),
        heroStats: document.querySelectorAll('.stat__number'),
        serviceCards: document.querySelectorAll('.service-card'),
        features: document.querySelectorAll('.feature'),
        steps: document.querySelectorAll('.step')
    };

    // ===== DYNAMIC DATA =====
    const dynamicData = {
        async loadData() {
            try {
                console.log('Loading dynamic data from API...');
                const response = await fetch(CONFIG.apiEndpoint);
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                const data = await response.json();
                console.log('Dynamic data loaded:', data);
                
                this.updateStatistics(data.statistics);
                this.updateServices(data.services);
                this.updateContactInfo(data.contact_info);
                this.updateSuccessStories(data.success_stories);
                
                return data;
            } catch (error) {
                console.error('Error loading dynamic data:', error);
                this.loadFallbackData();
            }
        },

        updateStatistics(stats) {
            // Update hero statistics
            const statElements = document.querySelectorAll('.stat__number');
            if (statElements.length >= 3) {
                statElements[0].textContent = stats.total_requests + '+';
                statElements[1].textContent = stats.avg_response_time + 'min';
                statElements[2].textContent = stats.satisfaction_rate + '%';
            }
            
            // Update other statistics throughout the page
            const elements = {
                totalProviders: document.querySelector('[data-stat="total-providers"]'),
                completionRate: document.querySelector('[data-stat="completion-rate"]'),
                recentRequests: document.querySelector('[data-stat="recent-requests"]')
            };
            
            if (elements.totalProviders) elements.totalProviders.textContent = stats.total_providers;
            if (elements.completionRate) elements.completionRate.textContent = stats.completion_rate + '%';
            if (elements.recentRequests) elements.recentRequests.textContent = stats.recent_requests;
        },

        updateServices(services) {
            // Update service cards with dynamic data
            const serviceCards = document.querySelectorAll('.service-card');
            serviceCards.forEach((card, index) => {
                if (services[index]) {
                    const service = services[index];
                    
                    // Update icon
                    const iconElement = card.querySelector('.service-icon i');
                    if (iconElement) {
                        iconElement.className = service.icon;
                    }
                    
                    // Update title
                    const titleElement = card.querySelector('.service-title');
                    if (titleElement) {
                        titleElement.textContent = service.name;
                    }
                    
                    // Update description
                    const descElement = card.querySelector('.service-desc');
                    if (descElement) {
                        descElement.textContent = service.description;
                    }
                    
                    // Update pricing
                    const priceElement = card.querySelector('.service-price');
                    if (priceElement) {
                        priceElement.textContent = `${service.min_price.toLocaleString()} - ${service.max_price.toLocaleString()} XAF`;
                    }
                    
                    // Add emergency badge if applicable
                    if (service.is_emergency) {
                        const emergencyBadge = document.createElement('div');
                        emergencyBadge.className = 'emergency-badge';
                        emergencyBadge.textContent = 'Urgence 24/7';
                        card.appendChild(emergencyBadge);
                    }
                }
            });
        },

        updateContactInfo(contactInfo) {
            // Update WhatsApp number
            CONFIG.whatsappNumber = contactInfo.whatsapp;
            
            // Update contact links
            const whatsappLinks = document.querySelectorAll('[data-whatsapp]');
            whatsappLinks.forEach(link => {
                link.href = `https://wa.me/${contactInfo.whatsapp.replace('+', '')}`;
            });
            
            // Update email links
            const emailLinks = document.querySelectorAll('[data-email]');
            emailLinks.forEach(link => {
                link.href = `mailto:${contactInfo.email}`;
            });
        },

        updateSuccessStories(stories) {
            // Update testimonials section with real success stories
            const testimonialContainer = document.querySelector('.testimonials-container');
            if (testimonialContainer && stories.length > 0) {
                testimonialContainer.innerHTML = '';
                
                stories.forEach(story => {
                    const testimonialCard = document.createElement('div');
                    testimonialCard.className = 'testimonial-card';
                    testimonialCard.innerHTML = `
                        <div class="testimonial-rating">
                            ${'★'.repeat(story.rating)}${'☆'.repeat(5-story.rating)}
                        </div>
                        <div class="testimonial-text">"${story.comment}"</div>
                        <div class="testimonial-service">${story.service} - ${story.zone}</div>
                        <div class="testimonial-time">${story.time_ago}</div>
                    `;
                    testimonialContainer.appendChild(testimonialCard);
                });
            }
        },

        loadFallbackData() {
            console.log('Loading fallback data...');
            // Fallback data if API fails
            const fallbackStats = {
                total_requests: 250,
                avg_response_time: 5,
                satisfaction_rate: 96,
                total_providers: 18,
                completion_rate: 94,
                recent_requests: 45
            };
            
            this.updateStatistics(fallbackStats);
        },

        async refreshStats() {
            try {
                const response = await fetch(CONFIG.statsEndpoint);
                if (response.ok) {
                    const stats = await response.json();
                    this.updateStatistics(stats);
                }
            } catch (error) {
                console.error('Error refreshing stats:', error);
            }
        }
    };

    // ===== UTILITIES =====
    const utils = {
        // Debounce function for performance optimization
        debounce(func, wait) {
            let timeout;
            return function executedFunction(...args) {
                const later = () => {
                    clearTimeout(timeout);
                    func(...args);
                };
                clearTimeout(timeout);
                timeout = setTimeout(later, wait);
            };
        },

        // Check if element is in viewport
        isInViewport(element) {
            const rect = element.getBoundingClientRect();
            return (
                rect.top >= 0 &&
                rect.left >= 0 &&
                rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
                rect.right <= (window.innerWidth || document.documentElement.clientWidth)
            );
        },

        // Simple counter animation without complications
        animateCounter(element, target, duration = 2000) {
            // Prevent multiple animations
            if (element.isAnimating) return;
            element.isAnimating = true;
            
            const suffix = element.dataset.suffix || '';
            const startTime = Date.now();
            
            function update() {
                const elapsed = Date.now() - startTime;
                const progress = Math.min(elapsed / duration, 1);
                
                // Simple easing
                const easeOut = 1 - Math.pow(1 - progress, 2);
                const current = Math.floor(target * easeOut);
                
                element.textContent = current + suffix;
                
                if (progress < 1) {
                    requestAnimationFrame(update);
                } else {
                    element.textContent = target + suffix;
                    element.isAnimating = false;
                }
            }
            
            requestAnimationFrame(update);
        },

        // Format phone number for WhatsApp
        formatWhatsAppNumber(number) {
            return number.replace(/\D/g, '');
        },

        // Get device type
        getDeviceType() {
            return window.innerWidth <= CONFIG.mobileBreakpoint ? 'mobile' : 'desktop';
        }
    };

    // ===== NAVIGATION =====
    const navigation = {
        init() {
            this.bindEvents();
            this.handleScroll();
        },

        bindEvents() {
            // Mobile menu toggle
            if (elements.navToggle) {
                elements.navToggle.addEventListener('click', this.openMobileMenu);
            }

            if (elements.navClose) {
                elements.navClose.addEventListener('click', this.closeMobileMenu);
            }

            // Navigation links
            elements.navLinks.forEach(link => {
                link.addEventListener('click', this.handleNavClick);
            });

            // Scroll event for header background
            window.addEventListener('scroll', utils.debounce(this.handleScroll, 10));

            // Close mobile menu on resize
            window.addEventListener('resize', utils.debounce(() => {
                if (window.innerWidth > CONFIG.mobileBreakpoint) {
                    this.closeMobileMenu();
                }
            }, 250));

            // Close mobile menu on outside click
            document.addEventListener('click', (e) => {
                if (elements.navMenu.classList.contains('active') && 
                    !elements.navMenu.contains(e.target) && 
                    !elements.navToggle.contains(e.target)) {
                    this.closeMobileMenu();
                }
            });
        },

        openMobileMenu() {
            elements.navMenu.classList.add('active');
            document.body.style.overflow = 'hidden';
            
            // Analytics
            analytics.track('mobile_menu_opened');
        },

        closeMobileMenu() {
            elements.navMenu.classList.remove('active');
            document.body.style.overflow = '';
            
            // Analytics
            analytics.track('mobile_menu_closed');
        },

        handleNavClick(e) {
            const href = e.target.getAttribute('href');
            
            if (href && href.startsWith('#')) {
                e.preventDefault();
                const targetElement = document.querySelector(href);
                
                if (targetElement) {
                    navigation.smoothScrollTo(targetElement);
                    navigation.closeMobileMenu();
                    
                    // Analytics
                    analytics.track('nav_link_clicked', { section: href });
                }
            }
        },

        smoothScrollTo(target) {
            const targetPosition = target.offsetTop - CONFIG.scrollOffset;
            
            window.scrollTo({
                top: targetPosition,
                behavior: 'smooth'
            });
        },

        handleScroll() {
            const scrollY = window.scrollY;
            
            // Add/remove header background
            if (scrollY > 100) {
                elements.header.classList.add('scrolled');
            } else {
                elements.header.classList.remove('scrolled');
            }

            // Update active navigation link
            navigation.updateActiveLink();
        },

        updateActiveLink() {
            const sections = document.querySelectorAll('section[id]');
            let activeSection = '';

            sections.forEach(section => {
                const sectionTop = section.offsetTop - CONFIG.scrollOffset;
                const sectionHeight = section.offsetHeight;
                
                if (window.scrollY >= sectionTop && window.scrollY < sectionTop + sectionHeight) {
                    activeSection = section.getAttribute('id');
                }
            });

            // Update navigation links
            elements.navLinks.forEach(link => {
                link.classList.remove('active');
                if (link.getAttribute('href') === `#${activeSection}`) {
                    link.classList.add('active');
                }
            });
        }
    };

    // ===== ANIMATIONS =====
    const animations = {
        init() {
            this.observeElements();
            this.initCounters();
        },

        observeElements() {
            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        entry.target.classList.add('animate-in');
                        
                        // Special handling for counters
                        if (entry.target.classList.contains('stat__number')) {
                            this.animateCounter(entry.target);
                        }
                    }
                });
            }, {
                threshold: 0.1,
                rootMargin: '-50px'
            });

            // Observe service cards
            elements.serviceCards.forEach(card => {
                observer.observe(card);
            });

            // Observe features
            elements.features.forEach(feature => {
                observer.observe(feature);
            });

            // Observe steps
            elements.steps.forEach(step => {
                observer.observe(step);
            });

            // Observe stats
            elements.heroStats.forEach(stat => {
                observer.observe(stat);
            });
        },

        initCounters() {
            // Counter data - just set them directly without animation
            const counters = [
                { element: elements.heroStats[0], target: 500, suffix: '+' },
                { element: elements.heroStats[1], target: 5, suffix: 'min' },
                { element: elements.heroStats[2], target: 100, suffix: '%' }
            ];

            // Set the values immediately without animation
            counters.forEach(counter => {
                if (counter.element) {
                    counter.element.textContent = counter.target + counter.suffix;
                }
            });
        },

        animateCounter(element) {
            // No animation - numbers are already set in initCounters
            return;
        }
    };

    // ===== WHATSAPP INTEGRATION =====
    const whatsapp = {
        openDirect(message = '') {
            const baseMessage = message || 'Bonjour! J\'aimerais avoir des informations sur vos services.';
            const encodedMessage = encodeURIComponent(baseMessage);
            const whatsappUrl = `https://wa.me/${utils.formatWhatsAppNumber(CONFIG.whatsappNumber)}?text=${encodedMessage}`;
            
            window.open(whatsappUrl, '_blank');
            
            // Analytics
            analytics.track('whatsapp_direct_opened', { message: baseMessage });
        },

        openWithService(serviceType) {
            const messages = {
                'plomberie': 'Bonjour! J\'ai besoin d\'un plombier. Pouvez-vous m\'aider?',
                'électricité': 'Bonjour! J\'ai un problème électrique. Pouvez-vous m\'aider?',
                'électroménager': 'Bonjour! Mon électroménager ne fonctionne pas. Pouvez-vous m\'aider?'
            };
            
            const message = messages[serviceType] || messages['plomberie'];
            this.openDirect(message);
            
            // Analytics
            analytics.track('whatsapp_service_requested', { service: serviceType });
        },

        openUrgent() {
            const urgentMessage = '🚨 URGENT! J\'ai besoin d\'aide immédiatement. C\'est une urgence!';
            this.openDirect(urgentMessage);
            
            // Analytics
            analytics.track('whatsapp_urgent_opened');
        }
    };

    // ===== SERVICE INTERACTIONS =====
    const services = {
        init() {
            this.bindEvents();
        },

        bindEvents() {
            // Service card hover effects
            elements.serviceCards.forEach(card => {
                card.addEventListener('mouseenter', this.onServiceHover);
                card.addEventListener('mouseleave', this.onServiceLeave);
            });
        },

        onServiceHover(e) {
            const card = e.currentTarget;
            card.style.transform = 'translateY(-8px) scale(1.02)';
            
            // Add subtle animation to icon
            const icon = card.querySelector('.service-card__icon');
            if (icon) {
                icon.style.transform = 'scale(1.1) rotate(5deg)';
            }
        },

        onServiceLeave(e) {
            const card = e.currentTarget;
            card.style.transform = '';
            
            // Reset icon
            const icon = card.querySelector('.service-card__icon');
            if (icon) {
                icon.style.transform = '';
            }
        }
    };

    // ===== ANALYTICS =====
    const analytics = {
        init() {
            console.log('Analytics system disabled to prevent API spam');
        },

        track(event, data = {}) {
            // Analytics completely disabled - only console logging for development
            if (event === 'page_view' || event === 'initialization_error') {
                console.log('Analytics Event (local only):', event, data);
            }
            // All other events are silently ignored to prevent spam
        },

        trackPageView() {
            this.track('page_view', {
                referrer: document.referrer,
                path: window.location.pathname
            });
        },

        trackUserEngagement() {
            let engagementStartTime = Date.now();
            let isActive = true;
            
            // Track visibility changes
            document.addEventListener('visibilitychange', () => {
                if (document.hidden) {
                    if (isActive) {
                        const sessionDuration = Date.now() - engagementStartTime;
                        this.track('session_end', { duration: sessionDuration });
                        isActive = false;
                    }
                } else {
                    engagementStartTime = Date.now();
                    isActive = true;
                    this.track('session_start');
                }
            });
            
            // Track scroll depth
            let maxScrollDepth = 0;
            window.addEventListener('scroll', utils.debounce(() => {
                const scrollDepth = Math.round((window.scrollY / (document.body.scrollHeight - window.innerHeight)) * 100);
                if (scrollDepth > maxScrollDepth) {
                    maxScrollDepth = scrollDepth;
                    if (scrollDepth >= 25 && maxScrollDepth < 25) {
                        this.track('scroll_depth_25');
                    } else if (scrollDepth >= 50 && maxScrollDepth < 50) {
                        this.track('scroll_depth_50');
                    } else if (scrollDepth >= 75 && maxScrollDepth < 75) {
                        this.track('scroll_depth_75');
                    } else if (scrollDepth >= 90 && maxScrollDepth < 90) {
                        this.track('scroll_depth_90');
                    }
                }
            }, 250));
        }
    };

    // ===== GLOBAL FUNCTIONS =====
    window.openWhatsApp = function(message) {
        whatsapp.openDirect(message);
    };

    window.startServiceChat = function(serviceType) {
        // First try to open chat widget, fallback to WhatsApp
        if (typeof toggleChatWidget === 'function') {
            toggleChatWidget();
            if (typeof sendQuickReply === 'function') {
                setTimeout(() => {
                    const messages = {
                        'plomberie': 'J\'ai un problème de plomberie',
                        'électricité': 'J\'ai un problème électrique',
                        'électroménager': 'Mon électroménager ne marche pas'
                    };
                    sendQuickReply(messages[serviceType] || messages['plomberie']);
                }, 500);
            }
        } else {
            whatsapp.openWithService(serviceType);
        }
    };

    window.handleUrgent = function() {
        // Show urgent modal or direct to WhatsApp
        const userConfirm = confirm('Situation d\'urgence détectée! Voulez-vous nous contacter immédiatement via WhatsApp?');
        if (userConfirm) {
            whatsapp.openUrgent();
        }
    };

    // ===== PERFORMANCE MONITORING =====
    const performance = {
        init() {
            this.measureLoadTime();
            this.measureCoreWebVitals();
        },

        measureLoadTime() {
            window.addEventListener('load', () => {
                const loadTime = performance && performance.now ? performance.now() : Date.now();
                analytics.track('page_load_time', { loadTime });
                
                // Log performance for development
                console.log(`Page loaded in ${loadTime.toFixed(2)}ms`);
            });
        },

        measureCoreWebVitals() {
            // Temporarily disable all performance tracking to stop excessive analytics calls
            // This prevents the CLS event spam that was causing 429 errors
            console.log('Performance monitoring temporarily disabled to prevent analytics spam');
            
            // Only track page load once
            if (!this.hasTrackedLoad) {
                this.hasTrackedLoad = true;
                setTimeout(() => {
                    analytics.track('performance_summary', { 
                        status: 'tracking_disabled',
                        reason: 'preventing_analytics_spam'
                    });
                }, 1000);
            }
        }
    };

    // ===== INITIALIZATION =====
    async function init() {
        // Wait for DOM to be ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', init);
            return;
        }

        try {
            // Load dynamic data first
            await dynamicData.loadData();
            
            // Initialize modules
            navigation.init();
            animations.init();
            services.init();
            analytics.init();
            analytics.trackPageView();
            analytics.trackUserEngagement();
            performance.init();

            // Add CSS classes for enhanced animations
            document.body.classList.add('js-enabled');

            // Set up periodic stats refresh (every 5 minutes)
            setInterval(() => {
                dynamicData.refreshStats();
            }, 300000);

            console.log('Djobea AI Landing Page V2 initialized successfully');
        } catch (error) {
            console.error('Error initializing landing page:', error);
            analytics.track('initialization_error', { error: error.message });
        }
    }

    // Start initialization
    init();

    // ===== ERROR HANDLING =====
    window.addEventListener('error', (event) => {
        analytics.track('javascript_error', {
            message: event.message,
            filename: event.filename,
            lineno: event.lineno,
            colno: event.colno
        });
    });

    // Handle unhandled promise rejections
    window.addEventListener('unhandledrejection', (event) => {
        analytics.track('promise_rejection', {
            reason: event.reason
        });
    });

})();