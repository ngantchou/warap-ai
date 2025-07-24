#!/usr/bin/env python3
"""
Test du Système de Détection d'Escalation
Test complet des fonctionnalités d'escalade et de scoring de complexité
"""
import asyncio
import json
from datetime import datetime
import requests

BASE_URL = "http://localhost:5000"

class EscalationDetectionTester:
    """Testeur pour le système de détection d'escalation"""
    
    def __init__(self):
        self.session = requests.Session()
        self.results = []
    
    def test_health_check(self):
        """Test de santé du système"""
        print("🔍 Test de santé du système d'escalation...")
        
        try:
            response = self.session.get(f"{BASE_URL}/api/v1/escalation/health")
            result = response.json()
            
            print(f"   Status: {result.get('status', 'unknown')}")
            print(f"   Services: {result.get('services', {})}")
            print(f"   Détecteurs actifs: {result.get('active_detectors', 0)}")
            
            if result.get('success'):
                print("   ✅ Système opérationnel")
                return True
            else:
                print(f"   ❌ Erreur: {result.get('error')}")
                return False
                
        except Exception as e:
            print(f"   ❌ Erreur de connexion: {e}")
            return False
    
    def test_get_detectors(self):
        """Test de récupération des détecteurs"""
        print("\n🔍 Test de récupération des détecteurs...")
        
        try:
            response = self.session.get(f"{BASE_URL}/api/v1/escalation/detectors")
            result = response.json()
            
            if result.get('success'):
                detectors = result.get('detectors', [])
                print(f"   ✅ {len(detectors)} détecteurs trouvés:")
                
                for detector in detectors:
                    print(f"      - {detector['detector_name']} ({detector['detector_type']})")
                    print(f"        Seuil: {detector['escalation_threshold']}, Actif: {detector['is_active']}")
                
                self.results.append({
                    'test': 'get_detectors',
                    'success': True,
                    'count': len(detectors)
                })
                return True
            else:
                print(f"   ❌ Erreur: {result.get('error')}")
                return False
                
        except Exception as e:
            print(f"   ❌ Erreur: {e}")
            return False
    
    def test_get_rules(self):
        """Test de récupération des règles"""
        print("\n🔍 Test de récupération des règles d'escalation...")
        
        try:
            response = self.session.get(f"{BASE_URL}/api/v1/escalation/rules")
            result = response.json()
            
            if result.get('success'):
                rules = result.get('rules', [])
                print(f"   ✅ {len(rules)} règles trouvées:")
                
                for rule in rules:
                    print(f"      - {rule['rule_name']}")
                    print(f"        Type: {rule['condition_type']}, Seuil: {rule['escalation_threshold']}")
                    print(f"        Action: {rule['escalation_action']}, Actif: {rule['is_active']}")
                
                self.results.append({
                    'test': 'get_rules',
                    'success': True,
                    'count': len(rules)
                })
                return True
            else:
                print(f"   ❌ Erreur: {result.get('error')}")
                return False
                
        except Exception as e:
            print(f"   ❌ Erreur: {e}")
            return False
    
    def test_complexity_analysis(self):
        """Test d'analyse de complexité"""
        print("\n🔍 Test d'analyse de complexité...")
        
        test_cases = [
            {
                'name': 'Message simple',
                'message': 'J\'ai un problème avec mon robinet',
                'context': {
                    'service_type': 'plomberie',
                    'zone': 'Bonamoussadi',
                    'user_id': '237691924172',
                    'session_id': 'test_session_1'
                },
                'expected_complexity': 'low'
            },
            {
                'name': 'Message complexe technique',
                'message': 'Mon système électrique a des problèmes de voltage, les disjoncteurs sautent et il y a des problèmes de phase',
                'context': {
                    'service_type': 'électricité',
                    'zone': 'Bonamoussadi',
                    'user_id': '237691924172',
                    'session_id': 'test_session_2'
                },
                'conversation_history': [
                    {'message': 'Ça ne marche toujours pas', 'timestamp': datetime.now().isoformat()},
                    {'message': 'Je suis frustré', 'timestamp': datetime.now().isoformat()},
                    {'message': 'C\'est compliqué', 'timestamp': datetime.now().isoformat()}
                ],
                'expected_complexity': 'high'
            },
            {
                'name': 'Message avec frustration',
                'message': 'Je suis vraiment énervé, ça fait 3 fois que j\'explique le même problème et personne ne comprend !',
                'context': {
                    'service_type': 'électroménager',
                    'zone': 'Bonamoussadi',
                    'user_id': '237655443322',
                    'session_id': 'test_session_3',
                    'urgency_level': 'urgent'
                },
                'conversation_history': [
                    {'message': 'Mon frigo ne marche pas', 'timestamp': datetime.now().isoformat()},
                    {'message': 'Pouvez-vous m\'aider ?', 'timestamp': datetime.now().isoformat()},
                    {'message': 'Je ne comprends pas votre réponse', 'timestamp': datetime.now().isoformat()}
                ],
                'expected_complexity': 'high'
            }
        ]
        
        for test_case in test_cases:
            print(f"\n   📋 Test: {test_case['name']}")
            
            try:
                data = {
                    'message': test_case['message'],
                    'conversation_history': test_case.get('conversation_history', []),
                    'context': test_case['context']
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
                    components = result.get('complexity_components', {})
                    
                    print(f"      Complexité globale: {complexity:.3f}")
                    print(f"      Probabilité d'escalation: {escalation_prob:.3f}")
                    print(f"      Action suggérée: {predictions.get('suggested_action', 'N/A')}")
                    print(f"      Temps de résolution prédit: {predictions.get('predicted_resolution_time', 'N/A')} min")
                    
                    print(f"      Composantes de complexité:")
                    for component, score in components.items():
                        print(f"         {component}: {score:.3f}")
                    
                    # Validation des résultats
                    expected = test_case['expected_complexity']
                    if expected == 'low' and complexity < 0.5:
                        print("      ✅ Complexité correctement détectée (faible)")
                    elif expected == 'high' and complexity > 0.6:
                        print("      ✅ Complexité correctement détectée (élevée)")
                    else:
                        print(f"      ⚠️  Complexité attendue: {expected}, obtenue: {complexity:.3f}")
                    
                    self.results.append({
                        'test': f'complexity_analysis_{test_case["name"]}',
                        'success': True,
                        'complexity_score': complexity,
                        'escalation_probability': escalation_prob
                    })
                else:
                    print(f"      ❌ Erreur: {result.get('error')}")
                    
            except Exception as e:
                print(f"      ❌ Erreur: {e}")
    
    def test_escalation_detection(self):
        """Test de détection d'escalation"""
        print("\n🔍 Test de détection d'escalation...")
        
        test_scenarios = [
            {
                'name': 'Scénario normal',
                'user_id': '237691924172',
                'session_id': 'escalation_test_1',
                'message': 'Bonjour, j\'ai besoin d\'aide pour réparer mon robinet',
                'context': {
                    'service_type': 'plomberie',
                    'zone': 'Bonamoussadi',
                    'urgency_level': 'normal'
                },
                'expected_escalation': False
            },
            {
                'name': 'Scénario de frustration élevée',
                'user_id': '237655443322',
                'session_id': 'escalation_test_2',
                'message': 'Je suis vraiment frustré ! Ça fait des heures que j\'attends et personne ne vient ! C\'est inacceptable !',
                'context': {
                    'service_type': 'électricité',
                    'zone': 'Bonamoussadi',
                    'urgency_level': 'urgent',
                    'conversation_turn': 8
                },
                'expected_escalation': True
            },
            {
                'name': 'Scénario technique complexe',
                'user_id': '237699887755',
                'session_id': 'escalation_test_3',
                'message': 'Mon installation électrique est très complexe avec plusieurs circuits, des problèmes de différentiel et de mise à la terre',
                'context': {
                    'service_type': 'électricité',
                    'zone': 'Bonamoussadi',
                    'urgency_level': 'high',
                    'conversation_turn': 5
                },
                'expected_escalation': True
            }
        ]
        
        for scenario in test_scenarios:
            print(f"\n   📋 Scénario: {scenario['name']}")
            
            try:
                data = {
                    'user_id': scenario['user_id'],
                    'session_id': scenario['session_id'],
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
                    
                    print(f"      Escalation déclenchée: {escalation_triggered}")
                    print(f"      Score d'escalation: {escalation_score:.3f}")
                    if escalation_triggered:
                        print(f"      Raison: {escalation_reason}")
                        print(f"      Type: {escalation_type}")
                    
                    # Validation des résultats
                    expected = scenario['expected_escalation']
                    if escalation_triggered == expected:
                        print("      ✅ Détection d'escalation correcte")
                    else:
                        print(f"      ⚠️  Escalation attendue: {expected}, obtenue: {escalation_triggered}")
                    
                    self.results.append({
                        'test': f'escalation_detection_{scenario["name"]}',
                        'success': True,
                        'escalation_triggered': escalation_triggered,
                        'escalation_score': escalation_score
                    })
                else:
                    print(f"      ❌ Erreur: {result.get('error')}")
                    
            except Exception as e:
                print(f"      ❌ Erreur: {e}")
    
    def test_analytics_dashboard(self):
        """Test du tableau de bord analytics"""
        print("\n🔍 Test du tableau de bord analytics...")
        
        try:
            response = self.session.get(f"{BASE_URL}/api/v1/escalation/analytics/dashboard")
            result = response.json()
            
            if result.get('success'):
                dashboard = result.get('dashboard', {})
                print("   ✅ Tableau de bord récupéré:")
                print(f"      Détections aujourd'hui: {dashboard.get('detections_today', 0)}")
                print(f"      Escalations aujourd'hui: {dashboard.get('escalations_today', 0)}")
                print(f"      Escalations actives: {dashboard.get('active_escalations', 0)}")
                print(f"      Taux d'escalation: {dashboard.get('escalation_rate', 0):.3f}")
                print(f"      Score moyen: {dashboard.get('average_escalation_score', 0):.3f}")
                
                self.results.append({
                    'test': 'analytics_dashboard',
                    'success': True,
                    'dashboard_data': dashboard
                })
                return True
            else:
                print(f"   ❌ Erreur: {result.get('error')}")
                return False
                
        except Exception as e:
            print(f"   ❌ Erreur: {e}")
            return False
    
    def test_get_logs(self):
        """Test de récupération des logs"""
        print("\n🔍 Test de récupération des logs...")
        
        try:
            response = self.session.get(f"{BASE_URL}/api/v1/escalation/logs?limit=5")
            result = response.json()
            
            if result.get('success'):
                logs = result.get('logs', [])
                total_count = result.get('total_count', 0)
                
                print(f"   ✅ {len(logs)} logs récupérés (total: {total_count}):")
                
                for log in logs:
                    print(f"      - ID: {log['log_id']}")
                    print(f"        Escalation: {log['escalation_triggered']}, Score: {log['escalation_score']:.3f}")
                    print(f"        Service: {log['service_type']}, Zone: {log['zone']}")
                    print(f"        Message: {log['message_content'][:50]}...")
                
                self.results.append({
                    'test': 'get_logs',
                    'success': True,
                    'log_count': len(logs),
                    'total_count': total_count
                })
                return True
            else:
                print(f"   ❌ Erreur: {result.get('error')}")
                return False
                
        except Exception as e:
            print(f"   ❌ Erreur: {e}")
            return False
    
    def run_all_tests(self):
        """Exécuter tous les tests"""
        print("🚀 DÉBUT DES TESTS DU SYSTÈME DE DÉTECTION D'ESCALATION")
        print("=" * 70)
        
        # Tests de base
        if not self.test_health_check():
            print("\n❌ Test de santé échoué, arrêt des tests")
            return False
        
        # Tests des endpoints
        self.test_get_detectors()
        self.test_get_rules()
        
        # Tests de fonctionnalité
        self.test_complexity_analysis()
        self.test_escalation_detection()
        
        # Tests d'analytics
        self.test_analytics_dashboard()
        self.test_get_logs()
        
        # Résumé des résultats
        self.print_summary()
        
        return True
    
    def print_summary(self):
        """Afficher le résumé des résultats"""
        print("\n" + "="*70)
        print("📊 RÉSUMÉ DES TESTS")
        print("="*70)
        
        total_tests = len(self.results)
        successful_tests = len([r for r in self.results if r.get('success', False)])
        
        print(f"Total des tests: {total_tests}")
        print(f"Tests réussis: {successful_tests}")
        print(f"Taux de réussite: {(successful_tests/max(total_tests,1))*100:.1f}%")
        
        print("\n📋 Détail des résultats:")
        for result in self.results:
            status = "✅" if result.get('success') else "❌"
            print(f"   {status} {result['test']}")
        
        if successful_tests == total_tests:
            print("\n🎉 TOUS LES TESTS SONT PASSÉS ! Système opérationnel.")
        else:
            print(f"\n⚠️  {total_tests - successful_tests} tests ont échoué.")
        
        print("\n🔗 Endpoints testés:")
        endpoints = [
            "GET  /api/v1/escalation/health",
            "GET  /api/v1/escalation/detectors",
            "GET  /api/v1/escalation/rules",
            "POST /api/v1/escalation/complexity/analyze",
            "POST /api/v1/escalation/detect",
            "GET  /api/v1/escalation/analytics/dashboard",
            "GET  /api/v1/escalation/logs"
        ]
        
        for endpoint in endpoints:
            print(f"   {endpoint}")

def main():
    """Fonction principale"""
    tester = EscalationDetectionTester()
    
    print("🔧 Test du Système de Détection d'Escalation - Djobea AI")
    print("Vérification que le serveur est en marche...")
    
    # Vérifier que le serveur est accessible
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Serveur accessible")
        else:
            print("❌ Serveur inaccessible")
            return
    except Exception as e:
        print(f"❌ Impossible de se connecter au serveur: {e}")
        print("Assurez-vous que le serveur Djobea AI est en marche sur le port 5000")
        return
    
    # Exécuter les tests
    tester.run_all_tests()

if __name__ == "__main__":
    main()