"""
Visual Analysis Service for Djobea AI
Handles AI-powered image/video analysis using Claude Vision API
"""

import json
import base64
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from loguru import logger
from io import BytesIO
from PIL import Image
import requests

from app.config import get_settings
from app.models.database_models import (
    MediaUpload, VisualAnalysis, ProblemPhoto, VisualProgress,
    ServiceRequest, ProblemSeverity, PhotoType, MediaType
)
from app.services.ai_service import ai_service


class VisualAnalysisService:
    """Service for AI-powered visual problem analysis"""
    
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()
        
        # Problem detection prompts
        self.analysis_prompts = {
            "plomberie": """
Analysez cette image pour identifier les problèmes de plomberie. Identifiez:
1. Type de problème (fuite, blocage, installation, réparation)
2. Gravité (mineur, modéré, majeur, urgence)
3. Localisation exacte du problème
4. Outils et matériaux nécessaires
5. Estimation du temps de réparation
6. Coût estimé en francs CFA (XAF)
7. Risques de sécurité éventuels
8. Recommandations pour des photos supplémentaires

Répondez en français avec des détails techniques précis pour le contexte camerounais.
            """,
            "électricité": """
Analysez cette image pour identifier les problèmes électriques. Identifiez:
1. Type de problème (panne, installation, court-circuit, surcharge)
2. Gravité (mineur, modéré, majeur, urgence)
3. Composants électriques concernés
4. Outils et matériaux nécessaires
5. Estimation du temps de réparation
6. Coût estimé en francs CFA (XAF)
7. Risques de sécurité et mesures de précaution
8. Recommandations pour des photos supplémentaires

IMPORTANT: Signalez tout risque électrique immédiat. Répondez en français pour le contexte camerounais.
            """,
            "réparation électroménager": """
Analysez cette image pour identifier les problèmes d'électroménager. Identifiez:
1. Type d'appareil et marque si visible
2. Type de problème (panne, usure, dysfonctionnement)
3. Gravité (mineur, modéré, majeur, remplacement nécessaire)
4. Pièces de rechange potentiellement nécessaires
5. Outils requis pour la réparation
6. Estimation du temps de réparation
7. Coût estimé en francs CFA (XAF)
8. Recommandations pour des photos supplémentaires

Répondez en français avec des conseils pratiques pour le contexte camerounais.
            """
        }
    
    async def analyze_image(self, media_upload: MediaUpload, service_type: str) -> Optional[VisualAnalysis]:
        """Analyze uploaded image using Claude Vision API"""
        try:
            # Download and prepare image
            image_data = await self._download_and_prepare_image(media_upload.file_url)
            if not image_data:
                logger.error(f"Failed to prepare image for analysis: {media_upload.id}")
                return None
            
            # Get analysis prompt for service type
            prompt = self.analysis_prompts.get(service_type.lower(), self.analysis_prompts["plomberie"])
            
            # Perform AI analysis
            analysis_result = await self._perform_vision_analysis(image_data, prompt)
            if not analysis_result:
                logger.error(f"AI analysis failed for media {media_upload.id}")
                return None
            
            # Create visual analysis record
            visual_analysis = VisualAnalysis(
                media_id=media_upload.id,
                detected_problems=analysis_result.get("detected_problems", []),
                primary_problem=analysis_result.get("primary_problem"),
                problem_confidence=analysis_result.get("problem_confidence", 0.0),
                severity=analysis_result.get("severity"),
                severity_confidence=analysis_result.get("severity_confidence", 0.0),
                safety_hazards=analysis_result.get("safety_hazards", []),
                required_expertise=analysis_result.get("required_expertise"),
                tools_needed=analysis_result.get("tools_needed", []),
                materials_needed=analysis_result.get("materials_needed", []),
                estimated_duration=analysis_result.get("estimated_duration"),
                estimated_cost_min=analysis_result.get("estimated_cost_min"),
                estimated_cost_max=analysis_result.get("estimated_cost_max"),
                cost_factors=analysis_result.get("cost_factors", []),
                damage_visible=analysis_result.get("damage_visible", False),
                damage_description=analysis_result.get("damage_description"),
                damage_extent=analysis_result.get("damage_extent"),
                ai_model_version=self.settings.claude_model,
                analysis_prompt=prompt,
                raw_response=json.dumps(analysis_result, ensure_ascii=False),
                image_quality=analysis_result.get("image_quality", "good"),
                lighting_quality=analysis_result.get("lighting_quality", "good"),
                angle_quality=analysis_result.get("angle_quality", "good"),
                focus_quality=analysis_result.get("focus_quality", "good"),
                additional_photos_needed=analysis_result.get("additional_photos_needed", []),
                photo_guidance=analysis_result.get("photo_guidance")
            )
            
            self.db.add(visual_analysis)
            
            # Update media upload status
            media_upload.analysis_completed = True
            media_upload.analysis_confidence = analysis_result.get("overall_confidence", 0.0)
            media_upload.analyzed_at = datetime.utcnow()
            
            self.db.commit()
            self.db.refresh(visual_analysis)
            
            logger.info(f"Visual analysis completed for media {media_upload.id}")
            return visual_analysis
            
        except Exception as e:
            logger.error(f"Error in visual analysis for media {media_upload.id}: {e}")
            media_upload.processing_error = str(e)
            self.db.commit()
            return None
    
    async def _download_and_prepare_image(self, file_url: str) -> Optional[str]:
        """Download image and convert to base64 for AI analysis"""
        try:
            # Download image
            response = requests.get(file_url, timeout=30)
            response.raise_for_status()
            
            # Open and process image
            image = Image.open(BytesIO(response.content))
            
            # Resize if too large (Claude has size limits)
            max_size = (1024, 1024)
            if image.size[0] > max_size[0] or image.size[1] > max_size[1]:
                image.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Convert to base64
            buffer = BytesIO()
            image.save(buffer, format='JPEG', quality=85)
            image_bytes = buffer.getvalue()
            
            return base64.b64encode(image_bytes).decode('utf-8')
            
        except Exception as e:
            logger.error(f"Error preparing image from {file_url}: {e}")
            return None
    
    async def _perform_vision_analysis(self, image_data: str, prompt: str) -> Optional[Dict]:
        """Perform AI vision analysis using Claude API"""
        try:
            # Construct message for Claude Vision
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt + "\n\nRépondez avec un JSON structuré contenant tous les éléments demandés."
                        },
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": image_data
                            }
                        }
                    ]
                }
            ]
            
            # Call Claude API through ai_service
            response = await ai_service.generate_response(messages)
            
            # Parse JSON response
            try:
                analysis_result = json.loads(response)
                
                # Validate and normalize the response
                analysis_result = self._normalize_analysis_result(analysis_result)
                
                return analysis_result
                
            except json.JSONDecodeError:
                # If response is not JSON, extract information manually
                logger.warning("AI response not in JSON format, parsing manually")
                return self._parse_text_response(response)
            
        except Exception as e:
            logger.error(f"Error in AI vision analysis: {e}")
            return None
    
    def _normalize_analysis_result(self, result: Dict) -> Dict:
        """Normalize and validate AI analysis result"""
        normalized = {
            "detected_problems": result.get("detected_problems", []),
            "primary_problem": result.get("primary_problem", ""),
            "problem_confidence": float(result.get("problem_confidence", 0.0)),
            "severity": result.get("severity", "moderate"),
            "severity_confidence": float(result.get("severity_confidence", 0.0)),
            "safety_hazards": result.get("safety_hazards", []),
            "required_expertise": result.get("required_expertise", ""),
            "tools_needed": result.get("tools_needed", []),
            "materials_needed": result.get("materials_needed", []),
            "estimated_duration": result.get("estimated_duration", ""),
            "estimated_cost_min": self._parse_cost(result.get("estimated_cost_min")),
            "estimated_cost_max": self._parse_cost(result.get("estimated_cost_max")),
            "cost_factors": result.get("cost_factors", []),
            "damage_visible": bool(result.get("damage_visible", False)),
            "damage_description": result.get("damage_description", ""),
            "damage_extent": result.get("damage_extent", ""),
            "image_quality": result.get("image_quality", "good"),
            "lighting_quality": result.get("lighting_quality", "good"),
            "angle_quality": result.get("angle_quality", "good"),
            "focus_quality": result.get("focus_quality", "good"),
            "additional_photos_needed": result.get("additional_photos_needed", []),
            "photo_guidance": result.get("photo_guidance", ""),
            "overall_confidence": float(result.get("overall_confidence", 0.0))
        }
        
        # Ensure severity is valid
        valid_severities = ["minor", "moderate", "major", "emergency"]
        if normalized["severity"] not in valid_severities:
            normalized["severity"] = "moderate"
        
        return normalized
    
    def _parse_cost(self, cost_str) -> Optional[float]:
        """Parse cost string to float value"""
        if not cost_str:
            return None
        
        try:
            # Remove currency symbols and spaces
            cost_str = str(cost_str).replace("XAF", "").replace("FCFA", "").replace(" ", "").replace(",", "")
            return float(cost_str)
        except (ValueError, TypeError):
            return None
    
    def _parse_text_response(self, response: str) -> Dict:
        """Parse text response when JSON parsing fails"""
        # Basic text parsing for fallback
        result = {
            "detected_problems": [],
            "primary_problem": "Problème détecté nécessitant inspection",
            "problem_confidence": 0.7,
            "severity": "moderate",
            "severity_confidence": 0.6,
            "safety_hazards": [],
            "required_expertise": "Technicien qualifié",
            "tools_needed": [],
            "materials_needed": [],
            "estimated_duration": "1-2 heures",
            "estimated_cost_min": 3000.0,
            "estimated_cost_max": 8000.0,
            "cost_factors": ["Complexité du problème"],
            "damage_visible": True,
            "damage_description": response[:200] + "..." if len(response) > 200 else response,
            "damage_extent": "moderate",
            "image_quality": "good",
            "lighting_quality": "good",
            "angle_quality": "good",
            "focus_quality": "good",
            "additional_photos_needed": ["Vue d'ensemble", "Détail du problème"],
            "photo_guidance": "Prenez des photos sous différents angles avec un bon éclairage",
            "overall_confidence": 0.6
        }
        
        return result
    
    def categorize_photo(self, media_upload: MediaUpload, photo_type: str = None) -> ProblemPhoto:
        """Categorize and store photo for problem documentation"""
        try:
            # Auto-detect photo type if not provided
            if not photo_type:
                photo_type = self._detect_photo_type(media_upload)
            
            problem_photo = ProblemPhoto(
                service_request_id=media_upload.service_request_id,
                media_id=media_upload.id,
                photo_type=photo_type,
                sequence_number=self._get_next_sequence_number(media_upload.service_request_id, photo_type),
                analysis_confidence=media_upload.analysis_confidence or 0.0,
                ai_description=self._generate_photo_description(media_upload),
                problem_visible=True,
                quality_score=self._assess_photo_quality(media_upload)
            )
            
            self.db.add(problem_photo)
            self.db.commit()
            self.db.refresh(problem_photo)
            
            logger.info(f"Categorized photo {media_upload.id} as {photo_type}")
            return problem_photo
            
        except Exception as e:
            logger.error(f"Error categorizing photo {media_upload.id}: {e}")
            return None
    
    def _detect_photo_type(self, media_upload: MediaUpload) -> str:
        """Auto-detect photo type based on service request status and analysis"""
        request = self.db.query(ServiceRequest).filter(
            ServiceRequest.id == media_upload.service_request_id
        ).first()
        
        if not request:
            return PhotoType.OVERVIEW
        
        # Check existing photos to determine type
        existing_photos = self.db.query(ProblemPhoto).filter(
            ProblemPhoto.service_request_id == request.id
        ).count()
        
        if existing_photos == 0:
            return PhotoType.BEFORE
        elif request.status in ["en cours", "IN_PROGRESS"]:
            return PhotoType.DURING
        elif request.status in ["terminée", "COMPLETED"]:
            return PhotoType.AFTER
        else:
            return PhotoType.OVERVIEW
    
    def _get_next_sequence_number(self, request_id: int, photo_type: str) -> int:
        """Get next sequence number for photo type"""
        max_sequence = self.db.query(ProblemPhoto).filter(
            ProblemPhoto.service_request_id == request_id,
            ProblemPhoto.photo_type == photo_type
        ).count()
        
        return max_sequence + 1
    
    def _generate_photo_description(self, media_upload: MediaUpload) -> str:
        """Generate AI description for photo"""
        if media_upload.visual_analysis:
            return media_upload.visual_analysis.primary_problem or "Photo du problème"
        return f"Photo {media_upload.photo_type or 'du problème'}"
    
    def _assess_photo_quality(self, media_upload: MediaUpload) -> float:
        """Assess photo quality score"""
        if media_upload.visual_analysis:
            quality_factors = [
                media_upload.visual_analysis.image_quality,
                media_upload.visual_analysis.lighting_quality,
                media_upload.visual_analysis.angle_quality,
                media_upload.visual_analysis.focus_quality
            ]
            
            quality_scores = {
                "excellent": 1.0,
                "good": 0.8,
                "fair": 0.6,
                "poor": 0.3
            }
            
            scores = [quality_scores.get(q, 0.5) for q in quality_factors if q]
            return sum(scores) / len(scores) if scores else 0.5
        
        return 0.5
    
    def create_visual_progress_entry(self, request_id: int, stage: str, photo_url: str = None, 
                                   provider_comments: str = None) -> VisualProgress:
        """Create visual progress tracking entry"""
        try:
            progress_entry = VisualProgress(
                service_request_id=request_id,
                stage=stage,
                stage_description=self._get_stage_description(stage),
                progress_percentage=self._calculate_progress_percentage(request_id, stage),
                photo_url=photo_url,
                photo_description=f"Photo de progression: {stage}",
                photo_type=self._get_photo_type_for_stage(stage),
                submitted_by_provider=bool(provider_comments),
                provider_comments=provider_comments,
                quality_approved=False,
                customer_approved=False
            )
            
            self.db.add(progress_entry)
            self.db.commit()
            self.db.refresh(progress_entry)
            
            logger.info(f"Created visual progress entry for request {request_id}, stage {stage}")
            return progress_entry
            
        except Exception as e:
            logger.error(f"Error creating visual progress entry: {e}")
            return None
    
    def _get_stage_description(self, stage: str) -> str:
        """Get human-readable stage description"""
        descriptions = {
            "assessment": "Évaluation initiale du problème",
            "in_progress": "Intervention en cours",
            "completed": "Travaux terminés",
            "quality_check": "Vérification qualité"
        }
        return descriptions.get(stage, stage)
    
    def _calculate_progress_percentage(self, request_id: int, stage: str) -> float:
        """Calculate progress percentage based on stage"""
        stage_percentages = {
            "assessment": 10.0,
            "in_progress": 50.0,
            "completed": 90.0,
            "quality_check": 100.0
        }
        return stage_percentages.get(stage, 0.0)
    
    def _get_photo_type_for_stage(self, stage: str) -> str:
        """Get appropriate photo type for stage"""
        stage_to_photo_type = {
            "assessment": PhotoType.BEFORE,
            "in_progress": PhotoType.DURING,
            "completed": PhotoType.AFTER,
            "quality_check": PhotoType.AFTER
        }
        return stage_to_photo_type.get(stage, PhotoType.OVERVIEW)
    
    def generate_visual_summary(self, request_id: int) -> Dict:
        """Generate comprehensive visual summary for service request"""
        try:
            # Get all media uploads for request
            media_uploads = self.db.query(MediaUpload).filter(
                MediaUpload.service_request_id == request_id
            ).all()
            
            # Get visual analyses
            analyses = []
            for media in media_uploads:
                if media.visual_analysis:
                    analyses.append(media.visual_analysis)
            
            # Generate summary
            summary = {
                "total_media": len(media_uploads),
                "total_analyses": len(analyses),
                "problem_types": self._extract_problem_types(analyses),
                "severity_distribution": self._calculate_severity_distribution(analyses),
                "safety_concerns": self._extract_safety_concerns(analyses),
                "cost_estimation": self._calculate_cost_range(analyses),
                "photo_quality_score": self._calculate_overall_quality(analyses),
                "recommendations": self._generate_recommendations(analyses)
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating visual summary for request {request_id}: {e}")
            return {}
    
    def _extract_problem_types(self, analyses: List[VisualAnalysis]) -> List[str]:
        """Extract unique problem types from analyses"""
        problems = set()
        for analysis in analyses:
            if analysis.detected_problems:
                problems.update(analysis.detected_problems)
            if analysis.primary_problem:
                problems.add(analysis.primary_problem)
        return list(problems)
    
    def _calculate_severity_distribution(self, analyses: List[VisualAnalysis]) -> Dict[str, int]:
        """Calculate distribution of severity levels"""
        distribution = {"minor": 0, "moderate": 0, "major": 0, "emergency": 0}
        for analysis in analyses:
            if analysis.severity in distribution:
                distribution[analysis.severity] += 1
        return distribution
    
    def _extract_safety_concerns(self, analyses: List[VisualAnalysis]) -> List[str]:
        """Extract all safety concerns from analyses"""
        concerns = set()
        for analysis in analyses:
            if analysis.safety_hazards:
                concerns.update(analysis.safety_hazards)
        return list(concerns)
    
    def _calculate_cost_range(self, analyses: List[VisualAnalysis]) -> Dict[str, float]:
        """Calculate overall cost range from analyses"""
        min_costs = [a.estimated_cost_min for a in analyses if a.estimated_cost_min]
        max_costs = [a.estimated_cost_max for a in analyses if a.estimated_cost_max]
        
        return {
            "min_cost": min(min_costs) if min_costs else 0,
            "max_cost": max(max_costs) if max_costs else 0,
            "confidence": "high" if len(analyses) > 1 else "medium"
        }
    
    def _calculate_overall_quality(self, analyses: List[VisualAnalysis]) -> float:
        """Calculate overall photo quality score"""
        if not analyses:
            return 0.0
        
        quality_mapping = {"excellent": 1.0, "good": 0.8, "fair": 0.6, "poor": 0.3}
        total_score = 0.0
        count = 0
        
        for analysis in analyses:
            qualities = [
                analysis.image_quality,
                analysis.lighting_quality,
                analysis.angle_quality,
                analysis.focus_quality
            ]
            
            for quality in qualities:
                if quality in quality_mapping:
                    total_score += quality_mapping[quality]
                    count += 1
        
        return total_score / count if count > 0 else 0.5
    
    def _generate_recommendations(self, analyses: List[VisualAnalysis]) -> List[str]:
        """Generate recommendations based on analyses"""
        recommendations = set()
        
        for analysis in analyses:
            if analysis.additional_photos_needed:
                recommendations.update(analysis.additional_photos_needed)
            if analysis.photo_guidance:
                recommendations.add(analysis.photo_guidance)
        
        # Add generic recommendations
        if not recommendations:
            recommendations.add("Prenez des photos sous différents angles")
            recommendations.add("Assurez-vous d'avoir un bon éclairage")
            recommendations.add("Incluez une vue d'ensemble et des détails")
        
        return list(recommendations)


# Global instance
visual_analysis_service = None

def get_visual_analysis_service(db: Session) -> VisualAnalysisService:
    """Get visual analysis service instance"""
    return VisualAnalysisService(db)