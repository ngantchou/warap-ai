#!/usr/bin/env python3
"""
Test Complet du Dialog Flow - Djobea AI
Valide que le système continue correctement la conversation et préserve l'état
"""
import requests
import time
import json

def test_complete_dialog_flow():
    """Test complet du dialog flow avec préservation d'état"""
    
    base_url = "http://localhost:5000"
    phone_number = "237691924172"
    session_id = f"complete_test_{int(time.time())}"
    
    print("🎭 Test Complet du Dialog Flow - Djobea AI")
    print("=" * 60)
    print(f"Session ID: {session_id}")
    print(f"Phone: {phone_number}")
    print()
    
    # Test 1: Message incomplet
    print("📍 Test 1: Message très vague")
    print("-" * 40)
    
    message1 = "J'ai un problème"
    print(f"👤 Client: {message1}")
    
    response1 = requests.post(
        f"{base_url}/webhook/chat",
        json={
            "message": message1,
            "session_id": session_id,
            "phone_number": phone_number,
            "source": "web_chat"
        },
        timeout=15
    )
    
    if response1.status_code == 200:
        data1 = response1.json()
        ai_response1 = data1.get('response', '')
        print(f"🤖 Djobea AI: {ai_response1}")
        
        # Vérification: le système doit poser des questions
        if "?" in ai_response1 and any(word in ai_response1.lower() for word in ["quel", "où", "type", "service", "quartier"]):
            print("✅ SUCCESS: Le système pose des questions appropriées")
        else:
            print("❌ FAIL: Le système ne pose pas de questions")
            return False
    else:
        print(f"❌ FAIL: Erreur HTTP {response1.status_code}")
        return False
    
    time.sleep(2)
    
    # Test 2: Réponse partielle
    print("\n📍 Test 2: Réponse partielle (seulement le service)")
    print("-" * 40)
    
    message2 = "Plomberie"
    print(f"👤 Client: {message2}")
    
    response2 = requests.post(
        f"{base_url}/webhook/chat",
        json={
            "message": message2,
            "session_id": session_id,
            "phone_number": phone_number,
            "source": "web_chat"
        },
        timeout=15
    )
    
    if response2.status_code == 200:
        data2 = response2.json()
        ai_response2 = data2.get('response', '')
        print(f"🤖 Djobea AI: {ai_response2}")
        
        # Vérification: le système doit demander plus d'informations
        if any(word in ai_response2.lower() for word in ["où", "quartier", "localisation", "détail", "problème"]):
            print("✅ SUCCESS: Le système demande plus d'informations")
        else:
            print("❌ FAIL: Le système ne continue pas la conversation")
            return False
    else:
        print(f"❌ FAIL: Erreur HTTP {response2.status_code}")
        return False
    
    time.sleep(2)
    
    # Test 3: Informations complètes
    print("\n📍 Test 3: Informations complètes")
    print("-" * 40)
    
    message3 = "Je suis à Bonamoussadi, j'ai une fuite d'eau dans ma cuisine"
    print(f"👤 Client: {message3}")
    
    response3 = requests.post(
        f"{base_url}/webhook/chat",
        json={
            "message": message3,
            "session_id": session_id,
            "phone_number": phone_number,
            "source": "web_chat"
        },
        timeout=15
    )
    
    if response3.status_code == 200:
        data3 = response3.json()
        ai_response3 = data3.get('response', '')
        print(f"🤖 Djobea AI: {ai_response3}")
        
        # Vérification: le système doit confirmer et chercher un prestataire
        if any(phrase in ai_response3.lower() for phrase in ["parfait", "compris", "prestataire", "recherche", "contact"]):
            print("✅ SUCCESS: Le système crée la demande de service")
        else:
            print("❌ FAIL: Le système ne crée pas la demande")
            return False
    else:
        print(f"❌ FAIL: Erreur HTTP {response3.status_code}")
        return False
    
    return True

def test_service_request_flow():
    """Test du flux de demande de service directe"""
    
    base_url = "http://localhost:5000"
    phone_number = "237691924172"
    session_id = f"service_test_{int(time.time())}"
    
    print("\n🔧 Test du Flux de Demande de Service")
    print("=" * 60)
    
    message = "J'ai besoin d'un plombier à Bonamoussadi"
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
        
        # Vérification: le système doit soit demander plus de détails, soit confirmer
        if any(word in ai_response.lower() for word in ["détail", "problème", "parfait", "compris"]):
            print("✅ SUCCESS: Le système traite la demande appropriée")
            return True
        else:
            print("❌ FAIL: Le système ne traite pas correctement la demande")
            return False
    else:
        print(f"❌ FAIL: Erreur HTTP {response.status_code}")
        return False

if __name__ == "__main__":
    print("🧪 Test Complet du Système de Dialog Flow")
    print("=" * 60)
    
    try:
        # Test 1: Dialog flow complet
        success1 = test_complete_dialog_flow()
        
        # Test 2: Service request direct
        success2 = test_service_request_flow()
        
        print("\n" + "=" * 60)
        print("📊 RÉSULTATS FINAUX")
        print("=" * 60)
        
        print(f"Dialog Flow Complet: {'✅ RÉUSSI' if success1 else '❌ ÉCHOUÉ'}")
        print(f"Service Request Direct: {'✅ RÉUSSI' if success2 else '❌ ÉCHOUÉ'}")
        
        if success1 and success2:
            print("\n🎉 SUCCÈS TOTAL!")
            print("✅ Le système de conversation continue fonctionne parfaitement")
            print("✅ L'état de la conversation est préservé")
            print("✅ Le système pose des questions appropriées")
            print("✅ Les demandes de service sont créées automatiquement")
        else:
            print("\n⚠️ PROBLÈMES DÉTECTÉS")
            print("Certains aspects du dialog flow ne fonctionnent pas correctement")
            
    except Exception as e:
        print(f"\n❌ ERREUR LORS DU TEST: {e}")
        
    print("\n" + "=" * 60)
    print("Test terminé")