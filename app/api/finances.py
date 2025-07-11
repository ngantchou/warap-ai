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
router = APIRouter(prefix="/finances", tags=["Finances"])

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