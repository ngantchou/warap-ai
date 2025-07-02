from fastapi import APIRouter, Request, HTTPException, Depends, Form
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from typing import Dict, Any
import asyncio
from datetime import datetime

from app.database import get_db
from app.services.ai_service import ai_service
from app.services.whatsapp_service import whatsapp_service
from app.services.provider_service import ProviderService
from app.services.request_service import RequestService
from app.services.conversation_manager import conversation_manager
from app.services.communication_service import CommunicationService
from app.services.quick_actions_service import QuickActionsService
from app.services.scheduling_service import SchedulingService
from app.services.media_upload_service import get_media_upload_service
from app.services.visual_analysis_service import get_visual_analysis_service
from app.models.database_models import RequestStatus, Conversation, ServiceRequest, User, ActionType, Provider, MediaUpload, VisualAnalysis
from app.utils.logger import setup_logger

logger = setup_logger(__name__)
router = APIRouter()

@router.post("/whatsapp")
async def whatsapp_webhook(
    request: Request,
    AccountSid: str = Form(...),
    MessageSid: str = Form(...),
    From: str = Form(...),
    To: str = Form(...),
    Body: str = Form(""),
    NumMedia: int = Form(0),
    MediaUrl0: str = Form(None),
    MediaContentType0: str = Form(None),
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
            "Body": Body,
            "NumMedia": NumMedia,
            "MediaUrl0": MediaUrl0,
            "MediaContentType0": MediaContentType0
        }
        
        message_data = whatsapp_service.parse_incoming_message(webhook_data)
        
        if not message_data:
            logger.error("Failed to parse incoming WhatsApp message")
            return PlainTextResponse("", status_code=200)
        
        user_phone = message_data["from"]
        message_body = message_data["body"].strip()
        has_media = NumMedia > 0 and MediaUrl0
        
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
            # Handle media uploads if present
            if has_media:
                await handle_media_upload(user.id, MediaUrl0, MediaContentType0, user_phone, db)
            
            # Handle text message if present
            if message_body:
                await handle_user_request(user.id, message_body, user_phone, db)
        
        return PlainTextResponse("", status_code=200)
        
    except Exception as e:
        logger.error(f"Error in WhatsApp webhook: {e}")
        return PlainTextResponse("", status_code=500)

async def handle_media_upload(user_id: int, media_url: str, content_type: str, user_phone: str, db: Session):
    """Handle media upload from WhatsApp"""
    try:
        logger.info(f"Processing media upload from user {user_id}: {media_url}")
        
        # Get user's current/most recent service request
        request_service = RequestService(db)
        user_requests = request_service.get_user_requests(user_id, limit=1)
        
        if not user_requests:
            # No existing request - ask user to describe the problem first
            response = """📸 J'ai reçu votre photo ! 

Pour mieux vous aider, pourriez-vous d'abord me décrire votre problème en quelques mots ? Par exemple :
• "Fuite d'eau dans la cuisine"
• "Panne électrique dans le salon" 
• "Climatiseur ne fonctionne plus"

Ensuite, je pourrai analyser votre photo et vous donner des conseils précis ! 🔧"""
            
            whatsapp_service.send_message(user_phone, response)
            return
        
        current_request = user_requests[0]
        
        # Check if request is in progress and needs visual progress tracking
        if current_request.status in ["ASSIGNED", "IN_PROGRESS"]:
            # Handle progress photo
            media_service = get_media_upload_service(db)
            media_upload = await media_service.process_whatsapp_media(
                media_url, "image", content_type, current_request.id
            )
            
            if media_upload:
                response = """📸 Photo reçue ! 

Je suis en train d'analyser votre image pour suivre les progrès des travaux. Je vous enverrai un rapport détaillé dans quelques instants.

Votre prestataire pourra également voir cette photo pour mieux comprendre la situation. 📋"""
                
                whatsapp_service.send_message(user_phone, response)
                
                # Notify the provider if request is assigned
                if current_request.provider_id:
                    provider = db.query(Provider).filter(
                        Provider.id == current_request.provider_id
                    ).first()
                    provider_phone = provider.whatsapp_id if provider else None
                    
                    if provider_phone:
                        provider_message = f"""📸 Nouvelle photo reçue du client !

Demande #{current_request.id} - {current_request.service_type}
📍 {current_request.location}

Le client a envoyé une nouvelle photo. Vous pouvez la consulter pour suivre l'évolution des travaux."""
                        
                        whatsapp_service.send_message(provider_phone, provider_message)
        
        else:
            # Handle initial problem photo
            media_service = get_media_upload_service(db)
            media_upload = await media_service.process_whatsapp_media(
                media_url, "image", content_type, current_request.id
            )
            
            if media_upload:
                # Generate initial analysis response
                response = f"""📸 Merci pour cette photo ! 

🔍 Je suis en train d'analyser votre image avec l'IA pour :
• Identifier le problème exact
• Évaluer la gravité de la situation  
• Estimer les coûts de réparation
• Recommander le bon spécialiste

📊 Analyse en cours... Je vous enverrai un rapport détaillé dans quelques instants !

Demande #{current_request.id} - {current_request.service_type}"""
                
                whatsapp_service.send_message(user_phone, response)
                
                # If analysis is completed, send detailed results
                if media_upload.analysis_completed and media_upload.visual_analysis:
                    await send_visual_analysis_results(current_request.id, user_phone, db)
    
    except Exception as e:
        logger.error(f"Error handling media upload: {e}")
        error_response = """❌ Désolé, j'ai eu un problème en traitant votre photo.

Pourriez-vous essayer de l'envoyer à nouveau ? Assurez-vous que :
• La photo est claire et bien éclairée
• Le problème est visible sur l'image
• La taille du fichier n'est pas trop importante

Je suis là pour vous aider ! 🔧"""
        
        whatsapp_service.send_message(user_phone, error_response)

async def send_visual_analysis_results(request_id: int, user_phone: str, db: Session):
    """Send detailed visual analysis results to user"""
    try:
        # Get the visual analysis
        media_uploads = db.query(MediaUpload).filter(
            MediaUpload.service_request_id == request_id,
            MediaUpload.analysis_completed == True
        ).all()
        
        if not media_uploads:
            return
        
        # Get service request
        request = db.query(ServiceRequest).filter(ServiceRequest.id == request_id).first()
        if not request:
            return
        
        # Get most recent analysis
        latest_media = media_uploads[-1]
        analysis = latest_media.visual_analysis
        
        if not analysis:
            return
        
        # Format analysis results
        severity_emoji = {
            "minor": "🟢",
            "moderate": "🟡", 
            "major": "🟠",
            "emergency": "🔴"
        }
        
        response = f"""🔍 **ANALYSE TERMINÉE** - Demande #{request_id}

{severity_emoji.get(analysis.severity, '🟡')} **Problème détecté :** {analysis.primary_problem}

📊 **Évaluation :**
• Gravité : {analysis.severity.upper()}
• Confiance : {int(analysis.problem_confidence * 100)}%

💰 **Estimation des coûts :**
{int(analysis.estimated_cost_min):,} - {int(analysis.estimated_cost_max):,} XAF

🔧 **Matériel requis :**
{chr(10).join(f"• {tool}" for tool in analysis.tools_needed[:3]) if analysis.tools_needed else "• À déterminer"}

⏱️ **Durée estimée :** {analysis.estimated_duration}

🚨 **Sécurité :** {'⚠️ Précautions nécessaires' if analysis.safety_hazards else '✅ Pas de risque immédiat'}"""

        if analysis.additional_photos_needed:
            response += f"""

📸 **Photos supplémentaires recommandées :**
{chr(10).join(f"• {photo}" for photo in analysis.additional_photos_needed[:2])}"""

        response += f"""

✅ Je recherche maintenant le meilleur prestataire pour votre {request.service_type} !"""

        whatsapp_service.send_message(user_phone, response)
        
        # Generate photo guidance for better documentation
        media_service = get_media_upload_service(db)
        guidance = media_service.generate_photo_guidance(request.service_type, media_uploads)
        
        if guidance.get("missing"):
            guidance_message = f"""💡 **Conseils pour de meilleures photos :**

{guidance['missing']}

📋 **Angles recommandés :**
{chr(10).join(f"• {angle}" for angle in guidance['angles'][:3]) if guidance.get('angles') else ''}

🎯 **Astuce :** {guidance['tips'][0] if guidance.get('tips') else 'Prenez des photos sous différents angles avec un bon éclairage'}"""
            
            whatsapp_service.send_message(user_phone, guidance_message)
        
    except Exception as e:
        logger.error(f"Error sending visual analysis results: {e}")

async def handle_user_request(user_id: int, message: str, user_phone: str, db: Session):
    """Handle incoming user request"""
    
    try:
        request_service = RequestService(db)
        provider_service = ProviderService(db)
        quick_actions_service = QuickActionsService(db)
        
        # First check if this is a quick action command
        detected_action = conversation_manager.detect_quick_action(message)
        
        if detected_action:
            # Handle quick action command
            response = await quick_actions_service.handle_action_command(
                user_id, user_phone, detected_action, message
            )
            
            # Log the action
            request_service.log_conversation(
                user_id=user_id,
                message_content=message,
                ai_response=response,
                extracted_data={"action_type": detected_action.value}
            )
            
            # Send response
            whatsapp_service.send_message(user_phone, response)
            
            logger.info(f"Handled quick action {detected_action.value} for user {user_id}")
            return
        
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
            # Initialize scheduling service
            scheduling_service = SchedulingService(db)
            
            # Check if user has an incomplete request to update
            incomplete_request = request_service.find_incomplete_request_for_user(user_id)
            
            if incomplete_request:
                # Update existing request with new information
                incomplete_request.service_type = request_info.service_type
                incomplete_request.description = request_info.description
                incomplete_request.location = request_info.location
                incomplete_request.preferred_time = request_info.urgency or request_info.preferred_time_details
                incomplete_request.urgency = request_info.urgency
                
                # Update enhanced scheduling fields
                if request_info.scheduling_preference:
                    scheduling_service.update_request_scheduling(
                        incomplete_request, 
                        request_info.scheduling_preference
                    )
                
                # Update enhanced location fields  
                if request_info.landmark_references:
                    incomplete_request.landmark_references = ", ".join(request_info.landmark_references)
                    incomplete_request.location_accuracy = "approximate" if request_info.location_confidence < 0.8 else "good"
                
                db.commit()
                service_request = incomplete_request
            else:
                # Create new service request using RequestInfo data
                request_data = {
                    "service_type": request_info.service_type,
                    "description": request_info.description,
                    "location": request_info.location,
                    "preferred_time": request_info.urgency or request_info.preferred_time_details,
                    "urgency": request_info.urgency or "normal"
                }
                service_request = request_service.create_request(user_id, request_data)
                
                # Apply enhanced scheduling if available
                if service_request and request_info.scheduling_preference:
                    scheduling_service.update_request_scheduling(
                        service_request, 
                        request_info.scheduling_preference
                    )
                
                # Apply enhanced location data if available
                if service_request and request_info.landmark_references:
                    service_request.landmark_references = ", ".join(request_info.landmark_references)
                    service_request.location_accuracy = "approximate" if request_info.location_confidence < 0.8 else "good"
                    db.commit()
            
            if service_request:
                # Send instant confirmation with pricing
                communication_service = CommunicationService()
                await communication_service.send_instant_confirmation(service_request.id, db)
                
                # Add quick actions menu
                actions_menu = quick_actions_service.generate_actions_menu(service_request.id)
                whatsapp_service.send_message(user_phone, actions_menu)
                
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
                
                # Send enhanced provider acceptance notification
                communication_service = CommunicationService()
                await communication_service.send_provider_acceptance(request.id, provider.id, db)
                
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
