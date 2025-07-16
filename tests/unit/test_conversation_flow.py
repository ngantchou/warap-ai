#!/usr/bin/env python3
"""
Test du flux de conversation pour vérifier que le système demande des informations
"""
import requests
import time

def test_conversation_flow():
    base_url = "http://localhost:5000"
    phone_number = "237691924172"
    
    print("🎭 Test du Flux de Conversation - Djobea AI")
    print("=" * 50)
    
    # Scénario 1: Message incomplet qui devrait déclencher des questions
    print("\n📍 Scénario 1: Message incomplet")
    print("-" * 30)
    
    session_id = f"flow_test_{int(time.time())}"
    
    try:
        # Message très vague
        message = "J'ai un problème"
        print(f"👤 Client: {message}")
        
        response = requests.post(
            f"{base_url}/webhook/chat",
            json={
                "message": message,
                "session_id": session_id,
                "phone_number": phone_number,
                "source": "web_chat"
            },
            timeout=15
        )
        
        if response.status_code == 200:
            data = response.json()
            ai_response = data.get('response', '')
            print(f"🤖 Djobea AI: {ai_response}")
            
            # Vérifier si le système pose des questions
            if "?" in ai_response or any(word in ai_response.lower() for word in ["quel", "où", "comment", "préciser", "détail"]):
                print("✅ Le système pose des questions pour obtenir plus d'informations")
                return True
            else:
                print("❌ Le système ne pose pas de questions")
                return False
        else:
            print(f"❌ Erreur HTTP: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False

def test_incomplete_service_request():
    base_url = "http://localhost:5000"
    phone_number = "237691924172"
    
    print("\n📍 Scénario 2: Demande de service incomplète")
    print("-" * 30)
    
    session_id = f"incomplete_test_{int(time.time())}"
    
    try:
        # Message avec service mais sans localisation
        message = "J'ai besoin d'un plombier"
        print(f"👤 Client: {message}")
        
        response = requests.post(
            f"{base_url}/webhook/chat",
            json={
                "message": message,
                "session_id": session_id,
                "phone_number": phone_number,
                "source": "web_chat"
            },
            timeout=15
        )
        
        if response.status_code == 200:
            data = response.json()
            ai_response = data.get('response', '')
            print(f"🤖 Djobea AI: {ai_response}")
            
            # Vérifier si le système demande plus d'informations
            if any(word in ai_response.lower() for word in ["quartier", "où", "localisation", "adresse", "lieu"]):
                print("✅ Le système demande la localisation")
                return True
            elif "?" in ai_response and len(ai_response) > 50:
                print("✅ Le système pose une question pour plus d'informations")
                return True
            else:
                print("❌ Le système ne demande pas plus d'informations")
                print(f"   Réponse reçue: {ai_response}")
                return False
        else:
            print(f"❌ Erreur HTTP: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False

if __name__ == "__main__":
    print("🔍 Test du système de conversation continue")
    
    # Test 1: Message très vague
    success1 = test_conversation_flow()
    
    # Test 2: Service sans localisation
    success2 = test_incomplete_service_request()
    
    print("\n" + "=" * 50)
    print("📊 RÉSULTATS")
    print("=" * 50)
    
    print(f"Test 1 (Message vague): {'✅ RÉUSSI' if success1 else '❌ ÉCHOUÉ'}")
    print(f"Test 2 (Service incomplet): {'✅ RÉUSSI' if success2 else '❌ ÉCHOUÉ'}")
    
    if success1 and success2:
        print("\n🎉 SUCCÈS: Le système pose des questions pour obtenir plus d'informations")
    else:
        print("\n⚠️ PROBLÈME: Le système ne continue pas correctement la conversation")
        print("Le système devrait poser des questions quand les informations sont incomplètes.")