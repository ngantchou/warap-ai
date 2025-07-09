#!/usr/bin/env python3
"""
Test complet d'intégration système - Djobea AI
Validation des action codes, escalade, tracking et tous les systèmes avancés
"""

import requests
import time
import json
from datetime import datetime

class SystemIntegrationTest:
    """Test complet des systèmes avancés Djobea AI"""
    
    def __init__(self):
        self.base_url = "http://localhost:5000"
        self.session_id = f"integration_test_{int(time.time())}"
        self.phone_number = "237691924250"
        self.results = []
        
    def log_test(self, test_name: str, success: bool, details: str = ""):
        """Log test results"""
        status = "✅" if success else "❌"
        self.results.append({
            "test": test_name,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
        print(f"{status} {test_name}: {details}")
    
    def test_action_codes_system(self):
        """Test du système d'action codes"""
        print("\n=== TEST SYSTÈME ACTION CODES ===")
        
        try:
            from app.models.action_codes import ActionCode, ActionCodeValidator
            
            # Test 1: Validation des codes
            total_codes = len(ActionCode)
            self.log_test("Action Codes Available", total_codes > 50, f"{total_codes} codes")
            
            # Test 2: Validation d'un code
            is_valid, _ = ActionCodeValidator.validate_code("COLLECTE_BESOIN")
            self.log_test("Code Validation", is_valid, "COLLECTE_BESOIN validé")
            
            # Test 3: Codes d'escalade
            escalation_codes = [code for code in ActionCode if "ESCALATE" in code.value]
            self.log_test("Escalation Codes", len(escalation_codes) >= 3, f"{len(escalation_codes)} codes d'escalade")
            
        except Exception as e:
            self.log_test("Action Codes System", False, f"Erreur: {str(e)}")
    
    def test_conversation_with_action_codes(self):
        """Test conversation avec détection d'action codes"""
        print("\n=== TEST CONVERSATION AVEC ACTION CODES ===")
        
        # Test 1: Collecte de besoin
        try:
            response = requests.post(f"{self.base_url}/webhook/chat", json={
                'message': 'j\'ai un problème de plomberie urgente',
                'session_id': self.session_id + "_action1",
                'phone_number': self.phone_number,
                'source': 'web_chat'
            }, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                response_text = data.get('response', '')
                has_urgency = 'urgente' in response_text.lower() or 'urgent' in response_text.lower()
                self.log_test("Urgency Detection", has_urgency, "Urgence détectée")
            else:
                self.log_test("Conversation Action Codes", False, f"Status {response.status_code}")
                
        except Exception as e:
            self.log_test("Conversation Action Codes", False, f"Erreur: {str(e)}")
    
    def test_request_management_system(self):
        """Test du système de gestion des demandes"""
        print("\n=== TEST GESTION DES DEMANDES ===")
        
        # Test 1: Voir mes demandes
        try:
            response = requests.post(f"{self.base_url}/webhook/chat", json={
                'message': 'voir mes demandes',
                'session_id': self.session_id + "_requests",
                'phone_number': self.phone_number,
                'source': 'web_chat'
            }, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                response_text = data.get('response', '')
                has_requests = 'DJB-' in response_text or 'demandes' in response_text.lower()
                self.log_test("View Requests", has_requests, "Demandes listées")
            else:
                self.log_test("View Requests", False, f"Status {response.status_code}")
                
        except Exception as e:
            self.log_test("View Requests", False, f"Erreur: {str(e)}")
    
    def test_escalation_system(self):
        """Test du système d'escalade"""
        print("\n=== TEST SYSTÈME D'ESCALADE ===")
        
        try:
            response = requests.get(f"{self.base_url}/api/v1/escalation/rules", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("Escalation Rules", True, f"Règles disponibles")
            else:
                self.log_test("Escalation Rules", False, f"Status {response.status_code}")
                
        except Exception as e:
            self.log_test("Escalation Rules", False, f"Erreur: {str(e)}")
    
    def test_knowledge_base_system(self):
        """Test du système de base de connaissances"""
        print("\n=== TEST BASE DE CONNAISSANCES ===")
        
        try:
            response = requests.get(f"{self.base_url}/api/v1/knowledge/search?query=plomberie", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("Knowledge Base", True, f"Articles disponibles")
            else:
                self.log_test("Knowledge Base", False, f"Status {response.status_code}")
                
        except Exception as e:
            self.log_test("Knowledge Base", False, f"Erreur: {str(e)}")
    
    def test_system_health(self):
        """Test de santé du système"""
        print("\n=== TEST SANTÉ SYSTÈME ===")
        
        try:
            response = requests.get(f"{self.base_url}/health", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("System Health", True, "Système opérationnel")
            else:
                self.log_test("System Health", False, f"Status {response.status_code}")
                
        except Exception as e:
            self.log_test("System Health", False, f"Erreur: {str(e)}")
    
    def run_all_tests(self):
        """Exécuter tous les tests"""
        print("🚀 DÉBUT DES TESTS D'INTÉGRATION SYSTÈME DJOBEA AI")
        print("=" * 60)
        
        start_time = time.time()
        
        # Exécuter tous les tests
        self.test_action_codes_system()
        self.test_conversation_with_action_codes()
        self.test_request_management_system()
        self.test_escalation_system()
        self.test_knowledge_base_system()
        self.test_system_health()
        
        end_time = time.time()
        
        # Résumé des résultats
        print("\n" + "=" * 60)
        print("📊 RÉSUMÉ DES TESTS")
        print("=" * 60)
        
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"Total des tests: {total_tests}")
        print(f"Tests réussis: {passed_tests}")
        print(f"Tests échoués: {failed_tests}")
        print(f"Taux de réussite: {(passed_tests/total_tests)*100:.1f}%")
        print(f"Temps d'exécution: {end_time - start_time:.2f}s")
        
        if failed_tests > 0:
            print("\n❌ TESTS ÉCHOUÉS:")
            for result in self.results:
                if not result["success"]:
                    print(f"  • {result['test']}: {result['details']}")
        
        print("\n🎯 ÉTAT DU SYSTÈME:")
        if passed_tests >= total_tests * 0.8:
            print("✅ SYSTÈME OPÉRATIONNEL - Prêt pour la production")
        elif passed_tests >= total_tests * 0.6:
            print("⚠️  SYSTÈME PARTIELLEMENT OPÉRATIONNEL - Maintenance requise")
        else:
            print("❌ SYSTÈME NON OPÉRATIONNEL - Débogage nécessaire")
        
        return {
            "total_tests": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
            "success_rate": (passed_tests/total_tests)*100,
            "execution_time": end_time - start_time,
            "results": self.results
        }

def main():
    """Fonction principale"""
    tester = SystemIntegrationTest()
    results = tester.run_all_tests()
    
    # Sauvegarder les résultats
    with open('integration_test_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n📄 Résultats sauvegardés dans integration_test_results.json")
    
    return results

if __name__ == "__main__":
    main()