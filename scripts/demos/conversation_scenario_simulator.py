#!/usr/bin/env python3
"""
Simulateur de scénarios de conversation - Djobea AI
Test complet du dialog flow pour différents cas de conversation avec les clients
"""
import asyncio
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
import requests
from dataclasses import dataclass, asdict


@dataclass
class ConversationScenario:
    """Scénario de conversation"""
    name: str
    description: str
    user_messages: List[str]
    expected_outcomes: List[str]
    context: Dict[str, Any]
    difficulty: str  # "easy", "medium", "hard", "extreme"
    language: str = "french"
    should_escalate: bool = False
    escalation_trigger: Optional[str] = None


class ConversationSimulator:
    """Simulateur de conversations pour tester le dialog flow"""
    
    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url
        self.test_results = []
        self.session_id = f"simulation_{int(time.time())}"
        self.phone_number = "237691924172"
        
    def create_conversation_scenarios(self) -> List[ConversationScenario]:
        """Créer différents scénarios de conversation"""
        scenarios = [
            # 1. Scénario basique - Demande simple
            ConversationScenario(
                name="Demande Simple - Plomberie",
                description="Client demande un plombier de manière directe",
                user_messages=[
                    "Bonjour, j'ai besoin d'un plombier",
                    "J'ai une fuite d'eau dans ma cuisine",
                    "Je suis à Bonamoussadi, quartier Carrefour"
                ],
                expected_outcomes=[
                    "Extraction service_type: plomberie",
                    "Extraction location: Bonamoussadi",
                    "Création de demande de service",
                    "Notification de provider"
                ],
                context={"service_type": "plomberie", "location": "Bonamoussadi"},
                difficulty="easy"
            ),
            
            # 2. Scénario avec interruptions et clarifications
            ConversationScenario(
                name="Conversation avec Interruptions",
                description="Client change d'avis et demande des clarifications",
                user_messages=[
                    "Bonjour, j'ai un problème électrique",
                    "En fait non, c'est plutôt un problème de plomberie",
                    "Mon robinet fuit beaucoup",
                    "Combien ça coûte ?",
                    "OK, je suis à Douala, Bonamoussadi"
                ],
                expected_outcomes=[
                    "Gestion changement de service",
                    "Réponse sur tarification",
                    "Extraction location finale",
                    "Création demande corrigée"
                ],
                context={"service_type": "plomberie", "location": "Bonamoussadi"},
                difficulty="medium"
            ),
            
            # 3. Scénario multilingue (Français/Anglais/Pidgin)
            ConversationScenario(
                name="Conversation Multilingue",
                description="Client mélange français, anglais et pidgin camerounais",
                user_messages=[
                    "Bonjour, I need help with ma télé",
                    "The TV don spoil, no dey work at all",
                    "I dey for Bonamoussadi, près du marché",
                    "How much wuna dey charge for dis kind work?"
                ],
                expected_outcomes=[
                    "Compréhension du mélange linguistique",
                    "Extraction service_type: réparation électroménager",
                    "Extraction location: Bonamoussadi",
                    "Réponse appropriée en français"
                ],
                context={"service_type": "electromenager", "location": "Bonamoussadi"},
                difficulty="medium"
            ),
            
            # 4. Scénario d'urgence
            ConversationScenario(
                name="Situation d'Urgence",
                description="Client avec problème urgent nécessitant intervention rapide",
                user_messages=[
                    "URGENT ! J'ai une fuite d'eau majeure chez moi",
                    "L'eau coule partout, ça inonde ma maison",
                    "J'ai coupé l'eau mais ça continue",
                    "Je suis à Bonamoussadi, besoin d'aide immédiate !",
                    "Vous pouvez envoyer quelqu'un maintenant ?"
                ],
                expected_outcomes=[
                    "Détection urgence élevée",
                    "Priorité assignée: urgent",
                    "Recherche provider disponible immédiatement",
                    "Notification client avec temps d'arrivée"
                ],
                context={"service_type": "plomberie", "location": "Bonamoussadi", "urgency": "urgent"},
                difficulty="medium"
            ),
            
            # 5. Scénario avec informations incomplètes
            ConversationScenario(
                name="Informations Incomplètes",
                description="Client donne des informations vagues et incomplètes",
                user_messages=[
                    "Salut, j'ai un problème",
                    "C'est cassé",
                    "Chez moi",
                    "Je sais pas trop quoi faire",
                    "C'est dans la cuisine"
                ],
                expected_outcomes=[
                    "Questions de clarification intelligentes",
                    "Extraction progressive d'informations",
                    "Identification du type de problème",
                    "Obtention de la localisation"
                ],
                context={"incomplete_info": True},
                difficulty="hard"
            ),
            
            # 6. Scénario de frustration (escalation)
            ConversationScenario(
                name="Client Frustré - Escalation",
                description="Client frustré après plusieurs tentatives, doit être escaladé",
                user_messages=[
                    "Ça fait 3 fois que j'appelle !",
                    "Votre service marche pas du tout",
                    "J'ai déjà expliqué mon problème hier",
                    "Vous m'avez dit qu'un plombier viendrait",
                    "Je veux parler à un responsable !",
                    "C'est vraiment nul votre service"
                ],
                expected_outcomes=[
                    "Détection de frustration",
                    "Tentative d'apaisement",
                    "Escalation vers agent humain",
                    "Création cas d'escalation"
                ],
                context={"previous_requests": 2, "escalation_expected": True},
                difficulty="hard",
                should_escalate=True,
                escalation_trigger="frustration"
            ),
            
            # 7. Scénario de demande complexe
            ConversationScenario(
                name="Demande Complexe Multi-Services",
                description="Client avec plusieurs problèmes nécessitant coordination",
                user_messages=[
                    "J'ai plusieurs problèmes dans ma maison",
                    "Mon électricité marche pas bien dans le salon",
                    "Et j'ai aussi une fuite d'eau dans la salle de bain",
                    "Et ma machine à laver fait du bruit bizarre",
                    "Vous pouvez envoyer une équipe complète ?",
                    "Je suis à Bonamoussadi, disponible tout l'après-midi"
                ],
                expected_outcomes=[
                    "Identification de services multiples",
                    "Coordination de providers",
                    "Planification d'interventions",
                    "Estimation globale des coûts"
                ],
                context={"multi_service": True, "services": ["électricité", "plomberie", "électroménager"]},
                difficulty="hard"
            ),
            
            # 8. Scénario avec négociation de prix
            ConversationScenario(
                name="Négociation de Prix",
                description="Client négocie les prix et demande des alternatives",
                user_messages=[
                    "J'ai besoin d'un électricien",
                    "C'est pour réparer des prises électriques",
                    "Je suis à Bonamoussadi",
                    "Combien ça coûte ?",
                    "C'est trop cher ! Vous avez moins cher ?",
                    "Et si je fournis les matériaux moi-même ?",
                    "OK, trouvez-moi le moins cher possible"
                ],
                expected_outcomes=[
                    "Fourniture d'estimations de prix",
                    "Présentation d'alternatives",
                    "Négociation intelligente",
                    "Recherche provider économique"
                ],
                context={"price_sensitive": True, "budget_constraint": True},
                difficulty="medium"
            ),
            
            # 9. Scénario avec planning spécifique
            ConversationScenario(
                name="Contraintes de Planning",
                description="Client avec contraintes horaires spécifiques",
                user_messages=[
                    "Bonjour, j'ai besoin d'un plombier",
                    "Problème de robinet qui fuit",
                    "Mais je suis disponible seulement le weekend",
                    "Et seulement entre 9h et 12h le samedi",
                    "Vous avez quelqu'un qui peut ?",
                    "Je suis à Bonamoussadi, près de l'école"
                ],
                expected_outcomes=[
                    "Prise en compte des contraintes horaires",
                    "Recherche provider disponible weekend",
                    "Planification précise",
                    "Confirmation de rendez-vous"
                ],
                context={"scheduling_constraints": True, "weekend_only": True},
                difficulty="medium"
            ),
            
            # 10. Scénario technique complexe
            ConversationScenario(
                name="Problème Technique Complexe",
                description="Client avec problème technique nécessitant expertise",
                user_messages=[
                    "J'ai un problème électrique bizarre",
                    "Les lumières clignotent dans toute la maison",
                    "Ça a commencé après l'orage d'hier",
                    "J'ai vérifié le compteur, tout semble normal",
                    "Mais certaines prises ne marchent plus",
                    "J'ai peur que ce soit dangereux",
                    "Il faut un électricien expérimenté"
                ],
                expected_outcomes=[
                    "Identification de problème complexe",
                    "Évaluation niveau d'expertise requis",
                    "Recherche provider spécialisé",
                    "Conseils de sécurité"
                ],
                context={"technical_complexity": "high", "safety_concern": True},
                difficulty="hard"
            ),
            
            # 11. Scénario d'annulation
            ConversationScenario(
                name="Annulation de Demande",
                description="Client veut annuler sa demande en cours",
                user_messages=[
                    "J'ai fait une demande hier pour un plombier",
                    "Je veux l'annuler",
                    "J'ai trouvé quelqu'un d'autre",
                    "Comment faire pour annuler ?",
                    "C'est urgent, le provider va arriver"
                ],
                expected_outcomes=[
                    "Identification de la demande existante",
                    "Processus d'annulation",
                    "Notification du provider",
                    "Confirmation d'annulation"
                ],
                context={"cancellation_request": True, "existing_request": True},
                difficulty="medium"
            ),
            
            # 12. Scénario de suivi de demande
            ConversationScenario(
                name="Suivi de Demande",
                description="Client demande le statut de sa demande",
                user_messages=[
                    "Bonjour, j'ai fait une demande ce matin",
                    "Je veux savoir où ça en est",
                    "Le plombier va venir quand ?",
                    "J'ai pas eu de nouvelles",
                    "C'est normal ?"
                ],
                expected_outcomes=[
                    "Récupération du statut de la demande",
                    "Informations sur le provider assigné",
                    "Estimation du temps d'arrivée",
                    "Mise à jour du client"
                ],
                context={"status_inquiry": True, "existing_request": True},
                difficulty="easy"
            )
        ]
        
        return scenarios
    
    async def simulate_conversation(self, scenario: ConversationScenario) -> Dict[str, Any]:
        """Simuler une conversation complète"""
        print(f"\n🎭 Simulation: {scenario.name}")
        print(f"📝 Description: {scenario.description}")
        print(f"🎯 Difficulté: {scenario.difficulty}")
        print("-" * 50)
        
        conversation_log = []
        outcomes_achieved = []
        escalation_detected = False
        
        # Initialiser la session
        session_data = {
            "session_id": f"{self.session_id}_{scenario.name.replace(' ', '_')}",
            "phone_number": self.phone_number,
            "scenario": scenario.name
        }
        
        # Simuler chaque message de l'utilisateur
        for i, message in enumerate(scenario.user_messages):
            print(f"\n👤 Client: {message}")
            
            # Envoyer le message via l'API
            try:
                response = await self.send_message(message, session_data)
                ai_response = response.get('response', 'Pas de réponse')
                
                print(f"🤖 Djobea AI: {ai_response}")
                
                # Enregistrer dans le log
                conversation_log.append({
                    "turn": i + 1,
                    "user_message": message,
                    "ai_response": ai_response,
                    "timestamp": datetime.now().isoformat()
                })
                
                # Analyser la réponse pour vérifier les outcomes
                self.analyze_response(ai_response, scenario, outcomes_achieved)
                
                # Vérifier si escalation détectée
                if "escalation" in ai_response.lower() or "agent" in ai_response.lower():
                    escalation_detected = True
                
                # Pause entre les messages
                await asyncio.sleep(1)
                
            except Exception as e:
                print(f"❌ Erreur lors de l'envoi du message: {e}")
                conversation_log.append({
                    "turn": i + 1,
                    "user_message": message,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })
        
        # Évaluer le résultat de la simulation
        success_rate = len(outcomes_achieved) / len(scenario.expected_outcomes) * 100
        
        # Vérifier l'escalation si attendue
        escalation_success = True
        if scenario.should_escalate:
            escalation_success = escalation_detected
            if escalation_detected:
                print(f"✅ Escalation détectée comme attendu")
            else:
                print(f"❌ Escalation attendue mais non détectée")
        
        result = {
            "scenario": scenario.name,
            "difficulty": scenario.difficulty,
            "success_rate": success_rate,
            "outcomes_achieved": outcomes_achieved,
            "outcomes_expected": scenario.expected_outcomes,
            "escalation_expected": scenario.should_escalate,
            "escalation_detected": escalation_detected,
            "escalation_success": escalation_success,
            "conversation_log": conversation_log,
            "overall_success": success_rate >= 70 and escalation_success,
            "context": scenario.context
        }
        
        print(f"\n📊 Résultat: {success_rate:.1f}% des objectifs atteints")
        if scenario.should_escalate:
            print(f"🚨 Escalation: {'✅ Réussie' if escalation_success else '❌ Échouée'}")
        
        return result
    
    async def send_message(self, message: str, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Envoyer un message à l'API de conversation"""
        try:
            # Utiliser l'endpoint chat ou webhook selon la disponibilité
            endpoints = [
                "/chat-enhanced",
                "/webhook/whatsapp-v2",
                "/webhook/whatsapp",
                "/chat"
            ]
            
            for endpoint in endpoints:
                try:
                    if endpoint.startswith("/webhook"):
                        # Format WhatsApp webhook
                        payload = {
                            "Body": message,
                            "From": f"whatsapp:+{session_data['phone_number']}",
                            "To": "whatsapp:+237123456789",
                            "MessageSid": f"sim_{int(time.time())}",
                            "AccountSid": "simulation_account",
                            "NumSegments": "1"
                        }
                        
                        response = requests.post(
                            f"{self.base_url}{endpoint}",
                            data=payload,
                            headers={'Content-Type': 'application/x-www-form-urlencoded'}
                        )
                    else:
                        # Format chat endpoint
                        payload = {
                            "message": message,
                            "phone_number": session_data['phone_number'],
                            "session_id": session_data['session_id']
                        }
                        
                        response = requests.post(
                            f"{self.base_url}{endpoint}",
                            json=payload,
                            headers={'Content-Type': 'application/json'}
                        )
                    
                    if response.status_code == 200:
                        return response.json()
                    
                except Exception as e:
                    continue
            
            # Si aucun endpoint ne fonctionne, utiliser une réponse par défaut
            return {
                "response": "Service temporairement indisponible. Veuillez réessayer.",
                "status": "error"
            }
            
        except Exception as e:
            return {
                "response": f"Erreur de communication: {str(e)}",
                "status": "error"
            }
    
    def analyze_response(self, response: str, scenario: ConversationScenario, outcomes_achieved: List[str]):
        """Analyser la réponse de l'IA pour vérifier les outcomes"""
        response_lower = response.lower()
        
        # Vérifier les outcomes selon le scénario
        for outcome in scenario.expected_outcomes:
            if outcome in outcomes_achieved:
                continue
                
            outcome_lower = outcome.lower()
            
            # Détection d'extraction de service
            if "service_type" in outcome_lower:
                service_keywords = ["plomberie", "électricité", "électroménager", "plombier", "électricien"]
                if any(keyword in response_lower for keyword in service_keywords):
                    outcomes_achieved.append(outcome)
            
            # Détection d'extraction de location
            elif "location" in outcome_lower:
                location_keywords = ["bonamoussadi", "douala", "quartier", "localisation", "adresse"]
                if any(keyword in response_lower for keyword in location_keywords):
                    outcomes_achieved.append(outcome)
            
            # Détection de création de demande
            elif "création" in outcome_lower or "demande" in outcome_lower:
                creation_keywords = ["demande créée", "enregistré", "recherche", "provider", "prestataire"]
                if any(keyword in response_lower for keyword in creation_keywords):
                    outcomes_achieved.append(outcome)
            
            # Détection de notification
            elif "notification" in outcome_lower:
                notification_keywords = ["notifié", "contacté", "envoyé", "informé"]
                if any(keyword in response_lower for keyword in notification_keywords):
                    outcomes_achieved.append(outcome)
            
            # Détection d'urgence
            elif "urgence" in outcome_lower:
                urgency_keywords = ["urgent", "immédiat", "rapidement", "priorité"]
                if any(keyword in response_lower for keyword in urgency_keywords):
                    outcomes_achieved.append(outcome)
            
            # Détection de tarification
            elif "tarification" in outcome_lower or "prix" in outcome_lower:
                price_keywords = ["prix", "coût", "tarif", "xaf", "franc"]
                if any(keyword in response_lower for keyword in price_keywords):
                    outcomes_achieved.append(outcome)
            
            # Détection de clarification
            elif "clarification" in outcome_lower:
                clarification_keywords = ["préciser", "détail", "expliquer", "question"]
                if any(keyword in response_lower for keyword in clarification_keywords):
                    outcomes_achieved.append(outcome)
    
    async def run_all_simulations(self) -> Dict[str, Any]:
        """Exécuter toutes les simulations"""
        print("🚀 Démarrage des simulations de conversation - Djobea AI")
        print("=" * 60)
        
        scenarios = self.create_conversation_scenarios()
        results = []
        
        for scenario in scenarios:
            try:
                result = await self.simulate_conversation(scenario)
                results.append(result)
                self.test_results.append(result)
                
                # Pause entre les scénarios
                await asyncio.sleep(2)
                
            except Exception as e:
                print(f"❌ Erreur lors de la simulation {scenario.name}: {e}")
                results.append({
                    "scenario": scenario.name,
                    "error": str(e),
                    "overall_success": False
                })
        
        return self.generate_summary_report(results)
    
    def generate_summary_report(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Générer un rapport de synthèse"""
        print("\n" + "=" * 60)
        print("📊 RAPPORT DE SYNTHÈSE - SIMULATIONS DE CONVERSATION")
        print("=" * 60)
        
        total_scenarios = len(results)
        successful_scenarios = [r for r in results if r.get('overall_success', False)]
        failed_scenarios = [r for r in results if not r.get('overall_success', False)]
        
        # Statistiques globales
        success_rate = len(successful_scenarios) / total_scenarios * 100
        avg_outcome_rate = sum(r.get('success_rate', 0) for r in results) / total_scenarios
        
        # Statistiques par difficulté
        difficulty_stats = {}
        for difficulty in ['easy', 'medium', 'hard', 'extreme']:
            difficulty_results = [r for r in results if r.get('difficulty') == difficulty]
            if difficulty_results:
                difficulty_success = len([r for r in difficulty_results if r.get('overall_success', False)])
                difficulty_stats[difficulty] = {
                    'total': len(difficulty_results),
                    'success': difficulty_success,
                    'rate': difficulty_success / len(difficulty_results) * 100
                }
        
        # Statistiques d'escalation
        escalation_scenarios = [r for r in results if r.get('escalation_expected', False)]
        escalation_success = len([r for r in escalation_scenarios if r.get('escalation_detected', False)])
        
        print(f"📊 Résultats Globaux:")
        print(f"   Total des scénarios: {total_scenarios}")
        print(f"   Scénarios réussis: {len(successful_scenarios)}")
        print(f"   Scénarios échoués: {len(failed_scenarios)}")
        print(f"   Taux de réussite global: {success_rate:.1f}%")
        print(f"   Taux moyen d'objectifs atteints: {avg_outcome_rate:.1f}%")
        
        print(f"\n📊 Résultats par Difficulté:")
        for difficulty, stats in difficulty_stats.items():
            print(f"   {difficulty.capitalize()}: {stats['success']}/{stats['total']} ({stats['rate']:.1f}%)")
        
        print(f"\n🚨 Escalations:")
        print(f"   Scénarios d'escalation: {len(escalation_scenarios)}")
        print(f"   Escalations détectées: {escalation_success}")
        print(f"   Taux de détection: {escalation_success/len(escalation_scenarios)*100 if escalation_scenarios else 0:.1f}%")
        
        print(f"\n📋 Détail des Résultats:")
        for result in results:
            status = "✅" if result.get('overall_success', False) else "❌"
            escalation = "🚨" if result.get('escalation_expected', False) else "💬"
            print(f"   {status} {escalation} {result.get('scenario', 'Unknown')} - {result.get('success_rate', 0):.1f}%")
        
        if failed_scenarios:
            print(f"\n❌ Scénarios Échoués:")
            for result in failed_scenarios:
                scenario = result.get('scenario', 'Unknown')
                if 'error' in result:
                    print(f"   - {scenario}: Erreur technique - {result['error']}")
                else:
                    missing_outcomes = set(result.get('outcomes_expected', [])) - set(result.get('outcomes_achieved', []))
                    print(f"   - {scenario}: Objectifs manqués - {list(missing_outcomes)}")
        
        # Évaluation finale
        overall_score = "EXCELLENT" if success_rate >= 90 else \
                       "TRÈS BON" if success_rate >= 80 else \
                       "BON" if success_rate >= 70 else \
                       "MOYEN" if success_rate >= 60 else \
                       "INSUFFISANT"
        
        print(f"\n🎯 ÉVALUATION FINALE: {overall_score}")
        
        if success_rate >= 80:
            print("✅ Le dialog flow est bien implémenté et gère correctement la majorité des scénarios.")
            print("✅ Les fonctionnalités de conversation sont opérationnelles.")
            
            if escalation_success == len(escalation_scenarios) and escalation_scenarios:
                print("✅ Le système d'escalation fonctionne parfaitement.")
            
        else:
            print("⚠️  Le dialog flow nécessite des améliorations pour mieux gérer certains scénarios.")
            
        print(f"\n🔗 Fonctionnalités Validées:")
        validated_features = []
        
        # Analyser les fonctionnalités validées
        for result in successful_scenarios:
            outcomes = result.get('outcomes_achieved', [])
            if any('service_type' in outcome for outcome in outcomes):
                validated_features.append("Extraction de type de service")
            if any('location' in outcome for outcome in outcomes):
                validated_features.append("Extraction de localisation")
            if any('création' in outcome for outcome in outcomes):
                validated_features.append("Création de demandes")
            if any('prix' in outcome for outcome in outcomes):
                validated_features.append("Gestion des prix")
            if any('urgence' in outcome for outcome in outcomes):
                validated_features.append("Gestion d'urgence")
        
        # Supprimer les doublons
        validated_features = list(set(validated_features))
        
        for feature in validated_features:
            print(f"   ✅ {feature}")
        
        return {
            "total_scenarios": total_scenarios,
            "successful_scenarios": len(successful_scenarios),
            "failed_scenarios": len(failed_scenarios),
            "success_rate": success_rate,
            "avg_outcome_rate": avg_outcome_rate,
            "difficulty_stats": difficulty_stats,
            "escalation_stats": {
                "total": len(escalation_scenarios),
                "detected": escalation_success,
                "rate": escalation_success/len(escalation_scenarios)*100 if escalation_scenarios else 0
            },
            "overall_score": overall_score,
            "validated_features": validated_features,
            "detailed_results": results
        }


async def main():
    """Fonction principale"""
    print("🎭 Simulateur de Scénarios de Conversation - Djobea AI")
    print("Testing Dialog Flow Implementation")
    print("=" * 60)
    
    # Vérifier que le serveur est accessible
    try:
        response = requests.get("http://localhost:5000/health")
        if response.status_code != 200:
            print("❌ Serveur non accessible. Assurez-vous que le serveur est en marche.")
            return
        print("✅ Serveur accessible")
    except Exception as e:
        print(f"❌ Erreur de connexion au serveur: {e}")
        return
    
    # Exécuter les simulations
    simulator = ConversationSimulator()
    await simulator.run_all_simulations()


if __name__ == "__main__":
    asyncio.run(main())