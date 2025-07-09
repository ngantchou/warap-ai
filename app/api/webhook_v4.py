"""
Webhook V4 - Enhanced Multi-turn Dialogue Engine Integration
Integrates the complete dialogue flow management system with WhatsApp webhook
"""
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import PlainTextResponse
from typing import Dict, Any, Optional
import logging
from datetime import datetime

from app.services.enhanced_conversation_manager_v4 import EnhancedConversationManagerV4
from app.services.whatsapp_service import WhatsAppService
from app.services.session_manager import SessionManager
from app.database import get_db
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize services
conversation_manager = EnhancedConversationManagerV4()
whatsapp_service = WhatsAppService()
session_manager = SessionManager()

@router.post("/webhook/whatsapp-v4")
async def whatsapp_webhook_v4(request: Request, db: Session = Depends(get_db)):
    """
    Enhanced WhatsApp webhook with complete multi-turn dialogue engine
    """
    try:
        # Get form data
        form_data = await request.form()
        
        # Extract message details
        message_body = form_data.get("Body", "").strip()
        from_number = form_data.get("From", "").replace("whatsapp:", "")
        to_number = form_data.get("To", "").replace("whatsapp:", "")
        
        if not message_body or not from_number:
            logger.warning("Received empty message or missing sender")
            return PlainTextResponse("", status_code=200)
        
        # Clean phone number
        phone_number = from_number.replace("+", "").replace(" ", "")
        user_id = f"whatsapp_{phone_number}"
        
        logger.info(f"Processing WhatsApp message from {phone_number}: {message_body}")
        
        # Process message through enhanced conversation manager
        conversation_result = await conversation_manager.process_message(
            message=message_body,
            phone_number=phone_number,
            user_id=user_id,
            db=db
        )
        
        # Log conversation metrics
        metrics = conversation_result.get("conversation_metrics", {})
        logger.info(f"Conversation metrics: {metrics}")
        
        # Send response via WhatsApp
        response_message = conversation_result.get("response", "Désolé, je n'ai pas compris votre message.")
        
        # Add suggested actions if available
        suggested_actions = conversation_result.get("suggested_actions", [])
        if suggested_actions:
            actions_text = "\n\n" + "\n".join(f"• {action}" for action in suggested_actions)
            response_message += actions_text
        
        # Add progress indicator
        progress = conversation_result.get("completion_progress", 0)
        if progress > 0:
            response_message += f"\n\n📊 Progression: {progress:.0f}%"
        
        # Send WhatsApp response
        await whatsapp_service.send_message(phone_number, response_message)
        
        # Log successful processing
        logger.info(f"Message processed successfully. Session: {conversation_result.get('session_id')}, "
                   f"State: {conversation_result.get('dialogue_state')}, "
                   f"Progress: {progress:.1f}%")
        
        return PlainTextResponse("", status_code=200)
        
    except Exception as e:
        logger.error(f"Error processing WhatsApp message: {e}", exc_info=True)
        
        # Send error response if possible
        if 'phone_number' in locals():
            try:
                await whatsapp_service.send_message(
                    phone_number,
                    "Désolé, une erreur technique s'est produite. Pouvez-vous répéter votre demande ?"
                )
            except:
                pass
        
        return PlainTextResponse("", status_code=200)

@router.post("/webhook/chat-v4")
async def chat_webhook_v4(request: Request, db: Session = Depends(get_db)):
    """
    Enhanced chat webhook for web interface
    """
    try:
        data = await request.json()
        
        message = data.get("message", "").strip()
        phone_number = data.get("phone_number", "")
        
        if not message or not phone_number:
            raise HTTPException(status_code=400, detail="Message and phone number required")
        
        # Clean phone number
        phone_number = phone_number.replace("+", "").replace(" ", "")
        user_id = f"chat_{phone_number}"
        
        logger.info(f"Processing chat message from {phone_number}: {message}")
        
        # Process message through enhanced conversation manager
        conversation_result = await conversation_manager.process_message(
            message=message,
            phone_number=phone_number,
            user_id=user_id,
            db=db
        )
        
        # Format response for chat interface
        response = {
            "status": "success",
            "message": conversation_result.get("response", "Désolé, je n'ai pas compris votre message."),
            "session_id": conversation_result.get("session_id"),
            "dialogue_state": conversation_result.get("dialogue_state"),
            "completion_progress": conversation_result.get("completion_progress", 0),
            "collected_info": conversation_result.get("collected_info", {}),
            "missing_info": conversation_result.get("missing_info", []),
            "suggested_actions": conversation_result.get("suggested_actions", []),
            "conversation_metrics": conversation_result.get("conversation_metrics", {}),
            "optimization_applied": conversation_result.get("optimization_applied", False),
            "interruption_handled": conversation_result.get("interruption_handled", False),
            "processing_time": conversation_result.get("processing_time", 0)
        }
        
        # Add optimization details if available
        if conversation_result.get("optimization_applied"):
            response["optimization_details"] = {
                "strategy": conversation_result.get("optimization_strategy"),
                "confidence": conversation_result.get("optimization_confidence"),
                "expected_turn_reduction": conversation_result.get("expected_turn_reduction")
            }
        
        # Add interruption details if available
        if conversation_result.get("interruption_handled"):
            response["interruption_details"] = {
                "type": conversation_result.get("interruption_type"),
                "recovery_actions": conversation_result.get("recovery_actions", [])
            }
        
        logger.info(f"Chat message processed successfully. Session: {response['session_id']}, "
                   f"State: {response['dialogue_state']}, "
                   f"Progress: {response['completion_progress']:.1f}%")
        
        return response
        
    except Exception as e:
        logger.error(f"Error processing chat message: {e}", exc_info=True)
        return {
            "status": "error",
            "message": "Désolé, une erreur technique s'est produite. Pouvez-vous répéter votre demande ?",
            "error": str(e)
        }

@router.get("/webhook/conversation-analytics/{session_id}")
async def get_conversation_analytics(session_id: str, db: Session = Depends(get_db)):
    """
    Get detailed conversation analytics for a session
    """
    try:
        analytics = await conversation_manager.get_conversation_analytics(session_id, db)
        return analytics
        
    except Exception as e:
        logger.error(f"Error getting conversation analytics: {e}")
        return {"error": str(e)}

@router.post("/webhook/optimize-conversation")
async def optimize_conversation(request: Request, db: Session = Depends(get_db)):
    """
    Manually optimize conversation flow
    """
    try:
        data = await request.json()
        phone_number = data.get("phone_number", "")
        
        if not phone_number:
            raise HTTPException(status_code=400, detail="Phone number required")
        
        # Clean phone number
        phone_number = phone_number.replace("+", "").replace(" ", "")
        
        optimization_result = await conversation_manager.optimize_conversation_flow(
            phone_number, db
        )
        
        return {
            "status": "success",
            "optimization_result": optimization_result
        }
        
    except Exception as e:
        logger.error(f"Error optimizing conversation: {e}")
        return {
            "status": "error",
            "error": str(e)
        }

@router.post("/webhook/test-dialogue-capabilities")
async def test_dialogue_capabilities(request: Request, db: Session = Depends(get_db)):
    """
    Test dialogue engine capabilities with predefined scenarios
    """
    try:
        data = await request.json()
        phone_number = data.get("phone_number", "237691924999")
        
        # Define test scenarios
        test_scenarios = [
            {
                "name": "Complete Service Request - Plumbing",
                "messages": [
                    "Bonjour, j'ai un problème de plomberie",
                    "Je suis à Bonamoussadi Village, rue des Palmiers",
                    "Mon robinet fuit dans la cuisine",
                    "C'est urgent, il faut réparer aujourd'hui"
                ],
                "expected_outcome": {
                    "should_complete": True,
                    "max_turns": 4
                }
            },
            {
                "name": "Interruption and Recovery",
                "messages": [
                    "J'ai besoin d'un électricien",
                    "En fait non, plutôt un plombier",
                    "Je suis à Bonamoussadi Carrefour",
                    "Toilette bouchée, très urgent"
                ],
                "expected_outcome": {
                    "should_complete": True,
                    "max_turns": 5
                }
            },
            {
                "name": "Multi-field Extraction",
                "messages": [
                    "Bonjour, j'ai une panne d'électricité urgente à Bonamoussadi Village, le courant a sauté dans toute la maison"
                ],
                "expected_outcome": {
                    "should_complete": False,
                    "max_turns": 2
                }
            },
            {
                "name": "Clarification Request",
                "messages": [
                    "Problème technique",
                    "Je ne comprends pas votre question",
                    "Panne d'électricité",
                    "Bonamoussadi Ndokoti",
                    "Tout de suite"
                ],
                "expected_outcome": {
                    "should_complete": True,
                    "max_turns": 6
                }
            }
        ]
        
        # Run test scenarios
        test_results = await conversation_manager.test_dialogue_capabilities(
            phone_number, test_scenarios, db
        )
        
        return {
            "status": "success",
            "test_results": test_results
        }
        
    except Exception as e:
        logger.error(f"Error testing dialogue capabilities: {e}")
        return {
            "status": "error",
            "error": str(e)
        }

@router.post("/webhook/reset-conversation")
async def reset_conversation(request: Request, db: Session = Depends(get_db)):
    """
    Reset conversation for testing
    """
    try:
        data = await request.json()
        phone_number = data.get("phone_number", "")
        
        if not phone_number:
            raise HTTPException(status_code=400, detail="Phone number required")
        
        # Clean phone number
        phone_number = phone_number.replace("+", "").replace(" ", "")
        user_id = f"test_{phone_number}"
        
        reset_result = await conversation_manager.reset_conversation(
            phone_number, user_id, db
        )
        
        return {
            "status": "success",
            "reset_result": reset_result
        }
        
    except Exception as e:
        logger.error(f"Error resetting conversation: {e}")
        return {
            "status": "error",
            "error": str(e)
        }

@router.get("/webhook/system-metrics")
async def get_system_metrics():
    """
    Get comprehensive system metrics
    """
    try:
        metrics = conversation_manager.get_system_metrics()
        return {
            "status": "success",
            "metrics": metrics
        }
        
    except Exception as e:
        logger.error(f"Error getting system metrics: {e}")
        return {
            "status": "error",
            "error": str(e)
        }

@router.post("/webhook/test-optimization")
async def test_optimization(request: Request, db: Session = Depends(get_db)):
    """
    Test optimization strategies
    """
    try:
        data = await request.json()
        phone_number = data.get("phone_number", "237691924555")
        
        # Test different user types
        user_scenarios = [
            {
                "name": "Detailed Responder",
                "messages": [
                    "Bonjour, j'ai un problème assez complexe avec mon système électrique. En fait, depuis hier soir, toutes les lumières de ma maison à Bonamoussadi Village clignotent de manière intermittente. J'ai vérifié le disjoncteur principal et il semble normal. Le problème affecte toute la maison et c'est assez urgent car j'ai des enfants à la maison."
                ]
            },
            {
                "name": "Brief Responder",
                "messages": [
                    "Panne électricité",
                    "Bonamoussadi",
                    "Urgent",
                    "Oui"
                ]
            },
            {
                "name": "Impatient User",
                "messages": [
                    "J'ai besoin d'un plombier MAINTENANT",
                    "Fuite d'eau importante",
                    "Bonamoussadi Village",
                    "Très urgent"
                ]
            }
        ]
        
        optimization_results = []
        
        for scenario in user_scenarios:
            # Reset conversation for each test
            await conversation_manager.reset_conversation(f"{phone_number}_{scenario['name']}", f"test_{phone_number}_{scenario['name']}", db)
            
            # Process messages
            for message in scenario["messages"]:
                result = await conversation_manager.process_message(
                    message,
                    f"{phone_number}_{scenario['name']}",
                    f"test_{phone_number}_{scenario['name']}",
                    db
                )
            
            # Get optimization analysis
            optimization_analysis = await conversation_manager.optimize_conversation_flow(
                f"{phone_number}_{scenario['name']}",
                db
            )
            
            optimization_results.append({
                "scenario": scenario["name"],
                "final_result": result,
                "optimization_analysis": optimization_analysis
            })
        
        return {
            "status": "success",
            "optimization_test_results": optimization_results
        }
        
    except Exception as e:
        logger.error(f"Error testing optimization: {e}")
        return {
            "status": "error",
            "error": str(e)
        }

@router.get("/webhook/health-v4")
async def health_check_v4():
    """
    Health check for enhanced webhook
    """
    try:
        metrics = conversation_manager.get_system_metrics()
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "v4",
            "components": {
                "conversation_manager": "active",
                "dialogue_flow_manager": "active",
                "intelligent_collection": "active",
                "interruption_manager": "active",
                "optimization_engine": "active"
            },
            "metrics": metrics
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }