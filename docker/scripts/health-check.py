#!/usr/bin/env python3
"""
Script de vérification de santé pour Djobea AI
Utilisé par Docker pour vérifier que l'application fonctionne correctement
"""

import os
import sys
import requests
import json
from typing import Dict, Any

# Configuration
HEALTH_CHECK_URL = "http://localhost:5000/health"
TIMEOUT = 10


def check_health_endpoint() -> Dict[str, Any]:
    """Vérifier l'endpoint de santé"""
    try:
        response = requests.get(HEALTH_CHECK_URL, timeout=TIMEOUT)
        
        if response.status_code == 200:
            return {
                "status": "healthy",
                "details": response.json()
            }
        else:
            return {
                "status": "unhealthy",
                "error": f"HTTP {response.status_code}",
                "details": response.text
            }
            
    except requests.exceptions.RequestException as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


def check_database_connection() -> Dict[str, Any]:
    """Vérifier la connexion à la base de données via l'API"""
    try:
        # Essayer d'accéder à un endpoint qui nécessite la base de données
        response = requests.get(f"{HEALTH_CHECK_URL}/db", timeout=TIMEOUT)
        
        if response.status_code == 200:
            return {
                "status": "healthy",
                "details": "Database connection OK"
            }
        else:
            return {
                "status": "unhealthy",
                "error": f"Database check failed: HTTP {response.status_code}"
            }
            
    except requests.exceptions.RequestException as e:
        return {
            "status": "unhealthy",
            "error": f"Database check failed: {str(e)}"
        }


def check_essential_services() -> Dict[str, Any]:
    """Vérifier les services essentiels"""
    checks = {
        "health_endpoint": check_health_endpoint(),
        "database": check_database_connection()
    }
    
    # Déterminer le statut global
    overall_status = "healthy"
    for check_name, check_result in checks.items():
        if check_result["status"] != "healthy":
            overall_status = "unhealthy"
            break
    
    return {
        "overall_status": overall_status,
        "checks": checks
    }


def main():
    """Fonction principale"""
    print("Vérification de la santé de Djobea AI...")
    
    # Exécuter les vérifications
    health_status = check_essential_services()
    
    # Afficher les résultats
    print(json.dumps(health_status, indent=2))
    
    # Retourner le code de sortie approprié
    if health_status["overall_status"] == "healthy":
        print("✅ Application en bonne santé")
        sys.exit(0)
    else:
        print("❌ Application en mauvaise santé")
        sys.exit(1)


if __name__ == "__main__":
    main()