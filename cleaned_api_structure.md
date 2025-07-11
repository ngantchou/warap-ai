# Clean API Structure Plan - Djobea AI

## Current Issues
- Multiple duplicate webhook endpoints (v1, v2, v3, v4)
- Multiple duplicate analytics routers 
- Multiple duplicate authentication endpoints
- Multiple duplicate dashboard endpoints
- Too many overlapping API modules

## Proposed Clean Structure

### Core Endpoints (Keep)
1. **Authentication** - `/auth/api/auth/login` (Keep main auth)
2. **Webhook** - `/webhook/whatsapp` (Keep main webhook)
3. **Analytics** - `/api/analytics/` (Keep main analytics)
4. **AI Services** - `/api/ai/` (Keep for external apps)
5. **Settings** - `/api/settings/` (Keep for external apps)
6. **Finances** - `/api/finances/` (Keep for external apps)

### Remove Duplicates
1. **Webhook duplicates**: Remove v2, v3, v4 webhooks
2. **Analytics duplicates**: Remove duplicate analytics routers
3. **Dashboard duplicates**: Keep only main dashboard
4. **Auth duplicates**: Remove demo auth endpoints
5. **Provider duplicates**: Keep only main provider endpoints

### Essential API Categories
1. **Core Business** (6 endpoints)
   - GET /api/analytics/
   - GET /api/ai/health
   - GET /api/settings/system
   - GET /api/finances/overview
   - POST /auth/api/auth/login
   - POST /webhook/whatsapp

2. **External Mobile/Web** (8 endpoints)
   - GET /api/providers/
   - GET /api/requests/
   - POST /api/requests/
   - GET /api/analytics/performance
   - GET /api/finances/transactions
   - GET /api/ai/chat
   - GET /api/settings/notifications
   - GET /api/system/health

### Target: 14 Essential Endpoints (vs current 44)