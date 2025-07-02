"""
Payment API routes for Djobea AI
Handles Monetbil payment integration and webhook processing
"""

import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.monetbil_service import MonetbilService
from app.models.database_models import ServiceRequest, Transaction, User
from app.services.whatsapp_service import WhatsAppService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/webhook/monetbil")
async def monetbil_webhook(
    request: Request,
    payment_ref: str = Form(...),
    status: str = Form(...),
    transaction_id: str = Form(None),
    amount: str = Form(None),
    error_message: str = Form(None),
    db: Session = Depends(get_db)
):
    """Handle Monetbil payment webhook notifications"""
    try:
        # Get request body for signature verification
        body = await request.body()
        signature = request.headers.get("X-Monetbil-Signature", "")
        
        monetbil_service = MonetbilService()
        
        # Verify webhook signature
        if not monetbil_service.verify_webhook_signature(body.decode(), signature):
            logger.warning(f"Invalid webhook signature for payment_ref: {payment_ref}")
            raise HTTPException(status_code=401, detail="Invalid signature")
        
        # Prepare notification data
        notification_data = {
            "payment_ref": payment_ref,
            "status": status,
            "transaction_id": transaction_id,
            "amount": amount,
            "error_message": error_message
        }
        
        # Process the payment notification
        success = monetbil_service.process_payment_notification(db, notification_data)
        
        if success:
            logger.info(f"Payment notification processed successfully: {payment_ref}")
            return {"status": "success", "message": "Notification processed"}
        else:
            logger.error(f"Failed to process payment notification: {payment_ref}")
            return {"status": "error", "message": "Failed to process notification"}
            
    except Exception as e:
        logger.error(f"Webhook processing error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/payment/success")
async def payment_success(
    request: Request,
    payment_ref: str = None,
    db: Session = Depends(get_db)
):
    """Payment success page"""
    try:
        transaction = None
        if payment_ref:
            monetbil_service = MonetbilService()
            transaction = monetbil_service.get_transaction_status(db, payment_ref)
        
        return HTMLResponse(content=f"""
        <!DOCTYPE html>
        <html lang="fr">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Paiement Confirmé - Djobea AI</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
            <style>
                body {{ background: linear-gradient(135deg, #25D366 0%, #128C7E 100%); min-height: 100vh; }}
                .card {{ border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.2); }}
                .success-icon {{ font-size: 4rem; color: #25D366; }}
            </style>
        </head>
        <body class="d-flex align-items-center">
            <div class="container">
                <div class="row justify-content-center">
                    <div class="col-md-6">
                        <div class="card">
                            <div class="card-body text-center py-5">
                                <div class="success-icon mb-4">✅</div>
                                <h2 class="text-success mb-4">Paiement Confirmé !</h2>
                                <p class="lead mb-4">Votre paiement a été traité avec succès.</p>
                                {f'<p><strong>Référence:</strong> {transaction.payment_reference}</p>' if transaction else ''}
                                {f'<p><strong>Montant:</strong> {transaction.amount:,.0f} FCFA</p>' if transaction else ''}
                                <p class="text-muted">Vous recevrez une confirmation par WhatsApp sous peu.</p>
                                <a href="/" class="btn btn-success btn-lg mt-3">Retour à l'accueil</a>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """)
        
    except Exception as e:
        logger.error(f"Payment success page error: {str(e)}")
        return HTMLResponse(content="""
        <!DOCTYPE html>
        <html lang="fr">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Erreur - Djobea AI</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body class="d-flex align-items-center bg-light">
            <div class="container">
                <div class="row justify-content-center">
                    <div class="col-md-6">
                        <div class="card">
                            <div class="card-body text-center py-5">
                                <h2 class="text-warning mb-4">⚠️ Erreur</h2>
                                <p>Une erreur s'est produite lors du traitement de votre paiement.</p>
                                <a href="/" class="btn btn-primary">Retour à l'accueil</a>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """, status_code=500)


@router.post("/api/payments/initiate")
async def initiate_payment(
    request: Request,
    db: Session = Depends(get_db)
):
    """API endpoint to initiate payment for a service request"""
    try:
        data = await request.json()
        service_request_id = data.get("service_request_id")
        amount = data.get("amount")
        
        if not service_request_id or not amount:
            raise HTTPException(status_code=400, detail="Missing required fields")
        
        monetbil_service = MonetbilService()
        result = monetbil_service.initiate_service_payment(db, service_request_id, amount)
        
        return JSONResponse(content=result)
        
    except Exception as e:
        logger.error(f"Payment initiation API error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/api/payments/status/{payment_reference}")
async def get_payment_status(
    payment_reference: str,
    db: Session = Depends(get_db)
):
    """Get payment status by reference"""
    try:
        monetbil_service = MonetbilService()
        transaction = monetbil_service.get_transaction_status(db, payment_reference)
        
        if not transaction:
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        return {
            "payment_reference": transaction.payment_reference,
            "status": transaction.status,
            "amount": transaction.amount,
            "currency": transaction.currency,
            "created_at": transaction.created_at.isoformat(),
            "completed_at": transaction.completed_at.isoformat() if transaction.completed_at else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Payment status API error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/api/payments/retry/{transaction_id}")
async def retry_payment(
    transaction_id: int,
    db: Session = Depends(get_db)
):
    """Retry a failed payment"""
    try:
        monetbil_service = MonetbilService()
        result = monetbil_service.retry_failed_payment(db, transaction_id)
        
        return JSONResponse(content=result)
        
    except Exception as e:
        logger.error(f"Payment retry API error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")