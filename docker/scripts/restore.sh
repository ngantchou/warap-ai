#!/bin/bash

# Script de restauration pour Djobea AI
# Restaure la base de données et les fichiers depuis une sauvegarde

set -e

# Configuration
BACKUP_DIR="/app/backups"
DB_BACKUP_DIR="$BACKUP_DIR/database"
FILES_BACKUP_DIR="$BACKUP_DIR/files"

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

# Afficher l'aide
show_help() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -d, --database BACKUP_FILE    Restaurer la base de données depuis le fichier spécifié"
    echo "  -f, --files BACKUP_FILE       Restaurer les fichiers depuis le fichier spécifié"
    echo "  -l, --list                    Lister les sauvegardes disponibles"
    echo "  -h, --help                    Afficher cette aide"
    echo ""
    echo "Exemples:"
    echo "  $0 --list                                    # Lister les sauvegardes"
    echo "  $0 --database djobea_db_20240101_120000.sql.gz  # Restaurer la DB"
    echo "  $0 --files djobea_files_20240101_120000.tar.gz  # Restaurer les fichiers"
}

# Lister les sauvegardes disponibles
list_backups() {
    log_info "Sauvegardes de base de données disponibles:"
    if [ -d "$DB_BACKUP_DIR" ]; then
        ls -la "$DB_BACKUP_DIR"/*.sql.gz 2>/dev/null || echo "Aucune sauvegarde de base de données trouvée"
    else
        echo "Répertoire de sauvegarde de base de données introuvable"
    fi
    
    echo ""
    log_info "Sauvegardes de fichiers disponibles:"
    if [ -d "$FILES_BACKUP_DIR" ]; then
        ls -la "$FILES_BACKUP_DIR"/*.tar.gz 2>/dev/null || echo "Aucune sauvegarde de fichiers trouvée"
    else
        echo "Répertoire de sauvegarde de fichiers introuvable"
    fi
}

# Restaurer la base de données
restore_database() {
    local backup_file="$1"
    
    if [ -z "$backup_file" ]; then
        log_error "Nom du fichier de sauvegarde requis"
        exit 1
    fi
    
    # Vérifier si le fichier existe
    if [ ! -f "$DB_BACKUP_DIR/$backup_file" ]; then
        log_error "Fichier de sauvegarde introuvable: $DB_BACKUP_DIR/$backup_file"
        exit 1
    fi
    
    log_warning "ATTENTION: Cette opération va remplacer la base de données actuelle!"
    read -p "Êtes-vous sûr de vouloir continuer? (y/N): " -n 1 -r
    echo
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Restauration annulée"
        exit 0
    fi
    
    log_info "Restauration de la base de données depuis $backup_file..."
    
    # Décompresser et restaurer
    if zcat "$DB_BACKUP_DIR/$backup_file" | docker-compose exec -T postgres psql -U djobea_user -d djobea_ai; then
        log_info "Base de données restaurée avec succès"
    else
        log_error "Erreur lors de la restauration de la base de données"
        exit 1
    fi
}

# Restaurer les fichiers
restore_files() {
    local backup_file="$1"
    
    if [ -z "$backup_file" ]; then
        log_error "Nom du fichier de sauvegarde requis"
        exit 1
    fi
    
    # Vérifier si le fichier existe
    if [ ! -f "$FILES_BACKUP_DIR/$backup_file" ]; then
        log_error "Fichier de sauvegarde introuvable: $FILES_BACKUP_DIR/$backup_file"
        exit 1
    fi
    
    log_warning "ATTENTION: Cette opération va remplacer les fichiers actuels!"
    read -p "Êtes-vous sûr de vouloir continuer? (y/N): " -n 1 -r
    echo
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Restauration annulée"
        exit 0
    fi
    
    log_info "Restauration des fichiers depuis $backup_file..."
    
    # Restaurer les fichiers
    if tar -xzf "$FILES_BACKUP_DIR/$backup_file" -C /; then
        log_info "Fichiers restaurés avec succès"
    else
        log_error "Erreur lors de la restauration des fichiers"
        exit 1
    fi
}

# Fonction principale
main() {
    if [ $# -eq 0 ]; then
        show_help
        exit 1
    fi
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            -d|--database)
                if [ -n "$2" ]; then
                    restore_database "$2"
                    shift 2
                else
                    log_error "Nom du fichier de sauvegarde requis pour --database"
                    exit 1
                fi
                ;;
            -f|--files)
                if [ -n "$2" ]; then
                    restore_files "$2"
                    shift 2
                else
                    log_error "Nom du fichier de sauvegarde requis pour --files"
                    exit 1
                fi
                ;;
            -l|--list)
                list_backups
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                log_error "Option inconnue: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

# Exécuter le script
main "$@"