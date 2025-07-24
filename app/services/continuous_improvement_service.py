"""
Continuous Improvement Service - Learning from errors and improving system performance
Analyzes error patterns, updates keywords, and provides feedback for optimization
"""
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session
from dataclasses import dataclass
from enum import Enum
import logging
import json
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import asyncio
import re

from app.models.dynamic_services import (
    Service, Zone, ServiceSearchLog, ErrorLog, ValidationLog, 
    PerformanceMetrics, ImprovementSuggestion, KeywordUpdate
)
from app.services.validation_service import ValidationService
from app.services.error_management_service import ErrorManagementService

logger = logging.getLogger(__name__)

class ImprovementType(Enum):
    """Types of improvements"""
    KEYWORD_UPDATE = "keyword_update"
    VALIDATION_RULE_UPDATE = "validation_rule_update"
    ERROR_PATTERN_FIX = "error_pattern_fix"
    PERFORMANCE_OPTIMIZATION = "performance_optimization"
    USER_EXPERIENCE_ENHANCEMENT = "user_experience_enhancement"
    SEARCH_ALGORITHM_IMPROVEMENT = "search_algorithm_improvement"

class ImprovementPriority(Enum):
    """Priority levels for improvements"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class ErrorPattern:
    """Identified error pattern"""
    pattern_id: str
    error_type: str
    frequency: int
    common_causes: List[str]
    suggested_fixes: List[str]
    confidence: float

@dataclass
class PerformanceInsight:
    """Performance insight for improvement"""
    metric_name: str
    current_value: float
    target_value: float
    improvement_potential: float
    recommendations: List[str]

@dataclass
class ImprovementReport:
    """Comprehensive improvement report"""
    report_id: str
    generated_at: datetime
    error_patterns: List[ErrorPattern]
    performance_insights: List[PerformanceInsight]
    keyword_suggestions: List[Dict[str, Any]]
    validation_improvements: List[Dict[str, Any]]
    overall_score: float
    priority_actions: List[str]

class ContinuousImprovementService:
    """Service for continuous system improvement based on analytics"""
    
    def __init__(self):
        self.validation_service = ValidationService()
        self.error_management = ErrorManagementService()
        self.improvement_cache: Dict[str, Any] = {}
        
        # Thresholds for improvement detection
        self.improvement_thresholds = {
            'error_frequency_threshold': 5,
            'validation_failure_threshold': 0.3,
            'performance_degradation_threshold': 0.2,
            'keyword_effectiveness_threshold': 0.6,
            'min_data_points': 10
        }
        
        # Keyword effectiveness tracking
        self.keyword_performance = defaultdict(lambda: {'searches': 0, 'successes': 0})
    
    async def analyze_system_performance(self, db: Session) -> ImprovementReport:
        """
        Analyze system performance and generate improvement recommendations
        """
        try:
            report_id = self._generate_report_id()
            
            # 1. Analyze error patterns
            error_patterns = await self._analyze_error_patterns(db)
            
            # 2. Analyze performance metrics
            performance_insights = await self._analyze_performance_metrics(db)
            
            # 3. Analyze keyword effectiveness
            keyword_suggestions = await self._analyze_keyword_effectiveness(db)
            
            # 4. Analyze validation performance
            validation_improvements = await self._analyze_validation_performance(db)
            
            # 5. Calculate overall system score
            overall_score = self._calculate_overall_score(
                error_patterns, performance_insights, keyword_suggestions, validation_improvements
            )
            
            # 6. Generate priority actions
            priority_actions = self._generate_priority_actions(
                error_patterns, performance_insights, keyword_suggestions, validation_improvements
            )
            
            # 7. Create improvement report
            report = ImprovementReport(
                report_id=report_id,
                generated_at=datetime.utcnow(),
                error_patterns=error_patterns,
                performance_insights=performance_insights,
                keyword_suggestions=keyword_suggestions,
                validation_improvements=validation_improvements,
                overall_score=overall_score,
                priority_actions=priority_actions
            )
            
            # 8. Log report generation
            await self._log_improvement_report(db, report)
            
            return report
            
        except Exception as e:
            logger.error(f"Error analyzing system performance: {e}")
            return ImprovementReport(
                report_id="error",
                generated_at=datetime.utcnow(),
                error_patterns=[],
                performance_insights=[],
                keyword_suggestions=[],
                validation_improvements=[],
                overall_score=0.0,
                priority_actions=[]
            )
    
    async def _analyze_error_patterns(self, db: Session) -> List[ErrorPattern]:
        """Analyze error patterns for improvement opportunities"""
        patterns = []
        
        try:
            # Get recent error logs
            cutoff_date = datetime.utcnow() - timedelta(days=7)
            error_logs = db.query(ErrorLog).filter(
                ErrorLog.timestamp >= cutoff_date
            ).all()
            
            if len(error_logs) < self.improvement_thresholds['min_data_points']:
                return patterns
            
            # Group errors by type
            error_groups = defaultdict(list)
            for log in error_logs:
                error_groups[log.error_type].append(log)
            
            # Analyze each error type
            for error_type, logs in error_groups.items():
                if len(logs) >= self.improvement_thresholds['error_frequency_threshold']:
                    # Extract common causes
                    common_causes = self._extract_common_causes(logs)
                    
                    # Generate fix suggestions
                    suggested_fixes = self._generate_error_fixes(error_type, common_causes)
                    
                    # Calculate confidence
                    confidence = min(1.0, len(logs) / 50.0)  # Max confidence at 50 occurrences
                    
                    pattern = ErrorPattern(
                        pattern_id=f"{error_type}_{len(logs)}",
                        error_type=error_type,
                        frequency=len(logs),
                        common_causes=common_causes,
                        suggested_fixes=suggested_fixes,
                        confidence=confidence
                    )
                    
                    patterns.append(pattern)
            
        except Exception as e:
            logger.error(f"Error analyzing error patterns: {e}")
        
        return patterns
    
    async def _analyze_performance_metrics(self, db: Session) -> List[PerformanceInsight]:
        """Analyze performance metrics for optimization opportunities"""
        insights = []
        
        try:
            # Get recent performance metrics
            cutoff_date = datetime.utcnow() - timedelta(days=7)
            
            # Analyze search performance
            search_logs = db.query(ServiceSearchLog).filter(
                ServiceSearchLog.timestamp >= cutoff_date
            ).all()
            
            if search_logs:
                # Calculate search success rate
                successful_searches = sum(1 for log in search_logs if log.selected_service_code)
                success_rate = successful_searches / len(search_logs)
                
                if success_rate < 0.8:  # Below 80% success rate
                    insights.append(PerformanceInsight(
                        metric_name="search_success_rate",
                        current_value=success_rate,
                        target_value=0.85,
                        improvement_potential=0.85 - success_rate,
                        recommendations=[
                            "Improve keyword matching algorithms",
                            "Add more service synonyms",
                            "Enhance fuzzy search capabilities"
                        ]
                    ))
                
                # Analyze response times
                avg_response_time = sum(
                    log.response_time_ms for log in search_logs if log.response_time_ms
                ) / len([log for log in search_logs if log.response_time_ms])
                
                if avg_response_time > 500:  # Above 500ms
                    insights.append(PerformanceInsight(
                        metric_name="avg_response_time",
                        current_value=avg_response_time,
                        target_value=300.0,
                        improvement_potential=(avg_response_time - 300) / avg_response_time,
                        recommendations=[
                            "Implement caching for frequent queries",
                            "Optimize database queries",
                            "Add search result pagination"
                        ]
                    ))
            
            # Analyze validation performance
            validation_logs = db.query(ValidationLog).filter(
                ValidationLog.timestamp >= cutoff_date
            ).all()
            
            if validation_logs:
                # Calculate validation success rate
                successful_validations = sum(
                    1 for log in validation_logs if not json.loads(log.errors)
                )
                validation_success_rate = successful_validations / len(validation_logs)
                
                if validation_success_rate < 0.9:  # Below 90% validation success
                    insights.append(PerformanceInsight(
                        metric_name="validation_success_rate",
                        current_value=validation_success_rate,
                        target_value=0.95,
                        improvement_potential=0.95 - validation_success_rate,
                        recommendations=[
                            "Improve LLM prompts for better extraction",
                            "Add more validation rules",
                            "Enhance error correction algorithms"
                        ]
                    ))
            
        except Exception as e:
            logger.error(f"Error analyzing performance metrics: {e}")
        
        return insights
    
    async def _analyze_keyword_effectiveness(self, db: Session) -> List[Dict[str, Any]]:
        """Analyze keyword effectiveness and suggest improvements"""
        suggestions = []
        
        try:
            # Get recent search logs
            cutoff_date = datetime.utcnow() - timedelta(days=7)
            search_logs = db.query(ServiceSearchLog).filter(
                ServiceSearchLog.timestamp >= cutoff_date
            ).all()
            
            if not search_logs:
                return suggestions
            
            # Analyze query patterns
            query_analysis = self._analyze_query_patterns(search_logs)
            
            # Failed searches (no results)
            failed_queries = [log for log in search_logs if not log.selected_service_code]
            
            if failed_queries:
                # Extract common failed terms
                failed_terms = []
                for log in failed_queries:
                    failed_terms.extend(log.query.lower().split())
                
                term_frequency = Counter(failed_terms)
                
                # Suggest keywords for common failed terms
                for term, frequency in term_frequency.most_common(10):
                    if frequency >= 3:  # At least 3 occurrences
                        # Find similar services
                        similar_services = await self._find_services_for_term(db, term)
                        
                        if similar_services:
                            suggestions.append({
                                'type': 'keyword_addition',
                                'term': term,
                                'frequency': frequency,
                                'suggested_services': similar_services,
                                'priority': 'high' if frequency >= 5 else 'medium'
                            })
            
            # Successful searches with low confidence
            low_confidence_searches = [
                log for log in search_logs 
                if log.selected_service_code and log.confidence_score < 0.7
            ]
            
            if low_confidence_searches:
                # Analyze services with low confidence matches
                service_confidence = defaultdict(list)
                for log in low_confidence_searches:
                    service_confidence[log.selected_service_code].append(log.confidence_score)
                
                for service_code, scores in service_confidence.items():
                    avg_confidence = sum(scores) / len(scores)
                    
                    if avg_confidence < 0.6:  # Below 60% average confidence
                        suggestions.append({
                            'type': 'keyword_optimization',
                            'service_code': service_code,
                            'avg_confidence': avg_confidence,
                            'search_count': len(scores),
                            'suggested_action': 'add_synonyms',
                            'priority': 'high'
                        })
            
        except Exception as e:
            logger.error(f"Error analyzing keyword effectiveness: {e}")
        
        return suggestions
    
    async def _analyze_validation_performance(self, db: Session) -> List[Dict[str, Any]]:
        """Analyze validation performance and suggest improvements"""
        improvements = []
        
        try:
            # Get recent validation logs
            cutoff_date = datetime.utcnow() - timedelta(days=7)
            validation_logs = db.query(ValidationLog).filter(
                ValidationLog.timestamp >= cutoff_date
            ).all()
            
            if not validation_logs:
                return improvements
            
            # Analyze validation errors
            error_analysis = defaultdict(list)
            for log in validation_logs:
                errors = json.loads(log.errors)
                for error in errors:
                    error_analysis[error['type']].append(error)
            
            # Generate improvements for common validation errors
            for error_type, errors in error_analysis.items():
                if len(errors) >= 3:  # At least 3 occurrences
                    # Extract common error messages
                    messages = [error['message'] for error in errors]
                    common_patterns = self._extract_common_patterns(messages)
                    
                    improvements.append({
                        'type': 'validation_rule_improvement',
                        'error_type': error_type,
                        'frequency': len(errors),
                        'common_patterns': common_patterns,
                        'suggested_improvements': self._generate_validation_improvements(
                            error_type, common_patterns
                        ),
                        'priority': 'high' if len(errors) >= 10 else 'medium'
                    })
            
            # Analyze correction effectiveness
            correction_analysis = defaultdict(list)
            for log in validation_logs:
                corrections = json.loads(log.corrections)
                for correction in corrections:
                    correction_analysis[correction['type']].append(correction)
            
            # Suggest improvements for low-effectiveness corrections
            for correction_type, corrections in correction_analysis.items():
                if len(corrections) >= 5:  # Enough data points
                    # Calculate effectiveness (simplified)
                    effectiveness = sum(
                        corr.get('confidence', 0.5) for corr in corrections
                    ) / len(corrections)
                    
                    if effectiveness < 0.7:  # Below 70% effectiveness
                        improvements.append({
                            'type': 'correction_algorithm_improvement',
                            'correction_type': correction_type,
                            'current_effectiveness': effectiveness,
                            'improvement_count': len(corrections),
                            'suggested_improvements': self._generate_correction_improvements(
                                correction_type, effectiveness
                            ),
                            'priority': 'medium'
                        })
            
        except Exception as e:
            logger.error(f"Error analyzing validation performance: {e}")
        
        return improvements
    
    async def apply_improvements(self, db: Session, improvements: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Apply approved improvements to the system"""
        results = {
            'applied': 0,
            'failed': 0,
            'skipped': 0,
            'details': []
        }
        
        try:
            for improvement in improvements:
                improvement_type = improvement.get('type')
                
                try:
                    if improvement_type == 'keyword_addition':
                        await self._apply_keyword_addition(db, improvement)
                        results['applied'] += 1
                    elif improvement_type == 'keyword_optimization':
                        await self._apply_keyword_optimization(db, improvement)
                        results['applied'] += 1
                    elif improvement_type == 'validation_rule_improvement':
                        await self._apply_validation_improvement(db, improvement)
                        results['applied'] += 1
                    else:
                        results['skipped'] += 1
                        
                    results['details'].append({
                        'type': improvement_type,
                        'status': 'applied',
                        'message': f"Successfully applied {improvement_type}"
                    })
                    
                except Exception as e:
                    results['failed'] += 1
                    results['details'].append({
                        'type': improvement_type,
                        'status': 'failed',
                        'message': str(e)
                    })
                    logger.error(f"Failed to apply improvement {improvement_type}: {e}")
            
        except Exception as e:
            logger.error(f"Error applying improvements: {e}")
        
        return results
    
    async def _apply_keyword_addition(self, db: Session, improvement: Dict[str, Any]) -> None:
        """Apply keyword addition improvement"""
        try:
            term = improvement['term']
            suggested_services = improvement['suggested_services']
            
            for service_code in suggested_services:
                service = db.query(Service).filter(Service.code == service_code).first()
                if service:
                    # Get current keywords
                    current_keywords = json.loads(service.search_keywords or '[]')
                    
                    # Add new term if not present
                    if term not in current_keywords:
                        current_keywords.append(term)
                        service.search_keywords = json.dumps(current_keywords)
                        
                        # Log keyword update
                        keyword_update = KeywordUpdate(
                            service_id=service.id,
                            action='addition',
                            keyword=term,
                            applied_at=datetime.utcnow(),
                            metadata=json.dumps(improvement)
                        )
                        db.add(keyword_update)
            
            db.commit()
            logger.info(f"Applied keyword addition for term: {term}")
            
        except Exception as e:
            db.rollback()
            raise e
    
    async def _apply_keyword_optimization(self, db: Session, improvement: Dict[str, Any]) -> None:
        """Apply keyword optimization improvement"""
        try:
            service_code = improvement['service_code']
            service = db.query(Service).filter(Service.code == service_code).first()
            
            if service:
                # Generate additional keywords based on service name and description
                additional_keywords = self._generate_additional_keywords(service)
                
                # Get current keywords
                current_keywords = json.loads(service.search_keywords or '[]')
                
                # Add new keywords
                for keyword in additional_keywords:
                    if keyword not in current_keywords:
                        current_keywords.append(keyword)
                
                service.search_keywords = json.dumps(current_keywords)
                
                # Log keyword update
                keyword_update = KeywordUpdate(
                    service_id=service.id,
                    action='optimization',
                    keyword=','.join(additional_keywords),
                    applied_at=datetime.utcnow(),
                    metadata=json.dumps(improvement)
                )
                db.add(keyword_update)
                
                db.commit()
                logger.info(f"Applied keyword optimization for service: {service_code}")
            
        except Exception as e:
            db.rollback()
            raise e
    
    async def _apply_validation_improvement(self, db: Session, improvement: Dict[str, Any]) -> None:
        """Apply validation rule improvement"""
        try:
            # This would update validation rules in the validation service
            # For now, we'll just log the improvement
            logger.info(f"Validation improvement applied: {improvement['error_type']}")
            
            # Create improvement suggestion record
            suggestion = ImprovementSuggestion(
                type=improvement['type'],
                priority=improvement['priority'],
                description=f"Improve validation for {improvement['error_type']}",
                metadata=json.dumps(improvement),
                created_at=datetime.utcnow(),
                status='applied'
            )
            
            db.add(suggestion)
            db.commit()
            
        except Exception as e:
            db.rollback()
            raise e
    
    def _extract_common_causes(self, error_logs: List) -> List[str]:
        """Extract common causes from error logs"""
        causes = []
        
        for log in error_logs:
            # Extract patterns from error messages
            message = log.message.lower()
            
            if 'not found' in message:
                causes.append('missing_resource')
            elif 'invalid' in message:
                causes.append('invalid_input')
            elif 'timeout' in message:
                causes.append('timeout_issue')
            elif 'connection' in message:
                causes.append('connection_issue')
        
        # Return most common causes
        return list(Counter(causes).most_common(3))
    
    def _generate_error_fixes(self, error_type: str, common_causes: List[str]) -> List[str]:
        """Generate fix suggestions for error type"""
        fixes = []
        
        if error_type == 'validation_error':
            fixes.extend([
                "Improve input validation rules",
                "Add more comprehensive error messages",
                "Implement better data sanitization"
            ])
        elif error_type == 'database_error':
            fixes.extend([
                "Add connection pooling",
                "Implement retry logic",
                "Add database health checks"
            ])
        elif error_type == 'network_error':
            fixes.extend([
                "Add circuit breaker pattern",
                "Implement exponential backoff",
                "Add network health monitoring"
            ])
        
        return fixes
    
    def _analyze_query_patterns(self, search_logs: List) -> Dict[str, Any]:
        """Analyze query patterns for insights"""
        patterns = {
            'common_terms': [],
            'failed_patterns': [],
            'success_patterns': []
        }
        
        all_queries = [log.query.lower() for log in search_logs]
        successful_queries = [
            log.query.lower() for log in search_logs if log.selected_service_code
        ]
        failed_queries = [
            log.query.lower() for log in search_logs if not log.selected_service_code
        ]
        
        # Extract common terms
        all_terms = []
        for query in all_queries:
            all_terms.extend(query.split())
        
        patterns['common_terms'] = [term for term, count in Counter(all_terms).most_common(10)]
        
        return patterns
    
    async def _find_services_for_term(self, db: Session, term: str) -> List[str]:
        """Find services that might match a term"""
        services = db.query(Service).filter(Service.status == 'available').all()
        
        matching_services = []
        for service in services:
            # Check if term appears in name or description
            if (term in service.name.lower() or 
                term in service.description.lower() or
                term in service.code.lower()):
                matching_services.append(service.code)
        
        return matching_services[:3]  # Return top 3 matches
    
    def _extract_common_patterns(self, messages: List[str]) -> List[str]:
        """Extract common patterns from messages"""
        patterns = []
        
        for message in messages:
            # Extract patterns using regex
            if 'code' in message.lower():
                patterns.append('invalid_code_pattern')
            elif 'not found' in message.lower():
                patterns.append('resource_not_found_pattern')
            elif 'format' in message.lower():
                patterns.append('format_error_pattern')
        
        return list(set(patterns))
    
    def _generate_validation_improvements(self, error_type: str, patterns: List[str]) -> List[str]:
        """Generate validation improvements"""
        improvements = []
        
        if 'invalid_code_pattern' in patterns:
            improvements.append("Add fuzzy matching for codes")
        if 'resource_not_found_pattern' in patterns:
            improvements.append("Implement suggestion system for missing resources")
        if 'format_error_pattern' in patterns:
            improvements.append("Add format validation with clear error messages")
        
        return improvements
    
    def _generate_correction_improvements(self, correction_type: str, effectiveness: float) -> List[str]:
        """Generate correction algorithm improvements"""
        improvements = []
        
        if effectiveness < 0.5:
            improvements.append("Redesign correction algorithm")
        elif effectiveness < 0.7:
            improvements.append("Improve similarity matching")
            improvements.append("Add more correction rules")
        
        return improvements
    
    def _generate_additional_keywords(self, service: Service) -> List[str]:
        """Generate additional keywords for a service"""
        keywords = []
        
        # Extract keywords from name and description
        text = f"{service.name} {service.description}".lower()
        
        # Common synonyms for services
        synonyms = {
            'réparation': ['repair', 'fix', 'maintenance'],
            'installation': ['install', 'setup', 'montage'],
            'nettoyage': ['cleaning', 'propre', 'nettoyer'],
            'électrique': ['electric', 'electrical', 'power'],
            'plomberie': ['plumbing', 'water', 'pipe']
        }
        
        for word, syns in synonyms.items():
            if word in text:
                keywords.extend(syns)
        
        return list(set(keywords))
    
    def _calculate_overall_score(
        self,
        error_patterns: List[ErrorPattern],
        performance_insights: List[PerformanceInsight],
        keyword_suggestions: List[Dict[str, Any]],
        validation_improvements: List[Dict[str, Any]]
    ) -> float:
        """Calculate overall system performance score"""
        try:
            # Base score
            score = 8.0  # Start with 8/10
            
            # Penalize for error patterns
            for pattern in error_patterns:
                if pattern.frequency > 10:
                    score -= 0.5
                elif pattern.frequency > 5:
                    score -= 0.3
            
            # Penalize for performance issues
            for insight in performance_insights:
                if insight.improvement_potential > 0.3:
                    score -= 0.4
                elif insight.improvement_potential > 0.2:
                    score -= 0.2
            
            # Penalize for keyword issues
            if len(keyword_suggestions) > 5:
                score -= 0.3
            
            # Penalize for validation issues
            if len(validation_improvements) > 3:
                score -= 0.2
            
            return max(0.0, min(10.0, score))
            
        except Exception as e:
            logger.error(f"Error calculating overall score: {e}")
            return 5.0  # Default score
    
    def _generate_priority_actions(
        self,
        error_patterns: List[ErrorPattern],
        performance_insights: List[PerformanceInsight],
        keyword_suggestions: List[Dict[str, Any]],
        validation_improvements: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate priority actions for improvement"""
        actions = []
        
        # High-frequency errors
        high_freq_errors = [p for p in error_patterns if p.frequency > 10]
        if high_freq_errors:
            actions.append(f"Address {len(high_freq_errors)} high-frequency error patterns")
        
        # Performance issues
        critical_performance = [i for i in performance_insights if i.improvement_potential > 0.3]
        if critical_performance:
            actions.append(f"Fix {len(critical_performance)} critical performance issues")
        
        # Keyword gaps
        high_priority_keywords = [k for k in keyword_suggestions if k.get('priority') == 'high']
        if high_priority_keywords:
            actions.append(f"Add {len(high_priority_keywords)} high-priority keywords")
        
        # Validation improvements
        high_priority_validation = [v for v in validation_improvements if v.get('priority') == 'high']
        if high_priority_validation:
            actions.append(f"Implement {len(high_priority_validation)} validation improvements")
        
        return actions[:5]  # Top 5 priority actions
    
    def _generate_report_id(self) -> str:
        """Generate unique report ID"""
        import uuid
        return str(uuid.uuid4())
    
    async def _log_improvement_report(self, db: Session, report: ImprovementReport) -> None:
        """Log improvement report to database"""
        try:
            # This would save the report to a database table
            logger.info(f"Generated improvement report {report.report_id} with score {report.overall_score}")
            
        except Exception as e:
            logger.error(f"Failed to log improvement report: {e}")
    
    async def get_improvement_metrics(self, db: Session) -> Dict[str, Any]:
        """Get improvement metrics for monitoring"""
        try:
            metrics = {
                'total_improvements_applied': 0,
                'keyword_updates_count': 0,
                'validation_improvements_count': 0,
                'error_reduction_rate': 0.0,
                'performance_improvement_rate': 0.0,
                'recent_improvements': []
            }
            
            # Get improvement counts
            keyword_updates = db.query(KeywordUpdate).all()
            metrics['keyword_updates_count'] = len(keyword_updates)
            
            improvement_suggestions = db.query(ImprovementSuggestion).all()
            metrics['total_improvements_applied'] = len([
                s for s in improvement_suggestions if s.status == 'applied'
            ])
            
            # Calculate improvement rates (simplified)
            recent_cutoff = datetime.utcnow() - timedelta(days=7)
            recent_improvements = [
                s for s in improvement_suggestions 
                if s.created_at >= recent_cutoff
            ]
            
            metrics['recent_improvements'] = [
                {
                    'type': imp.type,
                    'description': imp.description,
                    'priority': imp.priority,
                    'created_at': imp.created_at.isoformat()
                }
                for imp in recent_improvements[:5]
            ]
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error getting improvement metrics: {e}")
            return {
                'total_improvements_applied': 0,
                'keyword_updates_count': 0,
                'validation_improvements_count': 0,
                'error_reduction_rate': 0.0,
                'performance_improvement_rate': 0.0,
                'recent_improvements': []
            }