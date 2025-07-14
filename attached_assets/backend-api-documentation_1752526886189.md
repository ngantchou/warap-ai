# Djobea Analytics Backend API Documentation

Base URL: `http://localhost:5000/api`

## Authentication

All endpoints (except login) require Bearer token authentication:
\`\`\`
Authorization: Bearer <jwt_token>
\`\`\`

---

## 1. Authentication Module

### POST /auth/login
**Description**: User authentication
**Request Body**:
\`\`\`json
{
  "email": "admin@djobea.ai",
  "password": "password123"
}
\`\`\`
**Response (200)**:
\`\`\`json
{
  "success": true,
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "user": {
      "id": "user_123",
      "email": "admin@djobea.ai",
      "name": "Admin User",
      "role": "admin"
    }
  }
}
\`\`\`
**Error Response (401)**:
\`\`\`json
{
  "success": false,
  "error": "Invalid credentials",
  "message": "Email or password is incorrect"
}
\`\`\`

### POST /auth/logout
**Description**: User logout
**Headers**: `Authorization: Bearer <token>`
**Response (200)**:
\`\`\`json
{
  "success": true,
  "message": "Logged out successfully"
}
\`\`\`

### POST /auth/refresh
**Description**: Refresh JWT token
**Headers**: `Authorization: Bearer <token>`
**Response (200)**:
\`\`\`json
{
  "success": true,
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "expiresAt": "2024-01-20T10:30:00Z"
  }
}
\`\`\`

### GET /auth/profile
**Description**: Get user profile
**Headers**: `Authorization: Bearer <token>`
**Response (200)**:
\`\`\`json
{
  "success": true,
  "data": {
    "id": "user_123",
    "name": "Admin User",
    "email": "admin@djobea.ai",
    "role": "admin",
    "avatar": "https://example.com/avatar.jpg",
    "permissions": ["read", "write", "admin"],
    "lastLogin": "2024-01-15T10:30:00Z",
    "createdAt": "2024-01-01T00:00:00Z"
  }
}
\`\`\`

---

## 2. Dashboard Module

### GET /dashboard
**Description**: Get dashboard statistics and charts
**Query Parameters**:
- `period` (optional): "24h" | "7d" | "30d" | "90d" | "1y" (default: "7d")

**Response (200)**:
\`\`\`json
{
  "success": true,
  "data": {
    "stats": {
      "totalRequests": 247,
      "successRate": 89.2,
      "pendingRequests": 15,
      "activeProviders": 23,
      "completedToday": 12,
      "revenue": 1250000,
      "avgResponseTime": 14.5,
      "customerSatisfaction": 4.8
    },
    "charts": {
      "activity": {
        "labels": ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"],
        "data": [12, 19, 15, 25, 22, 18, 24]
      },
      "services": {
        "labels": ["Plomberie", "Électricité", "Électroménager", "Maintenance"],
        "data": [45, 35, 15, 5]
      },
      "revenue": {
        "labels": ["Jan", "Fév", "Mar", "Avr", "Mai", "Jun"],
        "data": [850000, 920000, 1100000, 980000, 1150000, 1250000]
      }
    },
    "activity": {
      "requests": [
        {
          "id": "REQ-001",
          "client": "Mme Ngo Balla",
          "service": "Fuite robinet cuisine",
          "location": "Bonamoussadi Centre",
          "time": "Il y a 5 min",
          "status": "pending",
          "avatar": "MN",
          "priority": "urgent"
        }
      ],
      "alerts": [
        {
          "id": "ALT-001",
          "title": "Temps de réponse élevé",
          "description": "Prestataire M. Foko - Zone Bonamoussadi Centre",
          "time": "Il y a 10 min",
          "type": "warning",
          "status": "Non résolu",
          "severity": "medium"
        }
      ]
    }
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
\`\`\`

---

## 3. Analytics Module

### GET /analytics
**Description**: Get comprehensive analytics data
**Query Parameters**:
- `period` (optional): "24h" | "7d" | "30d" | "90d" | "1y" (default: "7d")

**Response (200)**:
\`\`\`json
{
  "success": true,
  "data": {
    "stats": {
      "successRate": 89.2,
      "responseTime": 14.5,
      "totalRequests": 247,
      "satisfaction": 4.8,
      "trends": {
        "successRate": 2.3,
        "responseTime": -1.2,
        "totalRequests": 15,
        "satisfaction": 0.1
      }
    },
    "charts": {
      "performance": {
        "labels": ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"],
        "successRate": [85, 87, 89, 91, 88, 90, 92],
        "aiEfficiency": [88, 90, 92, 94, 91, 93, 95],
        "satisfaction": [4.5, 4.6, 4.7, 4.8, 4.7, 4.8, 4.9]
      },
      "services": {
        "labels": ["Plomberie", "Électricité", "Électroménager", "Maintenance"],
        "data": [45, 35, 15, 5]
      },
      "geographic": {
        "labels": ["Bonamoussadi Centre", "Bonamoussadi Nord", "Bonamoussadi Sud", "Bonamoussadi Est"],
        "data": [58, 32, 28, 15]
      }
    },
    "insights": [
      {
        "type": "positive",
        "icon": "trending-up",
        "title": "Performance Excellente",
        "description": "Le taux de réussite a augmenté de 2.3% cette semaine.",
        "confidence": 95
      }
    ],
    "leaderboard": [
      {
        "id": "1",
        "name": "Jean-Baptiste Électricité",
        "avatar": "JB",
        "missions": 45,
        "rating": 4.9,
        "responseTime": 12,
        "score": 98.2
      }
    ]
  }
}
\`\`\`

### GET /analytics/kpis
**Description**: Get key performance indicators
**Query Parameters**:
- `period` (optional): "24h" | "7d" | "30d" | "90d" | "1y" (default: "7d")

**Response (200)**:
\`\`\`json
{
  "success": true,
  "data": {
    "successRate": 89.2,
    "responseTime": 14.5,
    "totalRequests": 247,
    "satisfaction": 4.8,
    "trends": {
      "successRate": 2.3,
      "responseTime": -1.2,
      "totalRequests": 15,
      "satisfaction": 0.1
    }
  }
}
\`\`\`

### GET /analytics/insights
**Description**: Get AI-generated insights
**Response (200)**:
\`\`\`json
{
  "success": true,
  "data": [
    {
      "type": "positive",
      "icon": "trending-up",
      "title": "Performance Excellente",
      "description": "Le taux de réussite a augmenté de 2.3% cette semaine. Les prestataires de Bonamoussadi Centre sont particulièrement performants.",
      "confidence": 95
    },
    {
      "type": "warning",
      "icon": "alert-triangle",
      "title": "Zone à Optimiser",
      "description": "Les demandes de plomberie à Bonamoussadi Sud ont un temps de réponse 23% plus élevé que la moyenne.",
      "confidence": 87
    }
  ]
}
\`\`\`

### GET /analytics/performance
**Description**: Get performance metrics over time
**Query Parameters**:
- `period` (optional): "24h" | "7d" | "30d" | "90d" | "1y" (default: "7d")

**Response (200)**:
\`\`\`json
{
  "success": true,
  "data": {
    "labels": ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"],
    "successRate": [85, 87, 89, 91, 88, 90, 92],
    "aiEfficiency": [88, 90, 92, 94, 91, 93, 95],
    "satisfaction": [4.5, 4.6, 4.7, 4.8, 4.7, 4.8, 4.9]
  }
}
\`\`\`

### GET /analytics/services
**Description**: Get service distribution analytics
**Query Parameters**:
- `period` (optional): "24h" | "7d" | "30d" | "90d" | "1y" (default: "7d")

**Response (200)**:
\`\`\`json
{
  "success": true,
  "data": {
    "labels": ["Plomberie", "Électricité", "Électroménager", "Maintenance"],
    "data": [45, 35, 15, 5]
  }
}
\`\`\`

### GET /analytics/geographic
**Description**: Get geographic distribution analytics
**Query Parameters**:
- `period` (optional): "24h" | "7d" | "30d" | "90d" | "1y" (default: "7d")

**Response (200)**:
\`\`\`json
{
  "success": true,
  "data": {
    "labels": ["Bonamoussadi Centre", "Bonamoussadi Nord", "Bonamoussadi Sud", "Bonamoussadi Est"],
    "data": [58, 32, 28, 15]
  }
}
\`\`\`

### GET /analytics/leaderboard
**Description**: Get provider leaderboard
**Response (200)**:
\`\`\`json
{
  "success": true,
  "data": [
    {
      "id": "1",
      "name": "Jean-Baptiste Électricité",
      "avatar": "JB",
      "missions": 45,
      "rating": 4.9,
      "responseTime": 12,
      "score": 98.2
    },
    {
      "id": "2",
      "name": "Marie Réparation",
      "avatar": "MR",
      "missions": 23,
      "rating": 4.8,
      "responseTime": 8,
      "score": 96.7
    }
  ]
}
\`\`\`

---

## 4. Providers Module

### GET /providers
**Description**: Get list of providers with filtering and pagination
**Query Parameters**:
- `page` (optional): Page number (default: 1)
- `limit` (optional): Items per page (default: 10)
- `search` (optional): Search term
- `service` (optional): Filter by service type
- `location` (optional): Filter by location
- `status` (optional): "active" | "inactive" | "suspended"
- `rating` (optional): Minimum rating filter

**Response (200)**:
\`\`\`json
{
  "success": true,
  "data": [
    {
      "id": "PROV-001",
      "name": "Jean-Baptiste Électricité",
      "email": "jb.electricite@email.com",
      "phone": "+237 6 12 34 56 78",
      "whatsapp": "+237 6 12 34 56 78",
      "services": ["Électricité", "Installation", "Réparation"],
      "coverageAreas": ["Bonamoussadi Centre", "Bonamoussadi Nord"],
      "specialty": "Électricité",
      "zone": "Bonamoussadi Centre",
      "rating": 4.8,
      "reviewCount": 45,
      "totalMissions": 67,
      "completedJobs": 62,
      "cancelledJobs": 5,
      "successRate": 92,
      "responseTime": 15,
      "performanceStatus": "excellent",
      "status": "active",
      "availability": "available",
      "joinDate": "2023-01-15",
      "lastActivity": "2024-01-15T08:30:00Z",
      "hourlyRate": 6500,
      "experience": 8,
      "acceptanceRate": 95,
      "description": "Électricien professionnel avec 8 ans d'expérience."
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 10,
    "total": 25,
    "totalPages": 3,
    "hasNext": true,
    "hasPrev": false
  },
  "stats": {
    "total": 25,
    "active": 20,
    "inactive": 3,
    "suspended": 2,
    "available": 18,
    "avgRating": 4.6,
    "newThisMonth": 3
  }
}
\`\`\`

### POST /providers
**Description**: Create new provider
**Request Body**:
\`\`\`json
{
  "name": "Nouveau Prestataire",
  "email": "nouveau@email.com",
  "phone": "+237 6 12 34 56 78",
  "whatsapp": "+237 6 12 34 56 78",
  "services": "Électricité, Installation, Réparation",
  "coverage": "Bonamoussadi Centre, Bonamoussadi Nord",
  "rate": "6500",
  "experience": "8",
  "description": "Description du prestataire"
}
\`\`\`
**Response (201)**:
\`\`\`json
{
  "success": true,
  "data": {
    "id": "PROV-123456",
    "name": "Nouveau Prestataire",
    "email": "nouveau@email.com",
    "phone": "+237 6 12 34 56 78",
    "whatsapp": "+237 6 12 34 56 78",
    "services": ["Électricité", "Installation", "Réparation"],
    "coverageAreas": ["Bonamoussadi Centre", "Bonamoussadi Nord"],
    "specialty": "Électricité",
    "zone": "Bonamoussadi Centre",
    "rating": 0,
    "reviewCount": 0,
    "totalMissions": 0,
    "status": "active",
    "availability": "available",
    "joinDate": "2024-01-15",
    "hourlyRate": 6500,
    "experience": 8,
    "description": "Description du prestataire"
  },
  "message": "Prestataire créé avec succès"
}
\`\`\`

### GET /providers/{id}
**Description**: Get provider details by ID
**Path Parameters**:
- `id`: Provider ID

**Response (200)**:
\`\`\`json
{
  "success": true,
  "data": {
    "id": "PROV-001",
    "name": "Jean-Baptiste Électricité",
    "email": "jb.electricite@email.com",
    "phone": "+237 6 12 34 56 78",
    "whatsapp": "+237 6 12 34 56 78",
    "services": ["Électricité", "Installation", "Réparation"],
    "coverageAreas": ["Bonamoussadi Centre", "Bonamoussadi Nord"],
    "specialty": "Électricité",
    "zone": "Bonamoussadi Centre",
    "rating": 4.8,
    "reviewCount": 45,
    "totalMissions": 67,
    "completedJobs": 62,
    "cancelledJobs": 5,
    "successRate": 92,
    "responseTime": 15,
    "performanceStatus": "excellent",
    "status": "active",
    "availability": "available",
    "joinDate": "2023-01-15",
    "lastActivity": "2024-01-15T08:30:00Z",
    "hourlyRate": 6500,
    "experience": 8,
    "acceptanceRate": 95,
    "description": "Électricien professionnel avec 8 ans d'expérience."
  }
}
\`\`\`

### PUT /providers/{id}
**Description**: Update provider information
**Path Parameters**:
- `id`: Provider ID
**Request Body**:
\`\`\`json
{
  "name": "Jean-Baptiste Électricité Mise à jour",
  "phone": "+237 6 12 34 56 78",
  "whatsapp": "+237 6 12 34 56 78",
  "email": "jb.updated@email.com",
  "services": "Électricité, Installation, Réparation, Maintenance",
  "coverage": "Bonamoussadi Centre, Bonamoussadi Nord, Bonamoussadi Sud",
  "rate": "7000",
  "experience": "9",
  "description": "Description mise à jour"
}
\`\`\`
**Response (200)**:
\`\`\`json
{
  "success": true,
  "data": {
    "id": "PROV-001",
    "name": "Jean-Baptiste Électricité Mise à jour",
    "email": "jb.updated@email.com",
    "phone": "+237 6 12 34 56 78",
    "services": ["Électricité", "Installation", "Réparation", "Maintenance"],
    "coverageAreas": ["Bonamoussadi Centre", "Bonamoussadi Nord", "Bonamoussadi Sud"],
    "hourlyRate": 7000,
    "experience": 9,
    "description": "Description mise à jour",
    "lastActivity": "2024-01-15T10:30:00Z"
  },
  "message": "Prestataire mis à jour avec succès"
}
\`\`\`

### DELETE /providers/{id}
**Description**: Delete provider
**Path Parameters**:
- `id`: Provider ID

**Response (200)**:
\`\`\`json
{
  "success": true,
  "message": "Prestataire supprimé avec succès",
  "data": {
    "id": "PROV-001",
    "name": "Jean-Baptiste Électricité"
  }
}
\`\`\`

### PUT /providers/{id}/status
**Description**: Update provider status
**Path Parameters**:
- `id`: Provider ID
**Request Body**:
\`\`\`json
{
  "status": "active"
}
\`\`\`
**Response (200)**:
\`\`\`json
{
  "success": true,
  "message": "Statut du prestataire mis à jour: active",
  "data": {
    "id": "PROV-001",
    "status": "active",
    "availability": "available",
    "lastActivity": "2024-01-15T10:30:00Z"
  }
}
\`\`\`

---

## 5. Requests Module

### GET /requests
**Description**: Get list of requests with filtering and pagination
**Query Parameters**:
- `page` (optional): Page number (default: 1)
- `limit` (optional): Items per page (default: 10)
- `search` (optional): Search term
- `serviceType` (optional): Filter by service type
- `location` (optional): Filter by location
- `priority` (optional): "low" | "normal" | "high" | "urgent"
- `status` (optional): "pending" | "assigned" | "in-progress" | "completed" | "cancelled"
- `dateRange` (optional): "today" | "week" | "month" | "quarter"

**Response (200)**:
\`\`\`json
{
  "success": true,
  "data": [
    {
      "id": "REQ-001",
      "clientName": "Marie Dubois",
      "clientPhone": "+237 6 12 34 56 78",
      "clientEmail": "marie.dubois@email.com",
      "serviceType": "Électricité",
      "description": "Réparation d'une prise électrique défectueuse dans la cuisine",
      "location": "Bonamoussadi Centre",
      "address": "123 Rue de la Paix, Bonamoussadi",
      "priority": "high",
      "status": "pending",
      "createdAt": "2024-01-15T10:30:00Z",
      "updatedAt": "2024-01-15T10:30:00Z",
      "scheduledDate": "2024-01-16T14:00:00Z",
      "urgency": true,
      "estimatedCost": 15000,
      "images": ["/placeholder.svg?height=200&width=300"],
      "notes": "Client disponible après 14h"
    }
  ],
  "stats": {
    "total": 247,
    "pending": 15,
    "assigned": 45,
    "inProgress": 32,
    "completed": 145,
    "cancelled": 10,
    "avgResponseTime": "2.5h",
    "completionRate": 85
  },
  "pagination": {
    "page": 1,
    "limit": 10,
    "total": 247,
    "totalPages": 25
  }
}
\`\`\`

### POST /requests
**Description**: Create new request
**Request Body**:
\`\`\`json
{
  "clientName": "Marie Dubois",
  "clientPhone": "+237 6 12 34 56 78",
  "clientEmail": "marie.dubois@email.com",
  "serviceType": "Électricité",
  "description": "Réparation d'une prise électrique défectueuse",
  "location": "Bonamoussadi Centre",
  "address": "123 Rue de la Paix, Bonamoussadi",
  "priority": "high",
  "urgency": true,
  "estimatedCost": 15000,
  "images": ["/placeholder.svg?height=200&width=300"],
  "notes": "Client disponible après 14h"
}
\`\`\`
**Response (201)**:
\`\`\`json
{
  "success": true,
  "data": {
    "id": "REQ-123456",
    "clientName": "Marie Dubois",
    "clientPhone": "+237 6 12 34 56 78",
    "clientEmail": "marie.dubois@email.com",
    "serviceType": "Électricité",
    "description": "Réparation d'une prise électrique défectueuse",
    "location": "Bonamoussadi Centre",
    "address": "123 Rue de la Paix, Bonamoussadi",
    "priority": "high",
    "status": "pending",
    "createdAt": "2024-01-15T10:30:00Z",
    "updatedAt": "2024-01-15T10:30:00Z",
    "urgency": true,
    "estimatedCost": 15000,
    "images": ["/placeholder.svg?height=200&width=300"],
    "notes": "Client disponible après 14h"
  },
  "message": "Demande créée avec succès"
}
\`\`\`

### GET /requests/{id}
**Description**: Get request details by ID
**Path Parameters**:
- `id`: Request ID

**Response (200)**:
\`\`\`json
{
  "success": true,
  "data": {
    "id": "REQ-001",
    "client": {
      "name": "Mme Ngo Célestine",
      "phone": "+237 6XX XXX XXX",
      "email": "celestine.ngo@email.com",
      "address": "Bonamoussadi Centre, Douala"
    },
    "service": {
      "type": "Plomberie",
      "description": "Fuite robinet cuisine urgente - Le robinet de la cuisine fuit depuis ce matin",
      "category": "Urgence",
      "estimatedDuration": "2 heures"
    },
    "location": {
      "address": "Bonamoussadi Centre",
      "coordinates": { "lat": 4.0511, "lng": 9.7679 },
      "accessInstructions": "Maison bleue, portail noir"
    },
    "status": "assigned",
    "priority": "urgent",
    "createdAt": "2024-01-15T08:30:00Z",
    "assignedAt": "2024-01-15T09:15:00Z",
    "provider": {
      "id": "1",
      "name": "Jean Dupont",
      "phone": "+237 6XX XXX XXX",
      "rating": 4.8,
      "specialty": "Plomberie"
    },
    "timeline": [
      {
        "id": 1,
        "title": "Demande créée",
        "description": "Demande soumise par le client",
        "timestamp": "2024-01-15T08:30:00Z",
        "status": "completed"
      },
      {
        "id": 2,
        "title": "Prestataire assigné",
        "description": "Jean Dupont assigné à cette demande",
        "timestamp": "2024-01-15T09:15:00Z",
        "status": "completed"
      },
      {
        "id": 3,
        "title": "En route",
        "description": "Le prestataire est en route",
        "timestamp": "2024-01-15T09:45:00Z",
        "status": "current"
      }
    ],
    "estimatedCost": {
      "min": 15000,
      "max": 30000,
      "currency": "FCFA"
    }
  }
}
\`\`\`

### PUT /requests/{id}
**Description**: Update request information
**Path Parameters**:
- `id`: Request ID
**Request Body**:
\`\`\`json
{
  "status": "in-progress",
  "priority": "high",
  "notes": "Mise à jour des notes",
  "estimatedCost": {
    "min": 20000,
    "max": 35000,
    "currency": "FCFA"
  },
  "actualCost": 25000
}
\`\`\`
**Response (200)**:
\`\`\`json
{
  "success": true,
  "data": {
    "id": "REQ-001",
    "status": "in-progress",
    "updatedAt": "2024-01-15T11:30:00Z"
  },
  "message": "Demande mise à jour avec succès"
}
\`\`\`

### POST /requests/{id}/assign
**Description**: Assign request to provider
**Path Parameters**:
- `id`: Request ID
**Request Body**:
\`\`\`json
{
  "providerId": "PROV-001"
}
\`\`\`
**Response (200)**:
\`\`\`json
{
  "success": true,
  "data": {
    "id": "REQ-001",
    "status": "assigned",
    "assignedProvider": {
      "id": "PROV-001",
      "name": "Jean-Baptiste Électricité",
      "rating": 4.8
    },
    "updatedAt": "2024-01-15T11:30:00Z"
  },
  "message": "Demande assignée avec succès"
}
\`\`\`

### POST /requests/{id}/cancel
**Description**: Cancel request
**Path Parameters**:
- `id`: Request ID
**Request Body**:
\`\`\`json
{
  "reason": "Client a annulé"
}
\`\`\`
**Response (200)**:
\`\`\`json
{
  "success": true,
  "data": {
    "id": "REQ-001",
    "status": "cancelled",
    "cancelReason": "Client a annulé",
    "updatedAt": "2024-01-15T11:30:00Z"
  },
  "message": "Demande annulée avec succès"
}
\`\`\`

### PUT /requests/{id}/status
**Description**: Update request status
**Path Parameters**:
- `id`: Request ID
**Request Body**:
\`\`\`json
{
  "status": "completed"
}
\`\`\`
**Response (200)**:
\`\`\`json
{
  "success": true,
  "data": {
    "id": "REQ-001",
    "status": "completed",
    "updatedAt": "2024-01-15T11:30:00Z"
  },
  "message": "Statut mis à jour avec succès"
}
\`\`\`

---

## 6. Messages Module

### GET /messages
**Description**: Get messages, contacts, or stats based on type parameter
**Query Parameters**:
- `type` (optional): "contacts" | "messages" | "stats"
- `search` (optional): Search term
- `role` (optional): "client" | "provider" | "admin"
- `status` (optional): "active" | "archived" | "blocked"
- `conversationId` (optional): Filter messages by conversation
- `page` (optional): Page number (default: 1)
- `limit` (optional): Items per page (default: 10)

**Response for type=contacts (200)**:
\`\`\`json
{
  "success": true,
  "data": [
    {
      "id": "contact_1",
      "name": "Marie Dubois",
      "phone": "+237 6 12 34 56 78",
      "role": "client",
      "avatar": "MD",
      "lastMessage": "Merci pour votre aide",
      "lastMessageTime": "2024-01-15T10:30:00Z",
      "unreadCount": 2,
      "status": "active",
      "conversationId": "conv_123"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 10,
    "total": 25,
    "totalPages": 3
  }
}
\`\`\`

**Response for type=messages (200)**:
\`\`\`json
{
  "success": true,
  "data": [
    {
      "id": "msg_1",
      "conversationId": "conv_123",
      "senderId": "contact_1",
      "senderName": "Marie Dubois",
      "senderType": "client",
      "content": "Bonjour, j'ai besoin d'aide pour ma plomberie",
      "type": "text",
      "timestamp": "2024-01-15T10:30:00Z",
      "status": "delivered",
      "attachments": [],
      "location": null,
      "contact": null,
      "metadata": {}
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 50,
    "total": 150,
    "totalPages": 3
  }
}
\`\`\`

**Response for type=stats (200)**:
\`\`\`json
{
  "success": true,
  "data": {
    "totalContacts": 156,
    "activeConversations": 23,
    "unreadMessages": 12,
    "responseRate": 95.2,
    "avgResponseTime": "5 min",
    "messagesSentToday": 45,
    "messagesReceivedToday": 67,
    "clientMessages": 89,
    "providerMessages": 67
  }
}
\`\`\`

### POST /messages
**Description**: Send a new message
**Request Body**:
\`\`\`json
{
  "conversationId": "conv_123",
  "content": "Bonjour, comment puis-je vous aider?",
  "type": "text",
  "attachments": [],
  "location": null,
  "contact": null,
  "senderType": "admin",
  "metadata": {}
}
\`\`\`
**Response (201)**:
\`\`\`json
{
  "success": true,
  "data": {
    "id": "msg_456",
    "conversationId": "conv_123",
    "senderId": "admin_1",
    "senderName": "Admin",
    "senderType": "admin",
    "content": "Bonjour, comment puis-je vous aider?",
    "type": "text",
    "timestamp": "2024-01-15T11:30:00Z",
    "status": "sent",
    "attachments": [],
    "location": null,
    "contact": null,
    "metadata": {}
  },
  "message": "Message envoyé avec succès"
}
\`\`\`

### PATCH /messages
**Description**: Update message or contact status
**Request Body**:
\`\`\`json
{
  "messageId": "msg_456",
  "status": "read"
}
\`\`\`
**Response (200)**:
\`\`\`json
{
  "success": true,
  "data": {
    "id": "msg_456",
    "status": "read",
    "updatedAt": "2024-01-15T11:35:00Z"
  },
  "message": "Message mis à jour avec succès"
}
\`\`\`

### DELETE /messages
**Description**: Delete message or conversation
**Query Parameters**:
- `messageId`: Message ID to delete

**Response (200)**:
\`\`\`json
{
  "success": true,
  "message": "Message supprimé avec succès"
}
\`\`\`

---

## 7. Finances Module

### GET /finances
**Description**: Get financial data and statistics
**Query Parameters**:
- `dateRange` (optional): "today" | "week" | "month" | "quarter" | "year"
- `category` (optional): Filter by category
- `type` (optional): "income" | "expense"
- `status` (optional): "pending" | "completed" | "failed"

**Response (200)**:
\`\`\`json
{
  "success": true,
  "data": {
    "stats": {
      "totalRevenue": 1250000,
      "totalExpenses": 350000,
      "netProfit": 900000,
      "pendingPayments": 125000,
      "averageTransactionValue": 25000,
      "monthlyGrowth": 15.2,
      "trends": {
        "revenue": 12.5,
        "expenses": -5.2,
        "profit": 18.7
      }
    },
    "charts": {
      "revenue": {
        "labels": ["Jan", "Fév", "Mar", "Avr", "Mai", "Jun"],
        "income": [850000, 920000, 1100000, 980000, 1150000, 1250000],
        "expenses": [250000, 280000, 320000, 290000, 330000, 350000]
      },
      "categories": {
        "labels": ["Services", "Commissions", "Frais", "Marketing"],
        "data": [65, 20, 10, 5]
      },
      "cashFlow": {
        "labels": ["Sem 1", "Sem 2", "Sem 3", "Sem 4"],
        "values": [150000, 180000, 220000, 250000]
      }
    },
    "forecast": {
      "scenarios": {
        "optimistic": { "revenue": 1500000, "growth": 20 },
        "realistic": { "revenue": 1350000, "growth": 8 },
        "pessimistic": { "revenue": 1200000, "growth": -4 }
      },
      "insights": [
        "Croissance soutenue attendue",
        "Optimisation des coûts recommandée"
      ],
      "recommendations": [
        "Investir dans le marketing digital",
        "Diversifier les services"
      ]
    }
  }
}
\`\`\`

### GET /finances/transactions
**Description**: Get transaction history with pagination
**Query Parameters**:
- `page` (optional): Page number (default: 1)
- `limit` (optional): Items per page (default: 10)
- `dateRange` (optional): "today" | "week" | "month" | "quarter" | "year"
- `category` (optional): Filter by category
- `type` (optional): "income" | "expense"
- `status` (optional): "pending" | "completed" | "failed"

**Response (200)**:
\`\`\`json
{
  "success": true,
  "data": [
    {
      "id": "TXN-001",
      "type": "income",
      "amount": 25000,
      "currency": "FCFA",
      "category": "Service",
      "description": "Réparation électrique - Marie Dubois",
      "date": "2024-01-15T10:30:00Z",
      "status": "completed",
      "paymentMethod": "Mobile Money",
      "reference": "MM123456789",
      "relatedRequest": "REQ-001",
      "provider": {
        "id": "PROV-001",
        "name": "Jean-Baptiste Électricité"
      },
      "client": {
        "id": "CLIENT-001",
        "name": "Marie Dubois"
      }
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 10,
    "total": 156,
    "totalPages": 16
  },
  "summary": {
    "totalIncome": 850000,
    "totalExpenses": 125000,
    "netAmount": 725000,
    "transactionCount": 156
  }
}
\`\`\`

---

## 8. AI Predictions Module

### GET /ai/predictions
**Description**: Get AI predictions
**Query Parameters**:
- `type` (optional): Type of prediction

**Response (200)**:
\`\`\`json
{
  "success": true,
  "data": {
    "demandForecast": {
      "nextWeek": {
        "total": 45,
        "byService": {
          "Plomberie": 18,
          "Électricité": 15,
          "Électroménager": 8,
          "Maintenance": 4
        },
        "confidence": 87
      },
      "nextMonth": {
        "total": 180,
        "byService": {
          "Plomberie": 72,
          "Électricité": 60,
          "Électroménager": 32,
          "Maintenance": 16
        },
        "confidence": 82
      }
    },
    "providerOptimization": [
      {
        "providerId": "PROV-001",
        "name": "Jean-Baptiste Électricité",
        "recommendations": [
          "Augmenter la disponibilité le weekend",
          "Étendre la zone de couverture"
        ],
        "potentialIncrease": 25
      }
    ],
    "riskAnalysis": {
      "highRiskRequests": [
        {
          "requestId": "REQ-123",
          "riskScore": 0.85,
          "factors": ["Urgence élevée", "Zone difficile", "Historique client"]
        }
      ],
      "providerRisks": [
        {
          "providerId": "PROV-005",
          "riskScore": 0.72,
          "factors": ["Taux d'annulation élevé", "Temps de réponse lent"]
        }
      ]
    }
  }
}
\`\`\`

### GET /ai/insights
**Description**: Get AI-generated insights
**Response (200)**:
\`\`\`json
{
  "success": true,
  "data": [
    {
      "type": "optimization",
      "title": "Optimisation des Zones",
      "description": "Redistribuer les prestataires pour réduire le temps de réponse de 15%",
      "impact": "high",
      "confidence": 92,
      "actionable": true,
      "recommendations": [
        "Déplacer 2 prestataires vers Bonamoussadi Sud",
        "Recruter 1 nouveau prestataire pour Bonamoussadi Est"
      ]
    },
    {
      "type": "prediction",
      "title": "Pic de Demande Prévu",
      "description": "Augmentation de 30% des demandes prévue la semaine prochaine",
      "impact": "medium",
      "confidence": 85,
      "actionable": true,
      "recommendations": [
        "Préparer les prestataires",
        "Ajuster les tarifs si nécessaire"
      ]
    }
  ]
}
\`\`\`

---

## 9. Geolocation Module

### GET /geolocation
**Description**: Get geolocation data
**Query Parameters**:
- `north` (optional): North boundary
- `south` (optional): South boundary
- `east` (optional): East boundary
- `west` (optional): West boundary

**Response (200)**:
\`\`\`json
{
  "success": true,
  "data": {
    "providers": [
      {
        "id": "PROV-001",
        "name": "Jean-Baptiste Électricité",
        "location": {
          "lat": 4.0511,
          "lng": 9.7679
        },
        "status": "available",
        "service": "Électricité"
      }
    ],
    "requests": [
      {
        "id": "REQ-001",
        "location": {
          "lat": 4.0521,
          "lng": 9.7689
        },
        "status": "pending",
        "priority": "urgent",
        "service": "Plomberie"
      }
    ],
    "zones": [
      {
        "id": "ZONE-001",
        "name": "Bonamoussadi Centre",
        "boundaries": {
          "north": 4.0600,
          "south": 4.0400,
          "east": 9.7800,
          "west": 9.7600
        },
        "activeProviders": 8,
        "pendingRequests": 3
      }
    ]
  }
}
\`\`\`

### GET /zones
**Description**: Get available zones
**Response (200)**:
\`\`\`json
{
  "success": true,
  "data": [
    {
      "id": "ZONE-001",
      "name": "Bonamoussadi Centre",
      "boundaries": {
        "north": 4.0600,
        "south": 4.0400,
        "east": 9.7800,
        "west": 9.7600
      },
      "activeProviders": 8,
      "pendingRequests": 3,
      "avgResponseTime": 15,
      "coverage": 95
    },
    {
      "id": "ZONE-002",
      "name": "Bonamoussadi Nord",
      "boundaries": {
        "north": 4.0700,
        "south": 4.0600,
        "east": 9.7800,
        "west": 9.7600
      },
      "activeProviders": 5,
      "pendingRequests": 1,
      "avgResponseTime": 18,
      "coverage": 87
    }
  ]
}
\`\`\`

---

## 10. Settings Module

### GET /settings
**Description**: Get settings by category
**Query Parameters**:
- `category` (optional): Settings category

**Response (200)**:
\`\`\`json
{
  "success": true,
  "data": {
    "general": {
      "appName": "Djobea Analytics",
      "timezone": "Africa/Douala",
      "language": "fr",
      "currency": "FCFA",
      "dateFormat": "DD/MM/YYYY",
      "businessHours": {
        "start": "08:00",
        "end": "18:00",
        "days": ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]
      },
      "contactInfo": {
        "phone": "+237 6XX XXX XXX",
        "email": "contact@djobea.ai",
        "address": "Douala, Cameroun"
      }
    },
    "notifications": {
      "pushNotifications": {
        "enabled": true,
        "newRequests": true,
        "statusUpdates": true,
        "providerAlerts": true
      },
      "emailNotifications": {
        "enabled": true,
        "dailyReports": true,
        "weeklyReports": true,
        "systemAlerts": true
      },
      "smsNotifications": {
        "enabled": false,
        "urgentOnly": true,
        "providerUpdates": false
      }
    }
  }
}
\`\`\`

### PUT /settings/{category}
**Description**: Update settings for a specific category
**Path Parameters**:
- `category`: Settings category (general, notifications, security, etc.)
**Request Body**:
\`\`\`json
{
  "appName": "Djobea Analytics Updated",
  "timezone": "Africa/Douala",
  "language": "fr",
  "currency": "FCFA",
  "businessHours": {
    "start": "07:00",
    "end": "19:00",
    "days": ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
  }
}
\`\`\`
**Response (200)**:
\`\`\`json
{
  "success": true,
  "data": {
    "appName": "Djobea Analytics Updated",
    "timezone": "Africa/Douala",
    "language": "fr",
    "currency": "FCFA",
    "businessHours": {
      "start": "07:00",
      "end": "19:00",
      "days": ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    },
    "updatedAt": "2024-01-15T11:30:00Z"
  },
  "message": "Paramètres mis à jour avec succès"
}
\`\`\`

---

## 11. Export Module

### POST /export
**Description**: Export data in various formats
**Request Body**:
\`\`\`json
{
  "type": "requests",
  "format": "excel",
  "filters": {
    "dateRange": "month",
    "status": "completed",
    "serviceType": "Électricité"
  }
}
\`\`\`
**Response (200)**:
\`\`\`json
{
  "success": true,
  "data": {
    "downloadUrl": "http://djobea.ai/api/downloads/export_123456.xlsx",
    "expiresAt": "2024-01-16T11:30:00Z",
    "fileSize": 2048576,
    "recordCount": 156
  },
  "message": "Export généré avec succès"
}
\`\`\`

---

## 12. Notifications Module

### GET /notifications
**Description**: Get user notifications
**Query Parameters**:
- `page` (optional): Page number (default: 1)
- `limit` (optional): Items per page (default: 10)
- `read` (optional): Filter by read status
- `type` (optional): Filter by notification type

**Response (200)**:
\`\`\`json
{
  "success": true,
  "data": [
    {
      "id": "NOTIF-001",
      "title": "Nouvelle demande reçue",
      "message": "Une nouvelle demande de plomberie a été soumise",
      "type": "info",
      "read": false,
      "createdAt": "2024-01-15T10:30:00Z",
      "actionUrl": "/requests/REQ-123",
      "metadata": {
        "requestId": "REQ-123",
        "priority": "urgent"
      }
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 10,
    "total": 25,
    "totalPages": 3
  },
  "summary": {
    "total": 25,
    "unread": 8,
    "read": 17
  }
}
\`\`\`

### PUT /notifications/{id}/read
**Description**: Mark notification as read
**Path Parameters**:
- `id`: Notification ID

**Response (200)**:
\`\`\`json
{
  "success": true,
  "data": {
    "id": "NOTIF-001",
    "read": true,
    "readAt": "2024-01-15T11:30:00Z"
  },
  "message": "Notification marquée comme lue"
}
\`\`\`

### PUT /notifications/read-all
**Description**: Mark all notifications as read
**Response (200)**:
\`\`\`json
{
  "success": true,
  "data": {
    "markedCount": 8
  },
  "message": "Toutes les notifications ont été marquées comme lues"
}
\`\`\`

---

## Error Responses

All endpoints can return the following error responses:

### 400 Bad Request
\`\`\`json
{
  "success": false,
  "error": "Bad Request",
  "message": "Invalid request parameters",
  "details": {
    "field": "email",
    "message": "Invalid email format"
  }
}
\`\`\`

### 401 Unauthorized
\`\`\`json
{
  "success": false,
  "error": "Unauthorized",
  "message": "Authentication required"
}
\`\`\`

### 403 Forbidden
\`\`\`json
{
  "success": false,
  "error": "Forbidden",
  "message": "Insufficient permissions"
}
\`\`\`

### 404 Not Found
\`\`\`json
{
  "success": false,
  "error": "Not Found",
  "message": "Resource not found"
}
\`\`\`

### 429 Too Many Requests
\`\`\`json
{
  "success": false,
  "error": "Too Many Requests",
  "message": "Rate limit exceeded",
  "retryAfter": 60
}
\`\`\`

### 500 Internal Server Error
\`\`\`json
{
  "success": false,
  "error": "Internal Server Error",
  "message": "An unexpected error occurred",
  "requestId": "req_123456"
}
\`\`\`

---

## Rate Limiting

- **Authentication endpoints**: 5 requests per minute
- **Read operations**: 100 requests per minute
- **Write operations**: 30 requests per minute
- **Export operations**: 5 requests per hour

## Headers

All responses include:
- `X-Request-ID`: Unique request identifier
- `X-Rate-Limit-Remaining`: Remaining requests in current window
- `X-Rate-Limit-Reset`: Time when rate limit resets
