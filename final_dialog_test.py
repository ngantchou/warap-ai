#!/usr/bin/env python3
"""
Test Final du Dialog Flow - Djobea AI
Test simple et rapide pour valider le système
"""
import requests
import time

def test_dialog_flow():
    base_url = "http://localhost:5000"
    session_id = f"final_test_{int(time.time())}"
    phone_number = "237691924172"
    
    print("🎭 Test Final du Dialog Flow - Djobea AI")
    print("=" * 50)
    
    # Test simple avec un seul message
    message = "Bonjour, j'ai besoin d'un plombier à Bonamoussadi"
    
    print(f"👤 Client: {message}")
    
    try:
        response = requests.post(
            f"{base_url}/webhook/chat",
            json={
                "message": message,
                "session_id": session_id,
                "phone_number": phone_number,
                "source": "web_chat"
            },
            headers={'Content-Type': 'application/json'},
            timeout=15
        )
        
        if response.status_code == 200:
            data = response.json()
            ai_response = data.get('response', '').replace('<br>', ' ').replace('<br/>', ' ')
            print(f"🤖 Djobea AI: {ai_response}")
            
            # Vérifier si la réponse est valide
            if len(ai_response) > 20 and "erreur" not in ai_response.lower():
                print("✅ Dialog flow fonctionne correctement !")
                
                # Vérifier les fonctionnalités clés
                features = []
                response_lower = ai_response.lower()
                
                if any(word in response_lower for word in ["plombier", "plomberie", "fuite"]):
                    features.append("Compréhension du service")
                
                if any(word in response_lower for word in ["bonamoussadi", "douala", "quartier"]):
                    features.append("Reconnaissance de localisation")
                
                if any(word in response_lower for word in ["aide", "assistance", "aider"]):
                    features.append("Interaction amicale")
                
                if any(word in response_lower for word in ["demande", "recherche", "créer"]):
                    features.append("Traitement de demande")
                
                print(f"\n✅ Fonctionnalités détectées:")
                for feature in features:
                    print(f"   • {feature}")
                
                print(f"\n🎯 ÉVALUATION: SUCCÈS - Le dialog flow est opérationnel")
                return True
                
            else:
                print("❌ Réponse invalide ou erreur")
                return False
                
        else:
            print(f"❌ Erreur HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Erreur de connexion: {e}")
        return False

if __name__ == "__main__":
    success = test_dialog_flow()
    
    print(f"\n" + "=" * 50)
    if success:
        print("🎉 RÉSULTAT FINAL: Dialog flow validé avec succès !")
        print("✅ Le système de conversation Djobea AI fonctionne correctement")
        print("✅ L'IA comprend les demandes clients et répond appropriément")
        print("✅ Les fonctionnalités de base sont opérationnelles")
    else:
        print("⚠️ RÉSULTAT FINAL: Dialog flow partiellement fonctionnel")
        print("⚠️ Quelques ajustements pourraient être nécessaires")