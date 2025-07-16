# Djobea AI - Schéma d'Architecture de Communication

## Vue d'ensemble du Système

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              DJOBEA AI SYSTEM                                      │
│                    Architecture de Communication Conversationnelle                │
└─────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│     UTILISATEURS │    │    PRESTATAIRES  │    │     ADMIN WEB    │
│                  │    │                  │    │                  │
│  • WhatsApp      │    │  • WhatsApp      │    │  • Dashboard     │
│  • Chat Widget   │    │  • Dashboard     │    │  • Analytics     │
│  • Landing Page  │    │  • Mobile        │    │  • Monitoring    │
└─────────┬────────┘    └─────────┬────────┘    └─────────┬────────┘
          │                       │                       │
          ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           INTERFACES D'ENTRÉE                                  │
├─────────────────┬─────────────────┬─────────────────┬─────────────────────────┤
│   WhatsApp API  │   Chat Widget   │ Provider Portal │    Admin Interface      │
│                 │                 │                 │                         │
│ • Twilio Hook   │ • /api/chat     │ • /provider/*   │ • /admin/*              │
│ • /webhook/*    │ • Real-time     │ • Dashboard     │ • Analytics             │
│ • Media Support │ • Phone Number  │ • Profile Mgmt  │ • Request Management    │
└─────────┬───────┴─────────┬───────┴─────────┬───────┴─────────┬───────────────┘
          │                 │                 │                 │
          ▼                 ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      COUCHE DE ROUTAGE INTELLIGENTE                            │
├─────────────────────────────────────────────────────────────────────────────────┤
│                    Natural Conversation Engine                                 │
│                                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐                │
│  │ Intent Analyzer │  │ Context Manager │  │Response Generator│                │
│  │                 │  │                 │  │                 │                │
│  │ • NLP Analysis  │  │ • Session State │  │ • AI Responses  │                │
│  │ • Service Type  │  │ • Conversation  │  │ • Culturally    │                │
│  │ • Urgency       │  │   History       │  │   Adapted       │                │
│  │ • Location      │  │ • User Context  │  │ • Template-based│                │
│  └─────────┬───────┘  └─────────┬───────┘  └─────────┬───────┘                │
│            │                    │                    │                        │
│            └────────────────────┼────────────────────┘                        │
│                                 │                                             │
└─────────────────────────────────┼─────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         ORCHESTRATEUR MULTI-LLM                                │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐                │
│  │   CLAUDE AI     │  │    GEMINI AI    │  │    GPT-4O      │                │
│  │                 │  │                 │  │                 │                │
│  │ • Emotional     │  │ • Image/Video   │  │ • Complex       │                │
│  │   Intelligence  │  │   Analysis      │  │   Problem       │                │
│  │ • Cultural      │  │ • Multimodal    │  │   Solving       │                │
│  │   Adaptation    │  │   Processing    │  │ • Advanced      │                │
│  │ • Conversation  │  │ • Provider      │  │   Reasoning     │                │
│  │   Flow          │  │   Matching      │  │ • Technical     │                │
│  │                 │  │                 │  │   Analysis      │                │
│  └─────────┬───────┘  └─────────┬───────┘  └─────────┬───────┘                │
│            │                    │                    │                        │
│            └────────────────────┼────────────────────┘                        │
│                                 │                                             │
└─────────────────────────────────┼─────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        SERVICES MÉTIER CENTRALISÉS                             │
├─────────────────┬─────────────────┬─────────────────┬─────────────────────────┤
│ Conversation    │   Provider      │    Payment      │   Communication         │
│   Manager       │   Matching      │    Service      │     Service             │
│                 │                 │                 │                         │
│ • State Machine │ • Multi-Criteria│ • Monetbil      │ • WhatsApp Messages     │
│ • Multi-turn    │   Scoring       │   Integration   │ • Proactive Updates     │
│ • Context Aware │ • Geographic    │ • Mobile Money  │ • Status Notifications  │
│ • Memory Mgmt   │   Proximity     │ • Commission    │ • Template System       │
│                 │ • Availability  │   Tracking      │                         │
└─────────┬───────┴─────────┬───────┴─────────┬───────┴─────────┬───────────────┘
          │                 │                 │                 │
          ▼                 ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           BASE DE DONNÉES                                      │
├─────────────────┬─────────────────┬─────────────────┬─────────────────────────┤
│     Users       │   Providers     │ Service Requests│    Conversations        │
│                 │                 │                 │                         │
│ • WhatsApp ID   │ • Profiles      │ • Status Track  │ • Message History       │
│ • Preferences   │ • Trust Scores  │ • Lifecycle     │ • Context Memory        │
│ • History       │ • Availability  │ • Payments      │ • AI Responses          │
│ • Behavioral    │ • Ratings       │ • Progress      │ • Confidence Scores     │
│   Patterns      │ • Specialties   │ • Analytics     │                         │
└─────────┬───────┴─────────┬───────┴─────────┬───────┴─────────┬───────────────┘
          │                 │                 │                 │
          └─────────────────┼─────────────────┼─────────────────┘
                            │                 │
                            ▼                 ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                       SERVICES EXTERNES                                        │
├─────────────────┬─────────────────┬─────────────────┬─────────────────────────┤
│  Twilio API     │   Anthropic     │     Gemini      │       OpenAI            │
│                 │    Claude       │      API        │        API              │
│ • WhatsApp Bus. │                 │                 │                         │
│ • SMS/Voice     │ • Natural Lang. │ • Multimodal    │ • Advanced Reasoning    │
│ • Media Support │ • Conversation  │ • Image Analysis│ • Complex Problems      │
│ • Webhooks      │ • Cultural AI   │ • Video Process │ • Technical Solutions   │
└─────────────────┴─────────────────┴─────────────────┴─────────────────────────┘
```

## Flux de Communication Détaillé

### 1. Réception de Message

```
User WhatsApp → Twilio Webhook → FastAPI Router → Natural Conversation Engine
                    ↓
            Security Middleware
                    ↓
            Rate Limiting & Validation
                    ↓
            Message Normalization
```

### 2. Traitement Intelligent

```
Natural Conversation Engine
        ↓
Intent Analyzer (Extraction des intentions)
        ↓
Context Manager (Gestion d'état et historique)
        ↓
Multi-LLM Orchestrator (Sélection du bon LLM)
        ↓
Response Generator (Génération de réponse)
```

### 3. Actions Système Automatiques

```
Based on Intent:
    ├── Service Request → Provider Matching → Notification
    ├── Status Check → Database Query → Status Update
    ├── Cancellation → Workflow Update → Confirmation
    └── General Chat → Contextual Response
```

### 4. Réponse et Suivi

```
Response Generator → Communication Service → WhatsApp/Chat Widget
                            ↓
                    Background Tasks
                            ↓
                  Proactive Updates & Monitoring
```

## Caractéristiques Clés du Système

### 🧠 Intelligence Conversationnelle
- **100% Naturel**: Aucune interface bouton, conversation fluide
- **Multi-LLM**: Claude, Gemini, GPT-4 selon le contexte
- **Contexte Persistant**: Mémoire conversationnelle intelligente
- **Cultural Intelligence**: Adaptation au contexte camerounais

### 🔄 Flux de Données
- **Async Processing**: Traitement non-bloquant
- **Real-time Updates**: Notifications proactives
- **State Management**: Machine d'état sophistiquée
- **Error Recovery**: Mécanismes de récupération robustes

### 🛡️ Sécurité et Performance
- **Rate Limiting**: Protection contre le spam
- **Input Validation**: Validation stricte des entrées
- **Webhook Security**: Vérification des signatures Twilio
- **Database Pooling**: Optimisation des connexions

### 📊 Analytics et Monitoring
- **Real-time Metrics**: Métriques en temps réel
- **Conversation Analytics**: Analyse des conversations
- **Performance Tracking**: Suivi des performances
- **Error Monitoring**: Surveillance des erreurs

## Technologies Utilisées

- **Backend**: FastAPI (Python)
- **Database**: PostgreSQL avec SQLAlchemy
- **AI**: Claude 4.0, Gemini 2.5, GPT-4o
- **Messaging**: Twilio WhatsApp Business API
- **Payment**: Monetbil (Mobile Money Cameroun)
- **Frontend**: Vanilla JS + Bootstrap 5
- **Monitoring**: Loguru + Custom Analytics

Ce système offre une expérience conversationnelle complètement naturelle où l'utilisateur ne voit jamais les opérations de base de données ou les processus système - tout est géré de manière transparente par l'intelligence artificielle.