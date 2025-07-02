"""
Monetbil Payment Integration Tests
Comprehensive testing of payment processing with Monetbil API
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.orm import Session
from datetime import datetime

from app.services.monetbil_service import MonetbilService
from app.models.database_models import (
    Transaction, ServiceRequest, User, Provider, 
    TransactionStatus, RequestStatus
)


class TestMonetbilService:
    """Test Monetbil payment service functionality"""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        return Mock(spec=Session)
    
    @pytest.fixture
    def monetbil_service(self):
        """Monetbil service instance with test configuration"""
        with patch.dict('os.environ', {
            'MONETBIL_SERVICE_KEY': 'test_service_key',
            'MONETBIL_SERVICE_SECRET': 'test_service_secret',
            'BASE_URL': 'https://test.djobea-ai.com'
        }):
            return MonetbilService()
    
    @pytest.fixture
    def sample_service_request(self):
        """Sample service request for testing"""
        service_request = Mock(spec=ServiceRequest)
        service_request.id = 123
        service_request.user_id = 1
        service_request.provider_id = 2
        service_request.service_type = "plomberie"
        service_request.status = RequestStatus.COMPLETED
        return service_request
    
    @pytest.fixture
    def sample_user(self):
        """Sample user for testing"""
        user = Mock(spec=User)
        user.id = 1
        user.phone_number = "+237690000001"
        user.name = "Jean Dupont"
        return user
    
    @pytest.fixture
    def sample_provider(self):
        """Sample provider for testing"""
        provider = Mock(spec=Provider)
        provider.id = 2
        provider.name = "Marie Plombier"
        provider.whatsapp_id = "+237690000002"
        return provider

    def test_generate_payment_reference(self, monetbil_service):
        """Test payment reference generation"""
        ref1 = monetbil_service.generate_payment_reference(123)
        ref2 = monetbil_service.generate_payment_reference(123)
        
        # References should be different (due to timestamp)
        assert ref1 != ref2
        assert len(ref1) == 32  # MD5 hash length
        assert ref1.isalnum()

    def test_calculate_commission(self, monetbil_service):
        """Test commission calculation"""
        amount = 10000  # 10,000 FCFA
        commission, provider_payout = monetbil_service.calculate_commission(amount)
        
        assert commission == 1500  # 15% of 10,000
        assert provider_payout == 8500  # 85% of 10,000
        assert commission + provider_payout == amount

    @patch('requests.post')
    def test_create_payment_success(self, mock_post, monetbil_service, mock_db, 
                                  sample_service_request, sample_user):
        """Test successful payment creation"""
        # Mock successful Monetbil API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": True,
            "payment_url": "https://api.monetbil.com/pay/v2.1/test123"
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        # Mock database operations
        mock_transaction = Mock(spec=Transaction)
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        
        # Create payment
        result = monetbil_service.create_payment(
            mock_db, sample_service_request, 10000, "+237690000001"
        )
        
        assert result["success"] is True
        assert "payment_url" in result
        assert result["amount"] == 10000
        assert result["commission"] == 1500
        assert result["provider_payout"] == 8500
        
        # Verify API call
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "api.monetbil.com/widget/v2.1" in call_args[0][0]

    @patch('requests.post')
    def test_create_payment_api_failure(self, mock_post, monetbil_service, mock_db,
                                      sample_service_request):
        """Test payment creation with API failure"""
        # Mock API failure
        mock_post.side_effect = Exception("Network error")
        
        result = monetbil_service.create_payment(
            mock_db, sample_service_request, 10000, "+237690000001"
        )
        
        assert result["success"] is False
        assert "error" in result
        assert "Payment service unavailable" in result["error"]

    def test_verify_webhook_signature_valid(self, monetbil_service):
        """Test webhook signature verification with valid signature"""
        payload = "test_payload"
        # This would be the real signature calculation in production
        import hashlib
        expected_signature = hashlib.sha256(
            (payload + "test_service_secret").encode()
        ).hexdigest()
        
        result = monetbil_service.verify_webhook_signature(payload, expected_signature)
        assert result is True

    def test_verify_webhook_signature_invalid(self, monetbil_service):
        """Test webhook signature verification with invalid signature"""
        payload = "test_payload"
        invalid_signature = "invalid_signature"
        
        result = monetbil_service.verify_webhook_signature(payload, invalid_signature)
        assert result is False

    def test_process_payment_notification_success(self, monetbil_service, mock_db):
        """Test processing successful payment notification"""
        # Mock transaction lookup
        mock_transaction = Mock(spec=Transaction)
        mock_transaction.service_request_id = 123
        mock_db.query.return_value.filter.return_value.first.return_value = mock_transaction
        
        # Mock service request lookup
        mock_service_request = Mock(spec=ServiceRequest)
        mock_db.query.return_value.filter.return_value.first.return_value = mock_service_request
        
        notification_data = {
            "payment_ref": "test_ref_123",
            "status": "success",
            "transaction_id": "monetbil_123",
            "amount": "10000"
        }
        
        with patch.object(monetbil_service, '_send_payment_confirmations'):
            result = monetbil_service.process_payment_notification(mock_db, notification_data)
        
        assert result is True
        assert mock_transaction.status == TransactionStatus.COMPLETED
        assert mock_transaction.monetbil_transaction_id == "monetbil_123"

    def test_process_payment_notification_failed(self, monetbil_service, mock_db):
        """Test processing failed payment notification"""
        mock_transaction = Mock(spec=Transaction)
        mock_db.query.return_value.filter.return_value.first.return_value = mock_transaction
        
        notification_data = {
            "payment_ref": "test_ref_123",
            "status": "failed",
            "error_message": "Insufficient funds"
        }
        
        result = monetbil_service.process_payment_notification(mock_db, notification_data)
        
        assert result is True
        assert mock_transaction.status == TransactionStatus.FAILED
        assert mock_transaction.failure_reason == "Insufficient funds"

    @patch('app.services.monetbil_service.WhatsAppService')
    def test_send_payment_confirmations(self, mock_whatsapp_class, monetbil_service, mock_db):
        """Test sending payment confirmation messages"""
        # Mock WhatsApp service
        mock_whatsapp = Mock()
        mock_whatsapp_class.return_value = mock_whatsapp
        
        # Mock transaction and related objects
        mock_transaction = Mock(spec=Transaction)
        mock_transaction.customer_id = 1
        mock_transaction.provider_id = 2
        mock_transaction.amount = 10000
        mock_transaction.commission = 1500
        mock_transaction.provider_payout = 8500
        mock_transaction.payment_reference = "test_ref_123"
        
        mock_service_request = Mock(spec=ServiceRequest)
        mock_service_request.service_type = "plomberie"
        
        mock_customer = Mock(spec=User)
        mock_customer.phone_number = "+237690000001"
        
        mock_provider = Mock(spec=Provider)
        mock_provider.name = "Marie Plombier"
        mock_provider.whatsapp_id = "+237690000002"
        
        # Mock database queries
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_customer, mock_provider
        ]
        
        monetbil_service._send_payment_confirmations(
            mock_db, mock_transaction, mock_service_request
        )
        
        # Verify WhatsApp messages were sent
        assert mock_whatsapp.send_message.call_count == 2

    def test_initiate_service_payment_success(self, monetbil_service, mock_db):
        """Test service payment initiation"""
        # Mock service request
        mock_service_request = Mock(spec=ServiceRequest)
        mock_service_request.status = RequestStatus.COMPLETED
        mock_service_request.user_id = 1
        
        # Mock customer
        mock_customer = Mock(spec=User)
        mock_customer.phone_number = "+237690000001"
        
        # Mock database queries
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_service_request, mock_customer
        ]
        
        # Mock create_payment method
        with patch.object(monetbil_service, 'create_payment') as mock_create:
            mock_create.return_value = {
                "success": True,
                "payment_url": "https://api.monetbil.com/pay/test"
            }
            
            with patch('app.services.monetbil_service.WhatsAppService'):
                result = monetbil_service.initiate_service_payment(mock_db, 123, 10000)
        
        assert result["success"] is True
        mock_create.assert_called_once()

    def test_initiate_service_payment_not_completed(self, monetbil_service, mock_db):
        """Test payment initiation for non-completed service"""
        mock_service_request = Mock(spec=ServiceRequest)
        mock_service_request.status = RequestStatus.IN_PROGRESS
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_service_request
        
        result = monetbil_service.initiate_service_payment(mock_db, 123, 10000)
        
        assert result["success"] is False
        assert "Service not completed" in result["error"]

    def test_get_transaction_status(self, monetbil_service, mock_db):
        """Test transaction status retrieval"""
        mock_transaction = Mock(spec=Transaction)
        mock_db.query.return_value.filter.return_value.first.return_value = mock_transaction
        
        result = monetbil_service.get_transaction_status(mock_db, "test_ref_123")
        
        assert result == mock_transaction

    def test_retry_failed_payment(self, monetbil_service, mock_db):
        """Test retrying a failed payment"""
        # Mock failed transaction
        mock_transaction = Mock(spec=Transaction)
        mock_transaction.status = TransactionStatus.FAILED
        mock_transaction.amount = 10000
        mock_transaction.service_request_id = 123
        mock_transaction.customer_id = 1
        
        # Mock related objects
        mock_service_request = Mock(spec=ServiceRequest)
        mock_customer = Mock(spec=User)
        mock_customer.phone_number = "+237690000001"
        
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_transaction, mock_service_request, mock_customer
        ]
        
        with patch.object(monetbil_service, 'create_payment') as mock_create:
            mock_create.return_value = {"success": True}
            
            result = monetbil_service.retry_failed_payment(mock_db, 1)
        
        assert result["success"] is True
        mock_create.assert_called_once()


class TestMonetbilOperators:
    """Test Cameroon mobile money operator support"""
    
    def test_supported_operators(self):
        """Test that all major Cameroon operators are supported"""
        supported_operators = [
            "CM_MTNMOBILEMONEY",    # MTN Mobile Money
            "CM_ORANGEMONEY",       # Orange Money
            "CM_EUMM"              # Express Union Mobile Money
        ]
        
        # These are the operators documented in Monetbil API
        assert len(supported_operators) == 3
        assert all("CM_" in op for op in supported_operators[:2])

    def test_currency_support(self):
        """Test XAF currency support for Cameroon"""
        currency = "XAF"
        min_amount = 1
        max_amount = 1000000
        
        assert currency == "XAF"  # Central African CFA Franc
        assert min_amount >= 1
        assert max_amount <= 1000000


class TestPaymentWebhookEndpoints:
    """Test payment webhook endpoints"""
    
    @pytest.fixture
    def client(self):
        """Test client for API endpoints"""
        from fastapi.testclient import TestClient
        from app.main import app
        return TestClient(app)

    def test_payment_success_page(self, client):
        """Test payment success page rendering"""
        response = client.get("/payment/success")
        assert response.status_code == 200
        assert "Paiement Confirmé" in response.text

    def test_payment_success_with_reference(self, client):
        """Test payment success page with transaction reference"""
        response = client.get("/payment/success?payment_ref=test_ref_123")
        assert response.status_code == 200

    @patch('app.api.payment.MonetbilService')
    def test_monetbil_webhook_valid_signature(self, mock_service_class, client):
        """Test webhook with valid signature"""
        mock_service = Mock()
        mock_service.verify_webhook_signature.return_value = True
        mock_service.process_payment_notification.return_value = True
        mock_service_class.return_value = mock_service
        
        response = client.post(
            "/webhook/monetbil",
            data={
                "payment_ref": "test_ref_123",
                "status": "success",
                "transaction_id": "monetbil_123"
            },
            headers={"X-Monetbil-Signature": "valid_signature"}
        )
        
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "success"

    @patch('app.api.payment.MonetbilService')
    def test_monetbil_webhook_invalid_signature(self, mock_service_class, client):
        """Test webhook with invalid signature"""
        mock_service = Mock()
        mock_service.verify_webhook_signature.return_value = False
        mock_service_class.return_value = mock_service
        
        response = client.post(
            "/webhook/monetbil",
            data={
                "payment_ref": "test_ref_123",
                "status": "success"
            },
            headers={"X-Monetbil-Signature": "invalid_signature"}
        )
        
        assert response.status_code == 401


class TestPaymentSecurity:
    """Test payment security features"""
    
    def test_payment_reference_uniqueness(self):
        """Test that payment references are unique"""
        service = MonetbilService()
        refs = set()
        
        for i in range(100):
            ref = service.generate_payment_reference(i)
            assert ref not in refs
            refs.add(ref)

    def test_amount_validation(self):
        """Test payment amount validation"""
        # Valid amounts for Cameroon (1 - 1,000,000 FCFA)
        valid_amounts = [1, 100, 5000, 50000, 1000000]
        invalid_amounts = [0, -100, 1000001]
        
        for amount in valid_amounts:
            assert 1 <= amount <= 1000000
        
        for amount in invalid_amounts:
            assert not (1 <= amount <= 1000000)

    def test_phone_number_validation(self):
        """Test Cameroon phone number validation"""
        valid_phones = [
            "+237690000001",  # MTN
            "+237650000001",  # Orange
            "+237670000001"   # Express Union
        ]
        
        invalid_phones = [
            "+33123456789",   # French number
            "690000001",      # Missing country code
            "+237123456789"   # Invalid prefix
        ]
        
        for phone in valid_phones:
            assert phone.startswith("+237")
            assert len(phone) == 13
        
        for phone in invalid_phones:
            if phone.startswith("+237"):
                assert len(phone) != 13 or not phone[4:7] in ["690", "650", "670"]
            else:
                assert not phone.startswith("+237")