#!/bin/bash

# Script de monitoring pour Djobea AI
# Surveille la santé des services et envoie des alertes

set -e

# Configuration
MONITORING_INTERVAL=60  # Intervalle de vérification en secondes
LOG_FILE="/app/logs/monitoring.log"
ALERT_EMAIL=""  # Email pour les alertes (optionnel)
WEBHOOK_URL=""  # URL webhook pour les notifications (optionnel)

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    local message="[$(date '+%Y-%m-%d %H:%M:%S')] [INFO] $1"
    echo -e "${GREEN}$message${NC}"
    echo "$message" >> "$LOG_FILE"
}

log_warning() {
    local message="[$(date '+%Y-%m-%d %H:%M:%S')] [WARNING] $1"
    echo -e "${YELLOW}$message${NC}"
    echo "$message" >> "$LOG_FILE"
}

log_error() {
    local message="[$(date '+%Y-%m-%d %H:%M:%S')] [ERROR] $1"
    echo -e "${RED}$message${NC}"
    echo "$message" >> "$LOG_FILE"
}

# Vérifier la santé d'un service
check_service_health() {
    local service_name="$1"
    local health_check_command="$2"
    
    if eval "$health_check_command" &>/dev/null; then
        log_info "Service $service_name: OK"
        return 0
    else
        log_error "Service $service_name: FAILED"
        return 1
    fi
}

# Vérifier tous les services
check_all_services() {
    local all_healthy=true
    
    # Vérifier PostgreSQL
    if ! check_service_health "PostgreSQL" "docker-compose exec postgres pg_isready -U djobea_user -d djobea_ai"; then
        all_healthy=false
    fi
    
    # Vérifier Redis
    if ! check_service_health "Redis" "docker-compose exec redis redis-cli ping"; then
        all_healthy=false
    fi
    
    # Vérifier l'application
    if ! check_service_health "Djobea AI App" "curl -f http://localhost:5000/health"; then
        all_healthy=false
    fi
    
    # Vérifier Nginx
    if ! check_service_health "Nginx" "curl -f http://localhost:80/health"; then
        all_healthy=false
    fi
    
    return $all_healthy
}

# Vérifier les métriques système
check_system_metrics() {
    # Vérifier l'utilisation du disque
    local disk_usage=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
    if [ "$disk_usage" -gt 80 ]; then
        log_warning "Utilisation du disque élevée: ${disk_usage}%"
    fi
    
    # Vérifier l'utilisation de la mémoire
    local memory_usage=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100.0}')
    if [ "$memory_usage" -gt 80 ]; then
        log_warning "Utilisation de la mémoire élevée: ${memory_usage}%"
    fi
    
    # Vérifier les conteneurs Docker
    local containers_status=$(docker-compose ps --format "table {{.Name}}\t{{.Status}}" | grep -v "Up" | wc -l)
    if [ "$containers_status" -gt 1 ]; then  # 1 pour l'en-tête
        log_warning "Certains conteneurs ne sont pas en cours d'exécution"
    fi
}

# Envoyer une notification
send_notification() {
    local message="$1"
    local severity="$2"
    
    # Notification par email (si configuré)
    if [ -n "$ALERT_EMAIL" ]; then
        echo "$message" | mail -s "Djobea AI Alert - $severity" "$ALERT_EMAIL"
    fi
    
    # Notification par webhook (si configuré)
    if [ -n "$WEBHOOK_URL" ]; then
        curl -X POST "$WEBHOOK_URL" \
            -H "Content-Type: application/json" \
            -d "{\"text\":\"$message\",\"severity\":\"$severity\"}"
    fi
}

# Redémarrer les services en cas de problème
restart_failed_services() {
    log_info "Tentative de redémarrage des services..."
    
    # Redémarrer les services
    docker-compose restart
    
    # Attendre que les services redémarrent
    sleep 30
    
    # Vérifier à nouveau
    if check_all_services; then
        log_info "Services redémarrés avec succès"
        send_notification "Services Djobea AI redémarrés avec succès" "INFO"
    else
        log_error "Échec du redémarrage des services"
        send_notification "Échec du redémarrage des services Djobea AI" "CRITICAL"
    fi
}

# Fonction principale de monitoring
monitoring_loop() {
    log_info "Démarrage du monitoring de Djobea AI..."
    
    while true; do
        log_info "Vérification de la santé des services..."
        
        if check_all_services; then
            log_info "Tous les services sont en bonne santé"
            check_system_metrics
        else
            log_error "Certains services sont en panne"
            send_notification "Services Djobea AI en panne détectés" "WARNING"
            restart_failed_services
        fi
        
        log_info "Prochaine vérification dans $MONITORING_INTERVAL secondes"
        sleep "$MONITORING_INTERVAL"
    done
}

# Afficher le statut actuel
show_status() {
    echo "=== Statut des services Djobea AI ==="
    check_all_services
    echo ""
    echo "=== Métriques système ==="
    check_system_metrics
    echo ""
    echo "=== Statut des conteneurs ==="
    docker-compose ps
}

# Afficher l'aide
show_help() {
    echo "Usage: $0 [OPTION]"
    echo ""
    echo "Options:"
    echo "  monitor     Démarrer le monitoring en continu (par défaut)"
    echo "  status      Afficher le statut actuel"
    echo "  check       Vérifier une seule fois"
    echo "  help        Afficher cette aide"
    echo ""
    echo "Variables d'environnement:"
    echo "  MONITORING_INTERVAL   Intervalle de vérification en secondes (défaut: 60)"
    echo "  ALERT_EMAIL          Email pour les alertes"
    echo "  WEBHOOK_URL          URL webhook pour les notifications"
    echo ""
}

# Fonction principale
main() {
    # Créer le répertoire de logs
    mkdir -p "$(dirname "$LOG_FILE")"
    
    case "${1:-monitor}" in
        monitor)
            monitoring_loop
            ;;
        status)
            show_status
            ;;
        check)
            check_all_services
            check_system_metrics
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            log_error "Option invalide: $1"
            show_help
            exit 1
            ;;
    esac
}

# Gestion des signaux
trap 'log_info "Monitoring arrêté"; exit 0' INT TERM

# Exécuter le script
main "$@"