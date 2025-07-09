"""
Validation Service - Post-LLM validation and error correction
Handles validation of LLM responses, data consistency, and automatic corrections
"""
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session
from dataclasses import dataclass
from enum import Enum
import logging
import json
from datetime import datetime
import re
from difflib import SequenceMatcher

from app.models.dynamic_services import Service, Zone, ServiceCategory, ValidationLog, ValidationError
from app.services.zone_service import ZoneService
from app.services.service_management_service import ServiceManagementService

logger = logging.getLogger(__name__)

class ValidationErrorType(Enum):
    """Types of validation errors"""
    INVALID_SERVICE_CODE = "invalid_service_code"
    INVALID_ZONE_CODE = "invalid_zone_code"
    INCONSISTENT_DATA = "inconsistent_data"
    MISSING_REQUIRED_FIELD = "missing_required_field"
    INVALID_PRICE_RANGE = "invalid_price_range"
    ZONE_SERVICE_MISMATCH = "zone_service_mismatch"
    COMPREHENSION_ERROR = "comprehension_error"
    SEMANTIC_ERROR = "semantic_error"

class ValidationSeverity(Enum):
    """Severity levels for validation errors"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class ValidationResult:
    """Result of validation process"""
    is_valid: bool
    errors: List[Dict[str, Any]]
    corrections: List[Dict[str, Any]]
    confidence_score: float
    suggestions: List[Dict[str, Any]]
    corrected_data: Optional[Dict[str, Any]] = None

@dataclass
class ValidationMetrics:
    """Metrics for validation performance"""
    total_validations: int
    success_rate: float
    error_distribution: Dict[str, int]
    avg_correction_time: float
    auto_correction_rate: float

class ValidationService:
    """Service for validating LLM responses and providing intelligent corrections"""
    
    def __init__(self):
        self.zone_service = ZoneService()
        self.service_management = ServiceManagementService()
        self.validation_cache: Dict[str, ValidationResult] = {}
        
        # Validation rules and thresholds
        self.validation_rules = {
            'min_confidence_score': 0.6,
            'max_price_variance': 0.5,  # 50% variance allowed
            'similarity_threshold': 0.7,
            'max_retry_attempts': 3,
            'auto_correction_threshold': 0.8
        }
        
        # Common error patterns and corrections
        self.error_patterns = {
            'service_typos': {
                'plombrie': 'plomberie',
                'electrique': 'électrique',
                'reparation': 'réparation',
                'menage': 'ménage',
                'jardinage': 'jardinage'
            },
            'zone_variations': {
                'bona': 'bonamoussadi',
                'douala centre': 'douala',
                'yaounde': 'yaoundé',
                'bafoussam': 'bafoussam'
            }
        }
    
    async def validate_llm_response(
        self,
        db: Session,
        llm_response: Dict[str, Any],
        original_query: str,
        context: Dict[str, Any] = None
    ) -> ValidationResult:
        """
        Validate LLM response for correctness and consistency
        """
        try:
            # Create validation session
            validation_id = self._generate_validation_id()
            
            # Initialize validation result
            errors = []
            corrections = []
            suggestions = []
            confidence_score = llm_response.get('confidence', 0.0)
            
            # 1. Validate service codes
            service_validation = await self._validate_service_codes(db, llm_response)
            if not service_validation['is_valid']:
                errors.extend(service_validation['errors'])
                corrections.extend(service_validation['corrections'])
            
            # 2. Validate zone codes
            zone_validation = await self._validate_zone_codes(db, llm_response)
            if not zone_validation['is_valid']:
                errors.extend(zone_validation['errors'])
                corrections.extend(zone_validation['corrections'])
            
            # 3. Validate data consistency
            consistency_validation = await self._validate_data_consistency(db, llm_response)
            if not consistency_validation['is_valid']:
                errors.extend(consistency_validation['errors'])
                corrections.extend(consistency_validation['corrections'])
            
            # 4. Validate semantic coherence
            semantic_validation = await self._validate_semantic_coherence(
                db, llm_response, original_query
            )
            if not semantic_validation['is_valid']:
                errors.extend(semantic_validation['errors'])
                suggestions.extend(semantic_validation['suggestions'])
            
            # 5. Calculate final confidence score
            final_confidence = self._calculate_validation_confidence(
                confidence_score, errors, corrections
            )
            
            # 6. Generate suggestions if needed
            if errors or final_confidence < self.validation_rules['min_confidence_score']:
                suggestions.extend(await self._generate_suggestions(db, llm_response, errors))
            
            # 7. Attempt automatic corrections
            corrected_data = None
            if corrections and final_confidence > self.validation_rules['auto_correction_threshold']:
                corrected_data = await self._apply_corrections(llm_response, corrections)
            
            # 8. Log validation results
            await self._log_validation_result(
                db, validation_id, llm_response, errors, corrections, final_confidence
            )
            
            validation_result = ValidationResult(
                is_valid=len(errors) == 0,
                errors=errors,
                corrections=corrections,
                confidence_score=final_confidence,
                suggestions=suggestions,
                corrected_data=corrected_data
            )
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Error in validation: {e}")
            return ValidationResult(
                is_valid=False,
                errors=[{
                    'type': ValidationErrorType.COMPREHENSION_ERROR.value,
                    'message': f"Validation failed: {str(e)}",
                    'severity': ValidationSeverity.CRITICAL.value
                }],
                corrections=[],
                confidence_score=0.0,
                suggestions=[]
            )
    
    async def _validate_service_codes(
        self,
        db: Session,
        llm_response: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate service codes in LLM response"""
        errors = []
        corrections = []
        
        service_codes = llm_response.get('service_codes', [])
        if not service_codes:
            service_codes = [llm_response.get('service_code')] if llm_response.get('service_code') else []
        
        for code in service_codes:
            if not code:
                continue
                
            # Check if service exists
            service = db.query(Service).filter(Service.code == code).first()
            if not service:
                # Try to find similar service
                similar_services = await self._find_similar_services(db, code)
                if similar_services:
                    correction = {
                        'type': 'service_code_correction',
                        'original': code,
                        'suggestion': similar_services[0]['code'],
                        'confidence': similar_services[0]['similarity']
                    }
                    corrections.append(correction)
                else:
                    errors.append({
                        'type': ValidationErrorType.INVALID_SERVICE_CODE.value,
                        'message': f"Service code '{code}' not found",
                        'severity': ValidationSeverity.HIGH.value,
                        'field': 'service_code',
                        'value': code
                    })
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'corrections': corrections
        }
    
    async def _validate_zone_codes(
        self,
        db: Session,
        llm_response: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate zone codes in LLM response"""
        errors = []
        corrections = []
        
        zone_codes = llm_response.get('zone_codes', [])
        if not zone_codes:
            zone_codes = [llm_response.get('zone_code')] if llm_response.get('zone_code') else []
        
        for code in zone_codes:
            if not code:
                continue
                
            # Check if zone exists
            zone = await self.zone_service.find_zone_by_code(db, code)
            if not zone:
                # Try to find similar zone
                similar_zones = await self._find_similar_zones(db, code)
                if similar_zones:
                    correction = {
                        'type': 'zone_code_correction',
                        'original': code,
                        'suggestion': similar_zones[0]['code'],
                        'confidence': similar_zones[0]['similarity']
                    }
                    corrections.append(correction)
                else:
                    errors.append({
                        'type': ValidationErrorType.INVALID_ZONE_CODE.value,
                        'message': f"Zone code '{code}' not found",
                        'severity': ValidationSeverity.HIGH.value,
                        'field': 'zone_code',
                        'value': code
                    })
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'corrections': corrections
        }
    
    async def _validate_data_consistency(
        self,
        db: Session,
        llm_response: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate internal data consistency"""
        errors = []
        corrections = []
        
        # Check service-zone compatibility
        service_code = llm_response.get('service_code')
        zone_code = llm_response.get('zone_code')
        
        if service_code and zone_code:
            # Check if service is available in zone
            service = db.query(Service).filter(Service.code == service_code).first()
            zone = await self.zone_service.find_zone_by_code(db, zone_code)
            
            if service and zone:
                # Check service-zone relationship
                from app.models.dynamic_services import ServiceZone
                service_zone = db.query(ServiceZone).filter(
                    ServiceZone.service_id == service.id,
                    ServiceZone.zone_id == zone.id,
                    ServiceZone.is_available == True
                ).first()
                
                if not service_zone:
                    errors.append({
                        'type': ValidationErrorType.ZONE_SERVICE_MISMATCH.value,
                        'message': f"Service '{service_code}' not available in zone '{zone_code}'",
                        'severity': ValidationSeverity.MEDIUM.value,
                        'field': 'service_zone_compatibility'
                    })
        
        # Validate price ranges
        price_estimate = llm_response.get('price_estimate')
        if price_estimate and service_code:
            service = db.query(Service).filter(Service.code == service_code).first()
            if service:
                min_price = service.min_price_xaf
                max_price = service.max_price_xaf
                
                if price_estimate < min_price * 0.5 or price_estimate > max_price * 2:
                    errors.append({
                        'type': ValidationErrorType.INVALID_PRICE_RANGE.value,
                        'message': f"Price estimate {price_estimate} outside valid range ({min_price}-{max_price})",
                        'severity': ValidationSeverity.MEDIUM.value,
                        'field': 'price_estimate'
                    })
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'corrections': corrections
        }
    
    async def _validate_semantic_coherence(
        self,
        db: Session,
        llm_response: Dict[str, Any],
        original_query: str
    ) -> Dict[str, Any]:
        """Validate semantic coherence between query and response"""
        errors = []
        suggestions = []
        
        # Check if extracted service matches query intent
        service_code = llm_response.get('service_code')
        if service_code:
            service = db.query(Service).filter(Service.code == service_code).first()
            if service:
                # Calculate semantic similarity
                similarity = self._calculate_semantic_similarity(
                    original_query.lower(),
                    service.name.lower() + " " + service.description.lower()
                )
                
                if similarity < self.validation_rules['similarity_threshold']:
                    errors.append({
                        'type': ValidationErrorType.SEMANTIC_ERROR.value,
                        'message': f"Low semantic similarity ({similarity:.2f}) between query and service",
                        'severity': ValidationSeverity.MEDIUM.value,
                        'field': 'semantic_coherence'
                    })
                    
                    # Suggest better matches
                    better_matches = await self.service_management.search_services(
                        db, original_query, limit=3
                    )
                    for match in better_matches:
                        suggestions.append({
                            'type': 'alternative_service',
                            'service_code': match['service'].code,
                            'service_name': match['service'].name,
                            'relevance_score': match['relevance_score']
                        })
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'suggestions': suggestions
        }
    
    async def _find_similar_services(
        self,
        db: Session,
        service_code: str
    ) -> List[Dict[str, Any]]:
        """Find similar services based on code similarity"""
        services = db.query(Service).filter(Service.status == 'available').all()
        similar_services = []
        
        for service in services:
            similarity = SequenceMatcher(None, service_code.lower(), service.code.lower()).ratio()
            if similarity > 0.6:
                similar_services.append({
                    'code': service.code,
                    'name': service.name,
                    'similarity': similarity
                })
        
        return sorted(similar_services, key=lambda x: x['similarity'], reverse=True)
    
    async def _find_similar_zones(
        self,
        db: Session,
        zone_code: str
    ) -> List[Dict[str, Any]]:
        """Find similar zones based on code similarity"""
        zones = db.query(Zone).filter(Zone.is_active == True).all()
        similar_zones = []
        
        for zone in zones:
            similarity = SequenceMatcher(None, zone_code.lower(), zone.code.lower()).ratio()
            if similarity > 0.6:
                similar_zones.append({
                    'code': zone.code,
                    'name': zone.name,
                    'similarity': similarity
                })
        
        return sorted(similar_zones, key=lambda x: x['similarity'], reverse=True)
    
    async def _generate_suggestions(
        self,
        db: Session,
        llm_response: Dict[str, Any],
        errors: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate intelligent suggestions based on errors"""
        suggestions = []
        
        for error in errors:
            error_type = error['type']
            
            if error_type == ValidationErrorType.INVALID_SERVICE_CODE.value:
                # Suggest similar services
                similar_services = await self._find_similar_services(db, error['value'])
                for service in similar_services[:3]:
                    suggestions.append({
                        'type': 'service_suggestion',
                        'message': f"Did you mean '{service['name']}' ({service['code']})?",
                        'confidence': service['similarity'],
                        'suggestion': service['code']
                    })
            
            elif error_type == ValidationErrorType.INVALID_ZONE_CODE.value:
                # Suggest similar zones
                similar_zones = await self._find_similar_zones(db, error['value'])
                for zone in similar_zones[:3]:
                    suggestions.append({
                        'type': 'zone_suggestion',
                        'message': f"Did you mean '{zone['name']}' ({zone['code']})?",
                        'confidence': zone['similarity'],
                        'suggestion': zone['code']
                    })
            
            elif error_type == ValidationErrorType.ZONE_SERVICE_MISMATCH.value:
                # Suggest nearby zones with the service
                suggestions.extend(await self._suggest_nearby_zones_with_service(
                    db, llm_response.get('service_code'), llm_response.get('zone_code')
                ))
        
        return suggestions
    
    async def _suggest_nearby_zones_with_service(
        self,
        db: Session,
        service_code: str,
        zone_code: str
    ) -> List[Dict[str, Any]]:
        """Suggest nearby zones where service is available"""
        suggestions = []
        
        # Get current zone
        current_zone = await self.zone_service.find_zone_by_code(db, zone_code)
        if not current_zone:
            return suggestions
        
        # Find nearby zones with the service
        from app.models.dynamic_services import ServiceZone
        nearby_zones = await self.zone_service.find_nearby_zones(
            db, current_zone.latitude, current_zone.longitude, radius_km=10
        )
        
        for zone in nearby_zones:
            service_zone = db.query(ServiceZone).join(Service).filter(
                ServiceZone.zone_id == zone.id,
                Service.code == service_code,
                ServiceZone.is_available == True
            ).first()
            
            if service_zone:
                suggestions.append({
                    'type': 'nearby_zone_suggestion',
                    'message': f"Service available in nearby zone: {zone.name}",
                    'zone_code': zone.code,
                    'zone_name': zone.name,
                    'distance_km': self._calculate_distance(
                        current_zone.latitude, current_zone.longitude,
                        zone.latitude, zone.longitude
                    )
                })
        
        return sorted(suggestions, key=lambda x: x['distance_km'])[:3]
    
    def _calculate_validation_confidence(
        self,
        original_confidence: float,
        errors: List[Dict[str, Any]],
        corrections: List[Dict[str, Any]]
    ) -> float:
        """Calculate final confidence score after validation"""
        # Start with original confidence
        confidence = original_confidence
        
        # Penalize based on errors
        for error in errors:
            severity = error.get('severity', ValidationSeverity.MEDIUM.value)
            if severity == ValidationSeverity.CRITICAL.value:
                confidence *= 0.3
            elif severity == ValidationSeverity.HIGH.value:
                confidence *= 0.6
            elif severity == ValidationSeverity.MEDIUM.value:
                confidence *= 0.8
            else:
                confidence *= 0.9
        
        # Boost based on successful corrections
        for correction in corrections:
            correction_confidence = correction.get('confidence', 0.5)
            confidence = min(1.0, confidence + (correction_confidence * 0.1))
        
        return max(0.0, min(1.0, confidence))
    
    def _calculate_semantic_similarity(self, text1: str, text2: str) -> float:
        """Calculate semantic similarity between two texts"""
        # Simple similarity based on common words
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        if union == 0:
            return 0.0
        
        return intersection / union
    
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two coordinates"""
        import math
        
        R = 6371  # Earth's radius in km
        
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)
        
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    async def _apply_corrections(
        self,
        llm_response: Dict[str, Any],
        corrections: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Apply automatic corrections to LLM response"""
        corrected_data = llm_response.copy()
        
        for correction in corrections:
            correction_type = correction['type']
            
            if correction_type == 'service_code_correction':
                corrected_data['service_code'] = correction['suggestion']
            elif correction_type == 'zone_code_correction':
                corrected_data['zone_code'] = correction['suggestion']
        
        return corrected_data
    
    async def _log_validation_result(
        self,
        db: Session,
        validation_id: str,
        llm_response: Dict[str, Any],
        errors: List[Dict[str, Any]],
        corrections: List[Dict[str, Any]],
        confidence_score: float
    ) -> None:
        """Log validation results for analysis"""
        try:
            validation_log = ValidationLog(
                validation_id=validation_id,
                llm_response=json.dumps(llm_response),
                errors=json.dumps(errors),
                corrections=json.dumps(corrections),
                confidence_score=confidence_score,
                timestamp=datetime.utcnow()
            )
            
            db.add(validation_log)
            db.commit()
            
        except Exception as e:
            logger.error(f"Failed to log validation result: {e}")
    
    def _generate_validation_id(self) -> str:
        """Generate unique validation ID"""
        import uuid
        return str(uuid.uuid4())
    
    async def get_validation_metrics(self, db: Session) -> ValidationMetrics:
        """Get validation performance metrics"""
        try:
            # Get all validation logs
            logs = db.query(ValidationLog).all()
            
            if not logs:
                return ValidationMetrics(
                    total_validations=0,
                    success_rate=0.0,
                    error_distribution={},
                    avg_correction_time=0.0,
                    auto_correction_rate=0.0
                )
            
            # Calculate metrics
            total_validations = len(logs)
            successful_validations = sum(1 for log in logs if not json.loads(log.errors))
            success_rate = successful_validations / total_validations
            
            # Error distribution
            error_distribution = {}
            auto_corrections = 0
            
            for log in logs:
                errors = json.loads(log.errors)
                corrections = json.loads(log.corrections)
                
                if corrections:
                    auto_corrections += 1
                
                for error in errors:
                    error_type = error['type']
                    error_distribution[error_type] = error_distribution.get(error_type, 0) + 1
            
            auto_correction_rate = auto_corrections / total_validations
            
            return ValidationMetrics(
                total_validations=total_validations,
                success_rate=success_rate,
                error_distribution=error_distribution,
                avg_correction_time=0.0,  # TODO: Calculate from timing data
                auto_correction_rate=auto_correction_rate
            )
            
        except Exception as e:
            logger.error(f"Error calculating validation metrics: {e}")
            return ValidationMetrics(
                total_validations=0,
                success_rate=0.0,
                error_distribution={},
                avg_correction_time=0.0,
                auto_correction_rate=0.0
            )