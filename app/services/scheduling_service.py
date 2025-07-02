"""
Scheduling service for flexible time slot management and enhanced location recognition.
Handles appointment booking, provider availability, and landmark-based location matching.
"""

from datetime import datetime, date, time, timedelta
from typing import List, Dict, Optional, Tuple, Any
from enum import Enum
import pytz
from loguru import logger
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from app.models.database_models import (
    ServiceRequest, Provider, ProviderAvailability, AppointmentSlot, 
    Landmark, LocationMatch
)

# West Africa Time (Cameroon timezone)
WAT = pytz.timezone('Africa/Douala')

class SchedulingPreference(str, Enum):
    """Time slot preference options"""
    URGENT = "URGENT"  # Dans l'heure (supplément +2,000 XAF)
    TODAY = "TODAY"  # Aujourd'hui entre 9h-17h
    TOMORROW_MORNING = "TOMORROW_MORNING"  # Demain matin (8h-12h)
    TOMORROW_AFTERNOON = "TOMORROW_AFTERNOON"  # Demain après-midi (13h-17h)
    THIS_WEEK = "THIS_WEEK"  # Cette semaine, heure flexible
    WEEKEND = "WEEKEND"  # Weekend (samedi/dimanche)

class SchedulingService:
    """Service for handling appointment scheduling and location recognition"""
    
    def __init__(self, db: Session):
        self.db = db
        
        # Pricing supplements for urgency
        self.urgency_supplements = {
            SchedulingPreference.URGENT: 2000.0,  # +2,000 XAF for urgent requests
            SchedulingPreference.TODAY: 500.0,    # Small supplement for same-day
            SchedulingPreference.TOMORROW_MORNING: 0.0,
            SchedulingPreference.TOMORROW_AFTERNOON: 0.0,
            SchedulingPreference.THIS_WEEK: 0.0,
            SchedulingPreference.WEEKEND: 300.0,  # Weekend supplement
        }
        
        # Working hours configuration
        self.standard_working_hours = {
            'start': time(8, 0),  # 8:00 AM
            'end': time(17, 0),   # 5:00 PM
        }
    
    def get_scheduling_options(self, service_type: str, location: str) -> Dict[str, Any]:
        """Get available scheduling options for a service request"""
        
        now_wat = datetime.now(WAT)
        options = {}
        
        # Calculate time slots
        for preference in SchedulingPreference:
            slot_info = self._calculate_time_slot(preference, now_wat, service_type)
            if slot_info:
                options[preference.value] = {
                    'label': self._get_time_slot_label(preference),
                    'start_time': slot_info['start_time'],
                    'end_time': slot_info['end_time'],
                    'supplement': self.urgency_supplements.get(preference, 0.0),
                    'available': slot_info['available']
                }
        
        return options
    
    def _calculate_time_slot(self, preference: SchedulingPreference, 
                           base_time: datetime, service_type: str) -> Optional[Dict[str, Any]]:
        """Calculate specific time slot based on preference"""
        
        try:
            if preference == SchedulingPreference.URGENT:
                # Within the next hour
                start_time = base_time + timedelta(minutes=30)
                end_time = start_time + timedelta(hours=2)  # 2-hour window
                
            elif preference == SchedulingPreference.TODAY:
                # Today between 9h-17h
                today = base_time.date()
                start_time = datetime.combine(today, time(9, 0), WAT)
                end_time = datetime.combine(today, time(17, 0), WAT)
                
                # If it's already past 3 PM, not available today
                if base_time.hour >= 15:
                    return None
                    
            elif preference == SchedulingPreference.TOMORROW_MORNING:
                # Tomorrow morning (8h-12h)
                tomorrow = base_time.date() + timedelta(days=1)
                start_time = datetime.combine(tomorrow, time(8, 0), WAT)
                end_time = datetime.combine(tomorrow, time(12, 0), WAT)
                
            elif preference == SchedulingPreference.TOMORROW_AFTERNOON:
                # Tomorrow afternoon (13h-17h)
                tomorrow = base_time.date() + timedelta(days=1)
                start_time = datetime.combine(tomorrow, time(13, 0), WAT)
                end_time = datetime.combine(tomorrow, time(17, 0), WAT)
                
            elif preference == SchedulingPreference.THIS_WEEK:
                # This week, flexible hours
                days_ahead = 7 - base_time.weekday()  # Days until next Monday
                week_end = base_time.date() + timedelta(days=days_ahead)
                start_time = base_time + timedelta(hours=4)  # Starting in 4 hours
                end_time = datetime.combine(week_end, time(17, 0), WAT)
                
            elif preference == SchedulingPreference.WEEKEND:
                # Next weekend (Saturday/Sunday)
                days_until_saturday = 5 - base_time.weekday()  # Saturday = 5
                if days_until_saturday <= 0:
                    days_until_saturday += 7  # Next Saturday
                    
                saturday = base_time.date() + timedelta(days=days_until_saturday)
                start_time = datetime.combine(saturday, time(8, 0), WAT)
                end_time = datetime.combine(saturday + timedelta(days=1), time(17, 0), WAT)
            
            else:
                return None
            
            return {
                'start_time': start_time,
                'end_time': end_time,
                'available': True  # TODO: Check provider availability
            }
            
        except Exception as e:
            logger.error(f"Error calculating time slot for {preference}: {e}")
            return None
    
    def _get_time_slot_label(self, preference: SchedulingPreference) -> str:
        """Get user-friendly label for time slot preference"""
        
        labels = {
            SchedulingPreference.URGENT: "Dans l'heure (supplément +2,000 XAF)",
            SchedulingPreference.TODAY: "Aujourd'hui entre 9h-17h",
            SchedulingPreference.TOMORROW_MORNING: "Demain matin (8h-12h)",
            SchedulingPreference.TOMORROW_AFTERNOON: "Demain après-midi (13h-17h)",
            SchedulingPreference.THIS_WEEK: "Cette semaine, heure flexible",
            SchedulingPreference.WEEKEND: "Weekend (samedi/dimanche)"
        }
        
        return labels.get(preference, preference.value)
    
    def update_request_scheduling(self, request: ServiceRequest, 
                                scheduling_preference: str, 
                                preferred_time_start: Optional[datetime] = None,
                                preferred_time_end: Optional[datetime] = None) -> None:
        """Update service request with scheduling preferences"""
        
        try:
            request.scheduling_preference = scheduling_preference
            
            if preferred_time_start:
                request.preferred_time_start = preferred_time_start
            if preferred_time_end:
                request.preferred_time_end = preferred_time_end
            
            # Calculate urgency supplement
            preference_enum = SchedulingPreference(scheduling_preference)
            supplement = self.urgency_supplements.get(preference_enum, 0.0)
            request.urgency_supplement = supplement
            
            # Update urgency level
            if preference_enum == SchedulingPreference.URGENT:
                request.urgency = "urgent"
            elif preference_enum in [SchedulingPreference.TODAY, SchedulingPreference.TOMORROW_MORNING]:
                request.urgency = "normal"
            else:
                request.urgency = "flexible"
            
            self.db.commit()
            logger.info(f"Updated request {request.id} with scheduling: {scheduling_preference}")
            
        except Exception as e:
            logger.error(f"Error updating request scheduling: {e}")
            self.db.rollback()
            raise
    
    def find_landmark_matches(self, location_text: str, area: str = "Bonamoussadi") -> List[Dict[str, Any]]:
        """Find matching landmarks based on user location description"""
        
        try:
            # Normalize input text
            location_lower = location_text.lower().strip()
            
            # Search for landmarks
            landmarks = self.db.query(Landmark).filter(
                and_(
                    Landmark.is_active == True,
                    Landmark.area.ilike(f"%{area}%"),
                    or_(
                        Landmark.name.ilike(f"%{location_lower}%"),
                        func.json_extract(Landmark.aliases, '$').contains(location_lower),
                        func.json_extract(Landmark.common_references, '$').contains(location_lower)
                    )
                )
            ).limit(5).all()
            
            matches = []
            for landmark in landmarks:
                confidence = self._calculate_location_confidence(location_text, landmark)
                
                matches.append({
                    'landmark_id': landmark.id,
                    'name': landmark.name,
                    'type': landmark.landmark_type,
                    'area': landmark.area,
                    'coordinates': landmark.coordinates,
                    'confidence': confidence,
                    'aliases': landmark.aliases or [],
                    'common_references': landmark.common_references or []
                })
            
            # Sort by confidence score
            matches.sort(key=lambda x: x['confidence'], reverse=True)
            
            return matches
            
        except Exception as e:
            logger.error(f"Error finding landmark matches: {e}")
            return []
    
    def _calculate_location_confidence(self, user_input: str, landmark: Landmark) -> float:
        """Calculate confidence score for location match"""
        
        user_lower = user_input.lower()
        landmark_name = landmark.name.lower()
        
        # Direct name match
        if landmark_name in user_lower or user_lower in landmark_name:
            return 0.9
        
        # Check aliases
        if landmark.aliases:
            for alias in landmark.aliases:
                if alias.lower() in user_lower:
                    return 0.8
        
        # Check common references
        if landmark.common_references:
            for ref in landmark.common_references:
                if ref.lower() in user_lower:
                    return 0.7
        
        # Fuzzy matching for partial matches
        common_words = set(user_lower.split()) & set(landmark_name.split())
        if common_words:
            return 0.6
        
        return 0.1
    
    def confirm_location_match(self, request: ServiceRequest, landmark_id: int, 
                              user_confirmed: bool = True) -> None:
        """Confirm and store successful location match"""
        
        try:
            landmark = self.db.query(Landmark).filter(Landmark.id == landmark_id).first()
            if not landmark:
                logger.warning(f"Landmark {landmark_id} not found")
                return
            
            # Update request location details
            request.landmark_references = landmark.name
            request.location_confirmed = user_confirmed
            request.location_coordinates = landmark.coordinates
            request.location_accuracy = "exact" if user_confirmed else "approximate"
            
            # Create location match record for learning
            location_match = LocationMatch(
                user_input=request.location,
                matched_location=landmark.name,
                landmark_id=landmark_id,
                confidence_score=0.9 if user_confirmed else 0.7,
                service_request_id=request.id,
                user_confirmed=user_confirmed
            )
            
            self.db.add(location_match)
            self.db.commit()
            
            logger.info(f"Confirmed location match for request {request.id}: {landmark.name}")
            
        except Exception as e:
            logger.error(f"Error confirming location match: {e}")
            self.db.rollback()
            raise
    
    def get_provider_availability(self, provider_id: int, 
                                 start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """Get provider availability for date range"""
        
        try:
            availability = self.db.query(ProviderAvailability).filter(
                and_(
                    ProviderAvailability.provider_id == provider_id,
                    ProviderAvailability.is_active == True,
                    or_(
                        ProviderAvailability.effective_from.is_(None),
                        ProviderAvailability.effective_from <= start_date
                    ),
                    or_(
                        ProviderAvailability.effective_until.is_(None),
                        ProviderAvailability.effective_until >= end_date
                    )
                )
            ).all()
            
            availability_list = []
            for avail in availability:
                availability_list.append({
                    'day_of_week': avail.day_of_week,
                    'start_time': avail.start_time,
                    'end_time': avail.end_time,
                    'availability_type': avail.availability_type,
                    'emergency_supplement': avail.emergency_supplement
                })
            
            return availability_list
            
        except Exception as e:
            logger.error(f"Error getting provider availability: {e}")
            return []
    
    def create_appointment_slot(self, request: ServiceRequest, provider_id: int,
                               scheduled_date: date, start_time: time, 
                               duration_minutes: int = 120) -> Optional[AppointmentSlot]:
        """Create appointment slot for confirmed booking"""
        
        try:
            end_time = (datetime.combine(date.today(), start_time) + 
                       timedelta(minutes=duration_minutes)).time()
            
            appointment = AppointmentSlot(
                service_request_id=request.id,
                provider_id=provider_id,
                scheduled_date=scheduled_date,
                start_time=start_time,
                end_time=end_time,
                duration_minutes=duration_minutes,
                status="pending"
            )
            
            self.db.add(appointment)
            self.db.commit()
            
            # Update request with confirmed appointment time
            request.scheduled_at = datetime.combine(scheduled_date, start_time, WAT)
            self.db.commit()
            
            logger.info(f"Created appointment slot for request {request.id}")
            return appointment
            
        except Exception as e:
            logger.error(f"Error creating appointment slot: {e}")
            self.db.rollback()
            return None
    
    def generate_google_maps_link(self, location: str, coordinates: Optional[str] = None) -> str:
        """Generate Google Maps link for location confirmation"""
        
        if coordinates:
            # Use coordinates if available
            lat, lng = coordinates.split(',')
            return f"https://maps.google.com/?q={lat},{lng}"
        else:
            # Use location name with Douala, Cameroon context
            encoded_location = location.replace(' ', '+')
            return f"https://maps.google.com/?q={encoded_location}+Douala+Cameroon"
    
    def get_scheduling_summary(self, request: ServiceRequest) -> str:
        """Generate scheduling summary for WhatsApp messages"""
        
        summary_parts = []
        
        if request.scheduling_preference:
            label = self._get_time_slot_label(SchedulingPreference(request.scheduling_preference))
            summary_parts.append(f"⏰ Horaire: {label}")
        
        if request.urgency_supplement > 0:
            summary_parts.append(f"💰 Supplément urgence: +{int(request.urgency_supplement)} XAF")
        
        if request.location_confirmed and request.landmark_references:
            summary_parts.append(f"📍 Lieu confirmé: {request.landmark_references}")
        
        if request.scheduled_at:
            scheduled_str = request.scheduled_at.strftime("%d/%m/%Y à %H:%M")
            summary_parts.append(f"📅 Rendez-vous: {scheduled_str}")
        
        return "\n".join(summary_parts) if summary_parts else "Horaire flexible"