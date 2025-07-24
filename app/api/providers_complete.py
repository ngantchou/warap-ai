"""
Complete Provider API implementation for Djobea AI
Following the OpenAPI specification exactly
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from loguru import logger
import io
import csv
import json
from datetime import datetime

from app.database import get_db
from app.models.provider_models import (
    Provider, CreateProviderRequest, UpdateProviderRequest, UpdateProviderStatusRequest,
    ContactProviderRequest, AvailableProvidersRequest, ProvidersFilters, ExportProvidersRequest,
    ProvidersResponse, ProviderResponse, SuccessResponse, ErrorResponse,
    Pagination, ProvidersStats, ProviderStatus, ProviderAvailability,
    SortBy, SortOrder, ContactMethod, ExportFormat
)
from app.services.provider_service import ProviderService
from app.services.auth_service import AuthService
from app.services.auth_service import auth_service
from app.models.auth_models import User
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

router = APIRouter(prefix="/api/providers", tags=["Providers"])
security = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user"""
    token = credentials.credentials
    try:
        user = auth_service.get_current_user(token, db)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user
    except HTTPException:
        # Re-raise HTTPException from auth_service
        raise
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")

def get_provider_service(db: Session = Depends(get_db)) -> ProviderService:
    """Get provider service instance"""
    return ProviderService(db)

@router.get("", response_model=ProvidersResponse)
async def get_providers(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, max_length=255, description="Search term"),
    status: Optional[ProviderStatus] = Query(None, description="Provider status filter"),
    specialty: Optional[str] = Query(None, description="Specialty filter"),
    zone: Optional[str] = Query(None, description="Zone filter"),
    minRating: Optional[float] = Query(None, ge=0, le=5, description="Minimum rating"),
    services: Optional[List[str]] = Query(None, description="Services filter"),
    availability: Optional[ProviderAvailability] = Query(None, description="Availability filter"),
    sortBy: Optional[SortBy] = Query(None, description="Sort by field"),
    sortOrder: Optional[SortOrder] = Query(SortOrder.ASC, description="Sort order"),
    current_user: User = Depends(get_current_user),
    provider_service: ProviderService = Depends(get_provider_service)
):
    """Get paginated list of providers with filtering and sorting"""
    try:
        # Create filters object
        filters = ProvidersFilters(
            page=page,
            limit=limit,
            search=search,
            status=status,
            specialty=specialty,
            zone=zone,
            minRating=minRating,
            services=services,
            availability=availability,
            sortBy=sortBy,
            sortOrder=sortOrder
        )
        
        # Get providers
        providers, pagination, stats = provider_service.get_providers(filters, page, limit)
        
        # Return response
        return ProvidersResponse(
            success=True,
            data={
                "providers": providers,
                "pagination": pagination,
                "stats": stats
            },
            message="Providers retrieved successfully"
        )
        
    except Exception as e:
        logger.error(f"Error getting providers: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("", response_model=ProviderResponse)
async def create_provider(
    request: CreateProviderRequest,
    current_user: User = Depends(get_current_user),
    provider_service: ProviderService = Depends(get_provider_service)
):
    """Create a new provider"""
    try:
        provider = provider_service.create_provider(request)
        return ProviderResponse(
            success=True,
            data=provider,
            message="Provider created successfully"
        )
    except Exception as e:
        logger.error(f"Error creating provider: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{id}", response_model=ProviderResponse)
async def get_provider(
    id: str,
    current_user: User = Depends(get_current_user),
    provider_service: ProviderService = Depends(get_provider_service)
):
    """Get a provider by ID"""
    try:
        provider = provider_service.get_provider_by_id(id)
        if not provider:
            raise HTTPException(status_code=404, detail="Provider not found")
        
        return ProviderResponse(
            success=True,
            data=provider,
            message="Provider retrieved successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting provider {id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{id}", response_model=ProviderResponse)
async def update_provider(
    id: str,
    request: UpdateProviderRequest,
    current_user: User = Depends(get_current_user),
    provider_service: ProviderService = Depends(get_provider_service)
):
    """Update a provider"""
    try:
        provider = provider_service.update_provider(id, request)
        if not provider:
            raise HTTPException(status_code=404, detail="Provider not found")
        
        return ProviderResponse(
            success=True,
            data=provider,
            message="Provider updated successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating provider {id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{id}", response_model=SuccessResponse)
async def delete_provider(
    id: str,
    current_user: User = Depends(get_current_user),
    provider_service: ProviderService = Depends(get_provider_service)
):
    """Delete a provider"""
    try:
        success = provider_service.delete_provider(id)
        if not success:
            raise HTTPException(status_code=404, detail="Provider not found")
        
        return SuccessResponse(
            success=True,
            message="Provider deleted successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting provider {id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{id}/status", response_model=ProviderResponse)
async def update_provider_status(
    id: str,
    request: UpdateProviderStatusRequest,
    current_user: User = Depends(get_current_user),
    provider_service: ProviderService = Depends(get_provider_service)
):
    """Update provider status"""
    try:
        provider = provider_service.update_provider_status(id, request.status)
        if not provider:
            raise HTTPException(status_code=404, detail="Provider not found")
        
        return ProviderResponse(
            success=True,
            data=provider,
            message="Provider status updated successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating provider status {id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{id}/contact", response_model=SuccessResponse)
async def contact_provider(
    id: str,
    request: ContactProviderRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    provider_service: ProviderService = Depends(get_provider_service)
):
    """Contact a provider via call, WhatsApp, or email"""
    try:
        # Add contact task to background
        background_tasks.add_task(
            provider_service.contact_provider,
            id,
            request.method.value,
            request.message
        )
        
        return SuccessResponse(
            success=True,
            message="Provider contacted successfully"
        )
    except Exception as e:
        logger.error(f"Error contacting provider {id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/available")
async def get_available_providers(
    request: AvailableProvidersRequest = None,
    current_user: User = Depends(get_current_user),
    provider_service: ProviderService = Depends(get_provider_service)
):
    """Get available providers for a service request"""
    try:
        if request is None:
            request = AvailableProvidersRequest()
        
        providers = provider_service.get_available_providers(
            service_type=request.serviceType,
            location=request.location,
            urgency=request.urgency
        )
        
        return {
            "success": True,
            "data": providers
        }
    except Exception as e:
        logger.error(f"Error getting available providers: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/search")
async def search_providers(
    q: str = Query(..., min_length=1, max_length=255, description="Search query"),
    current_user: User = Depends(get_current_user),
    provider_service: ProviderService = Depends(get_provider_service)
):
    """Search providers by name, services, or other criteria"""
    try:
        providers = provider_service.search_providers(q)
        return {
            "success": True,
            "data": providers
        }
    except Exception as e:
        logger.error(f"Error searching providers: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/export")
async def export_providers(
    request: ExportProvidersRequest = None,
    current_user: User = Depends(get_current_user),
    provider_service: ProviderService = Depends(get_provider_service)
):
    """Export providers data in various formats"""
    try:
        if request is None:
            request = ExportProvidersRequest()
        
        # Get providers based on filters
        if request.filters:
            providers, _, _ = provider_service.get_providers(
                request.filters,
                request.filters.page or 1,
                request.filters.limit or 100
            )
        else:
            providers, _, _ = provider_service.get_providers(limit=1000)
        
        # Generate export file
        if request.format == ExportFormat.CSV:
            return await _export_csv(providers)
        elif request.format == ExportFormat.XLSX:
            return await _export_xlsx(providers)
        elif request.format == ExportFormat.PDF:
            return await _export_pdf(providers)
        else:
            return await _export_csv(providers)
            
    except Exception as e:
        logger.error(f"Error exporting providers: {e}")
        raise HTTPException(status_code=400, detail=str(e))

async def _export_csv(providers: List[Provider]) -> StreamingResponse:
    """Export providers to CSV format"""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        "ID", "Name", "Email", "Phone", "WhatsApp", "Services", "Coverage Areas",
        "Specialty", "Zone", "Rating", "Total Missions", "Success Rate", "Status",
        "Availability", "Join Date", "Last Activity"
    ])
    
    # Write data
    for provider in providers:
        writer.writerow([
            provider.id,
            provider.name,
            provider.email,
            provider.phone,
            provider.whatsapp,
            ", ".join(provider.services),
            ", ".join(provider.coverageAreas),
            provider.specialty,
            provider.zone,
            provider.rating,
            provider.totalMissions,
            provider.successRate,
            provider.status,
            provider.availability,
            provider.joinDate,
            provider.lastActivity
        ])
    
    output.seek(0)
    content = output.getvalue()
    output.close()
    
    return StreamingResponse(
        io.BytesIO(content.encode()),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=providers.csv"}
    )

async def _export_xlsx(providers: List[Provider]) -> StreamingResponse:
    """Export providers to XLSX format"""
    try:
        import pandas as pd
        
        # Convert to DataFrame
        data = []
        for provider in providers:
            data.append({
                "ID": provider.id,
                "Name": provider.name,
                "Email": provider.email,
                "Phone": provider.phone,
                "WhatsApp": provider.whatsapp,
                "Services": ", ".join(provider.services),
                "Coverage Areas": ", ".join(provider.coverageAreas),
                "Specialty": provider.specialty,
                "Zone": provider.zone,
                "Rating": provider.rating,
                "Total Missions": provider.totalMissions,
                "Success Rate": provider.successRate,
                "Status": provider.status,
                "Availability": provider.availability,
                "Join Date": provider.joinDate,
                "Last Activity": provider.lastActivity
            })
        
        df = pd.DataFrame(data)
        
        # Create Excel file
        output = io.BytesIO()
        df.to_excel(output, index=False)
        output.seek(0)
        
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=providers.xlsx"}
        )
        
    except ImportError:
        # Fallback to CSV if pandas not available
        logger.warning("pandas not available, falling back to CSV export")
        return await _export_csv(providers)

async def _export_pdf(providers: List[Provider]) -> StreamingResponse:
    """Export providers to PDF format"""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
        from reportlab.lib import colors
        
        # Create PDF
        output = io.BytesIO()
        doc = SimpleDocTemplate(output, pagesize=letter)
        elements = []
        
        # Add title
        styles = getSampleStyleSheet()
        title = Paragraph("Providers Report", styles['Title'])
        elements.append(title)
        
        # Create table data
        data = [["Name", "Email", "Phone", "Services", "Zone", "Rating", "Status"]]
        for provider in providers:
            data.append([
                provider.name,
                provider.email,
                provider.phone,
                ", ".join(provider.services[:2]),  # Limit services for space
                provider.zone,
                str(provider.rating),
                provider.status
            ])
        
        # Create table
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(table)
        doc.build(elements)
        
        output.seek(0)
        return StreamingResponse(
            output,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=providers.pdf"}
        )
        
    except ImportError:
        # Fallback to CSV if reportlab not available
        logger.warning("reportlab not available, falling back to CSV export")
        return await _export_csv(providers)

# Error handlers are managed by FastAPI's global exception handling