"""
Monitoring API endpoints for real-time system health
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any

from app.database import get_db
from app.services.proactive_monitoring_service import ProactiveMonitoringService
from app.utils.logger import setup_logger

logger = setup_logger(__name__)
router = APIRouter()

@router.get("/health", response_model=Dict[str, Any])
async def get_system_health(db: Session = Depends(get_db)):
    """Get system health status"""
    try:
        monitoring_service = ProactiveMonitoringService(db)
        health_status = await monitoring_service.get_system_health_status()
        return health_status
    except Exception as e:
        logger.error(f"Error getting system health: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/errors", response_model=Dict[str, Any])
async def get_error_analysis(db: Session = Depends(get_db)):
    """Get detailed error analysis"""
    try:
        monitoring_service = ProactiveMonitoringService(db)
        error_analysis = await monitoring_service.get_detailed_error_analysis()
        return error_analysis
    except Exception as e:
        logger.error(f"Error getting error analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/proactive-updates", response_model=Dict[str, Any])
async def get_proactive_update_status(db: Session = Depends(get_db)):
    """Get proactive update system status"""
    try:
        monitoring_service = ProactiveMonitoringService(db)
        proactive_status = await monitoring_service.get_proactive_update_status()
        return proactive_status
    except Exception as e:
        logger.error(f"Error getting proactive update status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/report", response_model=Dict[str, Any])
async def get_monitoring_report(db: Session = Depends(get_db)):
    """Get comprehensive monitoring report"""
    try:
        monitoring_service = ProactiveMonitoringService(db)
        report = await monitoring_service.generate_monitoring_report()
        return report
    except Exception as e:
        logger.error(f"Error generating monitoring report: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/communication-status", response_model=Dict[str, Any])
async def get_communication_status(db: Session = Depends(get_db)):
    """Get communication system status"""
    try:
        from app.services.communication_fallback_service import CommunicationFallbackService
        fallback_service = CommunicationFallbackService(db)
        status = fallback_service.get_communication_health_status()
        return status
    except Exception as e:
        logger.error(f"Error getting communication status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/retry-failed-messages", response_model=Dict[str, Any])
async def retry_failed_messages(db: Session = Depends(get_db)):
    """Manually trigger retry of failed messages"""
    try:
        from app.services.communication_fallback_service import CommunicationFallbackService
        fallback_service = CommunicationFallbackService(db)
        retry_stats = await fallback_service.check_and_retry_failed_messages()
        return retry_stats
    except Exception as e:
        logger.error(f"Error retrying failed messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dashboard", response_model=Dict[str, Any])
async def get_monitoring_dashboard(db: Session = Depends(get_db)):
    """Get monitoring dashboard data"""
    try:
        monitoring_service = ProactiveMonitoringService(db)
        
        # Get all monitoring data for dashboard
        health_status = await monitoring_service.get_system_health_status()
        error_analysis = await monitoring_service.get_detailed_error_analysis()
        proactive_status = await monitoring_service.get_proactive_update_status()
        
        # Get communication status
        from app.services.communication_fallback_service import CommunicationFallbackService
        fallback_service = CommunicationFallbackService(db)
        comm_status = fallback_service.get_communication_health_status()
        
        return {
            "dashboard_data": {
                "health": health_status,
                "errors": error_analysis,
                "proactive_updates": proactive_status,
                "communication": comm_status
            },
            "alerts": {
                "critical_alerts": [
                    alert for alert in health_status.get('recommendations', [])
                    if '🚨' in alert or 'URGENT' in alert
                ],
                "warning_alerts": [
                    alert for alert in health_status.get('recommendations', [])
                    if '⚠️' in alert or 'WARNING' in alert
                ]
            },
            "quick_stats": {
                "overall_health": health_status.get('health_status', 'unknown'),
                "success_rate": health_status.get('success_rate', 0),
                "active_requests": health_status.get('active_requests', 0),
                "failed_notifications": health_status.get('failed_notifications_1h', 0),
                "pending_retries": health_status.get('pending_retries', 0)
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting monitoring dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))