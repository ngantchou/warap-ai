"""
Test Error Handling System for Djobea AI
Tests WhatsApp failures, provider matching issues, and system recovery
"""
import asyncio
import sys
import os
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.services.error_handling_service import ErrorHandlingService
from app.services.notification_retry_service import NotificationRetryService
from app.models.notification import NotificationQueue
from app.models.database_models import ServiceRequest, User, Provider
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

class ErrorHandlingSystemTest:
    def __init__(self):
        # Database setup
        self.engine = create_engine(os.environ.get('DATABASE_URL'))
        Session = sessionmaker(bind=self.engine)
        self.db = Session()
        
        # Services
        self.error_service = ErrorHandlingService(self.db)
        self.retry_service = NotificationRetryService(self.db)
        
        self.test_results = []
    
    async def test_whatsapp_error_handling(self):
        """Test WhatsApp communication failure handling"""
        print("\n🔧 Testing WhatsApp Error Handling")
        print("=" * 40)
        
        try:
            # Create test notification failure
            success = await self.error_service.handle_whatsapp_failure(
                user_id="test_user_001",
                request_id=999,
                message="Test error message",
                notification_type="test_error"
            )
            
            if success:
                print("✅ WhatsApp failure handled successfully")
                self.test_results.append("whatsapp_error_handling: PASS")
            else:
                print("❌ WhatsApp failure handling failed")
                self.test_results.append("whatsapp_error_handling: FAIL")
                
        except Exception as e:
            print(f"❌ WhatsApp error handling test failed: {e}")
            self.test_results.append(f"whatsapp_error_handling: ERROR - {e}")
    
    async def test_notification_retry_system(self):
        """Test notification retry functionality"""
        print("\n🔄 Testing Notification Retry System")
        print("=" * 40)
        
        try:
            # Get retry statistics
            stats = self.retry_service.get_retry_statistics()
            print(f"📊 Retry Statistics: {stats}")
            
            # Test failed notification processing
            retried_count = await self.retry_service.process_failed_notifications()
            print(f"🔄 Processed {retried_count} failed notifications")
            
            self.test_results.append(f"notification_retry: PASS - {retried_count} notifications processed")
            
        except Exception as e:
            print(f"❌ Notification retry test failed: {e}")
            self.test_results.append(f"notification_retry: ERROR - {e}")
    
    async def test_provider_matching_error_handling(self):
        """Test provider matching failure handling"""
        print("\n👥 Testing Provider Matching Error Handling")
        print("=" * 40)
        
        try:
            # Create a test request
            test_request = ServiceRequest(
                id=9999,
                user_id="test_user_002",
                service_type="test_service",
                location="test_location",
                description="Test request for error handling",
                status="provider_search"
            )
            
            # Test provider matching failure
            success = await self.error_service.handle_provider_matching_failure(test_request)
            
            if success:
                print("✅ Provider matching failure handled successfully")
                self.test_results.append("provider_matching_error: PASS")
            else:
                print("❌ Provider matching failure handling failed")
                self.test_results.append("provider_matching_error: FAIL")
                
        except Exception as e:
            print(f"❌ Provider matching error test failed: {e}")
            self.test_results.append(f"provider_matching_error: ERROR - {e}")
    
    async def test_system_monitoring(self):
        """Test system monitoring and recovery"""
        print("\n📊 Testing System Monitoring")
        print("=" * 40)
        
        try:
            # Get error statistics
            stats = self.error_service.get_error_statistics()
            print(f"📈 Error Statistics: {stats}")
            
            # Test monitoring and retry
            monitoring_stats = await self.error_service.monitor_and_retry_failed_operations()
            print(f"🔧 Monitoring Results: {monitoring_stats}")
            
            self.test_results.append("system_monitoring: PASS")
            
        except Exception as e:
            print(f"❌ System monitoring test failed: {e}")
            self.test_results.append(f"system_monitoring: ERROR - {e}")
    
    def test_database_tables(self):
        """Test database tables creation"""
        print("\n🗄️ Testing Database Tables")
        print("=" * 40)
        
        try:
            # Test notification_queue table
            result = self.db.execute(text("SELECT COUNT(*) FROM notification_queue"))
            count = result.scalar()
            print(f"✅ notification_queue table exists with {count} records")
            
            # Test table structure
            result = self.db.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'notification_queue'"))
            columns = [row[0] for row in result.fetchall()]
            print(f"📋 Table columns: {columns}")
            
            self.test_results.append("database_tables: PASS")
            
        except Exception as e:
            print(f"❌ Database table test failed: {e}")
            self.test_results.append(f"database_tables: ERROR - {e}")
    
    def test_provider_data(self):
        """Test provider data availability"""
        print("\n👥 Testing Provider Data")
        print("=" * 40)
        
        try:
            # Check active providers
            providers = self.db.query(Provider).filter(Provider.is_active == True).limit(5).all()
            print(f"✅ Found {len(providers)} active providers")
            
            for provider in providers:
                phone = getattr(provider, 'phone_number', getattr(provider, 'phone', 'N/A'))
                print(f"   - {provider.name} ({phone}) - Services: {provider.services}")
            
            if len(providers) > 0:
                self.test_results.append("provider_data: PASS")
            else:
                self.test_results.append("provider_data: FAIL - No active providers")
                
        except Exception as e:
            print(f"❌ Provider data test failed: {e}")
            self.test_results.append(f"provider_data: ERROR - {e}")
    
    def generate_report(self):
        """Generate comprehensive test report"""
        print("\n📋 ERROR HANDLING SYSTEM TEST REPORT")
        print("=" * 50)
        
        print(f"🕐 Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🧪 Tests Executed: {len(self.test_results)}")
        
        passed = sum(1 for result in self.test_results if "PASS" in result)
        failed = sum(1 for result in self.test_results if "FAIL" in result)
        errors = sum(1 for result in self.test_results if "ERROR" in result)
        
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"⚠️  Errors: {errors}")
        
        print("\n📊 Detailed Results:")
        for result in self.test_results:
            status = "✅" if "PASS" in result else "❌" if "FAIL" in result else "⚠️"
            print(f"  {status} {result}")
        
        # Overall system health assessment
        if errors == 0 and failed == 0:
            print("\n🟢 SYSTEM STATUS: HEALTHY")
        elif errors == 0 and failed <= 2:
            print("\n🟡 SYSTEM STATUS: DEGRADED")
        else:
            print("\n🔴 SYSTEM STATUS: CRITICAL")
        
        print("\n🔧 RECOMMENDATIONS:")
        if failed > 0 or errors > 0:
            print("  - Review failed tests and fix underlying issues")
            print("  - Check Twilio configuration and API limits")
            print("  - Verify database connectivity and table structure")
            print("  - Add more test providers to database")
        else:
            print("  - System is operating normally")
            print("  - Continue monitoring error rates")
            print("  - Consider implementing proactive health checks")
    
    async def run_all_tests(self):
        """Run all error handling tests"""
        try:
            print("🚀 STARTING ERROR HANDLING SYSTEM TESTS")
            print("=" * 50)
            
            # Database tests
            self.test_database_tables()
            self.test_provider_data()
            
            # Error handling tests
            await self.test_whatsapp_error_handling()
            await self.test_notification_retry_system()
            await self.test_provider_matching_error_handling()
            await self.test_system_monitoring()
            
            # Generate final report
            self.generate_report()
            
        except Exception as e:
            print(f"❌ Test execution failed: {e}")
        finally:
            self.db.close()

async def main():
    """Main test function"""
    try:
        tester = ErrorHandlingSystemTest()
        await tester.run_all_tests()
        
    except Exception as e:
        print(f"❌ Test suite failed to initialize: {e}")
        print("🔧 Please check database connection and environment variables")

if __name__ == "__main__":
    asyncio.run(main())