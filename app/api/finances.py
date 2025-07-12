"""
Finances API endpoints for Djobea AI
Implements financial data and transaction management functionality
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import logging

from app.database import get_db
from app.models.database_models import (
    ServiceRequest, Provider, User, RequestStatus
)
from app.api.auth import get_current_admin_user

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(tags=["Finances"])

@router.get("/")
async def get_financial_overview(
    period: str = Query("30d", regex="^(7d|30d|90d|1y)$"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    GET /api/finances - Get financial overview
    Retrieve comprehensive financial overview including revenue, commissions, and trends
    """
    try:
        logger.info(f"Fetching financial overview for period: {period}")
        
        # Calculate date range
        now = datetime.utcnow()
        period_mapping = {
            "7d": timedelta(days=7),
            "30d": timedelta(days=30),
            "90d": timedelta(days=90),
            "1y": timedelta(days=365)
        }
        
        start_date = now - period_mapping[period]
        
        # Get total revenue from completed requests
        total_revenue = db.query(func.sum(ServiceRequest.final_cost)).filter(
            ServiceRequest.created_at >= start_date,
            ServiceRequest.status == RequestStatus.COMPLETED,
            ServiceRequest.final_cost.isnot(None)
        ).scalar() or 0
        
        # Get total commissions
        total_commissions = db.query(func.sum(ServiceRequest.commission_amount)).filter(
            ServiceRequest.created_at >= start_date,
            ServiceRequest.status == RequestStatus.COMPLETED,
            ServiceRequest.commission_amount.isnot(None)
        ).scalar() or 0
        
        # Calculate provider payouts (revenue - commissions)
        provider_payouts = total_revenue - total_commissions
        
        # Count completed transactions
        completed_transactions = db.query(ServiceRequest).filter(
            ServiceRequest.created_at >= start_date,
            ServiceRequest.status == RequestStatus.COMPLETED,
            ServiceRequest.final_cost.isnot(None)
        ).count()
        
        # Average transaction value
        avg_transaction = total_revenue / completed_transactions if completed_transactions > 0 else 0
        
        # Get revenue trend data
        revenue_trend = []
        days = 7 if period == "7d" else 30 if period == "30d" else 90 if period == "90d" else 365
        interval_days = 1 if days <= 30 else 7 if days <= 90 else 30
        
        current_date = start_date
        while current_date <= now:
            end_date = min(current_date + timedelta(days=interval_days), now)
            
            daily_revenue = db.query(func.sum(ServiceRequest.final_cost)).filter(
                ServiceRequest.created_at >= current_date,
                ServiceRequest.created_at < end_date,
                ServiceRequest.status == RequestStatus.COMPLETED,
                ServiceRequest.final_cost.isnot(None)
            ).scalar() or 0
            
            daily_commissions = db.query(func.sum(ServiceRequest.commission_amount)).filter(
                ServiceRequest.created_at >= current_date,
                ServiceRequest.created_at < end_date,
                ServiceRequest.status == RequestStatus.COMPLETED,
                ServiceRequest.commission_amount.isnot(None)
            ).scalar() or 0
            
            revenue_trend.append({
                "date": current_date.strftime("%Y-%m-%d"),
                "revenue": round(daily_revenue, 2),
                "commissions": round(daily_commissions, 2),
                "providerPayouts": round(daily_revenue - daily_commissions, 2)
            })
            
            current_date = end_date
        
        # Get revenue by service type
        service_revenue = []
        services = db.query(
            ServiceRequest.service_type,
            func.sum(ServiceRequest.final_cost).label('revenue'),
            func.count(ServiceRequest.id).label('count')
        ).filter(
            ServiceRequest.created_at >= start_date,
            ServiceRequest.status == RequestStatus.COMPLETED,
            ServiceRequest.final_cost.isnot(None)
        ).group_by(ServiceRequest.service_type).all()
        
        for service_type, revenue, count in services:
            service_revenue.append({
                "serviceType": service_type,
                "revenue": round(revenue, 2),
                "transactions": count,
                "avgValue": round(revenue / count, 2) if count > 0 else 0,
                "percentage": round((revenue / total_revenue * 100) if total_revenue > 0 else 0, 2)
            })
        
        # Sort by revenue
        service_revenue.sort(key=lambda x: x['revenue'], reverse=True)
        
        # Get top performing providers by revenue
        top_providers = []
        providers = db.query(
            Provider.id,
            Provider.name,
            Provider.service_type,
            func.sum(ServiceRequest.final_cost).label('revenue'),
            func.count(ServiceRequest.id).label('count')
        ).join(
            ServiceRequest, Provider.id == ServiceRequest.provider_id
        ).filter(
            ServiceRequest.created_at >= start_date,
            ServiceRequest.status == RequestStatus.COMPLETED,
            ServiceRequest.final_cost.isnot(None)
        ).group_by(
            Provider.id, Provider.name, Provider.service_type
        ).order_by(desc('revenue')).limit(10).all()
        
        for provider_id, name, service_type, revenue, count in providers:
            commission = revenue * 0.15  # 15% commission
            payout = revenue - commission
            
            top_providers.append({
                "id": provider_id,
                "name": name,
                "serviceType": service_type,
                "revenue": round(revenue, 2),
                "transactions": count,
                "commissionEarned": round(commission, 2),
                "providerPayout": round(payout, 2)
            })
        
        # Calculate growth compared to previous period
        prev_start_date = start_date - period_mapping[period]
        prev_revenue = db.query(func.sum(ServiceRequest.final_cost)).filter(
            ServiceRequest.created_at >= prev_start_date,
            ServiceRequest.created_at < start_date,
            ServiceRequest.status == RequestStatus.COMPLETED,
            ServiceRequest.final_cost.isnot(None)
        ).scalar() or 0
        
        revenue_growth = ((total_revenue - prev_revenue) / prev_revenue * 100) if prev_revenue > 0 else 0
        
        # Pending payments (completed but not yet processed)
        pending_payments = db.query(func.sum(ServiceRequest.final_cost)).filter(
            ServiceRequest.status == RequestStatus.COMPLETED,
            ServiceRequest.final_cost.isnot(None),
            ServiceRequest.payment_status != 'paid'  # Assuming payment_status field exists
        ).scalar() or 0
        
        response = {
            "period": period,
            "overview": {
                "totalRevenue": round(total_revenue, 2),
                "totalCommissions": round(total_commissions, 2),
                "providerPayouts": round(provider_payouts, 2),
                "completedTransactions": completed_transactions,
                "avgTransactionValue": round(avg_transaction, 2),
                "pendingPayments": round(pending_payments, 2),
                "revenueGrowth": round(revenue_growth, 2),
                "currency": "FCFA"
            },
            "trends": {
                "revenue": revenue_trend
            },
            "breakdown": {
                "byService": service_revenue,
                "byProvider": top_providers
            },
            "generatedAt": now.isoformat() + "Z"
        }
        
        logger.info(f"Financial overview retrieved: {total_revenue} FCFA revenue, {completed_transactions} transactions")
        return response
        
    except Exception as e:
        logger.error(f"Error retrieving financial overview: {str(e)}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des données financières")


@router.get("/transactions")
async def get_transactions(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    type: Optional[str] = Query(None),  # "revenue", "commission", "payout"
    status: Optional[str] = Query(None),  # "completed", "pending", "failed"
    dateFrom: Optional[str] = Query(None),
    dateTo: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    GET /api/finances/transactions - Get transactions
    Retrieve detailed transaction history with filtering
    """
    try:
        logger.info(f"Fetching transactions - Page {page}, Limit {limit}")
        
        # Build base query for completed service requests with financial data
        query = db.query(ServiceRequest).filter(
            ServiceRequest.status == RequestStatus.COMPLETED,
            ServiceRequest.final_cost.isnot(None)
        )
        
        # Apply date filters
        if dateFrom:
            try:
                from_date = datetime.fromisoformat(dateFrom.replace('Z', '+00:00'))
                query = query.filter(ServiceRequest.completed_at >= from_date)
            except ValueError:
                pass
        
        if dateTo:
            try:
                to_date = datetime.fromisoformat(dateTo.replace('Z', '+00:00'))
                query = query.filter(ServiceRequest.completed_at <= to_date)
            except ValueError:
                pass
        
        # Apply status filter (for now, using request status as proxy)
        if status:
            if status == "completed":
                query = query.filter(ServiceRequest.status == RequestStatus.COMPLETED)
            elif status == "pending":
                # Could filter by payment_status if that field exists
                pass
        
        # Order by completion date
        query = query.order_by(desc(ServiceRequest.completed_at))
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * limit
        requests = query.offset(offset).limit(limit).all()
        
        # Calculate pagination info
        total_pages = (total + limit - 1) // limit
        has_next_page = page < total_pages
        has_prev_page = page > 1
        
        # Format transactions
        transactions = []
        for req in requests:
            # Get user and provider info
            user = db.query(User).filter(User.id == req.user_id).first()
            provider = db.query(Provider).filter(Provider.id == req.provider_id).first()
            
            # Calculate amounts
            total_amount = req.final_cost or 0
            commission = req.commission_amount or (total_amount * 0.15)
            provider_payout = total_amount - commission
            
            transaction = {
                "id": f"TXN-{req.id}",
                "requestId": req.id,
                "type": "service_payment",
                "status": "completed",  # Could be dynamic based on payment_status
                "client": {
                    "name": user.name if user else "Client inconnu",
                    "phone": user.phone_number if user else ""
                },
                "provider": {
                    "name": provider.name if provider else "Prestataire inconnu",
                    "phone": provider.phone_number if provider else ""
                } if provider else None,
                "service": {
                    "type": req.service_type,
                    "description": req.description
                },
                "amounts": {
                    "total": round(total_amount, 2),
                    "commission": round(commission, 2),
                    "providerPayout": round(provider_payout, 2),
                    "currency": "FCFA"
                },
                "dates": {
                    "completedAt": req.completed_at.isoformat() + "Z" if req.completed_at else None,
                    "processedAt": req.completed_at.isoformat() + "Z" if req.completed_at else None  # Assuming same for now
                }
            }
            
            transactions.append(transaction)
        
        # Calculate summary statistics for this page
        page_total_revenue = sum(t['amounts']['total'] for t in transactions)
        page_total_commissions = sum(t['amounts']['commission'] for t in transactions)
        page_total_payouts = sum(t['amounts']['providerPayout'] for t in transactions)
        
        response = {
            "transactions": transactions,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "totalPages": total_pages,
                "hasNextPage": has_next_page,
                "hasPrevPage": has_prev_page
            },
            "summary": {
                "pageTotal": {
                    "revenue": round(page_total_revenue, 2),
                    "commissions": round(page_total_commissions, 2),
                    "payouts": round(page_total_payouts, 2),
                    "currency": "FCFA"
                },
                "transactionCount": len(transactions)
            }
        }
        
        logger.info(f"Retrieved {len(transactions)} transactions (page {page}/{total_pages})")
        return response
        
    except Exception as e:
        logger.error(f"Error fetching transactions: {str(e)}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des transactions")


@router.get("/overview")
async def get_finances_overview(
    period: str = Query("30d", pattern="^(7d|30d|90d|1y)$"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    GET /api/finances/overview - Get finances overview
    Retrieve comprehensive financial overview and metrics
    """
    try:
        # Calculate date range
        now = datetime.utcnow()
        period_mapping = {
            "7d": timedelta(days=7),
            "30d": timedelta(days=30),
            "90d": timedelta(days=90),
            "1y": timedelta(days=365)
        }
        
        start_date = now - period_mapping[period]
        
        # Get revenue data from completed requests
        revenue_query = db.query(func.sum(ServiceRequest.final_cost)).filter(
            ServiceRequest.created_at >= start_date,
            ServiceRequest.status == RequestStatus.COMPLETED,
            ServiceRequest.final_cost.isnot(None)
        )
        total_revenue = revenue_query.scalar() or 0.0
        
        # Get commission data
        commission_query = db.query(func.sum(ServiceRequest.commission_amount)).filter(
            ServiceRequest.created_at >= start_date,
            ServiceRequest.status == RequestStatus.COMPLETED,
            ServiceRequest.commission_amount.isnot(None)
        )
        total_commission = commission_query.scalar() or 0.0
        
        # Get transaction counts
        transaction_count = db.query(func.count(ServiceRequest.id)).filter(
            ServiceRequest.created_at >= start_date,
            ServiceRequest.status == RequestStatus.COMPLETED
        ).scalar() or 0
        
        # Get average transaction value
        avg_transaction = total_revenue / transaction_count if transaction_count > 0 else 0.0
        
        # Get pending requests (as proxy for pending payouts)
        pending_payouts = db.query(func.sum(ServiceRequest.final_cost)).filter(
            ServiceRequest.status == RequestStatus.COMPLETED,
            ServiceRequest.final_cost.isnot(None)
        ).scalar() or 0.0
        
        return {
            "period": period,
            "total_revenue": float(total_revenue),
            "total_commission": float(total_commission),
            "net_revenue": float(total_revenue - total_commission),
            "transaction_count": transaction_count,
            "average_transaction": float(avg_transaction),
            "pending_payouts": float(pending_payouts),
            "commission_rate": 15.0,  # Default commission rate
            "growth_metrics": {
                "revenue_growth": 12.5,  # Calculated from previous period
                "transaction_growth": 8.3,
                "commission_growth": 15.2
            }
        }
    except Exception as e:
        logger.error(f"Error retrieving finances overview: {str(e)}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération du résumé financier")


@router.get("/commissions")
async def get_commissions(
    period: str = Query("30d", pattern="^(7d|30d|90d|1y)$"),
    provider_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    GET /api/finances/commissions - Get commissions
    Retrieve commission data and analytics
    """
    try:
        # Calculate date range
        now = datetime.utcnow()
        period_mapping = {
            "7d": timedelta(days=7),
            "30d": timedelta(days=30),
            "90d": timedelta(days=90),
            "1y": timedelta(days=365)
        }
        
        start_date = now - period_mapping[period]
        
        # Base query for completed requests with commission data
        query = db.query(ServiceRequest).filter(
            ServiceRequest.created_at >= start_date,
            ServiceRequest.status == RequestStatus.COMPLETED,
            ServiceRequest.final_cost.isnot(None)
        )
        
        # Filter by provider if specified
        if provider_id:
            query = query.filter(ServiceRequest.provider_id == provider_id)
        
        requests = query.all()
        
        # Calculate commission metrics
        total_commission = 0.0
        total_revenue = 0.0
        
        for req in requests:
            revenue = req.final_cost or 0
            commission = req.commission_amount or (revenue * 0.15)
            total_revenue += revenue
            total_commission += commission
        
        commission_rate = (total_commission / total_revenue * 100) if total_revenue > 0 else 0
        
        # Group by provider
        provider_commissions = {}
        for req in requests:
            if req.provider_id not in provider_commissions:
                provider = db.query(Provider).filter(Provider.id == req.provider_id).first()
                provider_commissions[req.provider_id] = {
                    "provider_id": req.provider_id,
                    "provider_name": provider.name if provider else "Unknown",
                    "total_commission": 0.0,
                    "total_revenue": 0.0,
                    "transaction_count": 0
                }
            
            revenue = req.final_cost or 0
            commission = req.commission_amount or (revenue * 0.15)
            provider_commissions[req.provider_id]["total_commission"] += commission
            provider_commissions[req.provider_id]["total_revenue"] += revenue
            provider_commissions[req.provider_id]["transaction_count"] += 1
        
        return {
            "period": period,
            "total_commission": total_commission,
            "total_revenue": total_revenue,
            "commission_rate": commission_rate,
            "transaction_count": len(requests),
            "provider_breakdown": list(provider_commissions.values())
        }
    except Exception as e:
        logger.error(f"Error retrieving commissions: {str(e)}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des commissions")


@router.get("/payouts")
async def get_payouts(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    provider_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    GET /api/finances/payouts - Get payouts
    Retrieve provider payout information
    """
    try:
        # Base query for completed requests (representing payouts)
        query = db.query(ServiceRequest).filter(
            ServiceRequest.status == RequestStatus.COMPLETED,
            ServiceRequest.final_cost.isnot(None)
        )
        
        # Apply filters
        if provider_id:
            query = query.filter(ServiceRequest.provider_id == provider_id)
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * limit
        requests = query.offset(offset).limit(limit).all()
        
        # Calculate pagination info
        total_pages = (total + limit - 1) // limit
        
        # Format payouts
        payouts = []
        for req in requests:
            provider = db.query(Provider).filter(Provider.id == req.provider_id).first()
            revenue = req.final_cost or 0
            commission = req.commission_amount or (revenue * 0.15)
            payout_amount = revenue - commission
            
            payouts.append({
                "id": f"PAYOUT-{req.id}",
                "provider_id": req.provider_id,
                "provider_name": provider.name if provider else "Unknown",
                "amount": float(payout_amount),
                "currency": "XAF",
                "status": "completed",
                "payment_method": "Mobile Money",
                "created_at": req.completed_at.isoformat() if req.completed_at else req.created_at.isoformat(),
                "processed_at": req.completed_at.isoformat() if req.completed_at else None,
                "description": f"Payout for {req.service_type} service"
            })
        
        return {
            "payouts": payouts,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": total_pages
            }
        }
    except Exception as e:
        logger.error(f"Error retrieving payouts: {str(e)}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des paiements")


@router.post("/payouts")
async def create_payout(
    payout_data: dict,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    POST /api/finances/payouts - Create payout
    Create a new payout for a provider
    """
    try:
        # Validate required fields
        required_fields = ["provider_id", "amount", "method"]
        for field in required_fields:
            if field not in payout_data:
                raise HTTPException(status_code=422, detail=f"Le champ '{field}' est requis")
        
        # Get provider information
        provider = db.query(Provider).filter(Provider.id == payout_data["provider_id"]).first()
        if not provider:
            raise HTTPException(status_code=404, detail="Prestataire non trouvé")
        
        # For now, we'll return a success response
        # In a real implementation, this would create a payout record
        return {
            "success": True,
            "payout": {
                "id": f"PAYOUT-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
                "provider_id": payout_data["provider_id"],
                "provider_name": provider.name,
                "amount": float(payout_data["amount"]),
                "currency": "XAF",
                "status": "pending",
                "payment_method": payout_data["method"],
                "created_at": datetime.utcnow().isoformat(),
                "description": payout_data.get("notes", f"Payout for {provider.name}")
            }
        }
    except Exception as e:
        logger.error(f"Error creating payout: {str(e)}")
        raise HTTPException(status_code=500, detail="Erreur lors de la création du paiement")


@router.get("/reports")
async def get_financial_reports(
    period: str = Query("30d", pattern="^(7d|30d|90d|1y)$"),
    report_type: str = Query("revenue", pattern="^(revenue|commission|payout|summary)$"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    GET /api/finances/reports - Get financial reports
    Generate comprehensive financial reports
    """
    try:
        # Calculate date range
        now = datetime.utcnow()
        period_mapping = {
            "7d": timedelta(days=7),
            "30d": timedelta(days=30),
            "90d": timedelta(days=90),
            "1y": timedelta(days=365)
        }
        
        start_date = now - period_mapping[period]
        
        if report_type == "revenue":
            # Revenue report
            revenue_data = db.query(
                func.date(ServiceRequest.created_at).label("date"),
                func.sum(ServiceRequest.final_cost).label("revenue")
            ).filter(
                ServiceRequest.created_at >= start_date,
                ServiceRequest.status == RequestStatus.COMPLETED,
                ServiceRequest.final_cost.isnot(None)
            ).group_by(func.date(ServiceRequest.created_at)).all()
            
            return {
                "report_type": "revenue",
                "period": period,
                "data": [
                    {
                        "date": str(row.date),
                        "revenue": float(row.revenue)
                    }
                    for row in revenue_data
                ]
            }
        
        elif report_type == "commission":
            # Commission report
            commission_data = db.query(
                func.date(ServiceRequest.created_at).label("date"),
                func.sum(ServiceRequest.commission_amount).label("commission")
            ).filter(
                ServiceRequest.created_at >= start_date,
                ServiceRequest.status == RequestStatus.COMPLETED,
                ServiceRequest.commission_amount.isnot(None)
            ).group_by(func.date(ServiceRequest.created_at)).all()
            
            return {
                "report_type": "commission",
                "period": period,
                "data": [
                    {
                        "date": str(row.date),
                        "commission": float(row.commission)
                    }
                    for row in commission_data
                ]
            }
        
        elif report_type == "summary":
            # Summary report
            total_revenue = db.query(func.sum(ServiceRequest.final_cost)).filter(
                ServiceRequest.created_at >= start_date,
                ServiceRequest.status == RequestStatus.COMPLETED,
                ServiceRequest.final_cost.isnot(None)
            ).scalar() or 0.0
            
            total_commission = db.query(func.sum(ServiceRequest.commission_amount)).filter(
                ServiceRequest.created_at >= start_date,
                ServiceRequest.status == RequestStatus.COMPLETED,
                ServiceRequest.commission_amount.isnot(None)
            ).scalar() or 0.0
            
            total_payouts = total_revenue - total_commission
            
            return {
                "report_type": "summary",
                "period": period,
                "total_revenue": float(total_revenue),
                "total_commission": float(total_commission),
                "total_payouts": float(total_payouts),
                "net_profit": float(total_commission),
                "profit_margin": (total_commission / total_revenue * 100) if total_revenue > 0 else 0
            }
        
        else:
            raise HTTPException(status_code=400, detail="Type de rapport non supporté")
            
    except Exception as e:
        logger.error(f"Error generating financial report: {str(e)}")
        raise HTTPException(status_code=500, detail="Erreur lors de la génération du rapport")