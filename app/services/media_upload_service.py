"""
Media Upload Service for Djobea AI
Handles secure media uploads from WhatsApp and other sources
"""

import os
import uuid
import hashlib
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from loguru import logger
from urllib.parse import urlparse
import requests
from PIL import Image
from io import BytesIO

from app.config import get_settings
from app.models.database_models import (
    MediaUpload, ServiceRequest, MediaType, PhotoType
)
from app.services.visual_analysis_service import get_visual_analysis_service


class MediaUploadService:
    """Service for handling media uploads and processing"""
    
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()
        
        # Supported media formats
        self.supported_image_formats = {
            'image/jpeg': '.jpg',
            'image/png': '.png', 
            'image/gif': '.gif',
            'image/webp': '.webp',
            'image/heic': '.heic'
        }
        
        self.supported_video_formats = {
            'video/mp4': '.mp4',
            'video/3gpp': '.3gp',
            'video/quicktime': '.mov',
            'video/avi': '.avi'
        }
        
        self.supported_audio_formats = {
            'audio/mpeg': '.mp3',
            'audio/wav': '.wav',
            'audio/aac': '.aac',
            'audio/ogg': '.ogg'
        }
        
        # Size limits (in bytes)
        self.max_image_size = 16 * 1024 * 1024  # 16MB
        self.max_video_size = 64 * 1024 * 1024  # 64MB
        self.max_audio_size = 10 * 1024 * 1024  # 10MB
    
    async def process_whatsapp_media(self, media_url: str, media_type: str, mime_type: str, 
                                   request_id: int, filename: str = None) -> Optional[MediaUpload]:
        """Process media upload from WhatsApp webhook"""
        try:
            logger.info(f"Processing WhatsApp media: {media_url} for request {request_id}")
            
            # Validate media type and size
            if not self._is_supported_format(mime_type):
                logger.error(f"Unsupported media format: {mime_type}")
                return None
            
            # Download media from WhatsApp
            media_content, file_info = await self._download_whatsapp_media(media_url, mime_type)
            if not media_content:
                logger.error(f"Failed to download media from WhatsApp: {media_url}")
                return None
            
            # Validate file size
            if not self._validate_file_size(len(media_content), mime_type):
                logger.error(f"File size exceeds limit for {mime_type}")
                return None
            
            # Generate secure filename
            if not filename:
                filename = self._generate_filename(mime_type)
            
            # Store media securely
            stored_url = await self._store_media_securely(media_content, filename, mime_type)
            if not stored_url:
                logger.error("Failed to store media securely")
                return None
            
            # Create media upload record
            media_upload = MediaUpload(
                service_request_id=request_id,
                file_url=stored_url,
                file_name=filename,
                file_size=len(media_content),
                media_type=self._get_media_type(mime_type),
                mime_type=mime_type,
                duration_seconds=file_info.get('duration'),
                width=file_info.get('width'),
                height=file_info.get('height'),
                photo_type=self._detect_photo_type(request_id),
                angle_description=self._generate_angle_description(file_info),
                encrypted=True,
                expiry_date=datetime.utcnow() + timedelta(days=90)  # 90 days retention
            )
            
            self.db.add(media_upload)
            self.db.commit()
            self.db.refresh(media_upload)
            
            # Start visual analysis if it's an image
            if media_upload.media_type == MediaType.IMAGE:
                await self._trigger_visual_analysis(media_upload)
            
            logger.info(f"Successfully processed media upload: {media_upload.id}")
            return media_upload
            
        except Exception as e:
            logger.error(f"Error processing WhatsApp media: {e}")
            return None
    
    async def _download_whatsapp_media(self, media_url: str, mime_type: str) -> Tuple[Optional[bytes], Dict]:
        """Download media from WhatsApp with authentication"""
        try:
            headers = {
                'Authorization': f'Bearer {self.settings.twilio_auth_token}',
                'User-Agent': 'Djobea-AI/1.0'
            }
            
            response = requests.get(media_url, headers=headers, timeout=30)
            response.raise_for_status()
            
            media_content = response.content
            file_info = {}
            
            # Extract metadata for images
            if mime_type.startswith('image/'):
                try:
                    image = Image.open(BytesIO(media_content))
                    file_info['width'] = image.width
                    file_info['height'] = image.height
                    file_info['format'] = image.format
                except Exception as e:
                    logger.warning(f"Could not extract image metadata: {e}")
            
            return media_content, file_info
            
        except Exception as e:
            logger.error(f"Error downloading WhatsApp media: {e}")
            return None, {}
    
    def _is_supported_format(self, mime_type: str) -> bool:
        """Check if media format is supported"""
        return (mime_type in self.supported_image_formats or 
                mime_type in self.supported_video_formats or 
                mime_type in self.supported_audio_formats)
    
    def _validate_file_size(self, file_size: int, mime_type: str) -> bool:
        """Validate file size against limits"""
        if mime_type.startswith('image/'):
            return file_size <= self.max_image_size
        elif mime_type.startswith('video/'):
            return file_size <= self.max_video_size
        elif mime_type.startswith('audio/'):
            return file_size <= self.max_audio_size
        return False
    
    def _get_media_type(self, mime_type: str) -> str:
        """Get media type enum from mime type"""
        if mime_type.startswith('image/'):
            return MediaType.IMAGE
        elif mime_type.startswith('video/'):
            return MediaType.VIDEO
        elif mime_type.startswith('audio/'):
            return MediaType.AUDIO
        return MediaType.IMAGE  # default
    
    def _generate_filename(self, mime_type: str) -> str:
        """Generate secure filename"""
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        unique_id = str(uuid.uuid4())[:8]
        extension = self._get_file_extension(mime_type)
        return f"djobea_{timestamp}_{unique_id}{extension}"
    
    def _get_file_extension(self, mime_type: str) -> str:
        """Get file extension from mime type"""
        all_formats = {**self.supported_image_formats, 
                      **self.supported_video_formats, 
                      **self.supported_audio_formats}
        return all_formats.get(mime_type, '.bin')
    
    async def _store_media_securely(self, media_content: bytes, filename: str, mime_type: str) -> Optional[str]:
        """Store media in secure location (local storage for now, can be extended to cloud)"""
        try:
            # Create uploads directory if it doesn't exist
            upload_dir = "static/uploads"
            os.makedirs(upload_dir, exist_ok=True)
            
            # Generate secure path
            date_path = datetime.utcnow().strftime('%Y/%m/%d')
            full_upload_dir = os.path.join(upload_dir, date_path)
            os.makedirs(full_upload_dir, exist_ok=True)
            
            file_path = os.path.join(full_upload_dir, filename)
            
            # Write file
            with open(file_path, 'wb') as f:
                f.write(media_content)
            
            # Return URL path
            return f"/static/uploads/{date_path}/{filename}"
            
        except Exception as e:
            logger.error(f"Error storing media file: {e}")
            return None
    
    def _detect_photo_type(self, request_id: int) -> Optional[str]:
        """Detect photo type based on existing photos and request status"""
        try:
            request = self.db.query(ServiceRequest).filter(
                ServiceRequest.id == request_id
            ).first()
            
            if not request:
                return PhotoType.OVERVIEW
            
            # Count existing photos
            existing_count = self.db.query(MediaUpload).filter(
                MediaUpload.service_request_id == request_id,
                MediaUpload.media_type == MediaType.IMAGE
            ).count()
            
            # Determine photo type based on request status and count
            if existing_count == 0:
                return PhotoType.BEFORE
            elif request.status in ["en cours", "IN_PROGRESS"]:
                return PhotoType.DURING
            elif request.status in ["terminée", "COMPLETED"]:
                return PhotoType.AFTER
            else:
                return PhotoType.OVERVIEW
                
        except Exception as e:
            logger.error(f"Error detecting photo type: {e}")
            return PhotoType.OVERVIEW
    
    def _generate_angle_description(self, file_info: Dict) -> Optional[str]:
        """Generate description of photo angle/view"""
        if file_info.get('width') and file_info.get('height'):
            width, height = file_info['width'], file_info['height']
            
            if width > height * 1.5:
                return "Vue panoramique"
            elif height > width * 1.5:
                return "Vue verticale"
            else:
                return "Vue standard"
        
        return None
    
    async def _trigger_visual_analysis(self, media_upload: MediaUpload):
        """Trigger visual analysis for uploaded image"""
        try:
            # Get service request to determine service type
            request = self.db.query(ServiceRequest).filter(
                ServiceRequest.id == media_upload.service_request_id
            ).first()
            
            if not request:
                logger.error(f"Service request not found for media {media_upload.id}")
                return
            
            # Get visual analysis service and perform analysis
            visual_service = get_visual_analysis_service(self.db)
            await visual_service.analyze_image(media_upload, request.service_type)
            
        except Exception as e:
            logger.error(f"Error triggering visual analysis for media {media_upload.id}: {e}")
    
    def get_media_for_request(self, request_id: int) -> List[MediaUpload]:
        """Get all media uploads for a service request"""
        try:
            return self.db.query(MediaUpload).filter(
                MediaUpload.service_request_id == request_id
            ).order_by(MediaUpload.uploaded_at.desc()).all()
            
        except Exception as e:
            logger.error(f"Error getting media for request {request_id}: {e}")
            return []
    
    def get_images_by_type(self, request_id: int, photo_type: str = None) -> List[MediaUpload]:
        """Get images filtered by photo type"""
        try:
            query = self.db.query(MediaUpload).filter(
                MediaUpload.service_request_id == request_id,
                MediaUpload.media_type == MediaType.IMAGE
            )
            
            if photo_type:
                query = query.filter(MediaUpload.photo_type == photo_type)
            
            return query.order_by(MediaUpload.uploaded_at.desc()).all()
            
        except Exception as e:
            logger.error(f"Error getting images by type: {e}")
            return []
    
    def generate_photo_guidance(self, service_type: str, existing_photos: List[MediaUpload] = None) -> Dict[str, str]:
        """Generate guidance for taking better photos"""
        guidance = {
            "general": "Prenez des photos claires avec un bon éclairage naturel",
            "specific": "",
            "angles": [],
            "tips": []
        }
        
        # Service-specific guidance
        if service_type == "plomberie":
            guidance["specific"] = "Montrez clairement la fuite, les tuyaux et l'environnement"
            guidance["angles"] = [
                "Vue d'ensemble de la zone affectée",
                "Gros plan sur le point de fuite",
                "Vue des tuyaux et raccords",
                "Dégâts causés par l'eau si présents"
            ]
            guidance["tips"] = [
                "Utilisez une lampe de poche si nécessaire",
                "Montrez le débit de la fuite",
                "Incluez les compteurs d'eau si visible"
            ]
        
        elif service_type == "électricité":
            guidance["specific"] = "Montrez le problème électrique en toute sécurité"
            guidance["angles"] = [
                "Vue du tableau électrique",
                "Prise ou interrupteur défaillant",
                "Zone affectée par la panne",
                "Équipements électriques concernés"
            ]
            guidance["tips"] = [
                "NE TOUCHEZ PAS aux fils électriques",
                "Photographiez à distance de sécurité",
                "Montrez l'état des disjoncteurs",
                "Évitez les photos dans l'obscurité"
            ]
        
        elif service_type == "réparation électroménager":
            guidance["specific"] = "Montrez l'appareil et le problème rencontré"
            guidance["angles"] = [
                "Vue complète de l'appareil",
                "Écran ou panneau de contrôle",
                "Zone où se situe le problème",
                "Plaque signalétique avec modèle"
            ]
            guidance["tips"] = [
                "Incluez le numéro de modèle",
                "Montrez les codes d'erreur affichés",
                "Photographiez l'intérieur si sécurisé",
                "Documentez les bruits ou fumée"
            ]
        
        # Analyze existing photos to suggest missing angles
        if existing_photos:
            existing_types = [photo.photo_type for photo in existing_photos if photo.photo_type]
            needed_types = []
            
            if PhotoType.OVERVIEW not in existing_types:
                needed_types.append("Vue d'ensemble")
            if PhotoType.DETAIL not in existing_types:
                needed_types.append("Détail du problème")
            
            if needed_types:
                guidance["missing"] = f"Photos manquantes: {', '.join(needed_types)}"
        
        return guidance
    
    def cleanup_expired_media(self) -> int:
        """Clean up expired media files"""
        try:
            expired_media = self.db.query(MediaUpload).filter(
                MediaUpload.expiry_date < datetime.utcnow()
            ).all()
            
            cleaned_count = 0
            for media in expired_media:
                try:
                    # Delete physical file
                    if media.file_url.startswith('/static/'):
                        file_path = media.file_url[1:]  # Remove leading slash
                        if os.path.exists(file_path):
                            os.remove(file_path)
                    
                    # Delete database record
                    self.db.delete(media)
                    cleaned_count += 1
                    
                except Exception as e:
                    logger.error(f"Error deleting expired media {media.id}: {e}")
            
            self.db.commit()
            logger.info(f"Cleaned up {cleaned_count} expired media files")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Error during media cleanup: {e}")
            return 0
    
    def generate_media_report(self, request_id: int) -> Dict:
        """Generate comprehensive media report for service request"""
        try:
            media_uploads = self.get_media_for_request(request_id)
            
            report = {
                "total_files": len(media_uploads),
                "images": 0,
                "videos": 0,
                "audio": 0,
                "total_size": 0,
                "photo_types": {},
                "analysis_completed": 0,
                "quality_scores": []
            }
            
            for media in media_uploads:
                # Count by type
                if media.media_type == MediaType.IMAGE:
                    report["images"] += 1
                elif media.media_type == MediaType.VIDEO:
                    report["videos"] += 1
                elif media.media_type == MediaType.AUDIO:
                    report["audio"] += 1
                
                # Total size
                report["total_size"] += media.file_size
                
                # Photo types
                if media.photo_type:
                    report["photo_types"][media.photo_type] = report["photo_types"].get(media.photo_type, 0) + 1
                
                # Analysis status
                if media.analysis_completed:
                    report["analysis_completed"] += 1
                
                # Quality scores
                if media.analysis_confidence:
                    report["quality_scores"].append(media.analysis_confidence)
            
            # Calculate averages
            if report["quality_scores"]:
                report["average_quality"] = sum(report["quality_scores"]) / len(report["quality_scores"])
            else:
                report["average_quality"] = 0.0
            
            # Format size
            report["total_size_mb"] = round(report["total_size"] / (1024 * 1024), 2)
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating media report: {e}")
            return {}


# Global instance
def get_media_upload_service(db: Session) -> MediaUploadService:
    """Get media upload service instance"""
    return MediaUploadService(db)