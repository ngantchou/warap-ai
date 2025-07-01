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

## Recent Changes

### Project Cleanup for Sprint 4 (July 01, 2025)
✓ **Codebase Cleanup**: Removed duplicate files (config.py, database.py, main.py, models.py) - using app/ versions only
✓ **Structure Consolidation**: Removed redundant routes/, services/, utils/ folders - consolidated into app/ structure
✓ **Cache Cleanup**: Removed all __pycache__ directories
✓ **Docker Cleanup**: Removed Dockerfile, docker-compose.yml, alembic files (keeping core app functionality)
✓ **Test Optimization**: Kept essential tests (Cameroon conversations, Sprint 3 matching)
✓ **Asset Management**: Kept core documentation in attached_assets/

### Sprint 1 - Infrastructure Complete (July 01, 2025)
✓ **Project Structure**: Organized FastAPI application with proper separation of concerns
✓ **Database Schema**: Complete PostgreSQL schema with Users, Providers, ServiceRequests, Conversations tables
✓ **FastAPI Endpoints**: All required endpoints implemented (/webhook/whatsapp, /health, /admin/*)
✓ **Claude AI Integration**: Latest model (claude-sonnet-4-20250514) for natural language processing
✓ **WhatsApp Business API**: Twilio webhook integration for message handling
✓ **Testing Framework**: Pytest setup with essential unit tests
✓ **Structured Logging**: Loguru integration with proper error handling
✓ **Type Safety**: Complete type hints throughout codebase

### Sprint 2 - Conversational Intelligence Complete (July 01, 2025)
✓ **Conversation Manager**: Advanced Claude-powered conversation understanding system
✓ **Request Information Extraction**: Intelligent extraction of service type, location, description, and urgency
✓ **Multi-turn Conversations**: Context-aware dialogue management with conversation memory
✓ **Cameroon-specific Language Support**: Handles French/English/Pidgin mix and local expressions
✓ **WhatsApp Normalization**: Automatic correction of abbreviations and typos
✓ **Confidence Scoring**: AI confidence assessment for extraction reliability
✓ **Contextual Response Generation**: Dynamic question generation based on missing information
✓ **Complete Request Processing**: Automatic service request creation when all info is collected
✓ **Local Expression Understanding**: Supports "courant a jump", "coule-coule", "light don go", etc.
✓ **Memory Management**: Conversation history with configurable limits (10 messages)
✓ **Error Handling**: Graceful fallback for AI processing failures
✓ **Integration Testing**: Comprehensive test suite for Cameroon conversation scenarios

### Sprint 3 - Matching & Notifications Complete (July 01, 2025)
✓ **Advanced Provider Matching**: Multi-criteria scoring algorithm (proximity, rating, response time, specialization, availability)
✓ **Geographic Matching**: Douala/Bonamoussadi location-aware matching with zone coverage
✓ **Provider Scoring System**: Weighted scoring for optimal provider selection
✓ **WhatsApp Notification Service**: Automated provider notifications with exact message templates
✓ **Fallback Logic**: 10-minute timeout with automatic fallback to next best provider
✓ **Response Processing**: OUI/NON response handling with ambiguity resolution
✓ **Status Management**: Complete request lifecycle (PENDING → PROVIDER_NOTIFIED → ASSIGNED → IN_PROGRESS → COMPLETED)
✓ **Client Notifications**: Automated client updates on provider acceptance and extended delays
✓ **Metrics Tracking**: Acceptance rates, response times, timeout rates, and matching success
✓ **Provider Database**: Sample providers seeded for Bonamoussadi area testing
✓ **Async Processing**: Non-blocking provider notification with concurrent handling
✓ **Comprehensive Testing**: Full test suite for matching algorithm and notification system

### Sprint 4 - Finalization & Admin Interface Complete (July 01, 2025)
✓ **Complete User Journey Management**: Status tracking, cancellation, and feedback system
✓ **User Journey Manager**: Handle status requests, cancellations before provider acceptance, and rating system
✓ **Real-time Metrics Dashboard**: Auto-refreshing dashboard with key performance indicators
✓ **Advanced Analytics Service**: Success rate, response time, service type, and geographic analytics
✓ **Enhanced Admin Interface**: Metrics page with real-time updates and visual indicators
✓ **Interactive Analytics Dashboard**: Charts and graphs for performance analysis with Chart.js
✓ **Provider Performance Rankings**: Complete provider scoring and ranking system
✓ **Request Detail Pages**: Individual request management with timeline and conversation history
✓ **Admin Status Override**: Direct status management and request cancellation capabilities
✓ **End-to-End Testing**: Comprehensive test scenarios for success, timeout, failure, and cancellation cases
✓ **Robust Error Handling**: System resilience testing for database and service failures
✓ **Professional UI/UX**: Bootstrap 5 with custom styling for responsive admin interface
✓ **API Endpoints**: RESTful endpoints for metrics and analytics data access

### Technical Standards Met
- ✓ Type hints on all functions and classes
- ✓ Comprehensive docstrings for API documentation
- ✓ Structured error handling with try/catch blocks
- ✓ Environment-based configuration management
- ✓ Unit tests with pytest framework
- ✓ Database connection pooling and health checks

## Changelog

```
Changelog:
- July 01, 2025: Sprint 1 Infrastructure completed - Full FastAPI application with PostgreSQL, Claude AI, WhatsApp integration, and testing framework
- July 01, 2025: Sprint 2 Conversational Intelligence completed - Advanced conversation manager with Claude integration, multi-turn dialogue support, Cameroon-specific language handling, intelligent information extraction, and comprehensive testing framework
- July 01, 2025: Sprint 3 Matching & Notifications completed - Advanced provider matching algorithm with multi-criteria scoring, automated WhatsApp notifications with fallback logic, complete request lifecycle management, and comprehensive metrics tracking
- July 01, 2025: Project Cleanup completed - Consolidated project structure, removed duplicates, optimized for Sprint 4 development
- July 01, 2025: Sprint 4 Finalization completed - Complete user journey management, real-time metrics dashboard, advanced analytics service, enhanced admin interface, and comprehensive end-to-end testing
```