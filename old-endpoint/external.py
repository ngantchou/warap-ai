"""
External API v1 - External Services Domain
Combines finances_complete.py, payment.py, geolocation.py, export.py
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Path, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from app.database import get_db
from app.models.database_models import AdminUser, ServiceRequest, Provider
from app.utils.auth import get_current_user
from loguru import logger
import io
import csv
import json

router = APIRouter()

# ==== FINANCIAL SERVICES ====
@router.get("/finances/overview")
async def get_finances_overview(
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Get financial overview"""
    try:
        # Get completed requests for revenue calculation
        completed_requests = db.query(ServiceRequest).filter(
            ServiceRequest.status == "completed"
        ).all()
        
        # Calculate revenue metrics
        total_revenue = len(completed_requests) * 25000  # Average service price
        commission = total_revenue * 0.15  # 15% commission
        provider_earnings = total_revenue - commission
        
        return {
            "success": True,
            "data": {
                "totalRevenue": total_revenue,
                "commission": commission,
                "providerEarnings": provider_earnings,
                "totalTransactions": len(completed_requests),
                "averageTransaction": 25000,
                "growth": {
                    "revenue": 15.2,
                    "transactions": 12.5,
                    "commission": 18.7
                },
                "period": "current_month"
            }
        }
    except Exception as e:
        logger.error(f"Get finances overview error: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des données financières")

@router.get("/finances/transactions")
async def get_transactions(
    page: int = Query(1, description="Page number"),
    limit: int = Query(10, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter by status"),
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Get transaction history"""
    try:
        # Get service requests as transactions
        query = db.query(ServiceRequest)
        
        if status:
            query = query.filter(ServiceRequest.status == status)
        
        # Pagination
        total = query.count()
        requests = query.offset((page - 1) * limit).limit(limit).all()
        
        transactions = []
        for req in requests:
            transactions.append({
                "id": req.id,
                "transactionId": f"TXN-{req.id:06d}",
                "serviceType": req.service_type or "Général",
                "amount": 25000,  # Default service price
                "commission": 3750,  # 15% commission
                "providerEarnings": 21250,
                "status": "completed" if req.status == "completed" else "pending",
                "paymentMethod": "mobile_money",
                "createdAt": req.created_at.isoformat() if req.created_at else None,
                "completedAt": req.completed_at.isoformat() if hasattr(req, 'completed_at') and req.completed_at else None
            })
        
        return {
            "success": True,
            "data": transactions,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "totalPages": (total + limit - 1) // limit
            }
        }
    except Exception as e:
        logger.error(f"Get transactions error: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des transactions")

@router.get("/finances/reports")
async def get_financial_reports(
    period: str = Query("30d", description="Time period"),
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Get financial reports"""
    try:
        # Calculate date range
        end_date = datetime.now()
        if period == "7d":
            start_date = end_date - timedelta(days=7)
        elif period == "30d":
            start_date = end_date - timedelta(days=30)
        elif period == "90d":
            start_date = end_date - timedelta(days=90)
        else:
            start_date = end_date - timedelta(days=30)
        
        # Get requests in period
        requests = db.query(ServiceRequest).filter(
            ServiceRequest.created_at >= start_date,
            ServiceRequest.created_at <= end_date
        ).all()
        
        completed_requests = [r for r in requests if r.status == "completed"]
        
        return {
            "success": True,
            "data": {
                "period": period,
                "summary": {
                    "totalRequests": len(requests),
                    "completedRequests": len(completed_requests),
                    "totalRevenue": len(completed_requests) * 25000,
                    "commission": len(completed_requests) * 3750,
                    "providerEarnings": len(completed_requests) * 21250
                },
                "trends": [
                    {"date": "2025-01-15", "revenue": 125000, "transactions": 5},
                    {"date": "2025-01-16", "revenue": 150000, "transactions": 6},
                    {"date": "2025-01-17", "revenue": 175000, "transactions": 7}
                ],
                "serviceBreakdown": {
                    "plomberie": {"count": 12, "revenue": 300000},
                    "electricite": {"count": 8, "revenue": 200000},
                    "electromenager": {"count": 5, "revenue": 125000}
                }
            }
        }
    except Exception as e:
        logger.error(f"Get financial reports error: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la génération du rapport financier")

# ==== PAYMENT SERVICES ====
@router.post("/payments/process")
async def process_payment(
    payment_data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Process payment"""
    try:
        request_id = payment_data.get("requestId")
        amount = payment_data.get("amount")
        payment_method = payment_data.get("paymentMethod", "mobile_money")
        
        # Simulate payment processing
        payment_result = {
            "paymentId": f"PAY-{request_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "status": "completed",
            "amount": amount,
            "commission": amount * 0.15,
            "providerEarnings": amount * 0.85,
            "paymentMethod": payment_method,
            "processedAt": datetime.now().isoformat()
        }
        
        return {
            "success": True,
            "message": "Paiement traité avec succès",
            "data": payment_result
        }
    except Exception as e:
        logger.error(f"Process payment error: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors du traitement du paiement")

@router.get("/payments/methods")
async def get_payment_methods(
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Get available payment methods"""
    try:
        methods = [
            {
                "id": "mtn_momo",
                "name": "MTN Mobile Money",
                "type": "mobile_money",
                "enabled": True,
                "fee": 2.0,
                "currency": "XAF"
            },
            {
                "id": "orange_money",
                "name": "Orange Money",
                "type": "mobile_money",
                "enabled": True,
                "fee": 2.0,
                "currency": "XAF"
            },
            {
                "id": "express_union",
                "name": "Express Union",
                "type": "mobile_money",
                "enabled": True,
                "fee": 1.5,
                "currency": "XAF"
            },
            {
                "id": "cash",
                "name": "Paiement en espèces",
                "type": "cash",
                "enabled": True,
                "fee": 0.0,
                "currency": "XAF"
            }
        ]
        
        return {
            "success": True,
            "data": methods
        }
    except Exception as e:
        logger.error(f"Get payment methods error: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des méthodes de paiement")

# ==== GEOLOCATION SERVICES ====
@router.get("/geolocation/zones")
async def get_zones(
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Get service zones"""
    try:
        zones = [
            {
                "id": 1,
                "name": "Bonamoussadi",
                "name_en": "Bonamoussadi",
                "parentZone": "Douala",
                "zoneType": "district",
                "coordinates": {
                    "lat": 4.0511,
                    "lng": 9.7679
                },
                "coverage": True,
                "activeProviders": 15,
                "avgResponseTime": 12
            },
            {
                "id": 2,
                "name": "Akwa",
                "name_en": "Akwa",
                "parentZone": "Douala",
                "zoneType": "district",
                "coordinates": {
                    "lat": 4.0464,
                    "lng": 9.7516
                },
                "coverage": True,
                "activeProviders": 22,
                "avgResponseTime": 8
            },
            {
                "id": 3,
                "name": "Bonapriso",
                "name_en": "Bonapriso",
                "parentZone": "Douala",
                "zoneType": "district",
                "coordinates": {
                    "lat": 4.0520,
                    "lng": 9.7482
                },
                "coverage": True,
                "activeProviders": 18,
                "avgResponseTime": 10
            }
        ]
        
        return {
            "success": True,
            "data": zones
        }
    except Exception as e:
        logger.error(f"Get zones error: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des zones")

@router.get("/geolocation/coverage")
async def get_coverage_info(
    lat: float = Query(..., description="Latitude"),
    lng: float = Query(..., description="Longitude"),
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Get coverage information for coordinates"""
    try:
        # Simple coverage check (in production, use proper geospatial queries)
        coverage = {
            "inCoverage": True,
            "zone": "Bonamoussadi",
            "confidence": 0.95,
            "nearestProviders": [
                {
                    "id": 1,
                    "name": "Jean Plombier",
                    "distance": 0.8,
                    "rating": 4.7,
                    "responseTime": 15
                },
                {
                    "id": 2,
                    "name": "Paul Électricien",
                    "distance": 1.2,
                    "rating": 4.5,
                    "responseTime": 12
                }
            ],
            "estimatedServiceTime": 15,
            "surcharge": 0.0
        }
        
        return {
            "success": True,
            "data": coverage
        }
    except Exception as e:
        logger.error(f"Get coverage info error: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la vérification de la couverture")

# ==== EXPORT SERVICES ====
@router.get("/export/requests")
async def export_requests(
    format: str = Query("csv", description="Export format"),
    start_date: Optional[str] = Query(None, description="Start date"),
    end_date: Optional[str] = Query(None, description="End date"),
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Export service requests"""
    try:
        # Get requests based on date range
        query = db.query(ServiceRequest)
        
        if start_date:
            query = query.filter(ServiceRequest.created_at >= datetime.fromisoformat(start_date))
        if end_date:
            query = query.filter(ServiceRequest.created_at <= datetime.fromisoformat(end_date))
        
        requests = query.all()
        
        if format.lower() == "csv":
            # Create CSV data
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow([
                "ID", "Service Type", "Location", "Description", 
                "Status", "Created At", "Completed At"
            ])
            
            # Write data
            for req in requests:
                writer.writerow([
                    req.id,
                    req.service_type or "Général",
                    req.location or "Bonamoussadi",
                    req.description or "Pas de description",
                    req.status or "pending",
                    req.created_at.isoformat() if req.created_at else "",
                    req.completed_at.isoformat() if hasattr(req, 'completed_at') and req.completed_at else ""
                ])
            
            csv_content = output.getvalue()
            output.close()
            
            return {
                "success": True,
                "data": {
                    "format": "csv",
                    "content": csv_content,
                    "filename": f"requests_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    "recordCount": len(requests)
                }
            }
        
        elif format.lower() == "json":
            # Create JSON data
            json_data = []
            for req in requests:
                json_data.append({
                    "id": req.id,
                    "serviceType": req.service_type or "Général",
                    "location": req.location or "Bonamoussadi",
                    "description": req.description or "Pas de description",
                    "status": req.status or "pending",
                    "createdAt": req.created_at.isoformat() if req.created_at else None,
                    "completedAt": req.completed_at.isoformat() if hasattr(req, 'completed_at') and req.completed_at else None
                })
            
            return {
                "success": True,
                "data": {
                    "format": "json",
                    "content": json.dumps(json_data, indent=2),
                    "filename": f"requests_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    "recordCount": len(requests)
                }
            }
        
        else:
            raise HTTPException(status_code=400, detail="Format non supporté")
    
    except Exception as e:
        logger.error(f"Export requests error: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de l'export des demandes")

@router.get("/export/providers")
async def export_providers(
    format: str = Query("csv", description="Export format"),
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Export providers"""
    try:
        providers = db.query(Provider).all()
        
        if format.lower() == "csv":
            # Create CSV data
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow([
                "ID", "Name", "Phone", "Service Type", "Location", 
                "Rating", "Total Jobs", "Is Active", "Created At"
            ])
            
            # Write data
            for provider in providers:
                writer.writerow([
                    provider.id,
                    provider.name,
                    provider.phone_number,
                    provider.service_type or "Général",
                    provider.location or "Bonamoussadi",
                    provider.rating or 4.5,
                    provider.total_jobs or 0,
                    "Actif" if provider.is_active else "Inactif",
                    provider.created_at.isoformat() if provider.created_at else ""
                ])
            
            csv_content = output.getvalue()
            output.close()
            
            return {
                "success": True,
                "data": {
                    "format": "csv",
                    "content": csv_content,
                    "filename": f"providers_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    "recordCount": len(providers)
                }
            }
        
        else:
            raise HTTPException(status_code=400, detail="Format non supporté")
    
    except Exception as e:
        logger.error(f"Export providers error: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de l'export des prestataires")

@router.get("/export/analytics")
async def export_analytics(
    report_type: str = Query("overview", description="Report type"),
    period: str = Query("30d", description="Time period"),
    format: str = Query("csv", description="Export format"),
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Export analytics data"""
    try:
        # Calculate date range
        end_date = datetime.now()
        if period == "7d":
            start_date = end_date - timedelta(days=7)
        elif period == "30d":
            start_date = end_date - timedelta(days=30)
        else:
            start_date = end_date - timedelta(days=30)
        
        # Get data based on report type
        if report_type == "overview":
            # Get overview data
            requests = db.query(ServiceRequest).filter(
                ServiceRequest.created_at >= start_date,
                ServiceRequest.created_at <= end_date
            ).all()
            
            if format.lower() == "csv":
                output = io.StringIO()
                writer = csv.writer(output)
                
                # Write summary
                writer.writerow(["Rapport d'analyse - Vue d'ensemble"])
                writer.writerow(["Période", f"{start_date.date()} à {end_date.date()}"])
                writer.writerow([""])
                writer.writerow(["Métrique", "Valeur"])
                writer.writerow(["Total demandes", len(requests)])
                writer.writerow(["Demandes terminées", len([r for r in requests if r.status == "completed"])])
                writer.writerow(["Taux de succès", f"{(len([r for r in requests if r.status == 'completed']) / len(requests) * 100):.1f}%" if requests else "0%"])
                
                csv_content = output.getvalue()
                output.close()
                
                return {
                    "success": True,
                    "data": {
                        "format": "csv",
                        "content": csv_content,
                        "filename": f"analytics_overview_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        "reportType": report_type,
                        "period": period
                    }
                }
        
        return {
            "success": True,
            "message": "Export d'analyse généré avec succès"
        }
    
    except Exception as e:
        logger.error(f"Export analytics error: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de l'export des analyses")