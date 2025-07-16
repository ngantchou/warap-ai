# Schéma de Communication - Djobea AI
## Architecture Conversationnelle Naturelle (Juillet 2025)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           UTILISATEUR FINAL                              │
│                    (WhatsApp / Chat Widget Web)                          │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │
                           │ Message en français naturel
                           │ "J'ai un problème de plomberie"
                           │
┌──────────────────────────▼──────────────────────────────────────────────┐
│                    POINTS D'ENTRÉE                                       │
│  ┌─────────────────────┐    ┌──────────────────────────────────────────┐ │
│  │   WhatsApp API      │    │        Chat Widget Web                   │ │
│  │   /webhook/whatsapp │    │        /webhook/chat                     │ │
│  │   (Twilio)          │    │        (Landing Page)                    │ │
│  └─────────────────────┘    └──────────────────────────────────────────┘ │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │
                           │ Routage vers moteur principal
                           │
┌──────────────────────────▼──────────────────────────────────────────────┐
│                MOTEUR DE CONVERSATION NATURELLE                          │
│              (natural_conversation_engine.py)                            │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │ ORCHESTRATION MULTI-LLM                                             │ │
│  │ ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────────────┐ │ │
│  │ │   CLAUDE    │ │   GEMINI    │ │            GPT-4                │ │ │
│  │ │ Intelligence│ │ Multimodal  │ │      Résolution Complexe       │ │ │
│  │ │ Émotionnelle│ │ + Matching  │ │                                 │ │ │
│  │ └─────────────┘ └─────────────┘ └─────────────────────────────────┘ │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │
                           │ Traitement en parallèle
                           │
┌─────────────┬─────────────┼─────────────┬─────────────────────────────────┐
│             │             │             │                                 │
│             ▼             ▼             ▼                                 │
│  ┌─────────────────┐ ┌─────────────┐ ┌─────────────────────────────────┐ │
│  │ ANALYSEUR       │ │ GESTIONNAIRE│ │    GÉNÉRATEUR DE RÉPONSES       │ │
│  │ D'INTENTIONS    │ │ DE CONTEXTE │ │                                 │ │
│  │                 │ │             │ │ ┌─────────────────────────────┐ │ │
│  │• Extraction NLP │ │• État convs │ │ │ Intelligence Culturelle     │ │ │
│  │• Service type   │ │• Historique │ │ │ Adaptation Cameroun         │ │ │
│  │• Localisation   │ │• Mémoire    │ │ │ Expressions locales         │ │ │
│  │• Urgence        │ │• Sessions   │ │ │ Français/Anglais/Pidgin     │ │ │
│  │• Confiance      │ │             │ │ └─────────────────────────────┘ │ │
│  └─────────────────┘ └─────────────┘ └─────────────────────────────────┘ │
└─────────────┬─────────────┬─────────────┬─────────────────────────────────┘
              │             │             │
              │             ▼             │
              │    ┌─────────────────────┐ │
              │    │   BASE DE DONNÉES   │ │
              │    │     PostgreSQL      │ │
              │    │                     │ │
              │    │• Utilisateurs       │ │
              │    │• Conversations      │ │
              │    │• ServiceRequests    │ │
              │    │• Prestataires       │ │
              │    │• Contexte culturel  │ │
              │    │• Préférences        │ │
              │    └─────────────────────┘ │
              │                           │
              ▼                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     ACTIONS SYSTÈME AUTOMATIQUES                         │
│                     (Invisibles pour l'utilisateur)                      │
│                                                                           │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────────────────┐ │
│  │ CRÉATION        │ │ RECHERCHE       │ │      NOTIFICATION           │ │
│  │ DEMANDE SERVICE │ │ PRESTATAIRES    │ │      PRESTATAIRES           │ │
│  │                 │ │                 │ │                             │ │
│  │• Auto si infos  │ │• Géolocalisation│ │• WhatsApp automatique       │ │
│  │  complètes      │ │• Spécialisation │ │• Messages professionnels    │ │
│  │• Statut: PENDING│ │• Disponibilité  │ │• Suivi des réponses         │ │
│  └─────────────────┘ └─────────────────┘ └─────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        PRESTATAIRES                                      │
│                    (Notifications WhatsApp)                              │
│                                                                           │
│  ┌─────────────────┐    ┌─────────────────────────────────────────────┐ │
│  │ Notification    │    │           Réponse OUI/NON                  │ │
│  │ Automatique     │◄───┤                                             │ │
│  │                 │    │ • Acceptation mission                       │ │
│  │• Détails client │    │ • Refus avec raison                         │ │
│  │• Type service   │    │ • Demande informations                      │ │
│  │• Localisation   │    │                                             │ │
│  │• Estimation prix│    └─────────────────────────────────────────────┘ │
│  └─────────────────┘                                                     │
└─────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    GESTION DU CYCLE DE VIE                               │
│                                                                           │
│  PENDING → PROVIDER_NOTIFIED → ASSIGNED → IN_PROGRESS → COMPLETED        │
│                                                                           │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────────────────┐ │
│  │ Mises à jour    │ │ Suivi temps     │ │      Paiement Mobile        │ │
│  │ automatiques    │ │ réel            │ │                             │ │
│  │                 │ │                 │ │• Monetbil (MTN/Orange)      │ │
│  │• Confirmations  │ │• Timeouts       │ │• Commission 15%             │ │
│  │• Notifications  │ │• Escalations    │ │• Notifications auto         │ │
│  │• Statut client  │ │• Fallbacks      │ │                             │ │
│  └─────────────────┘ └─────────────────┘ └─────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

## Caractéristiques Clés de l'Architecture

### 1. **Interface Conversationnelle 100% Naturelle**
- Aucun bouton ou menu visible pour l'utilisateur
- Traitement en français avec intelligence culturelle Cameroun
- Compréhension des expressions locales ("courant a jump", "coule-coule")

### 2. **Orchestration Multi-LLM Intelligente**
- **Claude**: Intelligence émotionnelle et culturelle
- **Gemini**: Analyse multimodale et matching géographique
- **GPT-4**: Résolution de problèmes complexes

### 3. **Traitement Invisible des Opérations**
- L'utilisateur ne voit jamais les opérations base de données
- Création automatique des demandes de service
- Recherche et notification des prestataires en arrière-plan

### 4. **Contextualisation Culturelle Avancée**
- Adaptation au marché camerounais
- Tarification en XAF
- Localisation Douala/Bonamoussadi
- Support multilingue (Français/Anglais/Pidgin)

### 5. **Gestion Complète du Cycle de Vie**
- Suivi automatique des statuts
- Notifications proactives
- Intégration paiement mobile
- Analytics et métriques en temps réel

## Flux de Communication Type

```
Utilisateur: "Bonjour, j'ai un problème de plomberie"
    ↓ (Analyse intention + contexte culturel)
Système: "Bonjour ! Je peux vous aider avec votre problème de plomberie. 
         Pouvez-vous me décrire ce qui ne va pas ?"

Utilisateur: "Il y a une fuite dans ma cuisine à Bonamoussadi"
    ↓ (Extraction: service=plomberie, location=Bonamoussadi, problème=fuite)
Système: "Je comprends, une fuite dans la cuisine peut être urgente. 
         Est-ce que l'eau coule beaucoup ou c'est juste quelques gouttes ?"

Utilisateur: "Ça coule beaucoup, c'est urgent"
    ↓ (Création automatique ServiceRequest + recherche prestataires)
Système: "Parfait, j'ai votre demande. Je contacte immédiatement nos 
         plombiers disponibles à Bonamoussadi. Estimation: 5,000-15,000 XAF"
    ↓ (Notification automatique prestataires via WhatsApp)
```

Ce schéma montre comment notre système transforme une conversation naturelle en actions concrètes, tout en maintenant une expérience utilisateur fluide et culturellement adaptée.