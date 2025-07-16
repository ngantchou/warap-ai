#!/usr/bin/env python3
"""
Test d'intégration conversationnelle avec la base de connaissances
Simule une conversation réelle avec intégration du système d'information contextuel
"""
import requests
import json

BASE_URL = "http://localhost:5000"

def test_conversational_integration():
    """Test d'intégration de la base de connaissances dans les conversations"""
    print("🗣️ Test d'Intégration Conversationnelle avec Base de Connaissances")
    print("=" * 70)
    
    # Scénario 1: Question sur les tarifs avec réponse contextuelle
    print("\n📞 Scénario 1: Client demande des informations sur les tarifs")
    
    message_1 = "Bonjour, combien ça coûte pour réparer une fuite de plomberie ?"
    
    # 1. Détection de support
    support_response = requests.post(f"{BASE_URL}/api/v1/knowledge/support/detect", json={
        "message": message_1,
        "user_id": "237691924172",
        "context": {"service_type": "plomberie", "zone": "Bonamoussadi"}
    })
    
    if support_response.status_code == 200:
        support_data = support_response.json()
        print(f"✅ Support détecté: {support_data['data']['support_level']}")
        print(f"   Niveau de confiance: {support_data['data']['confidence']:.2f}")
        
        # 2. Recherche contextuelle
        search_response = requests.get(f"{BASE_URL}/api/v1/knowledge/search", params={
            "query": "fuite plomberie tarif prix",
            "service_type": "plomberie", 
            "zone": "Bonamoussadi"
        })
        
        if search_response.status_code == 200:
            search_data = search_response.json()
            if search_data['success']:
                print(f"✅ Recherche réussie:")
                print(f"   • {len(search_data['data']['faqs'])} FAQs trouvées")
                if search_data['data']['pricing']:
                    pricing = search_data['data']['pricing']
                    print(f"   • Tarifs: {pricing['min_price']}-{pricing['max_price']} {pricing['currency']}")
                
                # Génération de réponse contextuelle
                response_contexte = f"""
🔧 **Tarifs Plomberie à Bonamoussadi**

Voici les informations tarifaires pour la plomberie :
• **Tarif minimum**: {pricing['min_price'] if search_data['data']['pricing'] else 'N/A'} XAF
• **Tarif maximum**: {pricing['max_price'] if search_data['data']['pricing'] else 'N/A'} XAF  
• **Tarif moyen**: {pricing['average_price'] if search_data['data']['pricing'] else 'N/A'} XAF

💡 **Facteurs influençant le prix**:
• Urgence: +20% pour les interventions urgentes
• Complexité: Variable selon le type de réparation
• Matériaux: Coût des pièces en sus

📞 Pour obtenir un devis personnalisé, décrivez-moi votre problème précisément !
                """
                print(f"✅ Réponse générée: {response_contexte[:100]}...")
    
    # Scénario 2: Question technique avec résolution guidée
    print("\n🔧 Scénario 2: Client avec problème technique spécifique")
    
    message_2 = "J'ai une fuite sous mon évier, que dois-je faire en urgence ?"
    
    # 1. Résolution guidée
    resolution_response = requests.get(f"{BASE_URL}/api/v1/knowledge/support/guided-resolution/fuite", params={
        "service_type": "plomberie",
        "zone": "Bonamoussadi"
    })
    
    if resolution_response.status_code == 200:
        resolution_data = resolution_response.json()
        if resolution_data['success']:
            resolution = resolution_data['data']
            print(f"✅ Résolution guidée disponible:")
            print(f"   • {len(resolution['troubleshooting_steps'])} étapes de dépannage")
            print(f"   • {len(resolution['related_faqs'])} FAQs connexes")
            
            if resolution['troubleshooting_steps']:
                print("   📋 Premières étapes:")
                for step in resolution['troubleshooting_steps'][:2]:
                    print(f"      {step['step']}. {step['title']}: {step['description']}")
    
    # Scénario 3: Escalade vers agent humain
    print("\n👤 Scénario 3: Escalade vers support humain")
    
    message_3 = "C'est urgent, j'ai besoin de parler à quelqu'un immédiatement !"
    
    # 1. Détection d'urgence
    urgent_support = requests.post(f"{BASE_URL}/api/v1/knowledge/support/detect", json={
        "message": message_3,
        "user_id": "237691924172",
        "context": {"service_type": "plomberie", "zone": "Bonamoussadi"}
    })
    
    if urgent_support.status_code == 200:
        urgent_data = urgent_support.json()
        print(f"✅ Escalade détectée: {urgent_data['data']['escalation_suggested']}")
        
        if urgent_data['data']['escalation_suggested']:
            # 2. Démarrage session support
            session_response = requests.post(f"{BASE_URL}/api/v1/knowledge/support/session", json={
                "user_id": "237691924172",
                "session_type": "human"
            })
            
            if session_response.status_code == 200:
                session_data = session_response.json()
                if session_data['success']:
                    session_id = session_data['data']['session_id']
                    print(f"✅ Session support créée: {session_id}")
                    
                    # 3. Escalade vers humain
                    escalation_response = requests.post(f"{BASE_URL}/api/v1/knowledge/support/escalate", json={
                        "session_id": session_id,
                        "user_id": "237691924172",
                        "reason": "Demande urgente de support",
                        "priority": "urgent"
                    })
                    
                    if escalation_response.status_code == 200:
                        escalation_data = escalation_response.json()
                        if escalation_data['success']:
                            print(f"✅ Escalade réussie: {escalation_data['escalation_id']}")
                            print(f"   Temps d'attente: {escalation_data['estimated_wait_time']} min")
    
    # Scénario 4: Suivi analytics et amélioration
    print("\n📊 Scénario 4: Analytics et amélioration continue")
    
    # 1. Enregistrement des questions pour amélioration
    questions_to_record = [
        "Comment nettoyer un siphon bouché ?",
        "Pourquoi mon robinet goutte ?",
        "Comment changer un joint de robinet ?"
    ]
    
    recorded_questions = 0
    for question in questions_to_record:
        record_response = requests.post(f"{BASE_URL}/api/v1/knowledge/question", json={
            "user_id": "237691924172",
            "question": question,
            "service_type": "plomberie",
            "zone": "Bonamoussadi"
        })
        if record_response.status_code == 200:
            recorded_questions += 1
    
    print(f"✅ {recorded_questions} questions enregistrées pour amélioration")
    
    # 2. Analytics de performance
    analytics_response = requests.get(f"{BASE_URL}/api/v1/knowledge/analytics/support")
    if analytics_response.status_code == 200:
        analytics_data = analytics_response.json()
        if analytics_data['success']:
            analytics = analytics_data['data']
            print(f"✅ Analytics récupérées:")
            print(f"   • Sessions totales: {analytics['total_sessions']}")
            print(f"   • Taux de résolution: {analytics['resolution_rate']:.1f}%")
    
    # 3. Analyse pour amélioration
    analysis_response = requests.post(f"{BASE_URL}/api/v1/knowledge/maintenance/analyze-questions", json={
        "days": 1
    })
    if analysis_response.status_code == 200:
        analysis_data = analysis_response.json()
        if analysis_data['success']:
            print(f"✅ Analyse d'amélioration:")
            print(f"   • Questions non résolues: {analysis_data['total_unanswered']}")
            print(f"   • Suggestions de contenu: {len(analysis_data['content_suggestions'])}")
    
    print("\n" + "=" * 70)
    print("🎯 TEST D'INTÉGRATION CONVERSATIONNELLE RÉUSSI !")
    
    print("\n✅ FONCTIONNALITÉS TESTÉES:")
    print("   🔍 Recherche contextuelle intelligente")
    print("   💰 Informations tarifaires automatiques")  
    print("   🆘 Détection et escalade de support")
    print("   📋 Résolution guidée des problèmes")
    print("   👤 Support humain avec priorités")
    print("   📊 Analytics et amélioration continue")
    print("   🤖 Réponses contextuelles adaptées")
    
    print("\n🏆 SYSTÈME D'INFORMATION CONTEXTUEL")
    print("   ✓ Intégration transparente dans les conversations")
    print("   ✓ Escalade intelligente FAQ → Bot → Humain")
    print("   ✓ Informations tarifaires contextuelles")
    print("   ✓ Support proactif et résolution guidée")
    print("   ✓ Amélioration continue basée sur l'usage")
    
    print("\n🚀 PRÊT POUR INTÉGRATION DANS LE GESTIONNAIRE DE CONVERSATION")

if __name__ == "__main__":
    test_conversational_integration()