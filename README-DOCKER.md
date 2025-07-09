# Djobea AI - Déploiement Docker

Ce document décrit comment déployer Djobea AI avec Docker et Docker Compose.

## 🚀 Déploiement Rapide

### 1. Prérequis

- Docker (version 20.10 ou supérieure)
- Docker Compose (version 2.0 ou supérieure)
- Git

### 2. Installation

```bash
# Cloner le repository
git clone <repository-url>
cd djobea-ai

# Copier et configurer les variables d'environnement
cp .env.example .env

# Éditer le fichier .env avec vos clés API
nano .env
```

### 3. Configuration des variables d'environnement

Éditez le fichier `.env` et configurez les variables suivantes :

```bash
# API Keys - OBLIGATOIRES
ANTHROPIC_API_KEY=your_anthropic_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here

# Twilio Configuration - OBLIGATOIRE
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_PHONE_NUMBER=your_twilio_whatsapp_number

# Base de données (optionnel - des valeurs par défaut sont utilisées)
POSTGRES_PASSWORD=your_secure_password
REDIS_PASSWORD=your_redis_password
```

### 4. Déploiement

```bash
# Rendre le script exécutable
chmod +x deploy.sh

# Déployer l'application
./deploy.sh deploy
```

## 📋 Commandes Disponibles

### Script de déploiement principal

```bash
./deploy.sh [OPTION]

Options:
  deploy      Déploiement complet (par défaut)
  start       Démarrer les services
  stop        Arrêter les services
  restart     Redémarrer les services
  status      Afficher le statut des services
  backup      Sauvegarder la base de données
  cleanup     Nettoyer les ressources Docker
  logs        Afficher les logs
  help        Afficher l'aide
```

### Docker Compose

```bash
# Démarrer tous les services
docker-compose up -d

# Arrêter tous les services
docker-compose down

# Voir les logs
docker-compose logs -f

# Voir le statut
docker-compose ps

# Redémarrer un service spécifique
docker-compose restart djobea-ai
```

## 🏗️ Architecture

Le déploiement Docker inclut les services suivants :

- **PostgreSQL** : Base de données principale
- **Redis** : Cache et sessions
- **Djobea AI App** : Application FastAPI
- **Nginx** : Proxy inverse avec SSL

## 🔧 Services

### PostgreSQL
- **Port** : 5432
- **Base de données** : djobea_ai
- **Utilisateur** : djobea_user
- **Volume** : `postgres_data`

### Redis
- **Port** : 6379
- **Volume** : `redis_data`
- **Authentification** : Mot de passe configuré

### Application Djobea AI
- **Port** : 5000
- **Santé** : http://localhost:5000/health
- **Admin** : http://localhost:5000/admin

### Nginx
- **Port HTTP** : 80
- **Port HTTPS** : 443
- **SSL** : Certificats auto-signés (production : remplacer par des certificats valides)

## 🛠️ Maintenance

### Sauvegardes

```bash
# Sauvegarder la base de données
./deploy.sh backup

# Sauvegarder manuellement
chmod +x docker/scripts/backup.sh
./docker/scripts/backup.sh
```

### Restauration

```bash
# Voir les sauvegardes disponibles
chmod +x docker/scripts/restore.sh
./docker/scripts/restore.sh --list

# Restaurer une sauvegarde
./docker/scripts/restore.sh --database djobea_db_20240101_120000.sql.gz
```

### Monitoring

```bash
# Démarrer le monitoring
chmod +x docker/scripts/monitor.sh
./docker/scripts/monitor.sh monitor

# Vérifier le statut
./docker/scripts/monitor.sh status
```

## 🔐 Sécurité

### Certificats SSL

Le déploiement génère automatiquement des certificats SSL auto-signés. Pour la production :

1. Obtenez des certificats SSL valides
2. Placez-les dans `docker/nginx/ssl/`
3. Redémarrez Nginx : `docker-compose restart nginx`

### Pare-feu

Configurez votre pare-feu pour autoriser uniquement les ports nécessaires :

```bash
# Autoriser HTTP et HTTPS
sudo ufw allow 80
sudo ufw allow 443

# Optionnel : autoriser l'accès direct à l'application (développement)
sudo ufw allow 5000
```

## 📊 Monitoring et Logs

### Logs

```bash
# Logs de tous les services
docker-compose logs -f

# Logs d'un service spécifique
docker-compose logs -f djobea-ai

# Logs avec timestamp
docker-compose logs -f -t

# Dernières 100 lignes
docker-compose logs --tail=100
```

### Santé des services

```bash
# Vérifier la santé de l'application
curl http://localhost:5000/health

# Vérifier la santé de la base de données
docker-compose exec postgres pg_isready -U djobea_user -d djobea_ai

# Vérifier Redis
docker-compose exec redis redis-cli ping
```

## 🚨 Dépannage

### Problèmes courants

**1. Erreur de connexion à la base de données**
```bash
# Vérifier que PostgreSQL est démarré
docker-compose ps postgres

# Redémarrer PostgreSQL
docker-compose restart postgres
```

**2. Problème de permissions**
```bash
# Corriger les permissions
sudo chown -R $USER:$USER logs/
sudo chown -R $USER:$USER static/uploads/
```

**3. Ports déjà utilisés**
```bash
# Vérifier les ports utilisés
sudo netstat -tlnp | grep :5000

# Arrêter les processus conflictuels
sudo kill -9 <PID>
```

**4. Problème de mémoire**
```bash
# Vérifier l'utilisation mémoire
docker stats

# Nettoyer les ressources inutilisées
docker system prune -a
```

### Logs de débogage

```bash
# Activer les logs de débogage
echo "DEBUG=true" >> .env
echo "LOG_LEVEL=DEBUG" >> .env

# Redémarrer l'application
docker-compose restart djobea-ai
```

## 🔄 Mise à jour

```bash
# Arrêter l'application
./deploy.sh stop

# Sauvegarder
./deploy.sh backup

# Mettre à jour le code
git pull origin main

# Reconstruire et redémarrer
./deploy.sh deploy
```

## 📞 Support

Pour obtenir de l'aide :

1. Consultez les logs : `docker-compose logs -f`
2. Vérifiez le statut : `./deploy.sh status`
3. Consultez la documentation dans le répertoire `docs/`

## 🌐 Accès à l'application

Après le déploiement, l'application est accessible via :

- **HTTP** : http://localhost
- **HTTPS** : https://localhost (certificat auto-signé)
- **API directe** : http://localhost:5000
- **Interface d'administration** : http://localhost:5000/admin
- **Monitoring** : http://localhost:5000/health

## 📝 Notes importantes

- Les certificats SSL générés sont auto-signés et ne doivent pas être utilisés en production
- Changez tous les mots de passe par défaut avant le déploiement en production
- Configurez des sauvegardes régulières pour la production
- Surveillez les logs et les métriques système
- Mettez à jour régulièrement les dépendances pour la sécurité