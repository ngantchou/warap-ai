# Djobea AI Complete API Documentation

## Overview
This document provides comprehensive API documentation for the Djobea AI WhatsApp service marketplace platform. The API supports external mobile and web applications with JWT authentication and full CRUD operations.

**Base URL**: `https://your-domain.com` or `http://localhost:5000`  
**Authentication**: Bearer JWT Token  
**Content-Type**: `application/json`

## Authentication

### Login
```http
POST /api/auth/login
Content-Type: application/json

{
  "email": "admin@djobea.ai",
  "password": "your-password",
  "rememberMe": false
}
```

**Response:**
```json
{
  "success": true,
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_at": "2025-07-11T17:00:00Z",
  "user": {
    "id": "1",
    "email": "admin@djobea.ai",
    "username": "admin",
    "role": "admin"
  }
}
```

### Refresh Token
```http
POST /api/auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

### Logout
```http
POST /api/auth/logout
Authorization: Bearer {access_token}
```

## Analytics API

### Get Analytics Overview
```http
GET /api/analytics/?period=7d
Authorization: Bearer {access_token}
```

**Query Parameters:**
- `period` (optional): `24h`, `7d`, `30d`, `90d`, `1y` (default: `7d`)

**Response:**
```json
{
  "total_requests": 150,
  "completed_requests": 120,
  "success_rate": 80.0,
  "average_response_time": 12.5,
  "revenue": 45000.0,
  "active_providers": 25,
  "period": "7d",
  "trends": {
    "requests_growth": 15.2,
    "revenue_growth": 8.7,
    "success_rate_change": 2.1
  }
}
```

### Get KPI Metrics
```http
GET /api/analytics/kpis?period=7d
Authorization: Bearer {access_token}
```

**Response:**
```json
{
  "total_revenue": 125000.0,
  "total_requests": 450,
  "active_users": 320,
  "provider_utilization": 85.2,
  "average_completion_time": 2.5,
  "customer_satisfaction": 4.6,
  "commission_earned": 18750.0,
  "period": "7d"
}
```

### Get Performance Metrics
```http
GET /api/analytics/performance?period=7d
Authorization: Bearer {access_token}
```

### Get Services Analytics
```http
GET /api/analytics/services?period=7d
Authorization: Bearer {access_token}
```

### Get Geographic Analytics
```http
GET /api/analytics/geographic?period=7d
Authorization: Bearer {access_token}
```

### Get AI Insights
```http
GET /api/analytics/insights
Authorization: Bearer {access_token}
```

### Get Provider Leaderboard
```http
GET /api/analytics/leaderboard
Authorization: Bearer {access_token}
```

## Providers API

### Get Providers List
```http
GET /api/providers?page=1&limit=10&search=plumber&status=active
Authorization: Bearer {access_token}
```

**Query Parameters:**
- `page` (optional): Page number (default: 1)
- `limit` (optional): Items per page (default: 6, max: 100)
- `search` (optional): Search term
- `status` (optional): Filter by status
- `specialty` (optional): Filter by specialty
- `zone` (optional): Filter by coverage zone
- `minRating` (optional): Minimum rating filter

**Response:**
```json
{
  "providers": [
    {
      "id": 1,
      "name": "Jean Mbarga",
      "phone": "+237691234567",
      "serviceType": "Plomberie",
      "coverageZone": "Bonamoussadi",
      "rating": 4.8,
      "totalJobs": 156,
      "specialties": ["Réparation", "Installation"],
      "yearsExperience": 8,
      "isActive": true,
      "isAvailable": true,
      "trustScore": 92,
      "createdAt": "2025-01-15T10:30:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 10,
    "total": 45,
    "pages": 5
  }
}
```

### Create Provider
```http
POST /api/providers
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "name": "Marie Douala",
  "phone": "+237691234568",
  "serviceType": "Électricité",
  "coverageZone": "Bonamoussadi",
  "specialties": ["Réparation", "Installation"],
  "yearsExperience": 5,
  "bio": "Électricienne expérimentée avec 5 ans d'expérience",
  "certifications": ["CAP Électricité", "Habilitation électrique"]
}
```

### Get Provider by ID
```http
GET /api/providers/{id}
Authorization: Bearer {access_token}
```

### Update Provider
```http
PUT /api/providers/{id}
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "name": "Jean Mbarga",
  "phone": "+237691234567",
  "serviceType": "Plomberie",
  "coverageZone": "Bonamoussadi",
  "specialties": ["Réparation", "Installation", "Urgence"],
  "yearsExperience": 9,
  "bio": "Plombier expert avec 9 ans d'expérience",
  "status": "active"
}
```

### Delete Provider
```http
DELETE /api/providers/{id}
Authorization: Bearer {access_token}
```

### Contact Provider
```http
POST /api/providers/{id}/contact
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "message": "Nouvelle demande urgente de plomberie",
  "urgency": "urgent"
}
```

### Update Provider Status
```http
PUT /api/providers/{id}/status
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "status": "active"
}
```

### Get Available Providers
```http
GET /api/providers/available?serviceType=Plomberie&zone=Bonamoussadi
Authorization: Bearer {access_token}
```

### Get Provider Statistics
```http
GET /api/providers/stats
Authorization: Bearer {access_token}
```

## Requests API

### Get Requests List
```http
GET /api/requests?page=1&limit=10&status=pending&priority=high
Authorization: Bearer {access_token}
```

**Query Parameters:**
- `page`, `limit`: Pagination
- `search`: Search term
- `status`: Filter by status (`pending`, `assigned`, `in_progress`, `completed`, `cancelled`)
- `priority`: Filter by priority
- `service`: Filter by service type
- `location`: Filter by location
- `dateFrom`, `dateTo`: Date range filter
- `sortBy`: Sort field (default: `createdAt`)
- `sortOrder`: Sort order (`asc`, `desc`)

**Response:**
```json
{
  "requests": [
    {
      "id": 1,
      "title": "Fuite d'eau urgente",
      "description": "Fuite importante dans la cuisine",
      "serviceType": "Plomberie",
      "location": "Bonamoussadi, Douala",
      "priority": "high",
      "status": "pending",
      "estimatedCost": 15000.0,
      "clientName": "Paul Nkomo",
      "clientPhone": "+237691234569",
      "createdAt": "2025-07-11T14:30:00Z",
      "assignedProvider": null
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 10,
    "total": 78,
    "pages": 8
  }
}
```

### Get Request Details
```http
GET /api/requests/{id}
Authorization: Bearer {access_token}
```

### Assign Request to Provider
```http
POST /api/requests/{id}/assign
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "providerId": 5,
  "notes": "Provider specialized in urgent repairs"
}
```

### Cancel Request
```http
POST /api/requests/{id}/cancel
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "reason": "Client no longer needs service",
  "refundAmount": 5000.0
}
```

### Update Request Status
```http
PUT /api/requests/{id}/status
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "status": "in_progress",
  "notes": "Provider started working on the issue"
}
```

### Generate Invoice
```http
POST /api/requests/{id}/invoice
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "finalCost": 18000.0,
  "description": "Réparation fuite d'eau - remplacement joint",
  "materials": ["Joint de canalisation", "Mastic étanchéité"],
  "laborHours": 2.5
}
```

## Finances API

### Get Finances Overview
```http
GET /api/finances/overview?period=30d
Authorization: Bearer {access_token}
```

### Get Transactions
```http
GET /api/finances/transactions?page=1&limit=20&type=payment
Authorization: Bearer {access_token}
```

**Response:**
```json
{
  "transactions": [
    {
      "id": 1,
      "type": "payment",
      "amount": 18000.0,
      "currency": "XAF",
      "status": "completed",
      "requestId": 15,
      "providerId": 3,
      "clientName": "Paul Nkomo",
      "providerName": "Jean Mbarga",
      "paymentMethod": "MTN Mobile Money",
      "transactionDate": "2025-07-11T16:00:00Z",
      "commission": 2700.0
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 156,
    "pages": 8
  }
}
```

### Get Commissions
```http
GET /api/finances/commissions?period=30d
Authorization: Bearer {access_token}
```

### Get Payouts
```http
GET /api/finances/payouts?providerId=3
Authorization: Bearer {access_token}
```

### Create Payout
```http
POST /api/finances/payouts
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "providerId": 3,
  "amount": 45000.0,
  "method": "MTN Mobile Money",
  "notes": "Monthly payout for Jean Mbarga"
}
```

### Get Financial Reports
```http
GET /api/finances/reports?period=30d&type=revenue
Authorization: Bearer {access_token}
```

## System API

### Get Zones List
```http
GET /api/zones
Authorization: Bearer {access_token}
```

**Response:**
```json
{
  "zones": [
    {
      "id": 1,
      "name": "Bonamoussadi",
      "city": "Douala",
      "region": "Littoral",
      "coordinates": {
        "lat": 4.0511,
        "lng": 9.7679
      },
      "activeProviders": 15,
      "totalRequests": 89,
      "coverageRadius": 5.0
    }
  ]
}
```

### Get System Metrics
```http
GET /api/metrics/system
Authorization: Bearer {access_token}
```

**Response:**
```json
{
  "database": {
    "status": "healthy",
    "connections": 12,
    "query_time": 45.2
  },
  "api": {
    "status": "healthy",
    "response_time": 125.8,
    "success_rate": 99.2
  },
  "system": {
    "cpu_usage": 25.0,
    "memory_usage": 45.0,
    "disk_usage": 60.0,
    "uptime": 86400
  }
}
```

## AI API

### Get AI Models
```http
GET /api/ai/models
Authorization: Bearer {access_token}
```

### Get AI Metrics
```http
GET /api/ai/metrics
Authorization: Bearer {access_token}
```

### Analyze Text
```http
POST /api/ai/analyze
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "text": "J'ai un problème de plomberie urgent",
  "language": "fr",
  "context": "service_request"
}
```

### Chat with AI
```http
POST /api/ai/chat
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "message": "Bonjour, j'ai besoin d'un plombier",
  "sessionId": "session_123",
  "context": {
    "location": "Bonamoussadi",
    "urgency": "normal"
  }
}
```

### AI Health Check
```http
GET /api/ai/health
Authorization: Bearer {access_token}
```

## Settings API

### Get General Settings
```http
GET /api/settings/general
Authorization: Bearer {access_token}
```

### Update General Settings
```http
PUT /api/settings/general
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "platformName": "Djobea AI",
  "supportEmail": "support@djobea.ai",
  "defaultLanguage": "fr",
  "timezone": "Africa/Douala"
}
```

### Get Notification Settings
```http
GET /api/settings/notifications
Authorization: Bearer {access_token}
```

### Update Notification Settings
```http
PUT /api/settings/notifications
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "whatsappEnabled": true,
  "smsEnabled": true,
  "emailEnabled": false,
  "pushEnabled": true,
  "reminderInterval": 30
}
```

### Get Business Settings
```http
GET /api/settings/business
Authorization: Bearer {access_token}
```

### Update Business Settings
```http
PUT /api/settings/business
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "commissionRate": 15.0,
  "currency": "XAF",
  "paymentMethods": ["MTN Mobile Money", "Orange Money"],
  "serviceRadius": 10.0
}
```

## Error Responses

### Authentication Errors
```json
{
  "detail": "Could not validate credentials"
}
```

### Validation Errors
```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### Not Found Errors
```json
{
  "detail": "Provider not found"
}
```

### Server Errors
```json
{
  "detail": "Internal server error"
}
```

## Status Codes

- `200 OK`: Successful request
- `201 Created`: Resource created successfully
- `400 Bad Request`: Invalid request data
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `422 Unprocessable Entity`: Validation errors
- `500 Internal Server Error`: Server error

## Rate Limiting

- **Rate Limit**: 100 requests per minute per IP
- **Headers**: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`

## Pagination

All list endpoints support pagination:
- `page`: Page number (default: 1)
- `limit`: Items per page (default varies by endpoint)
- `total`: Total number of items
- `pages`: Total number of pages

## Field Validation

### Phone Numbers
- Format: `+237XXXXXXXXX` (Cameroon format)
- Example: `+237691234567`

### Currency
- All amounts in XAF (Central African CFA Franc)
- Example: `15000.0`

### Date/Time
- Format: ISO 8601 (`YYYY-MM-DDTHH:MM:SSZ`)
- Example: `2025-07-11T16:30:00Z`

## SDK Examples

### JavaScript/Node.js
```javascript
const axios = require('axios');

const client = axios.create({
  baseURL: 'https://your-domain.com',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  }
});

// Get analytics
const analytics = await client.get('/api/analytics/?period=7d');

// Create provider
const provider = await client.post('/api/providers', {
  name: 'Jean Mbarga',
  phone: '+237691234567',
  serviceType: 'Plomberie',
  coverageZone: 'Bonamoussadi'
});
```

### Python
```python
import requests

class DjobeaClient:
    def __init__(self, base_url, token):
        self.base_url = base_url
        self.headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
    
    def get_analytics(self, period='7d'):
        response = requests.get(
            f'{self.base_url}/api/analytics/',
            params={'period': period},
            headers=self.headers
        )
        return response.json()
    
    def create_provider(self, data):
        response = requests.post(
            f'{self.base_url}/api/providers',
            json=data,
            headers=self.headers
        )
        return response.json()

# Usage
client = DjobeaClient('https://your-domain.com', 'your-token')
analytics = client.get_analytics('30d')
```

---

**API Version**: 1.0  
**Last Updated**: July 11, 2025  
**Documentation**: Comprehensive API documentation for Djobea AI platform