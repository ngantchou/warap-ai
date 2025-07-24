#!/usr/bin/env python3
"""
Test Complet des Scénarios de Conversation - Djobea AI
Validation de tous les cas d'usage du dialog flow
"""
import requests
import time
import json
from datetime import datetime

class ComprehensiveConversationTest:
    
    def __init__(self):
        self.base_url = "http://localhost:5000"
        self.phone_number = "237691924172"
        self.test_results = []
        
    def send_message(self, message: str, session_id: str) -> dict:
        """Envoyer un message via l'API"""
        try:
            response = requests.post(
                f"{self.base_url}/webhook/chat",
                json={
                    "message": message,
                    "session_id": session_id,
                    "phone_number": self.phone_number,
                    "source": "web_chat"
                },
                headers={'Content-Type': 'application/json'},
                timeout=12
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            return {"error": str(e)}
    
    def test_scenario(self, scenario_name: str, messages: list, expected_features: list) -> dict:
        """Tester un scénario complet"""
        print(f"\n🎭 Scénario: {scenario_name}")
        print("-" * 50)
        
        session_id = f"scenario_{int(time.time())}_{scenario_name.replace(' ', '_')}"
        results = []
        detected_features = []
        
        for i, message in enumerate(messages):
            print(f"\n👤 Client: {message}")
            
            response = self.send_message(message, session_id)
            
            if "error" in response:
                print(f"❌ Erreur: {response['error']}")
                results.append({"success": False, "error": response["error"]})
                continue
            
            ai_response = response.get('response', '').replace('<br>', '\n').replace('<br/>', '\n')
            print(f"🤖 Djobea AI: {ai_response}")
            
            # Analyser les fonctionnalités détectées
            response_lower = ai_response.lower()
            
            # Vérifier chaque fonctionnalité attendue
            for feature in expected_features:
                if feature not in detected_features:
                    if feature == "service_extraction" and any(word in response_lower for word in ["plombier", "électricien", "plomberie", "électricité"]):
                        detected_features.append(feature)
                    elif feature == "location_recognition" and any(word in response_lower for word in ["bonamoussadi", "douala", "quartier"]):
                        detected_features.append(feature)
                    elif feature == "urgency_detection" and any(word in response_lower for word in ["urgent", "immédiat", "rapidement", "priorité"]):
                        detected_features.append(feature)
                    elif feature == "service_creation" and any(word in response_lower for word in ["demande", "créé", "enregistré", "recherche"]):
                        detected_features.append(feature)
                    elif feature == "price_information" and any(word in response_lower for word in ["prix", "coût", "tarif", "xaf"]):
                        detected_features.append(feature)
                    elif feature == "multilingual_support" and any(word in response_lower for word in ["télé", "tv", "spoil"]):
                        detected_features.append(feature)
                    elif feature == "clarification_request" and any(char in response_lower for char in ["?", "quel", "où", "comment"]):
                        detected_features.append(feature)
                    elif feature == "escalation_detection" and any(word in response_lower for word in ["agent", "responsable", "humain"]):
                        detected_features.append(feature)
            
            success = len(ai_response) > 15 and "erreur" not in response_lower
            results.append({
                "success": success,
                "message": message,
                "response": ai_response,
                "turn": i + 1
            })
            
            time.sleep(0.5)  # Petite pause
        
        # Calculer le taux de réussite
        successful_turns = sum(1 for r in results if r.get("success", False))
        total_turns = len(results)
        success_rate = (successful_turns / total_turns) * 100 if total_turns > 0 else 0
        
        # Calculer le taux de fonctionnalités détectées
        feature_rate = (len(detected_features) / len(expected_features)) * 100 if expected_features else 100
        
        print(f"\n📊 Résultats:")
        print(f"   Tours réussis: {successful_turns}/{total_turns} ({success_rate:.1f}%)")
        print(f"   Fonctionnalités détectées: {len(detected_features)}/{len(expected_features)} ({feature_rate:.1f}%)")
        print(f"   Fonctionnalités: {detected_features}")
        
        scenario_result = {
            "scenario": scenario_name,
            "success_rate": success_rate,
            "feature_rate": feature_rate,
            "detected_features": detected_features,
            "expected_features": expected_features,
            "overall_success": success_rate >= 70 and feature_rate >= 60,
            "results": results
        }
        
        self.test_results.append(scenario_result)
        return scenario_result
    
    def run_all_scenarios(self):
        """Exécuter tous les scénarios de test"""
        print("🎭 Test Complet des Scénarios de Conversation - Djobea AI")
        print("=" * 70)
        
        # Vérifier la connectivité
        try:
            response = requests.get(f"{self.base_url}/health")
            if response.status_code != 200:
                print("❌ Serveur non accessible")
                return
            print("✅ Serveur accessible")
        except Exception as e:
            print(f"❌ Erreur de connexion: {e}")
            return
        
        # Définir les scénarios de test
        scenarios = [
            {
                "name": "Demande Simple de Plomberie",
                "messages": [
                    "Bonjour, j'ai besoin d'un plombier",
                    "J'ai une fuite d'eau dans ma cuisine",
                    "Je suis à Bonamoussadi"
                ],
                "expected_features": ["service_extraction", "location_recognition", "service_creation"]
            },
            {
                "name": "Gestion d'Urgence",
                "messages": [
                    "URGENT ! J'ai une fuite d'eau majeure",
                    "L'eau coule partout dans ma maison",
                    "Je suis à Bonamoussadi"
                ],
                "expected_features": ["urgency_detection", "service_extraction", "location_recognition"]
            },
            {
                "name": "Support Multilingue",
                "messages": [
                    "Hello, I need help with ma télé",
                    "The TV don spoil completely",
                    "I dey for Bonamoussadi"
                ],
                "expected_features": ["multilingual_support", "service_extraction", "location_recognition"]
            },
            {
                "name": "Informations Incomplètes",
                "messages": [
                    "J'ai un problème",
                    "C'est cassé",
                    "Dans ma maison"
                ],
                "expected_features": ["clarification_request", "service_extraction"]
            },
            {
                "name": "Demande de Prix",
                "messages": [
                    "Combien coûte un plombier ?",
                    "Pour réparer une fuite",
                    "À Bonamoussadi"
                ],
                "expected_features": ["price_information", "service_extraction", "location_recognition"]
            }
        ]
        
        # Exécuter chaque scénario
        for scenario in scenarios:
            try:
                self.test_scenario(
                    scenario["name"],
                    scenario["messages"],
                    scenario["expected_features"]
                )
                time.sleep(2)  # Pause entre scénarios
            except Exception as e:
                print(f"❌ Erreur dans le scénario {scenario['name']}: {e}")
        
        # Générer le rapport final
        self.generate_final_report()
    
    def generate_final_report(self):
        """Générer le rapport final complet"""
        print("\n" + "=" * 70)
        print("📊 RAPPORT FINAL - SCÉNARIOS DE CONVERSATION")
        print("=" * 70)
        
        total_scenarios = len(self.test_results)
        successful_scenarios = [r for r in self.test_results if r["overall_success"]]
        
        overall_success_rate = (len(successful_scenarios) / total_scenarios) * 100 if total_scenarios > 0 else 0
        avg_success_rate = sum(r["success_rate"] for r in self.test_results) / total_scenarios if total_scenarios > 0 else 0
        avg_feature_rate = sum(r["feature_rate"] for r in self.test_results) / total_scenarios if total_scenarios > 0 else 0
        
        print(f"📊 Statistiques Globales:")
        print(f"   Total des scénarios: {total_scenarios}")
        print(f"   Scénarios réussis: {len(successful_scenarios)}")
        print(f"   Taux de réussite global: {overall_success_rate:.1f}%")
        print(f"   Taux de réussite moyen: {avg_success_rate:.1f}%")
        print(f"   Taux de fonctionnalités moyen: {avg_feature_rate:.1f}%")
        
        print(f"\n📋 Détail des Scénarios:")
        for result in self.test_results:
            status = "✅" if result["overall_success"] else "❌"
            print(f"   {status} {result['scenario']}: {result['success_rate']:.1f}% (Fonctionnalités: {result['feature_rate']:.1f}%)")
        
        # Fonctionnalités validées globalement
        all_detected_features = set()
        for result in self.test_results:
            all_detected_features.update(result["detected_features"])
        
        print(f"\n✅ Fonctionnalités Validées Globalement:")
        feature_names = {
            "service_extraction": "Extraction de type de service",
            "location_recognition": "Reconnaissance de localisation",
            "urgency_detection": "Détection d'urgence",
            "service_creation": "Création de demandes",
            "price_information": "Informations de prix",
            "multilingual_support": "Support multilingue",
            "clarification_request": "Demandes de clarification",
            "escalation_detection": "Détection d'escalation"
        }
        
        for feature in sorted(all_detected_features):
            feature_name = feature_names.get(feature, feature)
            print(f"   • {feature_name}")
        
        # Évaluation finale
        if overall_success_rate >= 90:
            evaluation = "EXCELLENT"
            message = "Le dialog flow est parfaitement implémenté et gère tous les scénarios"
        elif overall_success_rate >= 75:
            evaluation = "TRÈS BON"
            message = "Le dialog flow est bien implémenté avec quelques améliorations possibles"
        elif overall_success_rate >= 60:
            evaluation = "BON"
            message = "Le dialog flow est fonctionnel mais pourrait être optimisé"
        elif overall_success_rate >= 40:
            evaluation = "MOYEN"
            message = "Le dialog flow fonctionne partiellement, améliorations nécessaires"
        else:
            evaluation = "INSUFFISANT"
            message = "Le dialog flow nécessite des corrections importantes"
        
        print(f"\n🎯 ÉVALUATION FINALE: {evaluation}")
        print(f"📝 {message}")
        
        # Recommandations
        print(f"\n💡 Recommandations:")
        if overall_success_rate < 100:
            print("   • Continuer à améliorer la compréhension contextuelle")
            print("   • Optimiser les temps de réponse du système")
        
        if avg_feature_rate < 90:
            print("   • Renforcer la détection des fonctionnalités spécifiques")
            print("   • Améliorer la reconnaissance des intentions complexes")
        
        print(f"\n🏆 CONCLUSION:")
        if overall_success_rate >= 70:
            print("✅ Le système de dialog flow de Djobea AI est OPÉRATIONNEL")
            print("✅ Les clients peuvent interagir naturellement avec le système")
            print("✅ Les demandes de service sont traitées correctement")
        else:
            print("⚠️ Le système nécessite des ajustements avant déploiement")
            print("⚠️ Certains scénarios de conversation nécessitent des améliorations")


if __name__ == "__main__":
    tester = ComprehensiveConversationTest()
    tester.run_all_scenarios()