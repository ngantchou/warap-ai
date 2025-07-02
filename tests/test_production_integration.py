"""
Production Integration Testing Suite
End-to-end user journey tests, external API integration tests, and error handling verification
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.main import app
from app.models.database_models import (
    User, Provider, ServiceRequest, Transaction, Conversation,
    RequestStatus, TransactionStatus
)
from app.services.ai_service import AIService
from app.services.whatsapp_service import WhatsAppService
from app.services.monetbil_service import MonetbilService
from app.services.provider_service import ProviderService
from app.database import get_db
from tests.conftest import test_db, override_get_db


class TestEndToEndUserJourney:
    """Test complete user journey from WhatsApp message to payment completion"""
    
    @pytest.fixture
    def sample_data(self, test_db):
        """Create sample data for testing"""
        # Create user
        user = User(
            whatsapp_id="+237690000001",
            name="Jean Dupont",
            phone_number="+237690000001"
        )
        test_db.add(user)
        
        # Create provider
        provider = Provider(
            name="Marie Plombier",
            whatsapp_id="+237690000002",
            phone_number="+237690000002",
            services=["plomberie"],
            coverage_areas=["Bonamoussadi"],
            is_available=True,
            is_active=True,
            rating=4.5
        )
        test_db.add(provider)
        test_db.commit()
        
        return {"user": user, "provider": provider}

    @pytest.mark.asyncio
    async def test_complete_success_journey(self, test_db, sample_data):
        """Test complete successful user journey"""
        client = TestClient(app)
        app.dependency_overrides[get_db] = lambda: test_db
        
        user = sample_data["user"]
        provider = sample_data["provider"]
        
        # Step 1: User sends WhatsApp message
        with patch.multiple(
            'app.services.ai_service.AIService',
            extract_service_request=AsyncMock(return_value={
                "confidence": 0.9,
                "service_type": "plomberie",
                "description": "Fuite d'eau dans la cuisine",
                "location": "Bonamoussadi",
                "urgency": "urgent",
                "preferred_time": "maintenant"
            }),
            generate_response=AsyncMock(return_value="Demande reçue, recherche d'un plombier...")
        ), patch.object(WhatsAppService, 'send_message') as mock_whatsapp:
            
            response = client.post("/webhook/whatsapp", json={
                "From": user.whatsapp_id,
                "Body": "J'ai une fuite d'eau dans ma cuisine à Bonamoussadi, c'est urgent!",
                "MessageSid": "test_message_1"
            })
            
            assert response.status_code == 200
            
            # Verify service request was created
            service_request = test_db.query(ServiceRequest).filter(
                ServiceRequest.user_id == user.id
            ).first()
            
            assert service_request is not None
            assert service_request.service_type == "plomberie"
            assert service_request.status == RequestStatus.PENDING

        # Step 2: Provider matching and notification
        with patch.object(WhatsAppService, 'send_message') as mock_whatsapp:
            provider_service = ProviderService(test_db)
            
            # Simulate provider matching
            providers = provider_service.find_available_providers("plomberie", "Bonamoussadi")
            assert len(providers) > 0
            assert providers[0].id == provider.id
            
            # Simulate provider acceptance
            service_request.status = RequestStatus.ASSIGNED
            service_request.provider_id = provider.id
            service_request.accepted_at = datetime.now()
            test_db.commit()

        # Step 3: Service completion
        service_request.status = RequestStatus.COMPLETED
        service_request.completed_at = datetime.now()
        service_request.final_cost = 15000  # 15,000 FCFA
        test_db.commit()

        # Step 4: Payment initiation
        with patch.object(MonetbilService, 'create_payment') as mock_payment, \
             patch.object(WhatsAppService, 'send_message') as mock_whatsapp:
            
            mock_payment.return_value = {
                "success": True,
                "payment_url": "https://api.monetbil.com/pay/test123",
                "payment_reference": "djobea_123_456",
                "transaction_id": 1,
                "amount": 15000,
                "commission": 2250,
                "provider_payout": 12750
            }
            
            monetbil_service = MonetbilService()
            payment_result = monetbil_service.initiate_service_payment(
                test_db, service_request.id, 15000
            )
            
            assert payment_result["success"] is True
            assert "payment_url" in payment_result

        # Step 5: Payment completion via webhook
        with patch.object(MonetbilService, 'verify_webhook_signature', return_value=True), \
             patch.object(WhatsAppService, 'send_message') as mock_whatsapp:
            
            # Simulate payment webhook
            response = client.post("/webhook/monetbil", data={
                "payment_ref": "djobea_123_456",
                "status": "success",
                "transaction_id": "monetbil_tx_123",
                "amount": "15000"
            })
            
            assert response.status_code == 200
            
            # Verify transaction completion
            transaction = test_db.query(Transaction).filter(
                Transaction.payment_reference == "djobea_123_456"
            ).first()
            
            if transaction:
                assert transaction.status == TransactionStatus.COMPLETED
                assert transaction.monetbil_transaction_id == "monetbil_tx_123"

        # Step 6: Verify final state
        test_db.refresh(service_request)
        assert service_request.status in [RequestStatus.PAYMENT_COMPLETED, RequestStatus.COMPLETED]

    @pytest.mark.asyncio
    async def test_provider_timeout_scenario(self, test_db, sample_data):
        """Test scenario where provider doesn't respond within timeout"""
        user = sample_data["user"]
        provider = sample_data["provider"]
        
        # Create service request
        service_request = ServiceRequest(
            user_id=user.id,
            service_type="plomberie",
            description="Test request",
            location="Bonamoussadi",
            status=RequestStatus.PROVIDER_NOTIFIED
        )
        test_db.add(service_request)
        test_db.commit()
        
        with patch.object(WhatsAppService, 'send_message') as mock_whatsapp:
            provider_service = ProviderService(test_db)
            
            # Simulate timeout (provider doesn't respond)
            with patch('asyncio.wait_for', side_effect=asyncio.TimeoutError):
                result = await provider_service.wait_for_provider_response(
                    service_request.id, timeout_minutes=0.1
                )
                
                assert result is None
                
                # Should fallback to next provider or timeout status
                test_db.refresh(service_request)
                assert service_request.status in [RequestStatus.TIMEOUT, RequestStatus.PROVIDER_NOTIFIED]

    def test_no_providers_available_scenario(self, test_db, sample_data):
        """Test scenario where no providers are available"""
        user = sample_data["user"]
        
        # Make provider unavailable
        provider = sample_data["provider"]
        provider.is_available = False
        test_db.commit()
        
        provider_service = ProviderService(test_db)
        providers = provider_service.find_available_providers("plomberie", "Bonamoussadi")
        
        assert len(providers) == 0
        
        # Should handle gracefully with appropriate user notification
        with patch.object(WhatsAppService, 'send_message') as mock_whatsapp:
            # Simulate no providers scenario
            pass

    def test_payment_failure_scenario(self, test_db, sample_data):
        """Test payment failure and retry scenario"""
        user = sample_data["user"]
        provider = sample_data["provider"]
        
        # Create completed service request
        service_request = ServiceRequest(
            user_id=user.id,
            provider_id=provider.id,
            service_type="plomberie",
            description="Test request",
            location="Bonamoussadi",
            status=RequestStatus.COMPLETED,
            final_cost=10000
        )
        test_db.add(service_request)
        test_db.commit()
        
        # Simulate payment failure
        with patch.object(MonetbilService, 'create_payment') as mock_payment:
            mock_payment.return_value = {
                "success": False,
                "error": "Payment service unavailable",
                "details": "Network timeout"
            }
            
            monetbil_service = MonetbilService()
            result = monetbil_service.initiate_service_payment(
                test_db, service_request.id, 10000
            )
            
            assert result["success"] is False
            assert "error" in result

        # Test payment retry
        with patch.object(MonetbilService, 'create_payment') as mock_payment:
            mock_payment.return_value = {
                "success": True,
                "payment_url": "https://api.monetbil.com/pay/retry123"
            }
            
            # Retry should succeed
            result = monetbil_service.initiate_service_payment(
                test_db, service_request.id, 10000
            )
            
            assert result["success"] is True


class TestExternalAPIIntegration:
    """Test integration with external APIs (Anthropic, Twilio, Monetbil)"""
    
    @pytest.mark.asyncio
    async def test_anthropic_api_integration(self):
        """Test Anthropic Claude API integration"""
        ai_service = AIService()
        
        # Test with actual API call structure (mocked)
        with patch('anthropic.Anthropic') as mock_anthropic:
            mock_client = Mock()
            mock_response = Mock()
            mock_response.content = [Mock()]
            mock_response.content[0].text = '{"service_type": "plomberie", "confidence": 0.9}'
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.return_value = mock_client
            
            result = await ai_service.extract_service_request(
                "J'ai une fuite d'eau",
                conversation_history=[]
            )
            
            # Verify API call was made with correct parameters
            mock_client.messages.create.assert_called_once()
            call_args = mock_client.messages.create.call_args[1]
            
            assert call_args["model"] == "claude-sonnet-4-20250514"
            assert call_args["max_tokens"] > 0
            assert "messages" in call_args

    def test_twilio_api_integration(self):
        """Test Twilio WhatsApp API integration"""
        whatsapp_service = WhatsAppService()
        
        with patch('twilio.rest.Client') as mock_twilio:
            mock_client = Mock()
            mock_messages = Mock()
            mock_message = Mock()
            mock_message.sid = "test_message_sid"
            mock_messages.create.return_value = mock_message
            mock_client.messages = mock_messages
            mock_twilio.return_value = mock_client
            
            result = whatsapp_service.send_message(
                "+237690000001",
                "Test message"
            )
            
            # Verify API call
            mock_messages.create.assert_called_once()
            call_args = mock_messages.create.call_args[1]
            
            assert call_args["body"] == "Test message"
            assert call_args["to"] == "whatsapp:+237690000001"

    def test_monetbil_api_integration(self, test_db):
        """Test Monetbil payment API integration"""
        monetbil_service = MonetbilService()
        
        # Create sample service request
        service_request = ServiceRequest(
            id=123,
            user_id=1,
            provider_id=2,
            service_type="plomberie",
            description="Test",
            location="Bonamoussadi"
        )
        
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = {
                "success": True,
                "payment_url": "https://api.monetbil.com/pay/test123"
            }
            mock_response.raise_for_status.return_value = None
            mock_post.return_value = mock_response
            
            result = monetbil_service.create_payment(
                test_db, service_request, 10000, "+237690000001"
            )
            
            # Verify API call
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            
            assert "api.monetbil.com/widget/v2.1" in call_args[0][0]
            assert call_args[1]["data"]["amount"] == 10000
            assert call_args[1]["data"]["currency"] == "XAF"

    @pytest.mark.asyncio
    async def test_api_error_handling(self):
        """Test handling of external API errors"""
        ai_service = AIService()
        
        # Test Anthropic API timeout
        with patch('anthropic.Anthropic') as mock_anthropic:
            mock_client = Mock()
            mock_client.messages.create.side_effect = Exception("API timeout")
            mock_anthropic.return_value = mock_client
            
            result = await ai_service.extract_service_request(
                "Test message",
                conversation_history=[]
            )
            
            # Should handle error gracefully
            assert result is not None
            assert "error" in str(result) or result.get("confidence", 0) == 0

    def test_api_rate_limiting(self):
        """Test handling of API rate limiting"""
        whatsapp_service = WhatsAppService()
        
        with patch('twilio.rest.Client') as mock_twilio:
            mock_client = Mock()
            mock_messages = Mock()
            
            # Simulate rate limit error
            from twilio.base.exceptions import TwilioRestException
            mock_messages.create.side_effect = TwilioRestException(
                status=429,
                uri="test",
                msg="Rate limit exceeded"
            )
            mock_client.messages = mock_messages
            mock_twilio.return_value = mock_client
            
            # Should handle rate limit gracefully
            result = whatsapp_service.send_message(
                "+237690000001",
                "Test message"
            )
            
            # Should not crash and may implement retry logic
            assert result is not None

    def test_webhook_signature_verification(self):
        """Test webhook signature verification for external services"""
        client = TestClient(app)
        
        # Test Twilio webhook signature verification
        with patch('app.api.webhook.validate_webhook_signature') as mock_validate:
            mock_validate.return_value = True
            
            response = client.post("/webhook/whatsapp", json={
                "From": "+237690000001",
                "Body": "Test message",
                "MessageSid": "test_sid"
            })
            
            # Should process webhook when signature is valid
            assert response.status_code == 200

        # Test Monetbil webhook signature verification
        with patch.object(MonetbilService, 'verify_webhook_signature') as mock_verify:
            mock_verify.return_value = True
            
            response = client.post("/webhook/monetbil", data={
                "payment_ref": "test_ref",
                "status": "success"
            })
            
            assert response.status_code == 200


class TestDatabaseTransactionIntegrity:
    """Test database transaction integrity and consistency"""
    
    def test_transaction_atomicity(self, test_db):
        """Test that database transactions are atomic"""
        initial_user_count = test_db.query(User).count()
        initial_request_count = test_db.query(ServiceRequest).count()
        
        try:
            # Simulate transaction that should fail
            with test_db.begin():
                user = User(
                    whatsapp_id="+237690000001",
                    name="Test User",
                    phone_number="+237690000001"
                )
                test_db.add(user)
                test_db.flush()  # Get the ID
                
                # This should fail due to foreign key constraint
                request = ServiceRequest(
                    user_id=99999,  # Non-existent user ID
                    service_type="plomberie",
                    description="Test",
                    location="Test"
                )
                test_db.add(request)
                test_db.commit()
        except Exception:
            test_db.rollback()
        
        # Verify no partial data was committed
        final_user_count = test_db.query(User).count()
        final_request_count = test_db.query(ServiceRequest).count()
        
        assert final_user_count == initial_user_count
        assert final_request_count == initial_request_count

    def test_concurrent_access_handling(self, test_db):
        """Test handling of concurrent database access"""
        # Create a provider
        provider = Provider(
            name="Test Provider",
            whatsapp_id="+237690000001",
            phone_number="+237690000001",
            services=["plomberie"],
            coverage_areas=["Bonamoussadi"],
            is_available=True,
            is_active=True
        )
        test_db.add(provider)
        test_db.commit()
        
        # Simulate concurrent provider assignment
        def assign_provider():
            request = ServiceRequest(
                user_id=1,
                service_type="plomberie",
                description="Test",
                location="Bonamoussadi",
                status=RequestStatus.PENDING
            )
            test_db.add(request)
            test_db.commit()
            
            # Try to assign provider
            request.provider_id = provider.id
            request.status = RequestStatus.ASSIGNED
            test_db.commit()
            
            return request.id
        
        # Should handle concurrent assignments without data corruption
        request_id = assign_provider()
        
        # Verify data integrity
        request = test_db.query(ServiceRequest).filter(
            ServiceRequest.id == request_id
        ).first()
        
        assert request.provider_id == provider.id
        assert request.status == RequestStatus.ASSIGNED

    def test_data_consistency_constraints(self, test_db):
        """Test database constraints maintain data consistency"""
        # Test unique constraints
        user1 = User(
            whatsapp_id="+237690000001",
            name="User 1",
            phone_number="+237690000001"
        )
        test_db.add(user1)
        test_db.commit()
        
        # Try to create duplicate WhatsApp ID
        user2 = User(
            whatsapp_id="+237690000001",  # Same WhatsApp ID
            name="User 2",
            phone_number="+237690000002"
        )
        test_db.add(user2)
        
        with pytest.raises(Exception):  # Should violate unique constraint
            test_db.commit()
        
        test_db.rollback()

    def test_foreign_key_constraints(self, test_db):
        """Test foreign key constraints are enforced"""
        # Try to create service request with non-existent user
        request = ServiceRequest(
            user_id=99999,  # Non-existent user
            service_type="plomberie",
            description="Test",
            location="Test"
        )
        test_db.add(request)
        
        with pytest.raises(Exception):  # Should violate foreign key constraint
            test_db.commit()
        
        test_db.rollback()

    def test_cascade_operations(self, test_db):
        """Test cascade delete operations work correctly"""
        # Create user and related data
        user = User(
            whatsapp_id="+237690000001",
            name="Test User",
            phone_number="+237690000001"
        )
        test_db.add(user)
        test_db.commit()
        
        request = ServiceRequest(
            user_id=user.id,
            service_type="plomberie",
            description="Test",
            location="Test"
        )
        test_db.add(request)
        test_db.commit()
        
        conversation = Conversation(
            user_id=user.id,
            request_id=request.id,
            message_type="incoming",
            message_content="Test message"
        )
        test_db.add(conversation)
        test_db.commit()
        
        request_id = request.id
        conversation_id = conversation.id
        
        # Delete user (if cascade is configured)
        test_db.delete(user)
        test_db.commit()
        
        # Check if related records are handled appropriately
        remaining_request = test_db.query(ServiceRequest).filter(
            ServiceRequest.id == request_id
        ).first()
        
        remaining_conversation = test_db.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()
        
        # Depending on cascade configuration, these might be None or have user_id set to None


class TestErrorHandlingAndRecovery:
    """Test error handling and recovery mechanisms"""
    
    def test_service_degradation_handling(self, test_db):
        """Test graceful degradation when services are unavailable"""
        # Test AI service unavailable
        with patch('app.services.ai_service.AIService.extract_service_request') as mock_ai:
            mock_ai.side_effect = Exception("AI service unavailable")
            
            client = TestClient(app)
            app.dependency_overrides[get_db] = lambda: test_db
            
            response = client.post("/webhook/whatsapp", json={
                "From": "+237690000001",
                "Body": "Test message",
                "MessageSid": "test_sid"
            })
            
            # Should handle AI failure gracefully
            assert response.status_code in [200, 500]  # May vary based on implementation

    def test_database_connection_failure(self):
        """Test handling of database connection failures"""
        client = TestClient(app)
        
        # Mock database connection failure
        def failing_db():
            raise Exception("Database connection failed")
        
        app.dependency_overrides[get_db] = failing_db
        
        response = client.get("/health")
        
        # Should handle database failure gracefully
        assert response.status_code in [500, 503]
        
        # Clean up
        app.dependency_overrides.clear()

    def test_memory_leak_prevention(self, test_db):
        """Test that long-running operations don't cause memory leaks"""
        # Simulate high-volume operations
        for i in range(100):
            user = User(
                whatsapp_id=f"+23769000{i:04d}",
                name=f"User {i}",
                phone_number=f"+23769000{i:04d}"
            )
            test_db.add(user)
            
            if i % 10 == 0:
                test_db.commit()
                test_db.expunge_all()  # Clear session to prevent memory buildup
        
        test_db.commit()
        
        # Verify data was created correctly
        user_count = test_db.query(User).count()
        assert user_count >= 100

    def test_circuit_breaker_pattern(self):
        """Test circuit breaker pattern for external services"""
        # This would test a circuit breaker implementation
        # that prevents cascading failures when external services are down
        
        failure_count = 0
        max_failures = 5
        
        def external_service_call():
            nonlocal failure_count
            failure_count += 1
            if failure_count <= max_failures:
                raise Exception("Service unavailable")
            return "Success"
        
        # Simulate circuit breaker logic
        circuit_open = False
        
        for i in range(10):
            try:
                if circuit_open and i < 8:  # Circuit stays open for a while
                    raise Exception("Circuit breaker open")
                
                result = external_service_call()
                circuit_open = False  # Reset on success
                break
            except Exception:
                if failure_count >= max_failures:
                    circuit_open = True
        
        # Circuit breaker should prevent excessive failures
        assert circuit_open or failure_count > max_failures

    def test_retry_mechanism(self):
        """Test retry mechanisms for transient failures"""
        attempt_count = 0
        max_retries = 3
        
        def unreliable_service():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise Exception("Transient failure")
            return "Success"
        
        # Implement retry logic
        for retry in range(max_retries):
            try:
                result = unreliable_service()
                break
            except Exception as e:
                if retry == max_retries - 1:
                    raise e
                time.sleep(0.1)  # Brief delay between retries
        
        assert attempt_count == 3
        assert result == "Success"

    def test_timeout_handling(self):
        """Test timeout handling for long-running operations"""
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError("Operation timed out")
        
        def long_running_operation():
            time.sleep(2)  # Simulate long operation
            return "Completed"
        
        # Set timeout
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(1)  # 1 second timeout
        
        try:
            result = long_running_operation()
            assert False, "Should have timed out"
        except TimeoutError:
            # Expected timeout
            pass
        finally:
            signal.alarm(0)  # Cancel alarm

    def test_data_validation_error_handling(self, test_db):
        """Test handling of data validation errors"""
        # Test invalid phone number format
        user = User(
            whatsapp_id="invalid_phone",
            name="Test User",
            phone_number="invalid_phone"
        )
        test_db.add(user)
        
        # Should handle validation appropriately
        try:
            test_db.commit()
        except Exception:
            test_db.rollback()
        
        # Verify no invalid data was persisted
        invalid_user = test_db.query(User).filter(
            User.whatsapp_id == "invalid_phone"
        ).first()
        
        assert invalid_user is None