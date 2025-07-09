#!/bin/bash

# Djobea AI - Script de déploiement Docker complet
# Ce script automatise le déploiement complet de l'application

set -e  # Exit on any error

# Configuration
PROJECT_NAME="djobea-ai"
BACKUP_DIR="./backups"
DOCKER_COMPOSE_FILE="docker-compose.yml"
ENV_FILE=".env"

# Couleurs pour les messages
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Fonction pour afficher les messages
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Fonction pour vérifier les prérequis
check_prerequisites() {
    log_info "Vérification des prérequis..."
    
    # Vérifier Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker n'est pas installé. Veuillez installer Docker."
        exit 1
    fi
    
    # Vérifier Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose n'est pas installé. Veuillez installer Docker Compose."
        exit 1
    fi
    
    # Vérifier le fichier .env
    if [ ! -f "$ENV_FILE" ]; then
        log_warning "Fichier .env introuvable. Copie du fichier .env.example..."
        cp .env.example .env
        log_warning "Veuillez configurer le fichier .env avec vos clés API avant de continuer."
        log_warning "Éditez le fichier .env et relancez le script."
        exit 1
    fi
    
    log_success "Prérequis vérifiés avec succès."
}

# Fonction pour créer les répertoires nécessaires
create_directories() {
    log_info "Création des répertoires nécessaires..."
    
    mkdir -p logs
    mkdir -p static/uploads
    mkdir -p data
    mkdir -p docker/nginx/ssl
    mkdir -p $BACKUP_DIR
    
    log_success "Répertoires créés avec succès."
}

# Fonction pour générer les certificats SSL auto-signés
generate_ssl_certificates() {
    log_info "Génération des certificats SSL..."
    
    if [ ! -f "docker/nginx/ssl/cert.pem" ] || [ ! -f "docker/nginx/ssl/key.pem" ]; then
        log_info "Génération de certificats SSL auto-signés..."
        
        openssl req -x509 -newkey rsa:4096 -keyout docker/nginx/ssl/key.pem -out docker/nginx/ssl/cert.pem -days 365 -nodes -subj "/C=CM/ST=Littoral/L=Douala/O=Djobea AI/CN=localhost"
        
        log_success "Certificats SSL générés avec succès."
    else
        log_info "Certificats SSL déjà présents."
    fi
}

# Fonction pour sauvegarder la base de données
backup_database() {
    log_info "Sauvegarde de la base de données..."
    
    if docker-compose ps | grep -q "djobea-postgres"; then
        BACKUP_FILE="$BACKUP_DIR/db_backup_$(date +%Y%m%d_%H%M%S).sql"
        
        docker-compose exec -T postgres pg_dump -U djobea_user -d djobea_ai > "$BACKUP_FILE"
        
        log_success "Base de données sauvegardée dans $BACKUP_FILE"
    else
        log_info "Base de données non trouvée, pas de sauvegarde nécessaire."
    fi
}

# Fonction pour construire les images Docker
build_images() {
    log_info "Construction des images Docker..."
    
    docker-compose build --no-cache
    
    log_success "Images Docker construites avec succès."
}

# Fonction pour démarrer les services
start_services() {
    log_info "Démarrage des services..."
    
    docker-compose up -d
    
    log_success "Services démarrés avec succès."
}

# Fonction pour attendre que les services soient prêts
wait_for_services() {
    log_info "Attente de la disponibilité des services..."
    
    # Attendre PostgreSQL
    log_info "Attente de PostgreSQL..."
    while ! docker-compose exec postgres pg_isready -U djobea_user -d djobea_ai &> /dev/null; do
        sleep 2
    done
    
    # Attendre Redis
    log_info "Attente de Redis..."
    while ! docker-compose exec redis redis-cli ping &> /dev/null; do
        sleep 2
    done
    
    # Attendre l'application
    log_info "Attente de l'application..."
    while ! curl -f http://localhost:5000/health &> /dev/null; do
        sleep 5
    done
    
    log_success "Tous les services sont prêts."
}

# Fonction pour afficher le statut
show_status() {
    log_info "Statut des services:"
    docker-compose ps
    
    log_info "Logs récents:"
    docker-compose logs --tail=20
}

# Fonction pour nettoyer les ressources
cleanup() {
    log_info "Nettoyage des ressources Docker..."
    
    # Nettoyer les images non utilisées
    docker image prune -f
    
    # Nettoyer les volumes non utilisés
    docker volume prune -f
    
    log_success "Nettoyage terminé."
}

# Fonction pour arrêter les services
stop_services() {
    log_info "Arrêt des services..."
    
    docker-compose down
    
    log_success "Services arrêtés."
}

# Fonction pour redémarrer les services
restart_services() {
    log_info "Redémarrage des services..."
    
    stop_services
    start_services
    wait_for_services
    
    log_success "Services redémarrés avec succès."
}

# Fonction pour afficher l'aide
show_help() {
    echo "Usage: $0 [OPTION]"
    echo ""
    echo "Options:"
    echo "  deploy      Déploiement complet (par défaut)"
    echo "  start       Démarrer les services"
    echo "  stop        Arrêter les services"
    echo "  restart     Redémarrer les services"
    echo "  status      Afficher le statut des services"
    echo "  backup      Sauvegarder la base de données"
    echo "  cleanup     Nettoyer les ressources Docker"
    echo "  logs        Afficher les logs"
    echo "  help        Afficher cette aide"
    echo ""
}

# Fonction pour afficher les logs
show_logs() {
    log_info "Logs des services:"
    docker-compose logs -f
}

# Fonction de déploiement complet
deploy() {
    log_info "Démarrage du déploiement de Djobea AI..."
    
    check_prerequisites
    create_directories
    generate_ssl_certificates
    backup_database
    build_images
    start_services
    wait_for_services
    show_status
    
    log_success "Déploiement terminé avec succès!"
    log_info "Application disponible sur:"
    log_info "  - HTTP:  http://localhost"
    log_info "  - HTTPS: https://localhost"
    log_info "  - API:   http://localhost:5000"
    log_info "  - Admin: http://localhost:5000/admin"
}

# Script principal
main() {
    case "${1:-deploy}" in
        deploy)
            deploy
            ;;
        start)
            start_services
            wait_for_services
            ;;
        stop)
            stop_services
            ;;
        restart)
            restart_services
            ;;
        status)
            show_status
            ;;
        backup)
            backup_database
            ;;
        cleanup)
            cleanup
            ;;
        logs)
            show_logs
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
trap 'log_error "Déploiement interrompu par l\'utilisateur"; exit 1' INT TERM

# Exécuter le script principal
main "$@"