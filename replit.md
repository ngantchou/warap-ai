# Djobea AI

## Overview

Djobea AI is a WhatsApp-based service marketplace that connects customers with local service providers in Douala, Cameroon. The system uses AI-powered conversation understanding to process service requests via WhatsApp and automatically matches customers with available providers. It focuses on home services like plumbing, electrical work, and appliance repair in the Bonamoussadi district.

## System Architecture

### Backend Architecture
- **Framework**: FastAPI (Python) - chosen for its async capabilities, automatic API documentation, and strong type hints support
- **Database**: PostgreSQL with SQLAlchemy ORM - provides robust relational data storage with excellent Python integration
- **AI Integration**: Anthropic Claude API - latest model (claude-sonnet-4-20250514) for natural language understanding
- **Messaging**: Twilio WhatsApp API - enables WhatsApp communication without requiring business verification

### Frontend Architecture
- **Admin Interface**: Server-side rendered HTML templates using Jinja2
- **Styling**: Bootstrap 5 with custom CSS for responsive design
- **Client-side**: Vanilla JavaScript for form validation and dynamic interactions

### Communication Flow
- **Webhook-based**: Twilio webhooks trigger message processing
- **Async Processing**: FastAPI handles concurrent WhatsApp messages efficiently
- **AI Processing**: Claude analyzes messages to extract service requests

## Key Components

### Models (SQLAlchemy)
- **User**: WhatsApp users with conversation history
- **Provider**: Service providers with availability, ratings, and coverage areas
- **ServiceRequest**: Customer requests with status tracking
- **Conversation**: Message history for context-aware responses

### Services
- **AIService**: Claude integration for message understanding and response generation
- **WhatsAppService**: Twilio integration for sending/receiving messages
- **ProviderService**: Provider matching and management logic
- **RequestService**: Service request lifecycle management

### Routes
- **Webhook Router**: Handles incoming WhatsApp messages
- **Admin Router**: Web interface for system management

### Configuration
- **Environment-based**: Uses Pydantic Settings for type-safe configuration
- **Business Rules**: Configurable commission rates, timeouts, and service coverage

## Data Flow

1. **Message Reception**: WhatsApp message → Twilio → Webhook endpoint
2. **AI Processing**: Message → Claude API → Extract service request data
3. **Provider Matching**: Service type + location → Query available providers
4. **Response Generation**: AI generates appropriate response based on context
5. **Response Delivery**: Response → Twilio → WhatsApp user

### Request Lifecycle
- **Pending**: Initial request received and parsed
- **Assigned**: Matched with available provider
- **In Progress**: Service being performed
- **Completed**: Service finished successfully
- **Cancelled**: Request cancelled by user or system

## External Dependencies

### Required APIs
- **Anthropic Claude API**: Natural language processing and response generation
- **Twilio WhatsApp API**: Message sending and webhook handling
- **PostgreSQL Database**: Data persistence

### Service Integrations
- **WhatsApp Business**: Primary communication channel
- **AI-powered matching**: Intelligent provider-customer matching based on location and service type

## Deployment Strategy

### Environment Configuration
- Database URL configuration for PostgreSQL
- API keys for Anthropic and Twilio services
- Configurable business parameters (commission rates, coverage areas)

### Database Management
- SQLAlchemy models with automatic table creation
- Connection pooling with pre-ping and recycling
- Migration-ready structure

### Logging and Monitoring
- Structured logging with configurable levels
- Conversation logging for system improvement
- Error tracking with contextual information

## User Preferences

Preferred communication style: Simple, everyday language.

## Changelog

```
Changelog:
- July 01, 2025. Initial setup
```