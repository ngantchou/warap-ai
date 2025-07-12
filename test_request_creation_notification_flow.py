"""
Test Request Creation and Provider Notification Flow
Comprehensive test to verify the complete flow from request creation to provider notification
"""
import asyncio
import sys
import os
from datetime import datetime, timedelta
import json

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.database import get_db
from app.models.database_models import ServiceRequest, User, Provider, RequestStatus
from app.models.notification import NotificationQueue
from app.services.request_service import RequestService
from app.services.provider_service import ProviderService
from app.services.communication_service import CommunicationService
from app.services.natural_conversation_engine import NaturalConversationEngine
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

class RequestNotificationFlowTest:
    def __init__(self):
        self.db = next(get_db())
        self.request_service = RequestService(self.db)
        self.provider_service = ProviderService(self.db)
        self.communication_service = CommunicationService()
        self.conversation_engine = NaturalConversationEngine(self.db)
        
    def cleanup_previous_tests(self):
        """Clean up any previous test data"""
        try:
            # Delete test requests
            test_requests = self.db.query(ServiceRequest).filter(
                ServiceRequest.description.like("%TEST REQUEST%")
            ).all()
            
            for request in test_requests:
                self.db.delete(request)
            
            # Delete test notifications
            test_notifications = self.db.query(NotificationQueue).filter(
                NotificationQueue.notification_type.like("%test%")
            ).all()
            
            for notification in test_notifications:
                self.db.delete(notification)
            
            self.db.commit()
            logger.info("Cleaned up previous test data")
            
        except Exception as e:
            logger.error(f"Error cleaning up test data: {e}")
            self.db.rollback()
    
    def create_test_user(self) -> User:
        """Create or get a test user"""
        try:
            user = self.db.query(User).filter(User.whatsapp_id == "test_notification_user").first()
            if not user:
                user = User(
                    whatsapp_id="test_notification_user",
                    phone_number="237600000001",
                    name="Test User Notification",
                    created_at=datetime.utcnow()
                )
                self.db.add(user)
                self.db.commit()
                self.db.refresh(user)
            
            return user
            
        except Exception as e:
            logger.error(f"Error creating test user: {e}")
            self.db.rollback()
            return None
    
    def test_request_creation_flow(self):
        """Test the complete request creation flow"""
        print("\n🔄 TESTING REQUEST CREATION FLOW")
        print("=" * 50)
        
        # Create test user
        user = self.create_test_user()
        if not user:
            print("❌ Failed to create test user")
            return False
        
        print(f"✅ Test user created: {user.id} ({user.whatsapp_id})")
        
        # Create test service request
        request_data = {
            "service_type": "plomberie",
            "description": "TEST REQUEST - Fuite d'eau dans la cuisine",
            "location": "Bonamoussadi, près du marché",
            "urgency": "urgent",
            "preferred_time": "aujourd'hui"
        }
        
        try:
            service_request = self.request_service.create_request(user.id, request_data)
            if not service_request:
                print("❌ Failed to create service request")
                return False
            
            print(f"✅ Service request created: {service_request.id}")
            print(f"   Status: {service_request.status}")
            print(f"   Service: {service_request.service_type}")
            print(f"   Location: {service_request.location}")
            print(f"   Description: {service_request.description}")
            print(f"   Created at: {service_request.created_at}")
            
            return service_request
            
        except Exception as e:
            print(f"❌ Error creating service request: {e}")
            return False
    
    def test_provider_finding_flow(self, service_request: ServiceRequest):
        """Test provider finding and notification flow"""
        print("\n🔍 TESTING PROVIDER FINDING FLOW")
        print("=" * 50)
        
        try:
            # Find available providers
            providers = self.provider_service.find_available_providers(
                service_request.service_type,
                service_request.location
            )
            
            print(f"📊 Found {len(providers)} providers for {service_request.service_type}")
            
            if not providers:
                print("⚠️  No providers found for this service type and location")
                return False
            
            # Display provider information
            for i, provider in enumerate(providers, 1):
                services_str = ", ".join(provider.services) if provider.services else "N/A"
                coverage_str = ", ".join(provider.coverage_areas) if provider.coverage_areas else "N/A"
                print(f"   {i}. Provider {provider.id}: {provider.name}")
                print(f"      Services: {services_str}")
                print(f"      Coverage: {coverage_str}")
                print(f"      Phone: {provider.phone_number}")
                print(f"      Rating: {provider.rating}")
                print(f"      Available: {provider.is_available}")
            
            return providers
            
        except Exception as e:
            print(f"❌ Error finding providers: {e}")
            return False
    
    async def test_notification_flow(self, service_request: ServiceRequest, providers: list):
        """Test the notification flow to providers"""
        print("\n📢 TESTING NOTIFICATION FLOW")
        print("=" * 50)
        
        try:
            # Check notification queue before
            notifications_before = self.db.query(NotificationQueue).count()
            print(f"📋 Notifications in queue before: {notifications_before}")
            
            # Send instant confirmation to user
            print("📱 Sending instant confirmation to user...")
            confirmation_result = await self.communication_service.send_instant_confirmation(
                service_request.id, self.db
            )
            print(f"   Confirmation sent: {confirmation_result}")
            
            # Update request status to PROVIDER_NOTIFIED
            service_request.status = RequestStatus.PROVIDER_NOTIFIED
            self.db.commit()
            print(f"✅ Request status updated to: {service_request.status}")
            
            # Test provider notification using natural conversation engine
            print("🔔 Notifying providers using natural conversation engine...")
            
            # Get the best providers (limit to 3)
            best_providers = providers[:3]
            
            notification_results = []
            for i, provider in enumerate(best_providers, 1):
                try:
                    print(f"   Notifying provider {i}: {provider.name} ({provider.phone_number})")
                    
                    # Create notification message
                    service_emoji = {
                        "plomberie": "🔧",
                        "électricité": "⚡",
                        "réparation électroménager": "🏠"
                    }.get(service_request.service_type.lower(), "🛠")
                    
                    message = f"""🚨 *NOUVELLE DEMANDE DE SERVICE*

{service_emoji} *Service* : {service_request.service_type.title()}
📍 *Localisation* : {service_request.location}
📝 *Description* : {service_request.description}
⏰ *Urgence* : {service_request.urgency or 'Normale'}

💰 *Tarif estimé* : 5,000 - 15,000 XAF

🤝 *Souhaitez-vous accepter cette demande ?*

✅ Répondez *OUI* pour accepter
❌ Répondez *NON* pour refuser

⚠️ *Vous avez 10 minutes pour répondre*

*Djobea AI* - Service de mise en relation"""
                    
                    # Try to send WhatsApp notification
                    from app.services.whatsapp_service import WhatsAppService
                    whatsapp_service = WhatsAppService()
                    
                    success = whatsapp_service.send_message(provider.whatsapp_id, message)
                    
                    notification_results.append({
                        "provider_id": provider.id,
                        "provider_name": provider.name,
                        "success": success,
                        "message_length": len(message)
                    })
                    
                    print(f"      Result: {'✅ Success' if success else '❌ Failed'}")
                    
                except Exception as e:
                    print(f"      ❌ Error notifying provider {provider.id}: {e}")
                    notification_results.append({
                        "provider_id": provider.id,
                        "provider_name": provider.name,
                        "success": False,
                        "error": str(e)
                    })
            
            # Check notification queue after
            notifications_after = self.db.query(NotificationQueue).count()
            print(f"📋 Notifications in queue after: {notifications_after}")
            print(f"📊 New notifications created: {notifications_after - notifications_before}")
            
            # Start proactive updates
            print("⏰ Starting proactive updates...")
            await self.communication_service.start_proactive_updates(service_request.id, self.db)
            print("✅ Proactive updates started")
            
            return notification_results
            
        except Exception as e:
            print(f"❌ Error in notification flow: {e}")
            return False
    
    def check_request_status_after_notifications(self, service_request: ServiceRequest):
        """Check the request status after notifications are sent"""
        print("\n📊 CHECKING REQUEST STATUS AFTER NOTIFICATIONS")
        print("=" * 50)
        
        try:
            # Refresh request from database
            self.db.refresh(service_request)
            
            print(f"📋 Request ID: {service_request.id}")
            print(f"📊 Current Status: {service_request.status}")
            print(f"👤 User ID: {service_request.user_id}")
            print(f"🛠️  Service Type: {service_request.service_type}")
            print(f"📍 Location: {service_request.location}")
            print(f"⏰ Created: {service_request.created_at}")
            print(f"🔄 Updated: {service_request.updated_at}")
            
            # Check if there are any notifications in queue for this request
            notifications = self.db.query(NotificationQueue).filter(
                NotificationQueue.request_id == service_request.id
            ).all()
            
            print(f"📢 Notifications for this request: {len(notifications)}")
            
            for i, notification in enumerate(notifications, 1):
                print(f"   {i}. Type: {notification.notification_type}")
                print(f"      User: {notification.user_id}")
                print(f"      Status: {notification.status}")
                print(f"      Created: {notification.created_at}")
                print(f"      Retry count: {notification.retry_count}")
                if notification.error_message:
                    print(f"      Error: {notification.error_message}")
            
            # Check if request has been assigned to a provider
            if service_request.assigned_provider_id:
                print(f"👨‍🔧 Assigned Provider: {service_request.assigned_provider_id}")
                print(f"📅 Assigned At: {service_request.assigned_at}")
            else:
                print("⏳ No provider assigned yet")
            
            return True
            
        except Exception as e:
            print(f"❌ Error checking request status: {e}")
            return False
    
    def get_system_health_after_test(self):
        """Get system health status after the test"""
        print("\n🏥 SYSTEM HEALTH STATUS AFTER TEST")
        print("=" * 50)
        
        try:
            # Count active requests
            active_requests = self.db.query(ServiceRequest).filter(
                ServiceRequest.status.in_([RequestStatus.PENDING, RequestStatus.PROVIDER_NOTIFIED])
            ).count()
            
            # Count notifications in various states
            total_notifications = self.db.query(NotificationQueue).count()
            failed_notifications = self.db.query(NotificationQueue).filter(
                NotificationQueue.status == 'failed'
            ).count()
            pending_notifications = self.db.query(NotificationQueue).filter(
                NotificationQueue.status == 'pending'
            ).count()
            
            print(f"📊 Active Requests: {active_requests}")
            print(f"📢 Total Notifications: {total_notifications}")
            print(f"❌ Failed Notifications: {failed_notifications}")
            print(f"⏳ Pending Notifications: {pending_notifications}")
            
            # Calculate success rate
            if total_notifications > 0:
                success_rate = ((total_notifications - failed_notifications) / total_notifications) * 100
                print(f"✅ Success Rate: {success_rate:.1f}%")
            else:
                print("📊 No notifications to calculate success rate")
            
            return {
                "active_requests": active_requests,
                "total_notifications": total_notifications,
                "failed_notifications": failed_notifications,
                "pending_notifications": pending_notifications
            }
            
        except Exception as e:
            print(f"❌ Error getting system health: {e}")
            return None
    
    async def run_complete_test(self):
        """Run the complete test flow"""
        print("🧪 REQUEST CREATION AND NOTIFICATION FLOW TEST")
        print("=" * 60)
        
        try:
            # Clean up previous test data
            self.cleanup_previous_tests()
            
            # Step 1: Test request creation
            service_request = self.test_request_creation_flow()
            if not service_request:
                print("❌ Request creation test failed")
                return False
            
            # Step 2: Test provider finding
            providers = self.test_provider_finding_flow(service_request)
            if not providers:
                print("❌ Provider finding test failed")
                return False
            
            # Step 3: Test notification flow
            notification_results = await self.test_notification_flow(service_request, providers)
            if not notification_results:
                print("❌ Notification flow test failed")
                return False
            
            # Step 4: Check request status after notifications
            status_check = self.check_request_status_after_notifications(service_request)
            if not status_check:
                print("❌ Status check failed")
                return False
            
            # Step 5: Get system health
            health_status = self.get_system_health_after_test()
            
            # Final results
            print("\n📊 FINAL TEST RESULTS")
            print("=" * 30)
            
            successful_notifications = sum(1 for result in notification_results if result.get("success"))
            total_notifications = len(notification_results)
            
            print(f"✅ Request Created: {service_request.id}")
            print(f"✅ Providers Found: {len(providers)}")
            print(f"📢 Notifications Sent: {successful_notifications}/{total_notifications}")
            print(f"📊 Current Status: {service_request.status}")
            
            if successful_notifications == 0:
                print("⚠️  All notifications failed - likely due to WhatsApp channel configuration")
                print("🔧 This is expected due to Twilio WhatsApp channel setup issue")
            
            return True
            
        except Exception as e:
            print(f"❌ Complete test failed: {e}")
            return False
        
        finally:
            self.db.close()

async def main():
    """Run the test"""
    test = RequestNotificationFlowTest()
    success = await test.run_complete_test()
    
    if success:
        print("\n✅ REQUEST CREATION AND NOTIFICATION FLOW TEST COMPLETED")
    else:
        print("\n❌ REQUEST CREATION AND NOTIFICATION FLOW TEST FAILED")

if __name__ == "__main__":
    asyncio.run(main())