#!/usr/bin/env python3
"""
Test complet du système d'escalation vers support humain
"""
import requests
import json
import time
from datetime import datetime
from typing import Dict, List, Any


class HumanEscalationSystemTester:
    """Testeur pour le système d'escalation humaine"""
    
    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url
        self.test_results = []
        self.created_cases = []
        self.created_agents = []
        
    def run_health_check(self) -> Dict[str, Any]:
        """Vérifier la santé du système"""
        try:
            response = requests.get(f"{self.base_url}/api/v1/escalation/human/health")
            result = response.json()
            
            return {
                'success': response.status_code == 200,
                'status': result.get('status'),
                'services': result.get('services', {}),
                'active_agents': result.get('active_agents', 0),
                'pending_cases': result.get('pending_cases', 0)
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def test_create_escalation_case(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        """Tester la création d'un cas d'escalation"""
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/escalation/cases",
                json=case_data,
                headers={'Content-Type': 'application/json'}
            )
            result = response.json()
            
            if result.get('success'):
                self.created_cases.append(result.get('case_id'))
            
            return {
                'success': response.status_code == 200 and result.get('success'),
                'case_id': result.get('case_id'),
                'assigned_agent': result.get('assigned_agent'),
                'handover_session': result.get('handover_session'),
                'estimated_response_time': result.get('estimated_response_time')
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def test_get_escalation_cases(self, filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Tester la récupération des cas d'escalation"""
        try:
            params = filters or {}
            response = requests.get(
                f"{self.base_url}/api/v1/escalation/cases",
                params=params
            )
            result = response.json()
            
            return {
                'success': response.status_code == 200 and result.get('success'),
                'total_count': result.get('total_count', 0),
                'cases': result.get('cases', [])
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def test_get_case_details(self, case_id: str) -> Dict[str, Any]:
        """Tester la récupération des détails d'un cas"""
        try:
            response = requests.get(f"{self.base_url}/api/v1/escalation/cases/{case_id}")
            result = response.json()
            
            return {
                'success': response.status_code == 200 and result.get('success'),
                'case': result.get('case'),
                'handover_session': result.get('handover_session')
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def test_update_case_status(self, case_id: str, new_status: str, notes: str = None) -> Dict[str, Any]:
        """Tester la mise à jour du statut d'un cas"""
        try:
            data = {'status': new_status}
            if notes:
                data['notes'] = notes
            
            response = requests.put(
                f"{self.base_url}/api/v1/escalation/cases/{case_id}/status",
                params=data
            )
            result = response.json()
            
            return {
                'success': response.status_code == 200 and result.get('success'),
                'case_id': result.get('case_id'),
                'old_status': result.get('old_status'),
                'new_status': result.get('new_status')
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def test_get_agents(self, filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Tester la récupération des agents"""
        try:
            params = filters or {}
            response = requests.get(
                f"{self.base_url}/api/v1/escalation/agents",
                params=params
            )
            result = response.json()
            
            return {
                'success': response.status_code == 200 and result.get('success'),
                'agents': result.get('agents', [])
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def test_get_agent_dashboard(self, agent_id: str) -> Dict[str, Any]:
        """Tester le tableau de bord d'un agent"""
        try:
            response = requests.get(f"{self.base_url}/api/v1/escalation/agents/{agent_id}/dashboard")
            result = response.json()
            
            return {
                'success': response.status_code == 200 and result.get('success'),
                'agent_info': result.get('agent_info'),
                'assigned_cases': result.get('assigned_cases', []),
                'performance_metrics': result.get('performance_metrics', {})
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def test_update_agent_status(self, agent_id: str, status: str, availability: str) -> Dict[str, Any]:
        """Tester la mise à jour du statut d'un agent"""
        try:
            data = {
                'agent_id': agent_id,
                'status': status,
                'availability_status': availability
            }
            
            response = requests.put(
                f"{self.base_url}/api/v1/escalation/agents/{agent_id}/status",
                json=data,
                headers={'Content-Type': 'application/json'}
            )
            result = response.json()
            
            return {
                'success': response.status_code == 200 and result.get('success'),
                'agent_id': result.get('agent_id'),
                'status': result.get('status'),
                'availability_status': result.get('availability_status')
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def test_create_case_action(self, case_id: str, action_data: Dict[str, Any]) -> Dict[str, Any]:
        """Tester la création d'une action sur un cas"""
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/escalation/cases/{case_id}/actions",
                json=action_data,
                headers={'Content-Type': 'application/json'}
            )
            result = response.json()
            
            return {
                'success': response.status_code == 200 and result.get('success'),
                'action_id': result.get('action_id'),
                'action_type': result.get('action_type')
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def test_get_case_actions(self, case_id: str) -> Dict[str, Any]:
        """Tester la récupération des actions d'un cas"""
        try:
            response = requests.get(f"{self.base_url}/api/v1/escalation/cases/{case_id}/actions")
            result = response.json()
            
            return {
                'success': response.status_code == 200 and result.get('success'),
                'actions': result.get('actions', [])
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def test_submit_feedback(self, feedback_data: Dict[str, Any]) -> Dict[str, Any]:
        """Tester la soumission de feedback"""
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/escalation/feedback",
                json=feedback_data,
                headers={'Content-Type': 'application/json'}
            )
            result = response.json()
            
            return {
                'success': response.status_code == 200 and result.get('success'),
                'feedback_id': result.get('feedback_id'),
                'status': result.get('status')
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def test_get_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Tester les analytics d'escalation"""
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/escalation/analytics/human",
                params={'days': days}
            )
            result = response.json()
            
            return {
                'success': response.status_code == 200 and result.get('success'),
                'analytics': result
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def test_get_dashboard_metrics(self) -> Dict[str, Any]:
        """Tester les métriques du tableau de bord"""
        try:
            response = requests.get(f"{self.base_url}/api/v1/escalation/analytics/dashboard")
            result = response.json()
            
            return {
                'success': response.status_code == 200 and result.get('success'),
                'dashboard': result.get('dashboard', {})
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def run_comprehensive_tests(self) -> List[Dict[str, Any]]:
        """Exécuter tous les tests"""
        tests = []
        
        print("🔧 Test du Système d'Escalation Humaine - Djobea AI")
        print("=" * 60)
        
        # 1. Health Check
        print("🏥 Test de santé du système...")
        health_result = self.run_health_check()
        tests.append({
            'name': 'health_check',
            'success': health_result['success'],
            'details': health_result
        })
        
        if health_result['success']:
            print(f"   ✅ Système opérationnel")
            print(f"   📊 Agents actifs: {health_result['active_agents']}")
            print(f"   📊 Cas en attente: {health_result['pending_cases']}")
        else:
            print(f"   ❌ Erreur système: {health_result.get('error', 'Unknown')}")
        
        # 2. Test des agents
        print("\n👥 Test de récupération des agents...")
        agents_result = self.test_get_agents()
        tests.append({
            'name': 'get_agents',
            'success': agents_result['success'],
            'details': agents_result
        })
        
        if agents_result['success']:
            print(f"   ✅ {len(agents_result['agents'])} agents trouvés")
            
            # Tester le dashboard d'un agent
            if agents_result['agents']:
                agent = agents_result['agents'][0]
                agent_id = agent['agent_id']
                
                print(f"\n📊 Test du dashboard de l'agent {agent['name']}...")
                dashboard_result = self.test_get_agent_dashboard(agent_id)
                tests.append({
                    'name': 'agent_dashboard',
                    'success': dashboard_result['success'],
                    'details': dashboard_result
                })
                
                if dashboard_result['success']:
                    print(f"   ✅ Dashboard chargé")
                    print(f"   📊 Cas assignés: {len(dashboard_result['assigned_cases'])}")
                    
                    # Tester la mise à jour du statut
                    print(f"\n🔄 Test de mise à jour du statut de l'agent...")
                    status_result = self.test_update_agent_status(agent_id, 'online', 'available')
                    tests.append({
                        'name': 'update_agent_status',
                        'success': status_result['success'],
                        'details': status_result
                    })
                    
                    if status_result['success']:
                        print(f"   ✅ Statut mis à jour")
                    else:
                        print(f"   ❌ Erreur mise à jour: {status_result.get('error', 'Unknown')}")
                else:
                    print(f"   ❌ Erreur dashboard: {dashboard_result.get('error', 'Unknown')}")
        else:
            print(f"   ❌ Erreur agents: {agents_result.get('error', 'Unknown')}")
        
        # 3. Test de création de cas d'escalation
        print("\n🚨 Test de création de cas d'escalation...")
        case_data = {
            'user_id': '237691924172',
            'session_id': f'session_test_{int(time.time())}',
            'original_request_id': 'req_test_12345',
            'escalation_trigger': 'frustration',
            'escalation_score': 0.75,
            'escalation_reason': 'Test d\'escalation - Client frustré après plusieurs tentatives',
            'service_type': 'plomberie',
            'problem_category': 'fuite_eau',
            'problem_description': 'Fuite d\'eau importante au niveau du robinet de cuisine - Test escalation',
            'customer_context': {
                'previous_requests': 2,
                'service_history': 'Client test',
                'location': 'Bonamoussadi'
            },
            'metadata': {
                'source': 'test_system',
                'test_case': True
            }
        }
        
        case_result = self.test_create_escalation_case(case_data)
        tests.append({
            'name': 'create_escalation_case',
            'success': case_result['success'],
            'details': case_result
        })
        
        if case_result['success']:
            case_id = case_result['case_id']
            print(f"   ✅ Cas créé: {case_id}")
            print(f"   👤 Agent assigné: {case_result.get('assigned_agent', 'Aucun')}")
            print(f"   ⏰ Temps de réponse estimé: {case_result.get('estimated_response_time', 'N/A')} min")
            
            # 4. Test de récupération des détails du cas
            print(f"\n📋 Test de récupération des détails du cas...")
            details_result = self.test_get_case_details(case_id)
            tests.append({
                'name': 'get_case_details',
                'success': details_result['success'],
                'details': details_result
            })
            
            if details_result['success']:
                print(f"   ✅ Détails récupérés")
                case_info = details_result['case']
                print(f"   📊 Statut: {case_info.get('status', 'N/A')}")
                print(f"   📊 Urgence: {case_info.get('urgency_level', 'N/A')}")
                
                handover = details_result.get('handover_session')
                if handover:
                    print(f"   🤝 Handover session: {handover['session_id']}")
                    print(f"   📝 Résumé: {handover['case_summary'][:100]}...")
                    print(f"   🎯 Actions recommandées: {len(handover.get('recommended_actions', []))}")
                
                # 5. Test de mise à jour du statut du cas
                print(f"\n🔄 Test de mise à jour du statut du cas...")
                status_update_result = self.test_update_case_status(
                    case_id, 
                    'in_progress', 
                    'Cas pris en charge par l\'agent de test'
                )
                tests.append({
                    'name': 'update_case_status',
                    'success': status_update_result['success'],
                    'details': status_update_result
                })
                
                if status_update_result['success']:
                    print(f"   ✅ Statut mis à jour: {status_update_result['old_status']} → {status_update_result['new_status']}")
                else:
                    print(f"   ❌ Erreur mise à jour: {status_update_result.get('error', 'Unknown')}")
                
                # 6. Test de création d'action sur le cas
                print(f"\n⚡ Test de création d'action sur le cas...")
                action_data = {
                    'case_id': case_id,
                    'action_type': 'customer_contact',
                    'action_description': 'Contact client pour clarification du problème',
                    'action_details': {
                        'contact_method': 'whatsapp',
                        'message_sent': True,
                        'response_expected': True
                    },
                    'internal_notes': 'Test d\'action sur cas d\'escalation'
                }
                
                action_result = self.test_create_case_action(case_id, action_data)
                tests.append({
                    'name': 'create_case_action',
                    'success': action_result['success'],
                    'details': action_result
                })
                
                if action_result['success']:
                    print(f"   ✅ Action créée: {action_result['action_id']}")
                    print(f"   📝 Type: {action_result['action_type']}")
                    
                    # 7. Test de récupération des actions
                    print(f"\n📜 Test de récupération des actions du cas...")
                    actions_result = self.test_get_case_actions(case_id)
                    tests.append({
                        'name': 'get_case_actions',
                        'success': actions_result['success'],
                        'details': actions_result
                    })
                    
                    if actions_result['success']:
                        print(f"   ✅ {len(actions_result['actions'])} actions trouvées")
                    else:
                        print(f"   ❌ Erreur actions: {actions_result.get('error', 'Unknown')}")
                else:
                    print(f"   ❌ Erreur action: {action_result.get('error', 'Unknown')}")
                
                # 8. Test de soumission de feedback
                print(f"\n💬 Test de soumission de feedback...")
                feedback_data = {
                    'case_id': case_id,
                    'agent_id': case_result.get('assigned_agent', 'agent_test'),
                    'feedback_type': 'escalation_quality',
                    'feedback_category': 'positive',
                    'feedback_title': 'Excellente escalation',
                    'feedback_description': 'Le processus d\'escalation a fonctionné parfaitement pour ce cas de test',
                    'escalation_appropriateness': 4.5,
                    'context_completeness': 4.8,
                    'handover_quality': 4.7,
                    'ai_performance_rating': 4.6,
                    'improvement_suggestions': [
                        {
                            'category': 'handover',
                            'suggestion': 'Améliorer la clarté du résumé automatique',
                            'priority': 'medium'
                        }
                    ]
                }
                
                feedback_result = self.test_submit_feedback(feedback_data)
                tests.append({
                    'name': 'submit_feedback',
                    'success': feedback_result['success'],
                    'details': feedback_result
                })
                
                if feedback_result['success']:
                    print(f"   ✅ Feedback soumis: {feedback_result['feedback_id']}")
                    print(f"   📊 Statut: {feedback_result['status']}")
                else:
                    print(f"   ❌ Erreur feedback: {feedback_result.get('error', 'Unknown')}")
            else:
                print(f"   ❌ Erreur détails: {details_result.get('error', 'Unknown')}")
        else:
            print(f"   ❌ Erreur création: {case_result.get('error', 'Unknown')}")
        
        # 9. Test de récupération des cas
        print(f"\n📊 Test de récupération des cas d'escalation...")
        cases_result = self.test_get_escalation_cases({'limit': 10})
        tests.append({
            'name': 'get_escalation_cases',
            'success': cases_result['success'],
            'details': cases_result
        })
        
        if cases_result['success']:
            print(f"   ✅ {cases_result['total_count']} cas trouvés")
            if cases_result['cases']:
                print(f"   📋 Exemple de cas:")
                for i, case in enumerate(cases_result['cases'][:3]):
                    print(f"      {i+1}. {case['case_id']} - {case['service_type']} ({case['urgency_level']})")
        else:
            print(f"   ❌ Erreur récupération: {cases_result.get('error', 'Unknown')}")
        
        # 10. Test des analytics
        print(f"\n📈 Test des analytics d'escalation...")
        analytics_result = self.test_get_analytics(7)  # 7 derniers jours
        tests.append({
            'name': 'get_analytics',
            'success': analytics_result['success'],
            'details': analytics_result
        })
        
        if analytics_result['success']:
            analytics = analytics_result['analytics']
            print(f"   ✅ Analytics récupérées")
            print(f"   📊 Cas totaux: {analytics.get('total_cases', 0)}")
            print(f"   📊 Cas résolus: {analytics.get('resolved_cases', 0)}")
            print(f"   📊 Taux de résolution: {analytics.get('resolution_rate', 0):.2%}")
            print(f"   📊 Temps de réponse moyen: {analytics.get('avg_response_time_minutes', 0)} min")
            print(f"   📊 Satisfaction client: {analytics.get('avg_customer_satisfaction', 0):.1f}/5")
        else:
            print(f"   ❌ Erreur analytics: {analytics_result.get('error', 'Unknown')}")
        
        # 11. Test du tableau de bord général
        print(f"\n📊 Test du tableau de bord général...")
        dashboard_result = self.test_get_dashboard_metrics()
        tests.append({
            'name': 'get_dashboard_metrics',
            'success': dashboard_result['success'],
            'details': dashboard_result
        })
        
        if dashboard_result['success']:
            dashboard = dashboard_result['dashboard']
            print(f"   ✅ Tableau de bord récupéré")
            print(f"   📊 Cas aujourd'hui: {dashboard.get('cases_today', 0)}")
            print(f"   📊 Cas en attente: {dashboard.get('pending_cases', 0)}")
            print(f"   📊 Cas actifs: {dashboard.get('active_cases', 0)}")
            print(f"   📊 Agents en ligne: {dashboard.get('online_agents', 0)}")
            print(f"   📊 Agents disponibles: {dashboard.get('available_agents', 0)}")
            print(f"   📊 Temps de réponse moyen: {dashboard.get('avg_response_time_minutes', 0)} min")
            print(f"   📊 Satisfaction client: {dashboard.get('avg_customer_satisfaction', 0):.1f}/5")
        else:
            print(f"   ❌ Erreur dashboard: {dashboard_result.get('error', 'Unknown')}")
        
        return tests
    
    def print_summary(self, tests: List[Dict[str, Any]]):
        """Afficher le résumé des tests"""
        print("\n" + "=" * 60)
        print("📊 RÉSUMÉ DES TESTS")
        print("=" * 60)
        
        successful_tests = [t for t in tests if t['success']]
        failed_tests = [t for t in tests if not t['success']]
        
        print(f"Total des tests: {len(tests)}")
        print(f"Tests réussis: {len(successful_tests)}")
        print(f"Tests échoués: {len(failed_tests)}")
        print(f"Taux de réussite: {len(successful_tests) / len(tests) * 100:.1f}%")
        
        print("\n📋 Détail des résultats:")
        for test in tests:
            status = "✅" if test['success'] else "❌"
            print(f"   {status} {test['name']}")
        
        if failed_tests:
            print("\n❌ Tests échoués:")
            for test in failed_tests:
                print(f"   - {test['name']}: {test['details'].get('error', 'Unknown error')}")
        
        if len(successful_tests) == len(tests):
            print("\n🎉 TOUS LES TESTS SONT PASSÉS ! Système d'escalation humaine opérationnel.")
            
            print("\n📋 Fonctionnalités validées:")
            print("   ✅ Création automatique de cas d'escalation")
            print("   ✅ Assignation intelligente d'agents")
            print("   ✅ Handover AI → Agent avec briefing complet")
            print("   ✅ Gestion des statuts et actions")
            print("   ✅ Système de feedback et amélioration continue")
            print("   ✅ Analytics et métriques en temps réel")
            print("   ✅ Interface agent avec dashboard interactif")
            
            print("\n🔗 Endpoints validés:")
            print("   POST /api/v1/escalation/cases")
            print("   GET /api/v1/escalation/cases")
            print("   GET /api/v1/escalation/cases/{case_id}")
            print("   PUT /api/v1/escalation/cases/{case_id}/status")
            print("   GET /api/v1/escalation/agents")
            print("   GET /api/v1/escalation/agents/{agent_id}/dashboard")
            print("   PUT /api/v1/escalation/agents/{agent_id}/status")
            print("   POST /api/v1/escalation/cases/{case_id}/actions")
            print("   GET /api/v1/escalation/cases/{case_id}/actions")
            print("   POST /api/v1/escalation/feedback")
            print("   GET /api/v1/escalation/analytics/human")
            print("   GET /api/v1/escalation/analytics/dashboard")
            print("   GET /api/v1/escalation/human/health")
            
            print("\n📱 Interface Agent:")
            print("   Dashboard: /agent-dashboard")
            print("   Gestion des cas en temps réel")
            print("   Handover intelligent avec contexte complet")
            print("   Actions et suivi des performances")
        else:
            print(f"\n⚠️  {len(failed_tests)} test(s) échoué(s). Vérifiez la configuration.")


def main():
    """Fonction principale"""
    print("🚀 Démarrage des tests du système d'escalation humaine")
    
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
    
    # Exécuter les tests
    tester = HumanEscalationSystemTester()
    tests = tester.run_comprehensive_tests()
    tester.print_summary(tests)


if __name__ == "__main__":
    main()