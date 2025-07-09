#!/bin/bash

# Script de sauvegarde pour Djobea AI
# Sauvegarde la base de données et les fichiers importants

set -e

# Configuration
BACKUP_DIR="/app/backups"
DB_BACKUP_DIR="$BACKUP_DIR/database"
FILES_BACKUP_DIR="$BACKUP_DIR/files"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=7

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Créer les répertoires de sauvegarde
create_backup_dirs() {
    log_info "Création des répertoires de sauvegarde..."
    mkdir -p "$DB_BACKUP_DIR"
    mkdir -p "$FILES_BACKUP_DIR"
}

# Sauvegarder la base de données
backup_database() {
    log_info "Sauvegarde de la base de données..."
    
    BACKUP_FILE="$DB_BACKUP_DIR/djobea_db_$TIMESTAMP.sql"
    
    if docker-compose exec -T postgres pg_dump -U djobea_user -d djobea_ai > "$BACKUP_FILE"; then
        log_info "Base de données sauvegardée dans $BACKUP_FILE"
        
        # Compresser la sauvegarde
        gzip "$BACKUP_FILE"
        log_info "Sauvegarde compressée: $BACKUP_FILE.gz"
    else
        log_error "Erreur lors de la sauvegarde de la base de données"
        exit 1
    fi
}

# Sauvegarder les fichiers importants
backup_files() {
    log_info "Sauvegarde des fichiers importants..."
    
    BACKUP_FILE="$FILES_BACKUP_DIR/djobea_files_$TIMESTAMP.tar.gz"
    
    # Sauvegarder les logs, uploads et configurations
    tar -czf "$BACKUP_FILE" \
        --exclude='*.pyc' \
        --exclude='__pycache__' \
        --exclude='*.tmp' \
        logs/ \
        static/uploads/ \
        .env \
        docker-compose.yml \
        2>/dev/null || true
    
    log_info "Fichiers sauvegardés dans $BACKUP_FILE"
}

# Nettoyer les anciennes sauvegardes
cleanup_old_backups() {
    log_info "Nettoyage des anciennes sauvegardes (> $RETENTION_DAYS jours)..."
    
    # Nettoyer les sauvegardes de base de données
    find "$DB_BACKUP_DIR" -name "*.sql.gz" -mtime +$RETENTION_DAYS -delete 2>/dev/null || true
    
    # Nettoyer les sauvegardes de fichiers
    find "$FILES_BACKUP_DIR" -name "*.tar.gz" -mtime +$RETENTION_DAYS -delete 2>/dev/null || true
    
    log_info "Nettoyage terminé"
}

# Fonction principale
main() {
    log_info "Démarrage de la sauvegarde de Djobea AI..."
    
    create_backup_dirs
    backup_database
    backup_files
    cleanup_old_backups
    
    log_info "Sauvegarde terminée avec succès!"
    log_info "Sauvegardes disponibles dans $BACKUP_DIR"
}

# Gestion des signaux
trap 'log_error "Sauvegarde interrompue"; exit 1' INT TERM

# Exécuter le script
main "$@"