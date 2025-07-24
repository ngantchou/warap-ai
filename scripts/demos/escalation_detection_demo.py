#!/usr/bin/env python3
"""
Démonstration Interactive du Système de Détection d'Escalation
Interface interactive pour tester le système d'escalation
"""
import requests
import json
from datetime import datetime
import time

BASE_URL = "http://localhost:5000"

class EscalationDemo:
    """Démonstration interactive du système d'escalation"""
    
    def __init__(self):
        self.session = requests.Session()
        self.user_id = "237691924172"
        self.session_id = f"demo_{int(time.time())}"
        
    def display_header(self):
        """Afficher l'en-tête de la démonstration"""
        print("="*80)
        print("🚀 DÉMONSTRATION DU SYSTÈME DE DÉTECTION D'ESCALATION")
        print("🤖 Djobea AI - Assistant Intelligent pour Services à Domicile")
        print("="*80)
        print()
        print("Ce système détecte automatiquement quand un utilisateur a besoin")
        print("d'être escaladé vers un agent humain basé sur:")
        print("  • Analyse de sentiment et frustration")
        print("  • Complexité technique du problème")
        print("  • Durée de la conversation")
        print("  • Échecs de compréhension répétés")
        print()
    
    def get_system_status(self):
        """Obtenir le statut du système"""
        try:
            response = self.session.get(f"{BASE_URL}/api/v1/escalation/health")
            result = response.json()
            
            if result.get('success'):
                print("📊 STATUT DU SYSTÈME:")
                print(f"   Status: {result.get('status', 'unknown')}")
                services = result.get('services', {})
                for service, status in services.items():
                    emoji = "✅" if status == "operational" else "❌"
                    print(f"   {emoji} {service}: {status}")
                print(f"   🎯 Détecteurs actifs: {result.get('active_detectors', 0)}")
                print()
                return True
            else:
                print(f"❌ Erreur système: {result.get('error')}")
                return False
                
        except Exception as e:
            print(f"❌ Impossible de connecter au système: {e}")
            return False
    
    def demo_complexity_analysis(self):
        """Démonstration de l'analyse de complexité"""
        print("🧠 DÉMONSTRATION: ANALYSE DE COMPLEXITÉ")
        print("-" * 50)
        
        test_messages = [
            {
                'message': "Bonjour, mon robinet fuit",
                'context': {'service_type': 'plomberie', 'zone': 'Bonamoussadi'},
                'description': "Message simple - problème basique"
            },
            {
                'message': "J'ai des problèmes électriques complexes avec mon tableau, les disjoncteurs sautent constamment",
                'context': {'service_type': 'électricité', 'zone': 'Bonamoussadi'},
                'description': "Message technique - problème électrique complexe"
            },
            {
                'message': "Je suis vraiment frustré ! Ça fait 2 heures que j'attends et personne ne répond correctement !",
                'context': {'service_type': 'électroménager', 'zone': 'Bonamoussadi', 'urgency_level': 'urgent'},
                'description': "Message émotionnel - frustration élevée"
            }
        ]
        
        for i, test in enumerate(test_messages, 1):
            print(f"\n{i}. {test['description']}")
            print(f"   Message: \"{test['message']}\"")
            
            try:
                data = {
                    'message': test['message'],
                    'conversation_history': [],
                    'context': {
                        **test['context'],
                        'user_id': self.user_id,
                        'session_id': f"{self.session_id}_{i}"
                    }
                }
                
                response = self.session.post(
                    f"{BASE_URL}/api/v1/escalation/complexity/analyze",
                    json=data
                )
                result = response.json()
                
                if result.get('success'):
                    complexity = result.get('complexity_score', 0.0)
                    escalation_prob = result.get('escalation_probability', 0.0)
                    predictions = result.get('predictions', {})
                    
                    # Affichage des résultats avec couleurs
                    complexity_level = self._get_complexity_level(complexity)
                    prob_level = self._get_probability_level(escalation_prob)
                    
                    print(f"   📊 Complexité: {complexity:.3f} ({complexity_level})")
                    print(f"   ⚠️  Prob. Escalation: {escalation_prob:.3f} ({prob_level})")
                    print(f"   🎯 Action suggérée: {predictions.get('suggested_action', 'N/A')}")
                    print(f"   ⏱️  Temps estimé: {predictions.get('predicted_resolution_time', 'N/A')} min")
                    
                else:
                    print(f"   ❌ Erreur: {result.get('error')}")
                    
            except Exception as e:
                print(f"   ❌ Erreur de connexion: {e}")
        
        print()
    
    def demo_escalation_detection(self):
        """Démonstration de la détection d'escalation"""
        print("🚨 DÉMONSTRATION: DÉTECTION D'ESCALATION")
        print("-" * 50)
        
        scenarios = [
            {
                'message': "Bonjour, j'ai besoin d'aide pour mon évier",
                'context': {'service_type': 'plomberie', 'zone': 'Bonamoussadi', 'urgency_level': 'normal'},
                'description': "Conversation normale - pas d'escalation attendue"
            },
            {
                'message': "C'est la 5ème fois que j'explique le même problème ! Je suis vraiment énervé, personne ne comprend !",
                'context': {'service_type': 'électricité', 'zone': 'Bonamoussadi', 'urgency_level': 'urgent', 'conversation_turn': 8},
                'description': "Frustration élevée - escalation probable"
            },
            {
                'message': "Mon installation électrique est très complexe avec plusieurs phases, des problèmes de différentiel et de mise à la terre que personne n'arrive à résoudre",
                'context': {'service_type': 'électricité', 'zone': 'Bonamoussadi', 'urgency_level': 'high', 'conversation_turn': 6},
                'description': "Problème technique complexe - escalation technique"
            }
        ]
        
        for i, scenario in enumerate(scenarios, 1):
            print(f"\n{i}. {scenario['description']}")
            print(f"   Message: \"{scenario['message'][:60]}...\"")
            
            try:
                data = {
                    'user_id': self.user_id,
                    'session_id': f"{self.session_id}_escalation_{i}",
                    'message': scenario['message'],
                    'context': scenario['context']
                }
                
                response = self.session.post(
                    f"{BASE_URL}/api/v1/escalation/detect",
                    json=data
                )
                result = response.json()
                
                if result.get('success'):
                    escalation_triggered = result.get('escalation_triggered', False)
                    escalation_score = result.get('escalation_score', 0.0)
                    escalation_reason = result.get('escalation_reason', '')
                    escalation_type = result.get('escalation_type', '')
                    
                    # Affichage des résultats
                    status_emoji = "🚨" if escalation_triggered else "✅"
                    status_text = "ESCALATION DÉCLENCHÉE" if escalation_triggered else "Conversation normale"
                    
                    print(f"   {status_emoji} Résultat: {status_text}")
                    print(f"   📊 Score d'escalation: {escalation_score:.3f}")
                    
                    if escalation_triggered:
                        print(f"   💡 Raison: {escalation_reason}")
                        print(f"   🏷️  Type: {escalation_type}")
                        print(f"   👨‍💼 Action: Transfert vers agent humain requis")
                    
                else:
                    print(f"   ❌ Erreur: {result.get('error')}")
                    
            except Exception as e:
                print(f"   ❌ Erreur de connexion: {e}")
        
        print()
    
    def show_dashboard(self):
        """Afficher le tableau de bord"""
        print("📈 TABLEAU DE BORD EN TEMPS RÉEL")
        print("-" * 50)
        
        try:
            # Obtenir les statistiques du tableau de bord
            response = self.session.get(f"{BASE_URL}/api/v1/escalation/analytics/dashboard")
            result = response.json()
            
            if result.get('success'):
                dashboard = result.get('dashboard', {})
                
                print("📊 Statistiques d'aujourd'hui:")
                print(f"   🔍 Détections totales: {dashboard.get('detections_today', 0)}")
                print(f"   🚨 Escalations déclenchées: {dashboard.get('escalations_today', 0)}")
                print(f"   ⚡ Escalations actives: {dashboard.get('active_escalations', 0)}")
                print(f"   📈 Taux d'escalation: {dashboard.get('escalation_rate', 0):.1%}")
                print(f"   ⭐ Score moyen: {dashboard.get('average_escalation_score', 0):.3f}")
                
            else:
                print("❌ Erreur lors de la récupération du tableau de bord")
            
            # Obtenir les logs récents
            response = self.session.get(f"{BASE_URL}/api/v1/escalation/logs?limit=3")
            result = response.json()
            
            if result.get('success'):
                logs = result.get('logs', [])
                total_count = result.get('total_count', 0)
                
                print(f"\n📋 Logs récents ({len(logs)}/{total_count}):")
                for log in logs:
                    status_emoji = "🚨" if log['escalation_triggered'] else "✅"
                    timestamp = log['timestamp'][:19]  # Remove microseconds
                    
                    print(f"   {status_emoji} {timestamp}")
                    print(f"      Score: {log['escalation_score']:.3f} | Service: {log['service_type']}")
                    print(f"      Message: {log['message_content'][:50]}...")
                
            else:
                print("❌ Erreur lors de la récupération des logs")
                
        except Exception as e:
            print(f"❌ Erreur: {e}")
        
        print()
    
    def interactive_test(self):
        """Test interactif avec l'utilisateur"""
        print("🎮 TEST INTERACTIF")
        print("-" * 50)
        print("Tapez vos propres messages pour tester le système d'escalation.")
        print("Tapez 'quit' pour revenir au menu principal.")
        print()
        
        conversation_turn = 1
        session_id = f"{self.session_id}_interactive"
        
        while True:
            try:
                message = input(f"[Tour {conversation_turn}] Votre message: ").strip()
                
                if message.lower() in ['quit', 'exit', 'q']:
                    break
                
                if not message:
                    continue
                
                # Analyser d'abord la complexité
                complexity_data = {
                    'message': message,
                    'conversation_history': [],
                    'context': {
                        'service_type': 'général',
                        'zone': 'Bonamoussadi',
                        'user_id': self.user_id,
                        'session_id': session_id,
                        'conversation_turn': conversation_turn
                    }
                }
                
                response = self.session.post(
                    f"{BASE_URL}/api/v1/escalation/complexity/analyze",
                    json=complexity_data
                )
                complexity_result = response.json()
                
                # Détecter l'escalation
                escalation_data = {
                    'user_id': self.user_id,
                    'session_id': session_id,
                    'message': message,
                    'context': {
                        'service_type': 'général',
                        'zone': 'Bonamoussadi',
                        'conversation_turn': conversation_turn
                    }
                }
                
                response = self.session.post(
                    f"{BASE_URL}/api/v1/escalation/detect",
                    json=escalation_data
                )
                escalation_result = response.json()
                
                # Afficher les résultats
                print("\n" + "="*60)
                print("📊 ANALYSE DE VOTRE MESSAGE:")
                
                if complexity_result.get('success'):
                    complexity = complexity_result.get('complexity_score', 0.0)
                    escalation_prob = complexity_result.get('escalation_probability', 0.0)
                    
                    complexity_level = self._get_complexity_level(complexity)
                    prob_level = self._get_probability_level(escalation_prob)
                    
                    print(f"   🧠 Complexité: {complexity:.3f} ({complexity_level})")
                    print(f"   ⚠️  Probabilité d'escalation: {escalation_prob:.3f} ({prob_level})")
                
                if escalation_result.get('success'):
                    escalation_triggered = escalation_result.get('escalation_triggered', False)
                    escalation_score = escalation_result.get('escalation_score', 0.0)
                    
                    if escalation_triggered:
                        print(f"   🚨 ESCALATION DÉCLENCHÉE!")
                        print(f"   📞 Un agent humain va être contacté.")
                        print(f"   📊 Score: {escalation_score:.3f}")
                        reason = escalation_result.get('escalation_reason', '')
                        if reason:
                            print(f"   💡 Raison: {reason}")
                    else:
                        print(f"   ✅ Conversation normale (Score: {escalation_score:.3f})")
                        print(f"   🤖 L'IA peut continuer à vous aider.")
                
                print("="*60)
                print()
                
                conversation_turn += 1
                
            except KeyboardInterrupt:
                print("\n\nTest interactif interrompu.")
                break
            except Exception as e:
                print(f"❌ Erreur: {e}")
    
    def _get_complexity_level(self, score):
        """Obtenir le niveau de complexité en texte"""
        if score < 0.3:
            return "FAIBLE"
        elif score < 0.6:
            return "MODÉRÉE"
        elif score < 0.8:
            return "ÉLEVÉE"
        else:
            return "TRÈS ÉLEVÉE"
    
    def _get_probability_level(self, score):
        """Obtenir le niveau de probabilité en texte"""
        if score < 0.3:
            return "FAIBLE"
        elif score < 0.6:
            return "MODÉRÉE"
        elif score < 0.8:
            return "ÉLEVÉE"
        else:
            return "TRÈS ÉLEVÉE"
    
    def run_demo(self):
        """Exécuter la démonstration complète"""
        self.display_header()
        
        if not self.get_system_status():
            print("❌ Impossible de continuer sans connexion au système.")
            return
        
        while True:
            print("\n📋 MENU DE DÉMONSTRATION:")
            print("1. 🧠 Analyse de complexité")
            print("2. 🚨 Détection d'escalation") 
            print("3. 📈 Tableau de bord")
            print("4. 🎮 Test interactif")
            print("5. 🔄 Actualiser le statut")
            print("6. ❌ Quitter")
            print()
            
            try:
                choice = input("Choisissez une option (1-6): ").strip()
                
                if choice == '1':
                    self.demo_complexity_analysis()
                elif choice == '2':
                    self.demo_escalation_detection()
                elif choice == '3':
                    self.show_dashboard()
                elif choice == '4':
                    self.interactive_test()
                elif choice == '5':
                    self.get_system_status()
                elif choice == '6':
                    print("\n👋 Merci d'avoir testé le système de détection d'escalation !")
                    print("🚀 Djobea AI - Votre assistant intelligent pour les services à domicile")
                    break
                else:
                    print("❌ Option invalide. Choisissez entre 1 et 6.")
                    
            except KeyboardInterrupt:
                print("\n\n👋 Démonstration interrompue. Au revoir !")
                break
            except Exception as e:
                print(f"❌ Erreur: {e}")

def main():
    """Fonction principale"""
    # Vérifier que le serveur est accessible
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code != 200:
            print("❌ Serveur Djobea AI inaccessible")
            print("Assurez-vous que le serveur est en marche sur le port 5000")
            return
    except Exception as e:
        print(f"❌ Impossible de se connecter au serveur: {e}")
        print("Assurez-vous que le serveur Djobea AI est en marche sur le port 5000")
        return
    
    # Lancer la démonstration
    demo = EscalationDemo()
    demo.run_demo()

if __name__ == "__main__":
    main()