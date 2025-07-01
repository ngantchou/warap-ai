from fastapi import APIRouter, Request, HTTPException, Depends, Form
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from typing import Dict, Any
import asyncio
from datetime import datetime

from database import get_db
from services.ai_service import ai_service
from services.whatsapp_service import whatsapp_service
from services.provider_service import ProviderService
from services.request_service import RequestService
from app.services.conversation_manager import conversation_manager
from models import RequestStatus, Conversation, ServiceRequest, User
from utils.logger import setup_logger

logger = setup_logger(__name__)
router = APIRouter()

@router.post("/whatsapp")
async def whatsapp_webhook(
    request: Request,
    AccountSid: str = Form(...),
    MessageSid: str = Form(...),
    From: str = Form(...),
    To: str = Form(...),
    Body: str = Form(...),
    db: Session = Depends(get_db)
):
    """Handle incoming WhatsApp messages"""
    
    try:
        # Parse the incoming message
        webhook_data = {
            "AccountSid": AccountSid,
            "MessageSid": MessageSid,
            "From": From,
            "To": To,
            "Body": Body
        }
        
        message_data = whatsapp_service.parse_incoming_message(webhook_data)
        
        if not message_data:
            logger.error("Failed to parse incoming WhatsApp message")
            return PlainTextResponse("", status_code=200)
        
        user_phone = message_data["from"]
        message_body = message_data["body"].strip()
        
        logger.info(f"Received WhatsApp message from {user_phone}: {message_body}")
        
        # Initialize services
        request_service = RequestService(db)
        provider_service = ProviderService(db)
        
        # Get or create user
        user = request_service.get_user_or_create(user_phone)
        
        # Check if this is a provider responding to a request
        provider = provider_service.get_provider_by_whatsapp_id(user_phone)
        
        if provider:
            # Handle provider response
            await handle_provider_response(provider, message_body, db)
        else:
            # Handle user request
            await handle_user_request(user.id, message_body, user_phone, db)
        
        return PlainTextResponse("", status_code=200)
        
    except Exception as e:
        logger.error(f"Error in WhatsApp webhook: {e}")
        return PlainTextResponse("", status_code=500)

async def handle_user_request(user_id: int, message: str, user_phone: str, db: Session):
    """Handle incoming user request"""
    
    try:
        request_service = RequestService(db)
        provider_service = ProviderService(db)
        
        # Use Sprint 2 conversation manager for intelligent processing
        response_message, request_info = conversation_manager.process_message(str(user_id), message)
        
        # Send response to user
        whatsapp_service.send_message(user_phone, response_message)
        
        # Log the conversation
        request_service.log_conversation(
            user_id=user_id,
            message_content=message,
            ai_response=response_message,
            extracted_data={
                "service_type": request_info.service_type,
                "location": request_info.location,
                "description": request_info.description,
                "urgency": request_info.urgency,
                "confidence_score": request_info.confidence_score
            }
        )
        
        # If request is complete, create service request and notify providers
        if request_info.is_complete():
            # Check if user has an incomplete request to update
            incomplete_request = request_service.find_incomplete_request_for_user(user_id)
            
            if incomplete_request:
                # Update existing request
                incomplete_request.service_type = request_info.service_type
                incomplete_request.description = request_info.description
                incomplete_request.location = request_info.location
                incomplete_request.preferred_time = request_info.urgency
                incomplete_request.urgency = request_info.urgency
                db.commit()
                service_request = incomplete_request
            else:
                # Create new service request using RequestInfo data
                request_data = {
                    "service_type": request_info.service_type,
                    "description": request_info.description,
                    "location": request_info.location,
                    "preferred_time": request_info.urgency,
                    "urgency": request_info.urgency
                }
                service_request = request_service.create_request(user_id, request_data)
            
            if service_request:
                # Find available providers
                providers = provider_service.find_available_providers(
                    request_info.service_type,
                    request_info.location
                )
                
                if providers:
                    # Notify providers (start with the highest rated)
                    await notify_providers(service_request, providers[:3], db)  # Notify top 3 providers
                    logger.info(f"Created service request ID {service_request.id} and notified {len(providers)} providers")
                else:
                    # No providers available
                    no_provider_message = f"""
Désolé, nous n'avons actuellement aucun prestataire disponible pour le service {request_info.service_type} dans votre zone.

Notre équipe va rechercher des prestataires supplémentaires et vous recontactera dès que possible.

Merci de votre patience !
                    """.strip()
                    
                    whatsapp_service.send_message(user_phone, no_provider_message)
        
        # Note: With Sprint 2 conversation manager, all incomplete requests are handled automatically
        # through the intelligent conversation flow. No need for manual incomplete request creation.
        
    except Exception as e:
        logger.error(f"Error handling user request: {e}")
        # Send error message to user
        error_message = "Désolé, nous rencontrons un problème technique. Veuillez réessayer dans quelques minutes."
        whatsapp_service.send_message(user_phone, error_message)

async def handle_provider_response(provider, message: str, db: Session):
    """Handle provider response to service request"""
    
    try:
        message_lower = message.lower().strip()
        
        # Simple response parsing - could be enhanced with AI
        if message_lower in ["oui", "yes", "ok", "d'accord", "accepte"]:
            # Provider accepts - need to identify which request
            # For MVP, assume the most recent pending request for this provider
            pending_requests = db.query(ServiceRequest).filter(
                ServiceRequest.status == RequestStatus.PENDING
            ).order_by(ServiceRequest.created_at.desc()).limit(5).all()
            
            # In a real system, we'd track which request was sent to which provider
            # For MVP, we'll accept the first pending request
            if pending_requests:
                request = pending_requests[0]
                
                # Assign request to provider
                request.provider_id = provider.id
                request.status = RequestStatus.ASSIGNED
                request.accepted_at = datetime.utcnow()
                
                # Update provider stats
                provider.total_jobs += 1
                
                db.commit()
                
                # Notify user
                user_phone = request.user.whatsapp_id
                confirmation_message = f"""
✅ Bonne nouvelle ! Votre demande de {request.service_type} a été acceptée par {provider.name}.

📞 Contact du prestataire: {provider.phone_number}
📍 Adresse: {request.location}
⏰ Délai: {request.preferred_time or 'À convenir'}

Le prestataire va vous contacter directement pour organiser l'intervention.

Merci d'avoir utilisé Djobea AI !
                """.strip()
                
                whatsapp_service.send_message(user_phone, confirmation_message)
                
                # Confirm to provider
                provider_confirmation = f"""
✅ Mission acceptée avec succès !

📋 Détails de la mission:
- Service: {request.service_type}
- Description: {request.description}
- Adresse: {request.location}
- Client: {request.user.name or 'Non spécifié'}
- Téléphone client: {request.user.phone_number}

Veuillez contacter le client pour organiser l'intervention.
                """.strip()
                
                whatsapp_service.send_message(provider.whatsapp_id, provider_confirmation)
                
                logger.info(f"Provider {provider.id} accepted request {request.id}")
            
        elif message_lower in ["non", "no", "refuse", "pas disponible"]:
            # Provider refuses
            refusal_message = "Message reçu. Nous comprenons que vous n'êtes pas disponible pour cette mission."
            whatsapp_service.send_message(provider.whatsapp_id, refusal_message)
            
            logger.info(f"Provider {provider.id} refused a request")
        
        else:
            # Unknown response
            help_message = """
Pour répondre à une demande de mission:
• Tapez "OUI" pour accepter
• Tapez "NON" pour refuser

Pour toute autre question, contactez le support Djobea AI.
            """.strip()
            
            whatsapp_service.send_message(provider.whatsapp_id, help_message)
        
    except Exception as e:
        logger.error(f"Error handling provider response: {e}")

async def notify_providers(service_request, providers: list, db: Session):
    """Notify providers about new service request"""
    
    try:
        # Generate notification message
        notification_data = {
            "service_type": service_request.service_type,
            "description": service_request.description,
            "location": service_request.location,
            "preferred_time": service_request.preferred_time,
            "urgency": service_request.urgency
        }
        
        notification_message = ai_service.generate_provider_notification(notification_data)
        
        # Send notifications to providers
        for provider in providers:
            success = whatsapp_service.send_provider_notification(
                provider.whatsapp_id,
                notification_message
            )
            
            if success:
                logger.info(f"Notified provider {provider.id} about request {service_request.id}")
            else:
                logger.error(f"Failed to notify provider {provider.id} about request {service_request.id}")
        
        # Set a background task to check for responses
        # In production, this would be handled by a job queue
        asyncio.create_task(check_provider_responses(service_request.id, len(providers)))
        
    except Exception as e:
        logger.error(f"Error notifying providers: {e}")

async def check_provider_responses(request_id: int, providers_notified: int):
    """Check if providers respond within timeout"""
    
    # Wait for provider response timeout (10 minutes)
    await asyncio.sleep(600)  # 10 minutes
    
    try:
        # Use a new database session for this background task
        from database import SessionLocal
        db = SessionLocal()
        
        try:
            request = db.query(ServiceRequest).filter(
                ServiceRequest.id == request_id
            ).first()
            
            if request and request.status == RequestStatus.PENDING:
                # No provider accepted, notify user
                user_phone = request.user.whatsapp_id
                
                timeout_message = f"""
⏰ Nous recherchons encore un prestataire pour votre demande de {request.service_type}.

Notre équipe continue de chercher et vous contactera dès qu'un prestataire sera disponible.

Merci de votre patience !
                """.strip()
                
                whatsapp_service.send_message(user_phone, timeout_message)
                
                logger.info(f"Provider response timeout for request {request_id}")
        
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error checking provider responses: {e}")

# Status webhook for message delivery (optional)
@router.post("/whatsapp/status")
async def whatsapp_status_webhook(request: Request):
    """Handle WhatsApp message status updates"""
    
    try:
        form_data = await request.form()
        message_sid = form_data.get("MessageSid")
        message_status = form_data.get("MessageStatus")
        
        logger.info(f"Message {message_sid} status: {message_status}")
        
        return PlainTextResponse("", status_code=200)
        
    except Exception as e:
        logger.error(f"Error in status webhook: {e}")
        return PlainTextResponse("", status_code=200)
