"""
Chat API Endpoint for Web Chat Widget
Handles web chat requests and integrates with the conversation manager
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
import uuid
from datetime import datetime

from app.database import get_db
from app.services.natural_conversation_engine import NaturalConversationEngine
from app.services.llm_conversation_manager import LLMConversationManager
from app.models.database_models import User, Conversation
from app.config import get_settings

router = APIRouter()
settings = get_settings()

class ChatMessage(BaseModel):
    """Chat message model for web chat requests"""
    message: str = Field(..., min_length=1, max_length=1000, description="User message")
    session_id: str = Field(..., description="Unique session identifier")
    phone_number: Optional[str] = Field(None, description="User phone number for session linking")
    source: str = Field(default="web_chat", description="Message source")
    timestamp: Optional[str] = Field(None, description="Message timestamp")
    conversation_history: Optional[List[Dict[str, Any]]] = Field(default=[], description="Recent conversation context")
    button_value: Optional[str] = Field(None, description="Button value if user clicked a button")

class ChatResponse(BaseModel):
    """Response model for chat requests"""
    response: str = Field(..., description="AI response message")
    session_id: str = Field(..., description="Session identifier")
    request_complete: bool = Field(default=False, description="Whether service request is complete")
    request_id: Optional[int] = Field(None, description="Service request ID if created")
    suggestions: List[str] = Field(default=[], description="Suggested responses")
    needs_info: List[str] = Field(default=[], description="Missing information needed")
    status: str = Field(default="active", description="Conversation status")
    user_id: Optional[int] = Field(None, description="User ID")
    buttons: List[Dict[str, Any]] = Field(default=[], description="Button options for user interface")
    system_action: Optional[str] = Field(None, description="System action to perform")
    next_step: Optional[str] = Field(None, description="Next conversation step")

@router.post("/webhook/chat", response_model=ChatResponse)
async def handle_web_chat(
    chat_message: ChatMessage,
    db: Session = Depends(get_db)
):
    """
    Handle web chat messages from the chat widget
    
    Args:
        chat_message: The chat message data
        db: Database session
    
    Returns:
        ChatResponse: Structured response with AI message and metadata
    """
    try:
        # Check if phone number is provided - if not, prompt for it
        if not chat_message.phone_number:
            return ChatResponse(
                response="Bonjour! 👋 Bienvenue sur Djobea AI.<br><br>Pour mieux vous aider, veuillez d'abord entrer votre numéro de téléphone dans le champ prévu à cet effet.",
                session_id=chat_message.session_id,
                request_complete=False,
                needs_info=["phone_number"],
                status="phone_required"
            )
        
        # Initialize natural conversation engine
        conversation_engine = NaturalConversationEngine(db)
        
        # Get or create user based on session ID and phone number
        user = get_or_create_web_user(db, chat_message.session_id, chat_message.phone_number)
        
        # Process message through natural conversation engine
        try:
            # Use the actual phone number or session-based identifier
            user_identifier = chat_message.phone_number or f"web_{chat_message.session_id}"
            
            # Process message naturally - all database operations are hidden
            conversation_result = await conversation_engine.process_natural_conversation(
                user_identifier, 
                chat_message.message
            )
            
            # Convert natural conversation result to expected format
            result = {
                "response": conversation_result.response_message,
                "request_info": {
                    "is_complete": conversation_result.conversation_state.active_request_id is not None,
                    "confidence_score": conversation_result.confidence_score,
                    "phase": conversation_result.conversation_state.current_phase.value
                },
                "buttons": [],  # Natural conversation doesn't use buttons - purely conversational
                "system_action": None,
                "next_step": None
            }
        except Exception as e:
            # Fallback to simple response if conversation manager fails
            print(f"Conversation manager error: {str(e)}")
            result = {
                'response': get_simple_response(chat_message.message),
                'request_info': {},
                'request_id': None
            }
        
        # Extract response and metadata
        ai_response = result.get('response', 'Désolé, je n\'ai pas pu traiter votre message.')
        request_info = result.get('request_info', {})
        request_id = result.get('request_id')
        
        # Debug: Log extracted information
        print(f"Debug - Request info: {request_info}")
        print(f"Debug - Conversation phase: {request_info.get('phase', 'unknown')}")
        
        # Convert RequestInfo object to dict if needed
        if hasattr(request_info, '__dict__'):
            request_info_dict = request_info.__dict__
        else:
            request_info_dict = request_info if isinstance(request_info, dict) else {}
        
        # Format response for web chat (convert to HTML)
        formatted_response = format_web_response(ai_response)
        
        # Determine if request is complete
        is_complete = bool(request_id and request_info.get('all_info_collected', False))
        
        # Generate contextual suggestions based on conversation state
        # Hide suggestions if request is completed
        if is_complete or request_info.get('phase') == 'request_processing':
            suggestions = []  # No suggestions when request is completed
        else:
            suggestions = generate_contextual_suggestions(request_info_dict, result, ai_response)
        
        # Identify missing information
        needs_info = get_missing_info(request_info)
        
        # Log conversation for analytics with error handling
        try:
            log_web_conversation(db, user.id, chat_message.message, formatted_response)
        except Exception as log_error:
            print(f"Error logging conversation: {log_error}")
            # Don't fail the request if logging fails
            try:
                db.rollback()
            except Exception:
                pass  # Ignore rollback errors
        
        return ChatResponse(
            response=formatted_response,
            session_id=chat_message.session_id,
            request_complete=is_complete,
            request_id=request_id,
            suggestions=suggestions,
            needs_info=needs_info,
            status="completed" if is_complete else "active",
            user_id=user.id,
            buttons=result.get("buttons", []),
            system_action=result.get("system_action"),
            next_step=result.get("next_step")
        )
        
    except Exception as e:
        # Log error for debugging
        print(f"Chat API error: {str(e)}")
        
        # Return user-friendly error response
        return ChatResponse(
            response=get_error_response(str(e)),
            session_id=chat_message.session_id,
            request_complete=False,
            status="error"
        )

@router.post("/chat-llm", response_model=ChatResponse)
async def chat_llm_endpoint(
    chat_message: ChatMessage,
    db: Session = Depends(get_db)
):
    """
    LLM-driven chat endpoint with natural intent detection and action codes
    
    Args:
        chat_message: The chat message data
        db: Database session
    
    Returns:
        ChatResponse: Structured response with AI message and metadata
    """
    try:
        # Check if phone number is provided - if not, prompt for it
        if not chat_message.phone_number:
            return ChatResponse(
                response="Bonjour! 👋 Bienvenue sur Djobea AI.<br><br>Pour mieux vous aider, veuillez d'abord entrer votre numéro de téléphone dans le champ prévu à cet effet.",
                session_id=chat_message.session_id,
                request_complete=False,
                needs_info=["phone_number"],
                status="phone_required"
            )
        
        # Initialize LLM conversation manager
        llm_manager = LLMConversationManager(db)
        
        # Get or create user based on session ID and phone number
        user = get_or_create_web_user(db, chat_message.session_id, chat_message.phone_number)
        
        # Process message through LLM conversation manager
        try:
            # Use the actual phone number or session-based identifier
            user_identifier = chat_message.phone_number or f"web_{chat_message.session_id}"
            
            # Process message with LLM-driven approach
            result = await llm_manager.process_message(
                user_identifier, 
                chat_message.message,
                chat_message.session_id
            )
            
            # Format response for web chat
            formatted_response = format_web_response(result['response'])
            
            # Log conversation for analytics
            try:
                log_web_conversation(db, user.id, chat_message.message, formatted_response)
            except Exception as log_error:
                print(f"Error logging conversation: {log_error}")
                try:
                    db.rollback()
                except Exception:
                    pass
            
            return ChatResponse(
                response=formatted_response,
                session_id=result['session_id'],
                request_complete=result['request_complete'],
                request_id=result['request_id'],
                suggestions=result['suggestions'],
                needs_info=result['needs_info'],
                status=result['status'],
                user_id=result['user_id'] or user.id,
                buttons=result['buttons'],
                system_action=result['system_action'],
                next_step=result['next_step']
            )
            
        except Exception as e:
            # Fallback to simple response if LLM manager fails
            print(f"LLM conversation manager error: {str(e)}")
            return ChatResponse(
                response=get_simple_response(chat_message.message),
                session_id=chat_message.session_id,
                request_complete=False,
                status="fallback"
            )
        
    except Exception as e:
        # Log error for debugging
        print(f"Chat LLM API error: {str(e)}")
        
        # Return user-friendly error response
        return ChatResponse(
            response=get_error_response(str(e)),
            session_id=chat_message.session_id,
            request_complete=False,
            status="error"
        )

def get_or_create_web_user(db: Session, session_id: str, provided_phone: Optional[str] = None) -> User:
    """
    Get or create a user for web chat sessions
    
    Args:
        db: Database session
        session_id: Unique session identifier
        provided_phone: Phone number provided by user (optional)
    
    Returns:
        User: The user object
    """
    # If phone number is provided, try to find existing WhatsApp user first
    if provided_phone:
        # Clean and normalize phone number
        clean_phone = provided_phone.replace('+', '').replace('-', '').replace(' ', '')
        if not clean_phone.startswith('237'):
            clean_phone = f"237{clean_phone}"
        
        # Check for existing WhatsApp user with this phone number
        existing_user = db.query(User).filter(User.phone_number == clean_phone).first()
        if existing_user:
            print(f"Found existing user with phone {clean_phone}: {existing_user.name}")
            return existing_user
    
    # Otherwise, create a session-based phone number format (keep under 20 chars)
    session_phone = f"web_{session_id[-12:]}"  # Use last 12 chars to stay under limit
    
    # Check if session-based user already exists
    user = db.query(User).filter(User.phone_number == session_phone).first()
    
    if not user:
        # Create new web user with provided phone or session-based phone
        final_phone = provided_phone if provided_phone else session_phone
        
        user = User(
            whatsapp_id=session_id[-48:],  # Keep under 50 char limit
            phone_number=final_phone,
            name=f"Web User {session_id[-8:]}" if not provided_phone else f"User {final_phone[-4:]}"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"Created new user with phone {final_phone}: {user.name}")
    
    return user

def format_web_response(response: str) -> str:
    """
    Format AI response for web chat display
    
    Args:
        response: Raw AI response
    
    Returns:
        str: HTML-formatted response
    """
    # Convert newlines to HTML breaks
    formatted = response.replace('\n', '<br>')
    
    # Handle common formatting patterns
    formatted = formatted.replace('**', '<strong>').replace('**', '</strong>')
    formatted = formatted.replace('*', '<em>').replace('*', '</em>')
    
    # Add WhatsApp-style link formatting
    if 'whatsapp' in formatted.lower():
        formatted = formatted.replace(
            'WhatsApp',
            '<span style="color: #25D366; font-weight: bold;">WhatsApp</span>'
        )
    
    return formatted

def generate_contextual_suggestions(request_info: dict, result: dict, ai_response: str) -> List[str]:
    """
    Generate contextual suggestions based on conversation state and AI response
    
    Args:
        request_info: Current request information
        result: Processing result
        ai_response: AI response text
    
    Returns:
        List[str]: Contextual suggestions
    """
    suggestions = []
    
    # Analyze what information is already collected
    collected_info = request_info.get('collected_info', {})
    phase = request_info.get('phase', 'greeting')
    
    # Get service type if mentioned in response
    service_type = None
    if 'plomberie' in ai_response.lower():
        service_type = 'plomberie'
    elif 'électr' in ai_response.lower():
        service_type = 'electricite'
    elif 'électroménager' in ai_response.lower():
        service_type = 'electromenager'
    
    # Generate contextual suggestions based on conversation state
    if phase == 'greeting' or not collected_info:
        # First interaction - suggest common problems
        if service_type == 'plomberie':
            suggestions = [
                "Fuite d'eau sous l'évier",
                "WC bouché", 
                "Problème de pression d'eau"
            ]
        elif service_type == 'electricite':
            suggestions = [
                "Panne de courant dans une pièce",
                "Prise électrique qui ne marche pas",
                "Problème avec le disjoncteur"
            ]
        elif service_type == 'electromenager':
            suggestions = [
                "Réfrigérateur qui ne refroidit plus",
                "Machine à laver qui fuit",
                "Climatiseur qui ne marche pas"
            ]
        else:
            # Generic service suggestions
            suggestions = [
                "Problème de plomberie",
                "Problème électrique", 
                "Réparation électroménager"
            ]
    
    elif 'quartier' in ai_response.lower() or 'où' in ai_response.lower():
        # Location being asked
        suggestions = [
            "Bonamoussadi",
            "Akwa",
            "Douala centre"
        ]
    
    elif 'décrivez' in ai_response.lower() or 'détail' in ai_response.lower():
        # Description being asked
        if service_type == 'plomberie':
            suggestions = [
                "L'eau coule sous l'évier depuis hier",
                "Les WC sont complètement bouchés",
                "Plus d'eau chaude depuis ce matin"
            ]
        elif service_type == 'electricite':
            suggestions = [
                "Le courant a sauté dans la cuisine",
                "Plus de courant dans toute la maison",
                "Les prises ne marchent plus"
            ]
        else:
            suggestions = [
                "Ça marche plus depuis hier",
                "Il y a des bruits bizarres",
                "Ça fuit partout"
            ]
    
    elif 'urgent' in ai_response.lower() or 'rapidement' in ai_response.lower():
        # Urgency being discussed
        suggestions = [
            "Oui, c'est urgent",
            "Non, pas urgent",
            "Dans les 2 prochaines heures"
        ]
    
    else:
        # Default contextual suggestions
        suggestions = [
            "Oui, exactement",
            "Non, pas vraiment",
            "Pouvez-vous m'expliquer?"
        ]
    
    # Ensure we have at least some suggestions
    if not suggestions:
        suggestions = [
            "Continuez s'il vous plaît",
            "J'ai compris",
            "Merci"
        ]
    
    return suggestions[:3]  # Return max 3 suggestions

def generate_suggestions(request_info: dict, result: dict) -> List[str]:
    """
    Legacy function for backward compatibility
    
    Args:
        request_info: Current request information
        result: Conversation manager result
    
    Returns:
        List[str]: Suggested responses
    """
    suggestions = []
    
    # Check if this is the very first message (greeting)
    ai_response = result.get('response', '')
    is_greeting = any(greeting in ai_response.lower() for greeting in ['bonjour', 'comment puis-je', 'assistant'])
    
    # Only show service type suggestions if this is a greeting AND no service type detected
    if is_greeting and not request_info.get('service_type'):
        suggestions = [
            "J'ai un problème de plomberie",
            "J'ai un problème électrique", 
            "Mon électroménager ne marche pas"
        ]
    
    # If service type known but missing location
    elif request_info.get('service_type') and not request_info.get('location'):
        suggestions = [
            "Je suis à Bonamoussadi",
            "Je suis à Douala centre",
            "Je suis près de Total Bonamoussadi"
        ]
    
    # If service and location known but missing description
    elif (request_info.get('service_type') and 
          request_info.get('location') and 
          not request_info.get('description')):
        service_type = request_info.get('service_type', '')
        if 'plomberie' in service_type.lower():
            suggestions = [
                "J'ai une fuite d'eau",
                "Mon robinet ne marche pas", 
                "Mes toilettes sont bouchées"
            ]
        elif 'électricité' in service_type.lower():
            suggestions = [
                "Je n'ai plus de courant",
                "Ma prise ne marche pas",
                "Mon ventilateur s'est arrêté"
            ]
        elif 'électroménager' in service_type.lower():
            suggestions = [
                "Mon fer à repasser ne chauffe plus",
                "Ma bouilloire ne marche plus",
                "Mon mixeur fait du bruit"
            ]
    
    # If request is complete, suggest next actions
    elif request_info.get('all_info_collected'):
        suggestions = [
            "Quand le prestataire va-t-il arriver?",
            "Quel est le prix estimé?",
            "Comment puis-je contacter le prestataire?"
        ]
    
    # For cases where service is identified but conversation isn't complete, don't suggest service types
    return suggestions[:3]  # Limit to 3 suggestions

def get_missing_info(request_info: dict) -> List[str]:
    """
    Identify missing information for the request
    
    Args:
        request_info: Current request information
    
    Returns:
        List[str]: List of missing information fields
    """
    missing = []
    required_fields = ['service_type', 'location', 'description']
    
    for field in required_fields:
        if not request_info.get(field):
            field_names = {
                'service_type': 'Type de service',
                'location': 'Localisation',
                'description': 'Description du problème'
            }
            missing.append(field_names.get(field, field))
    
    return missing

def log_web_conversation(db: Session, user_id: int, user_message: str, ai_response: str):
    """
    Log conversation for analytics and history
    
    Args:
        db: Database session
        user_id: User ID
        user_message: User's message
        ai_response: AI response
    """
    try:
        # Create conversation record
        conversation = Conversation(
            user_id=user_id,
            message_type="incoming",
            message_content=user_message,
            ai_response=ai_response
        )
        db.add(conversation)
        db.commit()
    except Exception as e:
        print(f"Error logging conversation: {str(e)}")
        # Don't fail the main request if logging fails
        pass

def get_error_response(error_message: str) -> str:
    """
    Generate user-friendly error response
    
    Args:
        error_message: Technical error message
    
    Returns:
        str: User-friendly error message
    """
    # Map common errors to user-friendly messages
    if "database" in error_message.lower():
        return ("Désolé, nous rencontrons un problème technique temporaire. "
                "Veuillez réessayer dans quelques instants ou nous contacter "
                "directement sur WhatsApp.")
    
    elif "timeout" in error_message.lower():
        return ("La réponse prend plus de temps que prévu. "
                "Pouvez-vous reformuler votre demande ou nous contacter "
                "directement sur WhatsApp?")
    
    elif "api" in error_message.lower():
        return ("Notre service d'intelligence artificielle est temporairement "
                "indisponible. Nous vous invitons à nous contacter directement "
                "sur WhatsApp pour une assistance immédiate.")
    
    else:
        return ("Désolé, une erreur inattendue s'est produite. "
                "Veuillez réessayer ou nous contacter directement sur WhatsApp. "
                "Nous sommes là pour vous aider! 😊")

@router.get("/webhook/chat/health")
async def chat_health_check():
    """Health check endpoint for chat service"""
    return {
        "status": "healthy",
        "service": "djobea_chat_api",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "2.0"
    }

@router.get("/webhook/chat/session/{session_id}")
async def get_chat_session(session_id: str, db: Session = Depends(get_db)):
    """
    Get chat session information
    
    Args:
        session_id: Session identifier
        db: Database session
    
    Returns:
        Dict: Session information
    """
    try:
        user = get_or_create_web_user(db, session_id)
        
        # Get recent conversations
        recent_conversations = db.query(Conversation).filter(
            Conversation.user_id == user.id,
            Conversation.source == "web_chat"
        ).order_by(Conversation.created_at.desc()).limit(10).all()
        
        return {
            "session_id": session_id,
            "user_id": user.id,
            "conversation_count": len(recent_conversations),
            "last_activity": recent_conversations[0].created_at.isoformat() if recent_conversations else None,
            "status": "active"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def get_simple_response(message: str) -> str:
    """
    Generate simple fallback response
    
    Args:
        message: User's message
    
    Returns:
        str: Simple response
    """
    message_lower = message.lower()
    
    if any(word in message_lower for word in ['bonjour', 'salut', 'bonsoir', 'hello']):
        return "Bonjour ! Je suis Djobea AI, votre assistant pour les services à domicile à Douala. Comment puis-je vous aider aujourd'hui ?"
    elif any(word in message_lower for word in ['plombier', 'plomberie', 'robinet', 'fuite']):
        return "Je comprends que vous avez besoin d'un plombier. Pouvez-vous me donner plus de détails sur le problème et votre localisation ?"
    elif any(word in message_lower for word in ['électricien', 'électricité', 'courant', 'lumière']):
        return "Je vois que vous avez un problème électrique. Pouvez-vous me dire où vous êtes et quelle est la nature du problème ?"
    elif any(word in message_lower for word in ['réparation', 'panne', 'cassé']):
        return "Je peux vous aider à trouver un technicien. Quel appareil a besoin de réparation et où êtes-vous situé ?"
    else:
        return "Je suis là pour vous aider avec vos services à domicile. Pouvez-vous me dire de quel service vous avez besoin ?"