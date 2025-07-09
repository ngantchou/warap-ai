"""
Error Management Service - Comprehensive error handling with retry logic
Handles different error types, automatic retries, and escalation procedures
"""
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session
from dataclasses import dataclass
from enum import Enum
import logging
import json
from datetime import datetime, timedelta
import asyncio
from collections import defaultdict

from app.models.dynamic_services import ErrorLog, RetryAttempt, EscalationRecord
from app.services.validation_service import ValidationService
from app.services.suggestion_engine import SuggestionEngine

logger = logging.getLogger(__name__)

class ErrorType(Enum):
    """Types of errors in the system"""
    VALIDATION_ERROR = "validation_error"
    LLM_PROCESSING_ERROR = "llm_processing_error"
    DATABASE_ERROR = "database_error"
    NETWORK_ERROR = "network_error"
    TIMEOUT_ERROR = "timeout_error"
    AUTHENTICATION_ERROR = "authentication_error"
    RATE_LIMIT_ERROR = "rate_limit_error"
    RESOURCE_NOT_FOUND = "resource_not_found"
    PERMISSION_DENIED = "permission_denied"
    SYSTEM_ERROR = "system_error"

class ErrorSeverity(Enum):
    """Severity levels for errors"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class RetryStrategy(Enum):
    """Retry strategies for different error types"""
    IMMEDIATE = "immediate"
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    FIXED_INTERVAL = "fixed_interval"
    LINEAR_BACKOFF = "linear_backoff"
    NO_RETRY = "no_retry"

@dataclass
class ErrorContext:
    """Context information for error handling"""
    error_id: str
    error_type: ErrorType
    severity: ErrorSeverity
    message: str
    original_request: Dict[str, Any]
    timestamp: datetime
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = None

@dataclass
class RetryConfiguration:
    """Configuration for retry attempts"""
    strategy: RetryStrategy
    max_attempts: int
    base_delay: float
    max_delay: float
    backoff_multiplier: float
    should_retry: bool

@dataclass
class ErrorResolution:
    """Result of error handling"""
    resolved: bool
    resolution_method: str
    corrected_data: Optional[Dict[str, Any]]
    retry_needed: bool
    escalation_needed: bool
    suggestions: List[Dict[str, Any]]

class ErrorManagementService:
    """Service for comprehensive error management with intelligent retry logic"""
    
    def __init__(self):
        self.validation_service = ValidationService()
        self.suggestion_engine = SuggestionEngine()
        self.active_retries: Dict[str, int] = {}
        self.escalation_threshold = 3
        
        # Error type configurations
        self.error_configurations = {
            ErrorType.VALIDATION_ERROR: RetryConfiguration(
                strategy=RetryStrategy.IMMEDIATE,
                max_attempts=2,
                base_delay=0.5,
                max_delay=2.0,
                backoff_multiplier=1.0,
                should_retry=True
            ),
            ErrorType.LLM_PROCESSING_ERROR: RetryConfiguration(
                strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
                max_attempts=3,
                base_delay=1.0,
                max_delay=10.0,
                backoff_multiplier=2.0,
                should_retry=True
            ),
            ErrorType.DATABASE_ERROR: RetryConfiguration(
                strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
                max_attempts=3,
                base_delay=2.0,
                max_delay=20.0,
                backoff_multiplier=2.0,
                should_retry=True
            ),
            ErrorType.NETWORK_ERROR: RetryConfiguration(
                strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
                max_attempts=5,
                base_delay=1.0,
                max_delay=30.0,
                backoff_multiplier=2.0,
                should_retry=True
            ),
            ErrorType.TIMEOUT_ERROR: RetryConfiguration(
                strategy=RetryStrategy.LINEAR_BACKOFF,
                max_attempts=3,
                base_delay=5.0,
                max_delay=15.0,
                backoff_multiplier=1.5,
                should_retry=True
            ),
            ErrorType.RATE_LIMIT_ERROR: RetryConfiguration(
                strategy=RetryStrategy.FIXED_INTERVAL,
                max_attempts=5,
                base_delay=60.0,
                max_delay=300.0,
                backoff_multiplier=1.0,
                should_retry=True
            ),
            ErrorType.AUTHENTICATION_ERROR: RetryConfiguration(
                strategy=RetryStrategy.NO_RETRY,
                max_attempts=0,
                base_delay=0.0,
                max_delay=0.0,
                backoff_multiplier=1.0,
                should_retry=False
            ),
            ErrorType.SYSTEM_ERROR: RetryConfiguration(
                strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
                max_attempts=2,
                base_delay=5.0,
                max_delay=30.0,
                backoff_multiplier=3.0,
                should_retry=True
            )
        }
    
    async def handle_error(
        self,
        db: Session,
        error: Exception,
        context: Dict[str, Any],
        error_type: Optional[ErrorType] = None
    ) -> ErrorResolution:
        """
        Handle error with appropriate strategy based on error type
        """
        try:
            # Create error context
            error_context = self._create_error_context(error, context, error_type)
            
            # Log error
            await self._log_error(db, error_context)
            
            # Determine error handling strategy
            strategy = self._determine_error_strategy(error_context)
            
            # Handle based on error type
            if error_context.error_type == ErrorType.VALIDATION_ERROR:
                return await self._handle_validation_error(db, error_context, strategy)
            elif error_context.error_type == ErrorType.LLM_PROCESSING_ERROR:
                return await self._handle_llm_error(db, error_context, strategy)
            elif error_context.error_type == ErrorType.DATABASE_ERROR:
                return await self._handle_database_error(db, error_context, strategy)
            elif error_context.error_type == ErrorType.NETWORK_ERROR:
                return await self._handle_network_error(db, error_context, strategy)
            elif error_context.error_type == ErrorType.TIMEOUT_ERROR:
                return await self._handle_timeout_error(db, error_context, strategy)
            elif error_context.error_type == ErrorType.RATE_LIMIT_ERROR:
                return await self._handle_rate_limit_error(db, error_context, strategy)
            else:
                return await self._handle_generic_error(db, error_context, strategy)
            
        except Exception as e:
            logger.error(f"Error in error handling: {e}")
            return ErrorResolution(
                resolved=False,
                resolution_method="error_handler_failure",
                corrected_data=None,
                retry_needed=False,
                escalation_needed=True,
                suggestions=[]
            )
    
    async def _handle_validation_error(
        self,
        db: Session,
        error_context: ErrorContext,
        strategy: RetryConfiguration
    ) -> ErrorResolution:
        """Handle validation errors with correction attempts"""
        try:
            # Attempt to validate and correct the data
            original_data = error_context.original_request
            
            # Re-run validation with correction
            validation_result = await self.validation_service.validate_llm_response(
                db, original_data, original_data.get('query', ''), error_context.metadata
            )
            
            if validation_result.corrected_data:
                return ErrorResolution(
                    resolved=True,
                    resolution_method="automatic_correction",
                    corrected_data=validation_result.corrected_data,
                    retry_needed=False,
                    escalation_needed=False,
                    suggestions=[]
                )
            
            # If correction failed, generate suggestions
            suggestions = validation_result.suggestions
            
            # Check if retry is needed
            retry_needed = strategy.should_retry and self._should_retry(error_context.error_id, strategy)
            
            return ErrorResolution(
                resolved=False,
                resolution_method="validation_failed",
                corrected_data=None,
                retry_needed=retry_needed,
                escalation_needed=not retry_needed,
                suggestions=suggestions
            )
            
        except Exception as e:
            logger.error(f"Error handling validation error: {e}")
            return self._create_failure_resolution()
    
    async def _handle_llm_error(
        self,
        db: Session,
        error_context: ErrorContext,
        strategy: RetryConfiguration
    ) -> ErrorResolution:
        """Handle LLM processing errors"""
        try:
            # Check if retry is appropriate
            retry_needed = strategy.should_retry and self._should_retry(error_context.error_id, strategy)
            
            if retry_needed:
                # Modify request for retry
                modified_request = self._modify_request_for_llm_retry(
                    error_context.original_request,
                    error_context.message
                )
                
                return ErrorResolution(
                    resolved=False,
                    resolution_method="llm_retry_prepared",
                    corrected_data=modified_request,
                    retry_needed=True,
                    escalation_needed=False,
                    suggestions=[]
                )
            
            # Generate alternative suggestions
            suggestions = await self._generate_llm_alternatives(db, error_context)
            
            return ErrorResolution(
                resolved=False,
                resolution_method="llm_alternatives_generated",
                corrected_data=None,
                retry_needed=False,
                escalation_needed=True,
                suggestions=suggestions
            )
            
        except Exception as e:
            logger.error(f"Error handling LLM error: {e}")
            return self._create_failure_resolution()
    
    async def _handle_database_error(
        self,
        db: Session,
        error_context: ErrorContext,
        strategy: RetryConfiguration
    ) -> ErrorResolution:
        """Handle database errors with connection recovery"""
        try:
            # Check if it's a connection error
            if "connection" in error_context.message.lower():
                # Attempt to reconnect
                await self._attempt_database_reconnection(db)
                
                return ErrorResolution(
                    resolved=False,
                    resolution_method="database_reconnection_attempted",
                    corrected_data=None,
                    retry_needed=strategy.should_retry,
                    escalation_needed=False,
                    suggestions=[]
                )
            
            # For other database errors, check if retry is appropriate
            retry_needed = strategy.should_retry and self._should_retry(error_context.error_id, strategy)
            
            return ErrorResolution(
                resolved=False,
                resolution_method="database_error_logged",
                corrected_data=None,
                retry_needed=retry_needed,
                escalation_needed=not retry_needed,
                suggestions=[]
            )
            
        except Exception as e:
            logger.error(f"Error handling database error: {e}")
            return self._create_failure_resolution()
    
    async def _handle_network_error(
        self,
        db: Session,
        error_context: ErrorContext,
        strategy: RetryConfiguration
    ) -> ErrorResolution:
        """Handle network errors with retry logic"""
        try:
            # Check network connectivity
            network_status = await self._check_network_connectivity()
            
            if network_status:
                # Network is available, retry is appropriate
                retry_needed = strategy.should_retry and self._should_retry(error_context.error_id, strategy)
                
                return ErrorResolution(
                    resolved=False,
                    resolution_method="network_retry_scheduled",
                    corrected_data=None,
                    retry_needed=retry_needed,
                    escalation_needed=False,
                    suggestions=[]
                )
            else:
                # Network is down, escalate immediately
                return ErrorResolution(
                    resolved=False,
                    resolution_method="network_connectivity_lost",
                    corrected_data=None,
                    retry_needed=False,
                    escalation_needed=True,
                    suggestions=[]
                )
            
        except Exception as e:
            logger.error(f"Error handling network error: {e}")
            return self._create_failure_resolution()
    
    async def _handle_timeout_error(
        self,
        db: Session,
        error_context: ErrorContext,
        strategy: RetryConfiguration
    ) -> ErrorResolution:
        """Handle timeout errors with extended timeout"""
        try:
            # Increase timeout for retry
            modified_request = error_context.original_request.copy()
            current_timeout = modified_request.get('timeout', 30)
            modified_request['timeout'] = min(current_timeout * 2, 120)  # Max 2 minutes
            
            retry_needed = strategy.should_retry and self._should_retry(error_context.error_id, strategy)
            
            return ErrorResolution(
                resolved=False,
                resolution_method="timeout_extended",
                corrected_data=modified_request,
                retry_needed=retry_needed,
                escalation_needed=not retry_needed,
                suggestions=[]
            )
            
        except Exception as e:
            logger.error(f"Error handling timeout error: {e}")
            return self._create_failure_resolution()
    
    async def _handle_rate_limit_error(
        self,
        db: Session,
        error_context: ErrorContext,
        strategy: RetryConfiguration
    ) -> ErrorResolution:
        """Handle rate limit errors with backoff"""
        try:
            # Calculate backoff time
            backoff_time = self._calculate_rate_limit_backoff(error_context)
            
            # Schedule retry after backoff
            retry_needed = strategy.should_retry and self._should_retry(error_context.error_id, strategy)
            
            return ErrorResolution(
                resolved=False,
                resolution_method="rate_limit_backoff",
                corrected_data={"retry_after": backoff_time},
                retry_needed=retry_needed,
                escalation_needed=False,
                suggestions=[]
            )
            
        except Exception as e:
            logger.error(f"Error handling rate limit error: {e}")
            return self._create_failure_resolution()
    
    async def _handle_generic_error(
        self,
        db: Session,
        error_context: ErrorContext,
        strategy: RetryConfiguration
    ) -> ErrorResolution:
        """Handle generic errors"""
        try:
            retry_needed = strategy.should_retry and self._should_retry(error_context.error_id, strategy)
            
            return ErrorResolution(
                resolved=False,
                resolution_method="generic_error_logged",
                corrected_data=None,
                retry_needed=retry_needed,
                escalation_needed=not retry_needed,
                suggestions=[]
            )
            
        except Exception as e:
            logger.error(f"Error handling generic error: {e}")
            return self._create_failure_resolution()
    
    async def retry_operation(
        self,
        db: Session,
        error_context: ErrorContext,
        operation_func,
        *args,
        **kwargs
    ) -> Tuple[bool, Any]:
        """
        Retry an operation with exponential backoff
        """
        try:
            strategy = self.error_configurations.get(
                error_context.error_type,
                self.error_configurations[ErrorType.SYSTEM_ERROR]
            )
            
            for attempt in range(strategy.max_attempts):
                try:
                    # Log retry attempt
                    await self._log_retry_attempt(db, error_context.error_id, attempt + 1)
                    
                    # Execute operation
                    result = await operation_func(*args, **kwargs)
                    
                    # Success
                    logger.info(f"Operation succeeded on attempt {attempt + 1}")
                    return True, result
                    
                except Exception as e:
                    # Calculate delay
                    delay = self._calculate_retry_delay(strategy, attempt)
                    
                    logger.warning(f"Operation failed on attempt {attempt + 1}: {e}")
                    
                    # Wait before retry (except for last attempt)
                    if attempt < strategy.max_attempts - 1:
                        await asyncio.sleep(delay)
                    else:
                        # All attempts failed
                        await self._handle_retry_exhaustion(db, error_context, e)
                        return False, None
            
            return False, None
            
        except Exception as e:
            logger.error(f"Error in retry operation: {e}")
            return False, None
    
    def _create_error_context(
        self,
        error: Exception,
        context: Dict[str, Any],
        error_type: Optional[ErrorType] = None
    ) -> ErrorContext:
        """Create error context from exception and context"""
        import uuid
        
        # Determine error type if not provided
        if error_type is None:
            error_type = self._classify_error(error)
        
        # Determine severity
        severity = self._determine_error_severity(error, error_type)
        
        return ErrorContext(
            error_id=str(uuid.uuid4()),
            error_type=error_type,
            severity=severity,
            message=str(error),
            original_request=context.get('original_request', {}),
            timestamp=datetime.utcnow(),
            user_id=context.get('user_id'),
            session_id=context.get('session_id'),
            metadata=context.get('metadata', {})
        )
    
    def _classify_error(self, error: Exception) -> ErrorType:
        """Classify error based on exception type and message"""
        error_message = str(error).lower()
        
        if "validation" in error_message:
            return ErrorType.VALIDATION_ERROR
        elif "database" in error_message or "sql" in error_message:
            return ErrorType.DATABASE_ERROR
        elif "network" in error_message or "connection" in error_message:
            return ErrorType.NETWORK_ERROR
        elif "timeout" in error_message:
            return ErrorType.TIMEOUT_ERROR
        elif "rate limit" in error_message:
            return ErrorType.RATE_LIMIT_ERROR
        elif "auth" in error_message or "permission" in error_message:
            return ErrorType.AUTHENTICATION_ERROR
        elif "not found" in error_message:
            return ErrorType.RESOURCE_NOT_FOUND
        else:
            return ErrorType.SYSTEM_ERROR
    
    def _determine_error_severity(self, error: Exception, error_type: ErrorType) -> ErrorSeverity:
        """Determine error severity based on type and context"""
        critical_types = [ErrorType.SYSTEM_ERROR, ErrorType.DATABASE_ERROR]
        high_types = [ErrorType.AUTHENTICATION_ERROR, ErrorType.NETWORK_ERROR]
        medium_types = [ErrorType.VALIDATION_ERROR, ErrorType.LLM_PROCESSING_ERROR]
        
        if error_type in critical_types:
            return ErrorSeverity.CRITICAL
        elif error_type in high_types:
            return ErrorSeverity.HIGH
        elif error_type in medium_types:
            return ErrorSeverity.MEDIUM
        else:
            return ErrorSeverity.LOW
    
    def _determine_error_strategy(self, error_context: ErrorContext) -> RetryConfiguration:
        """Determine retry strategy based on error context"""
        return self.error_configurations.get(
            error_context.error_type,
            self.error_configurations[ErrorType.SYSTEM_ERROR]
        )
    
    def _should_retry(self, error_id: str, strategy: RetryConfiguration) -> bool:
        """Check if error should be retried"""
        current_attempts = self.active_retries.get(error_id, 0)
        return current_attempts < strategy.max_attempts
    
    def _calculate_retry_delay(self, strategy: RetryConfiguration, attempt: int) -> float:
        """Calculate delay for retry attempt"""
        if strategy.strategy == RetryStrategy.IMMEDIATE:
            return 0.0
        elif strategy.strategy == RetryStrategy.FIXED_INTERVAL:
            return strategy.base_delay
        elif strategy.strategy == RetryStrategy.LINEAR_BACKOFF:
            return min(strategy.base_delay * (attempt + 1), strategy.max_delay)
        elif strategy.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            return min(
                strategy.base_delay * (strategy.backoff_multiplier ** attempt),
                strategy.max_delay
            )
        else:
            return strategy.base_delay
    
    def _calculate_rate_limit_backoff(self, error_context: ErrorContext) -> float:
        """Calculate backoff time for rate limit errors"""
        # Extract retry-after from error message if available
        import re
        retry_after_match = re.search(r'retry[_\s]after[:\s](\d+)', error_context.message.lower())
        
        if retry_after_match:
            return float(retry_after_match.group(1))
        
        # Default backoff
        return 60.0  # 1 minute
    
    def _modify_request_for_llm_retry(
        self,
        original_request: Dict[str, Any],
        error_message: str
    ) -> Dict[str, Any]:
        """Modify request for LLM retry"""
        modified_request = original_request.copy()
        
        # Add error context to prompt
        modified_request['error_context'] = f"Previous attempt failed: {error_message}"
        
        # Reduce complexity or add constraints
        if 'max_tokens' in modified_request:
            modified_request['max_tokens'] = min(modified_request['max_tokens'], 1000)
        
        return modified_request
    
    async def _generate_llm_alternatives(
        self,
        db: Session,
        error_context: ErrorContext
    ) -> List[Dict[str, Any]]:
        """Generate alternative suggestions for LLM failures"""
        suggestions = []
        
        try:
            # Use suggestion engine to generate alternatives
            query = error_context.original_request.get('query', '')
            zone_code = error_context.original_request.get('zone_code')
            
            suggestion_response = await self.suggestion_engine.generate_suggestions(
                db, query, zone_code
            )
            
            for suggestion in suggestion_response.suggestions[:3]:
                suggestions.append({
                    'type': 'llm_alternative',
                    'title': suggestion.title,
                    'description': suggestion.description,
                    'confidence': suggestion.confidence
                })
            
        except Exception as e:
            logger.error(f"Error generating LLM alternatives: {e}")
        
        return suggestions
    
    async def _check_network_connectivity(self) -> bool:
        """Check network connectivity"""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get('https://httpbin.org/status/200', timeout=5) as response:
                    return response.status == 200
        except:
            return False
    
    async def _attempt_database_reconnection(self, db: Session) -> bool:
        """Attempt to reconnect to database"""
        try:
            # Test database connection
            db.execute("SELECT 1")
            return True
        except:
            return False
    
    def _create_failure_resolution(self) -> ErrorResolution:
        """Create failure resolution"""
        return ErrorResolution(
            resolved=False,
            resolution_method="error_handler_failure",
            corrected_data=None,
            retry_needed=False,
            escalation_needed=True,
            suggestions=[]
        )
    
    async def _log_error(self, db: Session, error_context: ErrorContext) -> None:
        """Log error to database"""
        try:
            error_log = ErrorLog(
                error_id=error_context.error_id,
                error_type=error_context.error_type.value,
                severity=error_context.severity.value,
                message=error_context.message,
                original_request=json.dumps(error_context.original_request),
                user_id=error_context.user_id,
                session_id=error_context.session_id,
                metadata=json.dumps(error_context.metadata or {}),
                timestamp=error_context.timestamp
            )
            
            db.add(error_log)
            db.commit()
            
        except Exception as e:
            logger.error(f"Failed to log error: {e}")
    
    async def _log_retry_attempt(self, db: Session, error_id: str, attempt: int) -> None:
        """Log retry attempt"""
        try:
            retry_log = RetryAttempt(
                error_id=error_id,
                attempt_number=attempt,
                timestamp=datetime.utcnow()
            )
            
            db.add(retry_log)
            db.commit()
            
            # Update active retries
            self.active_retries[error_id] = attempt
            
        except Exception as e:
            logger.error(f"Failed to log retry attempt: {e}")
    
    async def _handle_retry_exhaustion(
        self,
        db: Session,
        error_context: ErrorContext,
        final_error: Exception
    ) -> None:
        """Handle exhaustion of retry attempts"""
        try:
            # Log escalation
            escalation_record = EscalationRecord(
                error_id=error_context.error_id,
                escalation_reason="retry_exhaustion",
                final_error=str(final_error),
                timestamp=datetime.utcnow()
            )
            
            db.add(escalation_record)
            db.commit()
            
            # Clean up active retries
            self.active_retries.pop(error_context.error_id, None)
            
            logger.critical(f"Retry exhaustion for error {error_context.error_id}: {final_error}")
            
        except Exception as e:
            logger.error(f"Failed to handle retry exhaustion: {e}")
    
    async def get_error_statistics(self, db: Session) -> Dict[str, Any]:
        """Get error statistics for monitoring"""
        try:
            # Get error distribution
            error_logs = db.query(ErrorLog).all()
            
            error_stats = {
                'total_errors': len(error_logs),
                'error_distribution': {},
                'severity_distribution': {},
                'recent_errors': 0,
                'resolution_rate': 0.0
            }
            
            if error_logs:
                # Calculate distributions
                for log in error_logs:
                    error_stats['error_distribution'][log.error_type] = \
                        error_stats['error_distribution'].get(log.error_type, 0) + 1
                    
                    error_stats['severity_distribution'][log.severity] = \
                        error_stats['severity_distribution'].get(log.severity, 0) + 1
                
                # Recent errors (last 24 hours)
                recent_cutoff = datetime.utcnow() - timedelta(hours=24)
                error_stats['recent_errors'] = sum(
                    1 for log in error_logs if log.timestamp >= recent_cutoff
                )
                
                # Resolution rate (simplified)
                resolved_count = sum(1 for log in error_logs if log.severity != 'critical')
                error_stats['resolution_rate'] = resolved_count / len(error_logs)
            
            return error_stats
            
        except Exception as e:
            logger.error(f"Error getting error statistics: {e}")
            return {
                'total_errors': 0,
                'error_distribution': {},
                'severity_distribution': {},
                'recent_errors': 0,
                'resolution_rate': 0.0
            }