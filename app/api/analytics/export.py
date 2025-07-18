"""
Export Analytics Data API for Djobea AI
Handles exporting analytics data in various formats
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
import uuid
import json
import os
from pathlib import Path

from app.database import get_db
from app.models.database_models import ServiceRequest, Provider, User
from app.services.auth_service import AuthService
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
# Remove internal imports since we'll create simplified data collection

router = APIRouter()

# Authentication setup
security = HTTPBearer()
auth_service = AuthService()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Get current authenticated user"""
    token = credentials.credentials
    user = auth_service.get_current_user(token, db)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    return user

# Request Models
class ExportFilters(BaseModel):
    regions: Optional[List[str]] = Field(default=None, description="List of regions to filter by")
    services: Optional[List[str]] = Field(default=None, description="List of services to filter by")
    providers: Optional[List[str]] = Field(default=None, description="List of provider IDs to filter by")
    status: Optional[List[str]] = Field(default=None, description="List of request statuses to filter by")

class ExportRequest(BaseModel):
    format: str = Field(..., description="Export format (xlsx, csv, json, pdf)")
    data: List[str] = Field(..., description="Data types to include (kpis, performance, services, geographic, insights, leaderboard)")
    period: str = Field(default="30d", description="Time period for data (7d, 30d, 90d, 1y)")
    filters: Optional[ExportFilters] = Field(default=None, description="Additional filters")
    includeCharts: bool = Field(default=True, description="Whether to include charts in export")
    email: Optional[str] = Field(default=None, description="Email to send export to")

# Response Models
class ExportResponse(BaseModel):
    exportId: str
    downloadUrl: str
    filename: str
    fileSize: int
    expiresAt: str
    format: str
    status: str

class ExportAPIResponse(BaseModel):
    success: bool
    data: ExportResponse
    message: str

# Helper Functions
def _get_date_range(period: str) -> tuple[datetime, datetime]:
    """Get start and end dates for the given period"""
    end_date = datetime.now()
    
    if period == "7d":
        start_date = end_date - timedelta(days=7)
    elif period == "30d":
        start_date = end_date - timedelta(days=30)
    elif period == "90d":
        start_date = end_date - timedelta(days=90)
    elif period == "1y":
        start_date = end_date - timedelta(days=365)
    else:
        start_date = end_date - timedelta(days=30)
    
    return start_date, end_date

async def _collect_export_data(
    db: Session,
    data_types: List[str],
    period: str,
    filters: Optional[ExportFilters] = None
) -> Dict[str, Any]:
    """Collect all requested data for export"""
    
    start_date, end_date = _get_date_range(period)
    export_data = {}
    
    # Base query
    base_query = db.query(ServiceRequest).filter(
        ServiceRequest.created_at >= start_date,
        ServiceRequest.created_at <= end_date
    )
    
    # Apply filters if provided
    if filters:
        if filters.regions:
            base_query = base_query.filter(ServiceRequest.location.in_(filters.regions))
        if filters.services:
            base_query = base_query.filter(ServiceRequest.service_type.in_(filters.services))
        if filters.status:
            base_query = base_query.filter(ServiceRequest.status.in_(filters.status))
    
    # Collect requested data types
    if "kpis" in data_types:
        total_requests = base_query.count()
        completed_requests = base_query.filter(ServiceRequest.status == "completed").count()
        pending_requests = base_query.filter(ServiceRequest.status == "pending").count()
        success_rate = (completed_requests / total_requests * 100) if total_requests > 0 else 0
        
        export_data["kpis"] = {
            "totalRequests": total_requests,
            "completedRequests": completed_requests,
            "pendingRequests": pending_requests,
            "successRate": success_rate,
            "revenue": completed_requests * 15000  # Mock revenue
        }
    
    if "performance" in data_types:
        export_data["performance"] = {
            "avgResponseTime": 4.2,  # Mock data
            "completionRate": 85.5,
            "customerSatisfaction": 4.3
        }
    
    if "services" in data_types:
        services_data = []
        service_types = db.query(ServiceRequest.service_type).distinct().all()
        for service_type in service_types:
            count = base_query.filter(ServiceRequest.service_type == service_type[0]).count()
            services_data.append({
                "service": service_type[0],
                "count": count,
                "revenue": count * 15000
            })
        export_data["services"] = services_data
    
    if "geographic" in data_types:
        geographic_data = []
        locations = db.query(ServiceRequest.location).distinct().all()
        for location in locations:
            count = base_query.filter(ServiceRequest.location == location[0]).count()
            geographic_data.append({
                "location": location[0],
                "count": count,
                "revenue": count * 15000
            })
        export_data["geographic"] = geographic_data
    
    if "insights" in data_types:
        export_data["insights"] = {
            "trends": "Augmentation de 15% des demandes ce mois",
            "recommendations": "Augmenter le nombre de prestataires en plomberie",
            "forecast": "Croissance prévue de 20% le mois prochain"
        }
    
    if "leaderboard" in data_types:
        providers = db.query(Provider).limit(10).all()
        leaderboard_data = []
        for provider in providers:
            leaderboard_data.append({
                "name": provider.name,
                "rating": 4.5,
                "missions": 10,
                "revenue": 150000
            })
        export_data["leaderboard"] = leaderboard_data
    
    return export_data

async def _create_export_file(
    export_data: Dict[str, Any],
    format: str,
    export_id: str,
    include_charts: bool = True
) -> tuple[str, int]:
    """Create export file in the specified format"""
    
    # Create exports directory if it doesn't exist
    exports_dir = Path("exports")
    exports_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"analytics_export_{timestamp}.{format}"
    filepath = exports_dir / filename
    
    if format == "json":
        # Export as JSON
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2, default=str)
    
    elif format == "csv":
        # Export as CSV (simplified - only KPIs for now)
        import csv
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Write headers
            writer.writerow(["Data Type", "Metric", "Value", "Period"])
            
            # Write KPIs data
            if "kpis" in export_data:
                kpis = export_data["kpis"]
                for key, value in kpis.items():
                    if isinstance(value, (int, float)):
                        writer.writerow(["KPI", key, value, "Current Period"])
    
    elif format == "xlsx":
        # Export as Excel (mock implementation)
        # In production, would use openpyxl or similar
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("Excel export not fully implemented in this demo\n")
            f.write(f"Export Data: {json.dumps(export_data, default=str)}")
    
    elif format == "pdf":
        # Export as PDF (mock implementation)
        # In production, would use reportlab or similar
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("PDF export not fully implemented in this demo\n")
            f.write(f"Export Data: {json.dumps(export_data, default=str)}")
    
    else:
        raise ValueError(f"Unsupported export format: {format}")
    
    # Get file size
    file_size = filepath.stat().st_size
    
    return filename, file_size

async def _send_export_email(email: str, download_url: str, filename: str):
    """Send export email to user (mock implementation)"""
    # In production, would integrate with email service
    print(f"Sending export email to {email}")
    print(f"Download URL: {download_url}")
    print(f"Filename: {filename}")

# Background task for processing exports
async def process_export_background(
    export_id: str,
    db: Session,
    request: ExportRequest,
    user_email: str
):
    """Background task to process export"""
    try:
        # Collect data
        export_data = await _collect_export_data(
            db, request.data, request.period, request.filters
        )
        
        # Create file
        filename, file_size = await _create_export_file(
            export_data, request.format, export_id, request.includeCharts
        )
        
        # Send email if requested
        if request.email:
            download_url = f"https://api.djobea.ai/exports/{filename}"
            await _send_export_email(request.email, download_url, filename)
        
        print(f"Export {export_id} completed successfully")
        
    except Exception as e:
        print(f"Export {export_id} failed: {str(e)}")

@router.post("/export", response_model=ExportAPIResponse)
async def export_analytics_data(
    request: ExportRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Export analytics data in various formats"""
    
    try:
        # Generate export ID
        export_id = f"export_{uuid.uuid4().hex[:8]}"
        
        # Validate format
        supported_formats = ["xlsx", "csv", "json", "pdf"]
        if request.format not in supported_formats:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported format. Supported formats: {', '.join(supported_formats)}"
            )
        
        # Validate data types
        supported_data_types = ["kpis", "performance", "services", "geographic", "insights", "leaderboard"]
        invalid_types = [dt for dt in request.data if dt not in supported_data_types]
        if invalid_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid data types: {', '.join(invalid_types)}"
            )
        
        # For demo purposes, create export immediately
        # In production, would use background tasks for large exports
        export_data = await _collect_export_data(
            db, request.data, request.period, request.filters
        )
        
        filename, file_size = await _create_export_file(
            export_data, request.format, export_id, request.includeCharts
        )
        
        # Calculate expiration (7 days from now)
        expires_at = datetime.now() + timedelta(days=7)
        
        # Create download URL
        download_url = f"https://api.djobea.ai/exports/{filename}"
        
        # Send email if requested
        if request.email:
            await _send_export_email(request.email, download_url, filename)
        
        return ExportAPIResponse(
            success=True,
            data=ExportResponse(
                exportId=export_id,
                downloadUrl=download_url,
                filename=filename,
                fileSize=file_size,
                expiresAt=expires_at.isoformat() + "Z",
                format=request.format,
                status="completed"
            ),
            message="Export completed successfully"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error creating export: {str(e)}"
        )

@router.get("/export/{export_id}/status")
async def get_export_status(
    export_id: str,
    current_user = Depends(get_current_user)
):
    """Get export status by ID"""
    
    # Mock implementation - in production would track export status in database
    return {
        "success": True,
        "data": {
            "exportId": export_id,
            "status": "completed",
            "progress": 100,
            "createdAt": datetime.now().isoformat() + "Z",
            "completedAt": datetime.now().isoformat() + "Z"
        },
        "message": "Export status retrieved successfully"
    }

@router.delete("/export/{export_id}")
async def cancel_export(
    export_id: str,
    current_user = Depends(get_current_user)
):
    """Cancel or delete an export"""
    
    try:
        # Mock implementation - in production would cancel background task
        # and delete export file
        
        return {
            "success": True,
            "data": {
                "exportId": export_id,
                "status": "cancelled"
            },
            "message": "Export cancelled successfully"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error cancelling export: {str(e)}"
        )