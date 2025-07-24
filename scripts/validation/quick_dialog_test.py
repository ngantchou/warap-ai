#!/usr/bin/env python3
"""
Test Rapide du Dialog Flow - Djobea AI
Test rapide pour valider le fonctionnement du système conversationnel
"""
import requests
import json
import time
from datetime import datetime


class QuickDialogTester:
    
    def __init__(self):
        self.base_url = "http://localhost:5000"
        self.session_id = f"quick_test_{int(time.time())}"
        self.phone_number = "237691924172"
        
    def send_message(self, message: str) -> dict:
        """Envoyer un message et récupérer la réponse"""
        try:
            response = requests.post(
                f"{self.base_url}/webhook/chat",
                json={
                    "message": message,
                    "session_id": self.session_id,
                    "phone_number": self.phone_number,
                    "source": "web_chat"
                },
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            return {"error": str(e)}
    
    def test_simple_conversation(self):
        """Test de conversation simple"""
        print("🎭 Test Rapide du Dialog Flow - Djobea AI")
        print("=" * 50)
        
        # Scénario de test simple
        conversation = [
            "Bonjour, j'ai besoin d'un plombier",
            "J'ai une fuite d'eau dans ma cuisine",
            "Je suis à Bonamoussadi"
        ]
        
        results = []
        
        for i, message in enumerate(conversation):
            print(f"\n👤 Client: {message}")
            
            response = self.send_message(message)
            
            if "error" in response:
                print(f"❌ Erreur: {response['error']}")
                results.append({"success": False, "error": response["error"]})
            else:
                ai_response = response.get('response', '').replace('<br>', ' ').replace('<br/>', ' ')
                print(f"🤖 Djobea AI: {ai_response}")
                
                # Évaluer la qualité de la réponse
                success = (
                    len(ai_response) > 10 and 
                    ai_response.lower() != "service temporairement indisponible" and
                    "erreur" not in ai_response.lower()
                )
                
                results.append({
                    "success": success,
                    "message": message,
                    "response": ai_response,
                    "response_data": response
                })
            
            time.sleep(1)
        
        # Évaluer les résultats
        successful = sum(1 for r in results if r.get("success", False))
        total = len(results)
        success_rate = (successful / total) * 100 if total > 0 else 0
        
        print(f"\n📊 Résultats du Test:")
        print(f"   Messages traités: {total}")
        print(f"   Réponses réussies: {successful}")
        print(f"   Taux de réussite: {success_rate:.1f}%")
        
        # Vérifier les fonctionnalités clés
        features_detected = []
        for result in results:
            if result.get("success", False):
                response_text = result.get("response", "").lower()
                if any(word in response_text for word in ["plombier", "fuite", "eau", "plomberie"]):
                    features_detected.append("Compréhension du service")
                if any(word in response_text for word in ["bonamoussadi", "douala", "quartier"]):
                    features_detected.append("Reconnaissance de localisation")
                if any(word in response_text for word in ["aide", "assistance", "service"]):
                    features_detected.append("Interaction amicale")
        
        features_detected = list(set(features_detected))  # Supprimer les doublons
        
        print(f"\n✅ Fonctionnalités Détectées:")
        for feature in features_detected:
            print(f"   • {feature}")
        
        # Évaluation finale
        if success_rate >= 80:
            evaluation = "✅ SUCCÈS - Dialog flow fonctionne correctement"
        elif success_rate >= 60:
            evaluation = "⚠️ PARTIEL - Dialog flow partiellement fonctionnel"
        else:
            evaluation = "❌ ÉCHEC - Dialog flow nécessite des corrections"
        
        print(f"\n🎯 ÉVALUATION: {evaluation}")
        
        return {
            "success_rate": success_rate,
            "features_detected": features_detected,
            "evaluation": evaluation,
            "results": results
        }


if __name__ == "__main__":
    tester = QuickDialogTester()
    tester.test_simple_conversation()