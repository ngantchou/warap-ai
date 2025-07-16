#!/usr/bin/env python3
"""
Test Direct du Dialog Flow - Djobea AI
Test complet du système de conversation via l'endpoint chat
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
        """Envoyer un message via l'endpoint chat"""
        try:
            response = requests.post(
                f"{self.base_url}/chat",
                json={
                    "message": message,
                    "phone_number": self.phone_number,
                    "session_id": self.session_id
                },
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                # Essayer avec l'endpoint v2 si disponible
                response_v2 = requests.post(
                    f"{self.base_url}/chat-v2",
                    json={
                        "message": message,
                        "phone_number": self.phone_number,
                        "session_id": self.session_id
                    },
                    headers={'Content-Type': 'application/json'}
                )
                
                if response_v2.status_code == 200:
                    return response_v2.json()
                else:
                    return {
                        "response": "Erreur de communication",
                        "error": f"HTTP {response.status_code}"
                    }
                    
        except Exception as e:
            return {
                "response": "Erreur de connexion",
                "error": str(e)
            }
    
    def test_simple_plumbing_request(self) -> Dict[str, Any]:
        """Test 1: Demande simple de plomberie"""
        print("🔧 Test 1: Demande Simple de Plomberie")
        print("-" * 50)
        
        conversations = [
            "Bonjour, j'ai besoin d'un plombier",
            "J'ai une fuite d'eau dans ma cuisine",
            "Je suis à Bonamoussadi"
        ]
        
        results = []
        for i, message in enumerate(conversations):
            print(f"\n👤 Client: {message}")
            response = self.send_chat_message(message)
            ai_response = response.get('response', 'Pas de réponse')
            print(f"🤖 Djobea AI: {ai_response}")
            
            results.append({
                "turn": i + 1,
                "user_message": message,
                "ai_response": ai_response,
                "success": len(ai_response) > 10 and "erreur" not in ai_response.lower()
            })
        
        success_rate = sum(1 for r in results if r["success"]) / len(results) * 100
        print(f"\n📊 Résultat: {success_rate:.1f}% de succès")
        
        return {
            "test_name": "Simple Plumbing Request",
            "success_rate": success_rate,
            "results": results,
            "overall_success": success_rate >= 70
        }
    
    def test_urgency_handling(self) -> Dict[str, Any]:
        """Test 2: Gestion d'urgence"""
        print("\n🚨 Test 2: Gestion d'Urgence")
        print("-" * 50)
        
        conversations = [
            "URGENT ! J'ai une fuite d'eau majeure",
            "L'eau coule partout dans ma maison",
            "Je suis à Bonamoussadi, besoin d'aide immédiate"
        ]
        
        results = []
        for i, message in enumerate(conversations):
            print(f"\n👤 Client: {message}")
            response = self.send_chat_message(message)
            ai_response = response.get('response', 'Pas de réponse')
            print(f"🤖 Djobea AI: {ai_response}")
            
            # Vérifier si l'urgence est reconnue
            urgency_detected = any(word in ai_response.lower() for word in 
                                 ["urgent", "immédiat", "rapidement", "priorité"])
            
            results.append({
                "turn": i + 1,
                "user_message": message,
                "ai_response": ai_response,
                "urgency_detected": urgency_detected,
                "success": len(ai_response) > 10 and "erreur" not in ai_response.lower()
            })
        
        success_rate = sum(1 for r in results if r["success"]) / len(results) * 100
        urgency_rate = sum(1 for r in results if r.get("urgency_detected", False)) / len(results) * 100
        
        print(f"\n📊 Résultat: {success_rate:.1f}% de succès")
        print(f"🚨 Urgence détectée: {urgency_rate:.1f}%")
        
        return {
            "test_name": "Urgency Handling",
            "success_rate": success_rate,
            "urgency_detection_rate": urgency_rate,
            "results": results,
            "overall_success": success_rate >= 70 and urgency_rate >= 50
        }
    
    def test_multilingual_support(self) -> Dict[str, Any]:
        """Test 3: Support multilingue"""
        print("\n🌍 Test 3: Support Multilingue")
        print("-" * 50)
        
        conversations = [
            "Bonjour, I need help with ma télé",
            "The TV don spoil completely",
            "I dey for Bonamoussadi"
        ]
        
        results = []
        for i, message in enumerate(conversations):
            print(f"\n👤 Client: {message}")
            response = self.send_chat_message(message)
            ai_response = response.get('response', 'Pas de réponse')
            print(f"🤖 Djobea AI: {ai_response}")
            
            # Vérifier si la langue mixte est comprise
            language_understood = any(word in ai_response.lower() for word in 
                                    ["télé", "tv", "électroménager", "réparation"])
            
            results.append({
                "turn": i + 1,
                "user_message": message,
                "ai_response": ai_response,
                "language_understood": language_understood,
                "success": len(ai_response) > 10 and "erreur" not in ai_response.lower()
            })
        
        success_rate = sum(1 for r in results if r["success"]) / len(results) * 100
        language_rate = sum(1 for r in results if r.get("language_understood", False)) / len(results) * 100
        
        print(f"\n📊 Résultat: {success_rate:.1f}% de succès")
        print(f"🌍 Langue comprise: {language_rate:.1f}%")
        
        return {
            "test_name": "Multilingual Support",
            "success_rate": success_rate,
            "language_comprehension_rate": language_rate,
            "results": results,
            "overall_success": success_rate >= 70 and language_rate >= 50
        }
    
    def test_incomplete_information(self) -> Dict[str, Any]:
        """Test 4: Informations incomplètes"""
        print("\n❓ Test 4: Informations Incomplètes")
        print("-" * 50)
        
        conversations = [
            "J'ai un problème",
            "C'est cassé",
            "Dans ma maison",
            "À Bonamoussadi"
        ]
        
        results = []
        for i, message in enumerate(conversations):
            print(f"\n👤 Client: {message}")
            response = self.send_chat_message(message)
            ai_response = response.get('response', 'Pas de réponse')
            print(f"🤖 Djobea AI: {ai_response}")
            
            # Vérifier si des questions de clarification sont posées
            clarification_asked = any(word in ai_response.lower() for word in 
                                    ["quel", "où", "comment", "préciser", "détail"])
            
            results.append({
                "turn": i + 1,
                "user_message": message,
                "ai_response": ai_response,
                "clarification_asked": clarification_asked,
                "success": len(ai_response) > 10 and "erreur" not in ai_response.lower()
            })
        
        success_rate = sum(1 for r in results if r["success"]) / len(results) * 100
        clarification_rate = sum(1 for r in results if r.get("clarification_asked", False)) / len(results) * 100
        
        print(f"\n📊 Résultat: {success_rate:.1f}% de succès")
        print(f"❓ Clarifications demandées: {clarification_rate:.1f}%")
        
        return {
            "test_name": "Incomplete Information",
            "success_rate": success_rate,
            "clarification_rate": clarification_rate,
            "results": results,
            "overall_success": success_rate >= 70 and clarification_rate >= 50
        }
    
    def test_service_creation(self) -> Dict[str, Any]:
        """Test 5: Création de service complet"""
        print("\n✅ Test 5: Création de Service Complet")
        print("-" * 50)
        
        conversations = [
            "J'ai besoin d'un électricien",
            "Mes prises ne marchent plus",
            "Je suis à Bonamoussadi",
            "C'est urgent",
            "Oui, je confirme la demande"
        ]
        
        results = []
        service_created = False
        
        for i, message in enumerate(conversations):
            print(f"\n👤 Client: {message}")
            response = self.send_chat_message(message)
            ai_response = response.get('response', 'Pas de réponse')
            print(f"🤖 Djobea AI: {ai_response}")
            
            # Vérifier si un service est créé
            if "demande créée" in ai_response.lower() or "numéro" in ai_response.lower():
                service_created = True
            
            results.append({
                "turn": i + 1,
                "user_message": message,
                "ai_response": ai_response,
                "success": len(ai_response) > 10 and "erreur" not in ai_response.lower()
            })
        
        success_rate = sum(1 for r in results if r["success"]) / len(results) * 100
        
        print(f"\n📊 Résultat: {success_rate:.1f}% de succès")
        print(f"✅ Service créé: {'Oui' if service_created else 'Non'}")
        
        return {
            "test_name": "Service Creation",
            "success_rate": success_rate,
            "service_created": service_created,
            "results": results,
            "overall_success": success_rate >= 70 and service_created
        }
    
    def test_price_inquiry(self) -> Dict[str, Any]:
        """Test 6: Demande de prix"""
        print("\n💰 Test 6: Demande de Prix")
        print("-" * 50)
        
        conversations = [
            "Combien coûte un plombier ?",
            "Pour réparer une fuite d'eau",
            "À Bonamoussadi"
        ]
        
        results = []
        price_provided = False
        
        for i, message in enumerate(conversations):
            print(f"\n👤 Client: {message}")
            response = self.send_chat_message(message)
            ai_response = response.get('response', 'Pas de réponse')
            print(f"🤖 Djobea AI: {ai_response}")
            
            # Vérifier si un prix est fourni
            if any(word in ai_response.lower() for word in ["xaf", "franc", "prix", "coût", "tarif"]):
                price_provided = True
            
            results.append({
                "turn": i + 1,
                "user_message": message,
                "ai_response": ai_response,
                "success": len(ai_response) > 10 and "erreur" not in ai_response.lower()
            })
        
        success_rate = sum(1 for r in results if r["success"]) / len(results) * 100
        
        print(f"\n📊 Résultat: {success_rate:.1f}% de succès")
        print(f"💰 Prix fourni: {'Oui' if price_provided else 'Non'}")
        
        return {
            "test_name": "Price Inquiry",
            "success_rate": success_rate,
            "price_provided": price_provided,
            "results": results,
            "overall_success": success_rate >= 70 and price_provided
        }
    
    def test_frustration_escalation(self) -> Dict[str, Any]:
        """Test 7: Escalation de frustration"""
        print("\n😤 Test 7: Escalation de Frustration")
        print("-" * 50)
        
        conversations = [
            "Ça fait 3 fois que j'appelle !",
            "Votre service ne marche pas",
            "Je veux parler à un responsable"
        ]
        
        results = []
        escalation_detected = False
        
        for i, message in enumerate(conversations):
            print(f"\n👤 Client: {message}")
            response = self.send_chat_message(message)
            ai_response = response.get('response', 'Pas de réponse')
            print(f"🤖 Djobea AI: {ai_response}")
            
            # Vérifier si une escalation est détectée
            if any(word in ai_response.lower() for word in 
                  ["agent", "responsable", "escalation", "transfert", "humain"]):
                escalation_detected = True
            
            results.append({
                "turn": i + 1,
                "user_message": message,
                "ai_response": ai_response,
                "success": len(ai_response) > 10 and "erreur" not in ai_response.lower()
            })
        
        success_rate = sum(1 for r in results if r["success"]) / len(results) * 100
        
        print(f"\n📊 Résultat: {success_rate:.1f}% de succès")
        print(f"😤 Escalation détectée: {'Oui' if escalation_detected else 'Non'}")
        
        return {
            "test_name": "Frustration Escalation",
            "success_rate": success_rate,
            "escalation_detected": escalation_detected,
            "results": results,
            "overall_success": success_rate >= 70 and escalation_detected
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
        
        # Exécuter les tests
        test_results = []
        
        tests = [
            self.test_simple_plumbing_request,
            self.test_urgency_handling,
            self.test_multilingual_support,
            self.test_incomplete_information,
            self.test_service_creation,
            self.test_price_inquiry,
            self.test_frustration_escalation
        ]
        
        for test_func in tests:
            try:
                result = test_func()
                test_results.append(result)
                time.sleep(2)  # Pause entre les tests
            except Exception as e:
                print(f"❌ Erreur dans le test: {e}")
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
        print("📊 RAPPORT FINAL - DIALOG FLOW")
        print("=" * 60)
        
        total_tests = len(test_results)
        successful_tests = [r for r in test_results if r.get('overall_success', False)]
        failed_tests = [r for r in test_results if not r.get('overall_success', False)]
        
        success_rate = len(successful_tests) / total_tests * 100
        
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
        if any(r.get('test_name') == 'Simple Plumbing Request' and r.get('overall_success') for r in test_results):
            validated_features.append("Demandes simples")
        if any(r.get('test_name') == 'Urgency Handling' and r.get('overall_success') for r in test_results):
            validated_features.append("Gestion d'urgence")
        if any(r.get('test_name') == 'Multilingual Support' and r.get('overall_success') for r in test_results):
            validated_features.append("Support multilingue")
        if any(r.get('test_name') == 'Service Creation' and r.get('overall_success') for r in test_results):
            validated_features.append("Création de services")
        if any(r.get('test_name') == 'Price Inquiry' and r.get('overall_success') for r in test_results):
            validated_features.append("Informations de prix")
        if any(r.get('test_name') == 'Frustration Escalation' and r.get('overall_success') for r in test_results):
            validated_features.append("Escalation de frustration")
        
        print(f"\n✅ Fonctionnalités Validées:")
        for feature in validated_features:
            print(f"   • {feature}")
        
        # Évaluation finale
        if success_rate >= 85:
            evaluation = "EXCELLENT - Dialog flow parfaitement implémenté"
        elif success_rate >= 70:
            evaluation = "TRÈS BON - Dialog flow bien implémenté"
        elif success_rate >= 50:
            evaluation = "BON - Dialog flow fonctionnel avec améliorations possibles"
        else:
            evaluation = "INSUFFISANT - Dialog flow nécessite des corrections"
        
        print(f"\n🎯 ÉVALUATION: {evaluation}")
        
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