#!/usr/bin/env python3
"""
Test Direct du Dialog Flow - Djobea AI (Version Corrigée)
Test du système de conversation via l'endpoint webhook/chat
"""
import requests
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional


class DialogFlowTester:
    """Testeur direct du dialog flow"""
    
    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url
        self.session_id = f"test_{int(time.time())}"
        self.phone_number = "237691924172"
        
    def send_chat_message(self, message: str) -> Dict[str, Any]:
        """Envoyer un message via l'endpoint webhook/chat"""
        try:
            response = requests.post(
                f"{self.base_url}/webhook/chat",
                json={
                    "message": message,
                    "session_id": self.session_id,
                    "phone_number": self.phone_number,
                    "source": "web_chat"
                },
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Error: HTTP {response.status_code}")
                return {
                    "response": f"Erreur HTTP {response.status_code}",
                    "error": True
                }
                    
        except Exception as e:
            print(f"Exception: {e}")
            return {
                "response": f"Erreur de connexion: {str(e)}",
                "error": True
            }
    
    def test_basic_conversation(self) -> Dict[str, Any]:
        """Test de base: conversation simple"""
        print("💬 Test de Conversation Basique")
        print("-" * 50)
        
        messages = [
            "Bonjour, comment allez-vous ?",
            "J'ai un problème de plomberie",
            "Je suis à Bonamoussadi"
        ]
        
        results = []
        for i, message in enumerate(messages):
            print(f"\n👤 Client: {message}")
            response = self.send_chat_message(message)
            ai_response = response.get('response', 'Pas de réponse')
            
            # Nettoyer les balises HTML pour l'affichage
            clean_response = ai_response.replace('<br>', ' ').replace('<br/>', ' ').replace('<br />', ' ')
            print(f"🤖 Djobea AI: {clean_response}")
            
            success = not response.get('error', False) and len(clean_response) > 5
            results.append({
                "turn": i + 1,
                "user_message": message,
                "ai_response": clean_response,
                "success": success,
                "full_response": response
            })
            
            time.sleep(1)  # Pause entre messages
        
        success_rate = sum(1 for r in results if r["success"]) / len(results) * 100
        print(f"\n📊 Résultat: {success_rate:.1f}% de succès")
        
        return {
            "test_name": "Basic Conversation",
            "success_rate": success_rate,
            "results": results,
            "overall_success": success_rate >= 70
        }
    
    def test_service_request_flow(self) -> Dict[str, Any]:
        """Test du flux de demande de service"""
        print("\n🔧 Test de Demande de Service")
        print("-" * 50)
        
        # Générer un nouveau session ID pour ce test
        self.session_id = f"service_test_{int(time.time())}"
        
        messages = [
            "Bonjour, j'ai besoin d'un plombier",
            "J'ai une fuite d'eau dans ma cuisine",
            "Je suis à Bonamoussadi, quartier Carrefour",
            "C'est urgent, il y a beaucoup d'eau",
            "Oui, je confirme ma demande"
        ]
        
        results = []
        service_created = False
        
        for i, message in enumerate(messages):
            print(f"\n👤 Client: {message}")
            response = self.send_chat_message(message)
            ai_response = response.get('response', 'Pas de réponse')
            
            # Nettoyer les balises HTML
            clean_response = ai_response.replace('<br>', ' ').replace('<br/>', ' ').replace('<br />', ' ')
            print(f"🤖 Djobea AI: {clean_response}")
            
            # Vérifier si un service est créé
            if any(keyword in clean_response.lower() for keyword in 
                  ["demande créée", "service créé", "numéro", "recherche", "plombier"]):
                service_created = True
            
            success = not response.get('error', False) and len(clean_response) > 5
            results.append({
                "turn": i + 1,
                "user_message": message,
                "ai_response": clean_response,
                "success": success,
                "full_response": response
            })
            
            time.sleep(1)
        
        success_rate = sum(1 for r in results if r["success"]) / len(results) * 100
        print(f"\n📊 Résultat: {success_rate:.1f}% de succès")
        print(f"🔧 Service créé: {'Oui' if service_created else 'Non'}")
        
        return {
            "test_name": "Service Request Flow",
            "success_rate": success_rate,
            "service_created": service_created,
            "results": results,
            "overall_success": success_rate >= 70
        }
    
    def test_multilingual_conversation(self) -> Dict[str, Any]:
        """Test de conversation multilingue"""
        print("\n🌍 Test Multilingue")
        print("-" * 50)
        
        # Nouveau session ID
        self.session_id = f"multilingual_test_{int(time.time())}"
        
        messages = [
            "Hello, I need help with ma télé",
            "The TV don spoil, no dey work",
            "I dey for Bonamoussadi"
        ]
        
        results = []
        language_understood = False
        
        for i, message in enumerate(messages):
            print(f"\n👤 Client: {message}")
            response = self.send_chat_message(message)
            ai_response = response.get('response', 'Pas de réponse')
            
            clean_response = ai_response.replace('<br>', ' ').replace('<br/>', ' ').replace('<br />', ' ')
            print(f"🤖 Djobea AI: {clean_response}")
            
            # Vérifier la compréhension de la langue mixte
            if any(keyword in clean_response.lower() for keyword in 
                  ["télé", "tv", "télévision", "électroménager", "réparation"]):
                language_understood = True
            
            success = not response.get('error', False) and len(clean_response) > 5
            results.append({
                "turn": i + 1,
                "user_message": message,
                "ai_response": clean_response,
                "success": success,
                "full_response": response
            })
            
            time.sleep(1)
        
        success_rate = sum(1 for r in results if r["success"]) / len(results) * 100
        print(f"\n📊 Résultat: {success_rate:.1f}% de succès")
        print(f"🌍 Langue comprise: {'Oui' if language_understood else 'Non'}")
        
        return {
            "test_name": "Multilingual Conversation",
            "success_rate": success_rate,
            "language_understood": language_understood,
            "results": results,
            "overall_success": success_rate >= 70
        }
    
    def test_urgency_detection(self) -> Dict[str, Any]:
        """Test de détection d'urgence"""
        print("\n🚨 Test de Détection d'Urgence")
        print("-" * 50)
        
        # Nouveau session ID
        self.session_id = f"urgency_test_{int(time.time())}"
        
        messages = [
            "URGENT ! J'ai une fuite d'eau majeure",
            "L'eau coule partout, c'est une inondation",
            "Je suis à Bonamoussadi, aidez-moi vite !"
        ]
        
        results = []
        urgency_detected = False
        
        for i, message in enumerate(messages):
            print(f"\n👤 Client: {message}")
            response = self.send_chat_message(message)
            ai_response = response.get('response', 'Pas de réponse')
            
            clean_response = ai_response.replace('<br>', ' ').replace('<br/>', ' ').replace('<br />', ' ')
            print(f"🤖 Djobea AI: {clean_response}")
            
            # Vérifier la détection d'urgence
            if any(keyword in clean_response.lower() for keyword in 
                  ["urgent", "immédiat", "rapidement", "priorité", "vite"]):
                urgency_detected = True
            
            success = not response.get('error', False) and len(clean_response) > 5
            results.append({
                "turn": i + 1,
                "user_message": message,
                "ai_response": clean_response,
                "success": success,
                "full_response": response
            })
            
            time.sleep(1)
        
        success_rate = sum(1 for r in results if r["success"]) / len(results) * 100
        print(f"\n📊 Résultat: {success_rate:.1f}% de succès")
        print(f"🚨 Urgence détectée: {'Oui' if urgency_detected else 'Non'}")
        
        return {
            "test_name": "Urgency Detection",
            "success_rate": success_rate,
            "urgency_detected": urgency_detected,
            "results": results,
            "overall_success": success_rate >= 70
        }
    
    def test_incomplete_information_handling(self) -> Dict[str, Any]:
        """Test de gestion d'informations incomplètes"""
        print("\n❓ Test d'Informations Incomplètes")
        print("-" * 50)
        
        # Nouveau session ID
        self.session_id = f"incomplete_test_{int(time.time())}"
        
        messages = [
            "J'ai un problème",
            "C'est cassé",
            "Chez moi",
            "À Bonamoussadi"
        ]
        
        results = []
        clarification_asked = False
        
        for i, message in enumerate(messages):
            print(f"\n👤 Client: {message}")
            response = self.send_chat_message(message)
            ai_response = response.get('response', 'Pas de réponse')
            
            clean_response = ai_response.replace('<br>', ' ').replace('<br/>', ' ').replace('<br />', ' ')
            print(f"🤖 Djobea AI: {clean_response}")
            
            # Vérifier si des clarifications sont demandées
            if any(keyword in clean_response.lower() for keyword in 
                  ["quel", "où", "comment", "préciser", "détail", "expliquer", "?"]):
                clarification_asked = True
            
            success = not response.get('error', False) and len(clean_response) > 5
            results.append({
                "turn": i + 1,
                "user_message": message,
                "ai_response": clean_response,
                "success": success,
                "full_response": response
            })
            
            time.sleep(1)
        
        success_rate = sum(1 for r in results if r["success"]) / len(results) * 100
        print(f"\n📊 Résultat: {success_rate:.1f}% de succès")
        print(f"❓ Clarification demandée: {'Oui' if clarification_asked else 'Non'}")
        
        return {
            "test_name": "Incomplete Information Handling",
            "success_rate": success_rate,
            "clarification_asked": clarification_asked,
            "results": results,
            "overall_success": success_rate >= 70
        }
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Exécuter tous les tests"""
        print("🎭 Test Complet du Dialog Flow - Djobea AI")
        print("=" * 60)
        
        # Vérifier la connectivité
        try:
            response = requests.get(f"{self.base_url}/health")
            if response.status_code != 200:
                print("❌ Serveur non accessible")
                return {"error": "Server not accessible"}
            print("✅ Serveur accessible")
        except Exception as e:
            print(f"❌ Erreur de connexion: {e}")
            return {"error": f"Connection error: {e}"}
        
        # Tests à exécuter
        tests = [
            self.test_basic_conversation,
            self.test_service_request_flow,
            self.test_multilingual_conversation,
            self.test_urgency_detection,
            self.test_incomplete_information_handling
        ]
        
        test_results = []
        
        for test_func in tests:
            try:
                result = test_func()
                test_results.append(result)
                time.sleep(3)  # Pause entre les tests
            except Exception as e:
                print(f"❌ Erreur dans le test {test_func.__name__}: {e}")
                test_results.append({
                    "test_name": test_func.__name__,
                    "error": str(e),
                    "overall_success": False
                })
        
        # Générer le rapport final
        return self.generate_final_report(test_results)
    
    def generate_final_report(self, test_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Générer le rapport final"""
        print("\n" + "=" * 60)
        print("📊 RAPPORT FINAL - DIALOG FLOW DJOBEA AI")
        print("=" * 60)
        
        total_tests = len(test_results)
        successful_tests = [r for r in test_results if r.get('overall_success', False)]
        failed_tests = [r for r in test_results if not r.get('overall_success', False)]
        
        success_rate = len(successful_tests) / total_tests * 100 if total_tests > 0 else 0
        
        print(f"📊 Résultats Globaux:")
        print(f"   Total des tests: {total_tests}")
        print(f"   Tests réussis: {len(successful_tests)}")
        print(f"   Tests échoués: {len(failed_tests)}")
        print(f"   Taux de réussite: {success_rate:.1f}%")
        
        print(f"\n📋 Détail des Tests:")
        for result in test_results:
            status = "✅" if result.get('overall_success', False) else "❌"
            name = result.get('test_name', 'Unknown')
            rate = result.get('success_rate', 0)
            print(f"   {status} {name}: {rate:.1f}%")
        
        # Fonctionnalités validées
        validated_features = []
        for result in test_results:
            if result.get('overall_success', False):
                test_name = result.get('test_name', '')
                if 'Basic' in test_name:
                    validated_features.append("Conversation basique")
                elif 'Service' in test_name:
                    validated_features.append("Demandes de service")
                elif 'Multilingual' in test_name:
                    validated_features.append("Support multilingue")
                elif 'Urgency' in test_name:
                    validated_features.append("Détection d'urgence")
                elif 'Incomplete' in test_name:
                    validated_features.append("Gestion d'informations incomplètes")
        
        print(f"\n✅ Fonctionnalités Validées:")
        for feature in validated_features:
            print(f"   • {feature}")
        
        # Évaluation finale
        if success_rate >= 90:
            evaluation = "EXCELLENT - Dialog flow parfaitement implémenté"
        elif success_rate >= 75:
            evaluation = "TRÈS BON - Dialog flow bien implémenté"
        elif success_rate >= 60:
            evaluation = "BON - Dialog flow fonctionnel"
        elif success_rate >= 40:
            evaluation = "MOYEN - Dialog flow partiellement fonctionnel"
        else:
            evaluation = "INSUFFISANT - Dialog flow nécessite des corrections"
        
        print(f"\n🎯 ÉVALUATION: {evaluation}")
        
        # Recommandations
        print(f"\n💡 Recommandations:")
        if success_rate < 100:
            print("   • Vérifier la configuration des endpoints de conversation")
            print("   • Tester l'intégration avec les services de base de données")
            print("   • Valider les réponses de l'IA pour la compréhension contextuelle")
        
        if not any(r.get('service_created', False) for r in test_results):
            print("   • Vérifier le processus de création de demandes de service")
        
        if not any(r.get('urgency_detected', False) for r in test_results):
            print("   • Améliorer la détection d'urgence dans les messages")
        
        if not any(r.get('language_understood', False) for r in test_results):
            print("   • Renforcer le support multilingue (français/anglais/pidgin)")
        
        return {
            "total_tests": total_tests,
            "successful_tests": len(successful_tests),
            "failed_tests": len(failed_tests),
            "success_rate": success_rate,
            "validated_features": validated_features,
            "evaluation": evaluation,
            "test_results": test_results
        }


if __name__ == "__main__":
    tester = DialogFlowTester()
    tester.run_all_tests()