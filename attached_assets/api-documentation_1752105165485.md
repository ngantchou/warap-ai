# 📚 API Documentation - Djobea Analytics

## 🔐 Authentication
All API endpoints require JWT authentication via `Authorization: Bearer <token>` header.

---

## 📊 **1. DASHBOARD MODULE**

### **GET /api/dashboard**
Récupère les données principales du tableau de bord
\`\`\`typescript
Response: {
  stats: {
    totalRequests: number
    successRate: number
    pendingRequests: number
    activeProviders: number
  }
  charts: {
    activity: { labels: string[], values: number[] }
    services: { labels: string[], values: number[] }
  }
  activity: {
    requests: Request[]
    alerts: Alert[]
  }
}
\`\`\`

### **GET /api/dashboard/stats**
Statistiques en temps réel
\`\`\`typescript
Query: ?period=24h|7d|30d
Response: {
  totalRequests: number
  successRate: number
  averageResponseTime: number
  satisfaction: number
  trends: {
    requests: number
    successRate: number
    responseTime: number
  }
}
\`\`\`

### **GET /api/dashboard/activity**
Activité récente
\`\`\`typescript
Query: ?limit=10&offset=0
Response: {
  requests: Request[]
  alerts: Alert[]
  notifications: Notification[]
}
\`\`\`

---

## 📋 **2. REQUESTS MODULE**

### **GET /api/requests**
Liste des demandes avec filtres
\`\`\`typescript
Query: {
  status?: 'pending'|'assigned'|'completed'|'cancelled'
  priority?: 'low'|'normal'|'high'|'urgent'
  service?: string
  location?: string
  dateFrom?: string
  dateTo?: string
  page?: number
  limit?: number
}
Response: {
  requests: Request[]
  pagination: {
    total: number
    page: number
    limit: number
    totalPages: number
  }
  stats: {
    pending: number
    assigned: number
    completed: number
    cancelled: number
  }
}
\`\`\`

### **POST /api/requests**
Créer une nouvelle demande
\`\`\`typescript
Body: {
  clientName: string
  clientPhone: string
  serviceType: string
  description: string
  location: string
  priority: 'low'|'normal'|'high'|'urgent'
  scheduledDate?: string
}
Response: {
  success: boolean
  requestId: string
  message: string
}
\`\`\`

### **GET /api/requests/:id**
Détails d'une demande
\`\`\`typescript
Response: {
  id: string
  client: ClientInfo
  service: ServiceInfo
  provider?: ProviderInfo
  status: RequestStatus
  timeline: TimelineEvent[]
  messages: Message[]
}
\`\`\`

### **PUT /api/requests/:id**
Mettre à jour une demande
\`\`\`typescript
Body: {
  status?: RequestStatus
  providerId?: string
  notes?: string
  priority?: Priority
}
Response: {
  success: boolean
  message: string
}
\`\`\`

### **DELETE /api/requests/:id**
Annuler une demande
\`\`\`typescript
Response: {
  success: boolean
  message: string
}
\`\`\`

### **POST /api/requests/:id/assign**
Assigner un prestataire
\`\`\`typescript
Body: {
  providerId: string
  notes?: string
}
Response: {
  success: boolean
  message: string
  assignedProvider: ProviderInfo
}
\`\`\`

### **POST /api/requests/:id/complete**
Marquer comme terminée
\`\`\`typescript
Body: {
  rating?: number
  feedback?: string
  cost?: number
}
Response: {
  success: boolean
  message: string
}
\`\`\`

### **GET /api/requests/stats**
Statistiques des demandes
\`\`\`typescript
Query: ?period=24h|7d|30d|90d
Response: {
  total: number
  byStatus: Record<string, number>
  byService: Record<string, number>
  byLocation: Record<string, number>
  byPriority: Record<string, number>
  trends: {
    daily: { date: string, count: number }[]
    hourly: { hour: number, count: number }[]
  }
}
\`\`\`

---

## 👥 **3. PROVIDERS MODULE**

### **GET /api/providers**
Liste des prestataires
\`\`\`typescript
Query: {
  status?: 'active'|'inactive'|'suspended'
  availability?: 'available'|'busy'|'offline'
  service?: string
  location?: string
  rating?: number
  page?: number
  limit?: number
}
Response: {
  providers: Provider[]
  pagination: PaginationInfo
  stats: {
    total: number
    active: number
    available: number
    averageRating: number
  }
}
\`\`\`

### **POST /api/providers**
Ajouter un prestataire
\`\`\`typescript
Body: {
  name: string
  phone: string
  whatsapp: string
  email: string
  services: string[]
  coverageAreas: string[]
  hourlyRate: number
  experience: number
  description: string
}
Response: {
  success: boolean
  providerId: string
  message: string
}
\`\`\`

### **GET /api/providers/:id**
Détails d'un prestataire
\`\`\`typescript
Response: {
  id: string
  personalInfo: PersonalInfo
  services: ServiceInfo[]
  performance: PerformanceMetrics
  availability: AvailabilityInfo
  reviews: Review[]
  missions: Mission[]
}
\`\`\`

### **PUT /api/providers/:id**
Mettre à jour un prestataire
\`\`\`typescript
Body: Partial<Provider>
Response: {
  success: boolean
  message: string
}
\`\`\`

### **DELETE /api/providers/:id**
Supprimer un prestataire
\`\`\`typescript
Response: {
  success: boolean
  message: string
}
\`\`\`

### **POST /api/providers/:id/suspend**
Suspendre un prestataire
\`\`\`typescript
Body: {
  reason: string
  duration?: number
}
Response: {
  success: boolean
  message: string
}
\`\`\`

### **POST /api/providers/:id/activate**
Activer un prestataire
\`\`\`typescript
Response: {
  success: boolean
  message: string
}
\`\`\`

### **GET /api/providers/:id/performance**
Métriques de performance
\`\`\`typescript
Query: ?period=7d|30d|90d|1y
Response: {
  missions: number
  successRate: number
  averageRating: number
  responseTime: number
  earnings: number
  trends: PerformanceTrend[]
}
\`\`\`

### **GET /api/providers/:id/availability**
Disponibilité du prestataire
\`\`\`typescript
Response: {
  status: 'available'|'busy'|'offline'
  schedule: TimeSlot[]
  nextAvailable: string
}
\`\`\`

### **PUT /api/providers/:id/availability**
Mettre à jour la disponibilité
\`\`\`typescript
Body: {
  status: AvailabilityStatus
  schedule?: TimeSlot[]
}
Response: {
  success: boolean
  message: string
}
\`\`\`

---

## 📈 **4. ANALYTICS MODULE**

### **GET /api/analytics**
Données analytiques globales
\`\`\`typescript
Query: ?period=24h|7d|30d|90d|1y
Response: {
  stats: AnalyticsStats
  charts: {
    performance: ChartData
    services: ChartData
    geographic: ChartData
  }
  insights: Insight[]
  leaderboard: LeaderboardEntry[]
}
\`\`\`

### **GET /api/analytics/kpis**
Indicateurs clés de performance
\`\`\`typescript
Query: ?period=7d
Response: {
  successRate: number
  responseTime: number
  totalRequests: number
  satisfaction: number
  trends: {
    successRate: number
    responseTime: number
    totalRequests: number
    satisfaction: number
  }
}
\`\`\`

### **GET /api/analytics/performance**
Données de performance
\`\`\`typescript
Query: ?period=7d
Response: {
  labels: string[]
  successRate: number[]
  aiEfficiency: number[]
  satisfaction: number[]
}
\`\`\`

### **GET /api/analytics/services**
Répartition par services
\`\`\`typescript
Query: ?period=7d
Response: {
  labels: string[]
  data: number[]
}
\`\`\`

### **GET /api/analytics/geographic**
Répartition géographique
\`\`\`typescript
Query: ?period=7d
Response: {
  labels: string[]
  data: number[]
}
\`\`\`

### **GET /api/analytics/insights**
Insights IA
\`\`\`typescript
Response: Insight[]
\`\`\`

### **GET /api/analytics/leaderboard**
Classement des prestataires
\`\`\`typescript
Response: LeaderboardEntry[]
\`\`\`

### **GET /api/analytics/reports**
Rapports personnalisés
\`\`\`typescript
Query: {
  type: 'daily'|'weekly'|'monthly'
  format: 'json'|'pdf'|'excel'
  dateFrom: string
  dateTo: string
}
Response: ReportData | File
\`\`\`

### **POST /api/analytics/export**
Exporter les données
\`\`\`typescript
Body: {
  type: 'requests'|'providers'|'analytics'
  format: 'csv'|'excel'|'pdf'
  filters: FilterOptions
}
Response: {
  downloadUrl: string
  expiresAt: string
}
\`\`\`

---

## ⚙️ **5. SETTINGS MODULE**

### **5.1 General Settings**

#### **GET /api/settings/general**
\`\`\`typescript
Response: {
  appName: string
  timezone: string
  language: string
  currency: string
  dateFormat: string
  notifications: NotificationSettings
}
\`\`\`

#### **POST /api/settings/general**
\`\`\`typescript
Body: GeneralSettings
Response: {
  success: boolean
  message: string
}
\`\`\`

### **5.2 AI Settings**

#### **GET /api/settings/ai**
\`\`\`typescript
Response: {
  matching: MatchingSettings
  optimization: OptimizationSettings
  learning: LearningSettings
}
\`\`\`

#### **POST /api/settings/ai**
\`\`\`typescript
Body: AISettings
Response: {
  success: boolean
  message: string
}
\`\`\`

#### **POST /api/settings/ai/test**
\`\`\`typescript
Body: {
  algorithm: string
  parameters: object
}
Response: {
  success: boolean
  results: TestResults
}
\`\`\`

### **5.3 Provider Settings**

#### **GET /api/settings/providers**
\`\`\`typescript
Response: {
  validation: ValidationRules
  performance: PerformanceSettings
  payments: PaymentSettings
}
\`\`\`

#### **POST /api/settings/providers**
\`\`\`typescript
Body: ProviderSettings
Response: {
  success: boolean
  message: string
}
\`\`\`

### **5.4 WhatsApp Settings**

#### **GET /api/settings/whatsapp**
\`\`\`typescript
Response: {
  webhook: WebhookConfig
  templates: MessageTemplate[]
  automation: AutomationRules
}
\`\`\`

#### **POST /api/settings/whatsapp**
\`\`\`typescript
Body: WhatsAppSettings
Response: {
  success: boolean
  message: string
}
\`\`\`

#### **POST /api/settings/whatsapp/test**
\`\`\`typescript
Response: {
  success: boolean
  message: string
  details: TestDetails
}
\`\`\`

### **5.5 Security Settings**

#### **GET /api/settings/security**
\`\`\`typescript
Response: {
  authentication: AuthSettings
  encryption: EncryptionSettings
  audit: AuditSettings
  compliance: ComplianceSettings
}
\`\`\`

#### **POST /api/settings/security**
\`\`\`typescript
Body: SecuritySettings
Response: {
  success: boolean
  message: string
}
\`\`\`

### **5.6 Performance Settings**

#### **GET /api/settings/performance**
\`\`\`typescript
Response: {
  caching: CacheSettings
  database: DatabaseSettings
  monitoring: MonitoringSettings
}
\`\`\`

#### **POST /api/settings/performance**
\`\`\`typescript
Body: PerformanceSettings
Response: {
  success: boolean
  message: string
}
\`\`\`

### **5.7 Request Settings**

#### **GET /api/settings/requests**
\`\`\`typescript
Response: {
  automaticProcessing: AutoProcessingSettings
  matchingAlgorithm: MatchingSettings
  timeouts: TimeoutSettings
  statuses: StatusSettings
}
\`\`\`

#### **POST /api/settings/requests**
\`\`\`typescript
Body: RequestSettings
Response: {
  success: boolean
  message: string
}
\`\`\`

#### **POST /api/settings/requests/test-matching**
\`\`\`typescript
Body: MatchingAlgorithmSettings
Response: {
  providersCount: number
  executionTime: number
  averageScore: number
  topProviders: ProviderMatch[]
}
\`\`\`

### **5.8 Notification Settings**

#### **GET /api/settings/notifications**
\`\`\`typescript
Response: {
  pushNotifications: PushSettings
  emailNotifications: EmailSettings
  smsNotifications: SMSSettings
  notificationRules: NotificationRules
  templates: MessageTemplates
}
\`\`\`

#### **POST /api/settings/notifications**
\`\`\`typescript
Body: NotificationSettings
Response: {
  success: boolean
  message: string
}
\`\`\`

#### **POST /api/settings/notifications/test**
\`\`\`typescript
Body: {
  type: 'push'|'email'|'sms'
  settings: object
}
Response: {
  success: boolean
  message: string
  details: TestDetails
}
\`\`\`

### **5.9 Admin Settings**

#### **GET /api/settings/admin**
\`\`\`typescript
Response: {
  users: UserManagement
  roles: RoleSettings
  permissions: PermissionSettings
  debug: DebugSettings
  mobile: MobileSettings
}
\`\`\`

#### **POST /api/settings/admin**
\`\`\`typescript
Body: AdminSettings
Response: {
  success: boolean
  message: string
}
\`\`\`

### **5.10 Maintenance Settings**

#### **GET /api/settings/maintenance**
\`\`\`typescript
Response: {
  schedule: MaintenanceSchedule
  deployment: DeploymentSettings
  environments: EnvironmentSettings
}
\`\`\`

#### **POST /api/settings/maintenance**
\`\`\`typescript
Body: MaintenanceSettings
Response: {
  success: boolean
  message: string
}
\`\`\`

### **5.11 Business Settings**

#### **GET /api/settings/business**
\`\`\`typescript
Response: {
  services: ServiceSettings
  scheduling: SchedulingSettings
  billing: BillingSettings
}
\`\`\`

#### **POST /api/settings/business**
\`\`\`typescript
Body: BusinessSettings
Response: {
  success: boolean
  message: string
}
\`\`\`

---

## 🔔 **6. NOTIFICATIONS MODULE**

### **GET /api/notifications**
Liste des notifications
\`\`\`typescript
Query: {
  type?: 'info'|'warning'|'error'|'success'
  read?: boolean
  page?: number
  limit?: number
}
Response: {
  notifications: Notification[]
  pagination: PaginationInfo
  unreadCount: number
}
\`\`\`

### **POST /api/notifications**
Créer une notification
\`\`\`typescript
Body: {
  title: string
  message: string
  type: NotificationType
  recipients: string[]
  channels: ('push'|'email'|'sms')[]
}
Response: {
  success: boolean
  notificationId: string
}
\`\`\`

### **PUT /api/notifications/:id/read**
Marquer comme lue
\`\`\`typescript
Response: {
  success: boolean
  message: string
}
\`\`\`

### **DELETE /api/notifications/:id**
Supprimer une notification
\`\`\`typescript
Response: {
  success: boolean
  message: string
}
\`\`\`

---

## 👤 **7. USER MANAGEMENT MODULE**

### **GET /api/users**
Liste des utilisateurs
\`\`\`typescript
Query: {
  role?: string
  status?: 'active'|'inactive'
  page?: number
  limit?: number
}
Response: {
  users: User[]
  pagination: PaginationInfo
}
\`\`\`

### **POST /api/users**
Créer un utilisateur
\`\`\`typescript
Body: {
  name: string
  email: string
  role: string
  permissions: string[]
}
Response: {
  success: boolean
  userId: string
  temporaryPassword: string
}
\`\`\`

### **PUT /api/users/:id**
Mettre à jour un utilisateur
\`\`\`typescript
Body: Partial<User>
Response: {
  success: boolean
  message: string
}
\`\`\`

### **DELETE /api/users/:id**
Supprimer un utilisateur
\`\`\`typescript
Response: {
  success: boolean
  message: string
}
\`\`\`

---

## 🔐 **8. AUTHENTICATION MODULE**

### **POST /api/auth/login**
Connexion
\`\`\`typescript
Body: {
  email: string
  password: string
  rememberMe?: boolean
}
Response: {
  success: boolean
  token: string
  refreshToken: string
  user: UserInfo
  expiresAt: string
}
\`\`\`

### **POST /api/auth/logout**
Déconnexion
\`\`\`typescript
Response: {
  success: boolean
  message: string
}
\`\`\`

### **POST /api/auth/refresh**
Renouveler le token
\`\`\`typescript
Body: {
  refreshToken: string
}
Response: {
  success: boolean
  token: string
  expiresAt: string
}
\`\`\`

### **POST /api/auth/forgot-password**
Mot de passe oublié
\`\`\`typescript
Body: {
  email: string
}
Response: {
  success: boolean
  message: string
}
\`\`\`

### **POST /api/auth/reset-password**
Réinitialiser le mot de passe
\`\`\`typescript
Body: {
  token: string
  newPassword: string
}
Response: {
  success: boolean
  message: string
}
\`\`\`

---

## 📱 **9. WHATSAPP INTEGRATION MODULE**

### **POST /api/whatsapp/webhook**
Webhook WhatsApp
\`\`\`typescript
Body: WhatsAppWebhookPayload
Response: {
  success: boolean
}
\`\`\`

### **POST /api/whatsapp/send**
Envoyer un message
\`\`\`typescript
Body: {
  to: string
  message: string
  template?: string
  variables?: object
}
Response: {
  success: boolean
  messageId: string
}
\`\`\`

### **GET /api/whatsapp/templates**
Templates de messages
\`\`\`typescript
Response: {
  templates: MessageTemplate[]
}
\`\`\`

### **POST /api/whatsapp/templates**
Créer un template
\`\`\`typescript
Body: {
  name: string
  content: string
  variables: string[]
  category: string
}
Response: {
  success: boolean
  templateId: string
}
\`\`\`

---

## 💳 **10. PAYMENTS MODULE**

### **GET /api/payments**
Liste des paiements
\`\`\`typescript
Query: {
  status?: 'pending'|'completed'|'failed'
  method?: 'mobile_money'|'cash'|'bank'
  dateFrom?: string
  dateTo?: string
  page?: number
  limit?: number
}
Response: {
  payments: Payment[]
  pagination: PaginationInfo
  stats: PaymentStats
}
\`\`\`

### **POST /api/payments**
Créer un paiement
\`\`\`typescript
Body: {
  requestId: string
  amount: number
  method: PaymentMethod
  providerId: string
}
Response: {
  success: boolean
  paymentId: string
  paymentUrl?: string
}
\`\`\`

### **GET /api/payments/:id**
Détails d'un paiement
\`\`\`typescript
Response: {
  id: string
  amount: number
  status: PaymentStatus
  method: PaymentMethod
  transaction: TransactionInfo
  request: RequestInfo
}
\`\`\`

---

## 🔍 **11. SEARCH MODULE**

### **GET /api/search**
Recherche globale
\`\`\`typescript
Query: {
  q: string
  type?: 'requests'|'providers'|'all'
  limit?: number
}
Response: {
  requests: SearchResult[]
  providers: SearchResult[]
  total: number
}
\`\`\`

### **GET /api/search/suggestions**
Suggestions de recherche
\`\`\`typescript
Query: {
  q: string
  type?: string
}
Response: {
  suggestions: string[]
}
\`\`\`

---

## 📊 **12. REPORTS MODULE**

### **GET /api/reports**
Liste des rapports
\`\`\`typescript
Response: {
  reports: ReportInfo[]
}
\`\`\`

### **POST /api/reports/generate**
Générer un rapport
\`\`\`typescript
Body: {
  type: ReportType
  period: string
  format: 'pdf'|'excel'|'csv'
  filters: ReportFilters
}
Response: {
  success: boolean
  reportId: string
  downloadUrl: string
}
\`\`\`

### **GET /api/reports/:id**
Télécharger un rapport
\`\`\`typescript
Response: File
\`\`\`

---

## 🚨 **Error Responses**

Tous les endpoints peuvent retourner ces erreurs :

\`\`\`typescript
// 400 Bad Request
{
  error: "VALIDATION_ERROR"
  message: "Données invalides"
  details: ValidationError[]
}

// 401 Unauthorized
{
  error: "UNAUTHORIZED"
  message: "Token invalide ou expiré"
}

// 403 Forbidden
{
  error: "FORBIDDEN"
  message: "Permissions insuffisantes"
}

// 404 Not Found
{
  error: "NOT_FOUND"
  message: "Ressource introuvable"
}

// 429 Too Many Requests
{
  error: "RATE_LIMIT_EXCEEDED"
  message: "Trop de requêtes"
  retryAfter: number
}

// 500 Internal Server Error
{
  error: "INTERNAL_ERROR"
  message: "Erreur serveur interne"
  requestId: string
}
\`\`\`

---

## 🔒 **Rate Limiting**

| Endpoint Category | Limite | Fenêtre |
|------------------|--------|---------|
| Authentication | 5 req/min | Par IP |
| Dashboard | 60 req/min | Par utilisateur |
| CRUD Operations | 100 req/min | Par utilisateur |
| Analytics | 30 req/min | Par utilisateur |
| Settings | 20 req/min | Par utilisateur |
| WhatsApp Webhook | 1000 req/min | Global |

---

## 📝 **Request/Response Headers**

### **Required Headers**
\`\`\`
Authorization: Bearer <jwt_token>
Content-Type: application/json
X-API-Version: v1
\`\`\`

### **Optional Headers**
\`\`\`
X-Request-ID: <unique_id>
X-Client-Version: <version>
Accept-Language: fr-FR
\`\`\`

### **Response Headers**
\`\`\`
X-Request-ID: <request_id>
X-Rate-Limit-Remaining: <count>
X-Rate-Limit-Reset: <timestamp>
