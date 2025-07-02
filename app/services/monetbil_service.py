"""
Monetbil Payment Service for Djobea AI
Handles all payment operations using Monetbil payment aggregator for Cameroon mobile money
"""

import os
import hashlib
import uuid
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import requests
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.database_models import Transaction, ServiceRequest, Provider, User
from app.services.whatsapp_service import WhatsAppService

settings = get_settings()
logger = logging.getLogger(__name__)


class MonetbilService:
    """Monetbil payment integration service"""
    
    def __init__(self):
        self.service_key = os.getenv("MONETBIL_SERVICE_KEY")
        self.service_secret = os.getenv("MONETBIL_SERVICE_SECRET")
        self.base_url = "https://api.monetbil.com/widget/v2.1/"
        self.notify_url = f"{os.getenv('BASE_URL', 'https://djobea-ai.replit.app')}/webhook/monetbil"
        self.return_url = f"{os.getenv('BASE_URL', 'https://djobea-ai.replit.app')}/payment/success"
        
        if not self.service_key or not self.service_secret:
            logger.warning("Monetbil credentials not configured")
    
    def generate_payment_reference(self, request_id: int) -> str:
        """Generate unique payment reference for a service request"""
        timestamp = str(int(datetime.now().timestamp()))
        unique_string = f"djobea_{request_id}_{timestamp}"
        return hashlib.md5(unique_string.encode()).hexdigest()
    
    def calculate_commission(self, amount: float) -> tuple[float, float]:
        """Calculate platform commission and provider payout"""
        commission = amount * settings.commission_rate
        provider_payout = amount - commission
        return commission, provider_payout
    
    def create_payment(self, db: Session, service_request: ServiceRequest, amount: float, 
                      customer_phone: str) -> Dict[str, Any]:
        """Create a payment request with Monetbil"""
        try:
            # Generate payment reference
            payment_ref = self.generate_payment_reference(service_request.id)
            
            # Calculate commission
            commission, provider_payout = self.calculate_commission(amount)
            
            # Create transaction record
            transaction = Transaction(
                service_request_id=service_request.id,
                customer_id=service_request.user_id,
                provider_id=service_request.provider_id,
                amount=amount,
                commission=commission,
                provider_payout=provider_payout,
                currency="XAF",
                payment_reference=payment_ref,
                status="PENDING",
                monetbil_transaction_id=None
            )
            db.add(transaction)
            db.commit()
            
            # Prepare payment data for Monetbil
            payment_data = {
                "amount": int(amount),  # Monetbil expects integer amount
                "phone": customer_phone,
                "phone_lock": "true",
                "locale": "fr",  # French for Cameroon
                "country": "CM",
                "currency": "XAF",
                "item_ref": f"service_{service_request.id}",
                "payment_ref": payment_ref,
                "user": str(service_request.user_id),
                "return_url": self.return_url,
                "notify_url": self.notify_url,
                "logo": f"{os.getenv('BASE_URL', 'https://djobea-ai.replit.app')}/static/logo.png"
            }
            
            # Make request to Monetbil API
            url = f"{self.base_url}{self.service_key}"
            headers = {
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            response = requests.post(url, data=payment_data, headers=headers, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            
            if result.get("success"):
                # Update transaction with Monetbil payment URL
                transaction.monetbil_payment_url = result.get("payment_url")
                transaction.status = "INITIATED"
                db.commit()
                
                logger.info(f"Payment created successfully for request {service_request.id}")
                return {
                    "success": True,
                    "payment_url": result.get("payment_url"),
                    "payment_reference": payment_ref,
                    "transaction_id": transaction.id,
                    "amount": amount,
                    "commission": commission,
                    "provider_payout": provider_payout
                }
            else:
                transaction.status = "FAILED"
                transaction.failure_reason = "Monetbil payment creation failed"
                db.commit()
                
                logger.error(f"Monetbil payment creation failed: {result}")
                return {
                    "success": False,
                    "error": "Payment creation failed",
                    "details": result
                }
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Monetbil API request failed: {str(e)}")
            if 'transaction' in locals():
                transaction.status = "FAILED"
                transaction.failure_reason = f"API request failed: {str(e)}"
                db.commit()
            
            return {
                "success": False,
                "error": "Payment service unavailable",
                "details": str(e)
            }
        
        except Exception as e:
            logger.error(f"Payment creation error: {str(e)}")
            if 'transaction' in locals():
                transaction.status = "FAILED"
                transaction.failure_reason = f"Internal error: {str(e)}"
                db.commit()
            
            return {
                "success": False,
                "error": "Internal payment error",
                "details": str(e)
            }
    
    def verify_webhook_signature(self, payload: str, signature: str) -> bool:
        """Verify Monetbil webhook signature"""
        try:
            # Generate expected signature
            expected_signature = hashlib.sha256(
                (payload + self.service_secret).encode()
            ).hexdigest()
            
            return signature == expected_signature
        except Exception as e:
            logger.error(f"Webhook signature verification failed: {str(e)}")
            return False
    
    def process_payment_notification(self, db: Session, notification_data: Dict[str, Any]) -> bool:
        """Process payment notification from Monetbil webhook"""
        try:
            payment_ref = notification_data.get("payment_ref")
            status = notification_data.get("status")
            monetbil_transaction_id = notification_data.get("transaction_id")
            
            if not payment_ref:
                logger.error("Payment notification missing payment_ref")
                return False
            
            # Find transaction by payment reference
            transaction = db.query(Transaction).filter(
                Transaction.payment_reference == payment_ref
            ).first()
            
            if not transaction:
                logger.error(f"Transaction not found for payment_ref: {payment_ref}")
                return False
            
            # Update transaction status
            if status == "success":
                transaction.status = "COMPLETED"
                transaction.monetbil_transaction_id = monetbil_transaction_id
                transaction.completed_at = datetime.now()
                
                # Update service request status
                service_request = db.query(ServiceRequest).filter(
                    ServiceRequest.id == transaction.service_request_id
                ).first()
                
                if service_request:
                    service_request.status = "PAYMENT_COMPLETED"
                    service_request.completed_at = datetime.now()
                
                # Send confirmation messages
                self._send_payment_confirmations(db, transaction, service_request)
                
                logger.info(f"Payment completed for transaction {transaction.id}")
                
            elif status == "failed":
                transaction.status = "FAILED"
                transaction.failure_reason = notification_data.get("error_message", "Payment failed")
                
                logger.warning(f"Payment failed for transaction {transaction.id}")
            
            db.commit()
            return True
            
        except Exception as e:
            logger.error(f"Payment notification processing error: {str(e)}")
            return False
    
    def _send_payment_confirmations(self, db: Session, transaction: Transaction, 
                                  service_request: ServiceRequest):
        """Send payment confirmation messages to customer and provider"""
        try:
            whatsapp_service = WhatsAppService()
            
            # Get customer and provider info
            customer = db.query(User).filter(User.id == transaction.customer_id).first()
            provider = db.query(Provider).filter(Provider.id == transaction.provider_id).first()
            
            if customer:
                # Send confirmation to customer
                customer_message = f"""
✅ *Paiement confirmé !*

Votre paiement de {transaction.amount:,.0f} FCFA pour le service de {service_request.service_type} a été traité avec succès.

📝 *Détails:*
• Montant: {transaction.amount:,.0f} FCFA
• Service: {service_request.service_type}
• Prestataire: {provider.name if provider else 'N/A'}
• Référence: {transaction.payment_reference}

Merci d'avoir utilisé Djobea AI ! 🙏
                """.strip()
                
                whatsapp_service.send_message(customer.phone_number, customer_message)
            
            if provider:
                # Send notification to provider
                provider_message = f"""
💰 *Paiement reçu !*

Le client a effectué le paiement pour votre service.

📝 *Détails:*
• Montant total: {transaction.amount:,.0f} FCFA
• Votre part: {transaction.provider_payout:,.0f} FCFA
• Commission plateforme: {transaction.commission:,.0f} FCFA
• Service: {service_request.service_type}
• Référence: {transaction.payment_reference}

Le paiement sera traité sous 24h. 💼
                """.strip()
                
                whatsapp_service.send_message(provider.whatsapp_id, provider_message)
                
        except Exception as e:
            logger.error(f"Failed to send payment confirmations: {str(e)}")
    
    def initiate_service_payment(self, db: Session, service_request_id: int, 
                               amount: float) -> Dict[str, Any]:
        """Initiate payment after service completion"""
        try:
            service_request = db.query(ServiceRequest).filter(
                ServiceRequest.id == service_request_id
            ).first()
            
            if not service_request:
                return {"success": False, "error": "Service request not found"}
            
            if service_request.status != "COMPLETED":
                return {"success": False, "error": "Service not completed yet"}
            
            # Get customer info
            customer = db.query(User).filter(
                User.id == service_request.user_id
            ).first()
            
            if not customer:
                return {"success": False, "error": "Customer not found"}
            
            # Create payment
            result = self.create_payment(db, service_request, amount, customer.phone_number)
            
            if result["success"]:
                # Send payment link to customer
                whatsapp_service = WhatsAppService()
                payment_message = f"""
🎉 *Service terminé !*

Votre service de {service_request.service_type} est maintenant terminé.

💳 *Procéder au paiement:*
• Montant: {amount:,.0f} FCFA
• Lien de paiement: {result['payment_url']}

Cliquez sur le lien pour payer via Mobile Money (MTN, Orange, Express Union).

Merci de votre confiance ! 🙏
                """.strip()
                
                whatsapp_service.send_message(customer.phone_number, payment_message)
                
                # Update service request status
                service_request.status = "PAYMENT_PENDING"
                db.commit()
            
            return result
            
        except Exception as e:
            logger.error(f"Payment initiation error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def get_transaction_status(self, db: Session, payment_reference: str) -> Optional[Transaction]:
        """Get transaction status by payment reference"""
        return db.query(Transaction).filter(
            Transaction.payment_reference == payment_reference
        ).first()
    
    def retry_failed_payment(self, db: Session, transaction_id: int) -> Dict[str, Any]:
        """Retry a failed payment"""
        try:
            transaction = db.query(Transaction).filter(
                Transaction.id == transaction_id
            ).first()
            
            if not transaction:
                return {"success": False, "error": "Transaction not found"}
            
            if transaction.status != "FAILED":
                return {"success": False, "error": "Transaction is not in failed state"}
            
            # Get related data
            service_request = db.query(ServiceRequest).filter(
                ServiceRequest.id == transaction.service_request_id
            ).first()
            
            customer = db.query(User).filter(
                User.id == transaction.customer_id
            ).first()
            
            if not service_request or not customer:
                return {"success": False, "error": "Related data not found"}
            
            # Create new payment attempt
            return self.create_payment(db, service_request, transaction.amount, 
                                     customer.phone_number)
            
        except Exception as e:
            logger.error(f"Payment retry error: {str(e)}")
            return {"success": False, "error": str(e)}