"""
Cultural Data Service for Djobea AI
Seeds and manages cultural context data for Cameroon
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from loguru import logger

from app.models.cultural_models import (
    CulturalContext, CulturalCalendar, EmotionalResponse,
    CulturalSensitivityRule, CommunityIntegration
)


class CulturalDataService:
    """Service for managing cultural context and community data"""
    
    def __init__(self):
        self.cameroon_cultural_data = self._get_cameroon_cultural_data()
        self.douala_cultural_data = self._get_douala_cultural_data()
        
    def seed_cultural_contexts(self, db: Session) -> None:
        """Seed cultural context data for Cameroon regions"""
        
        try:
            # Check if data already exists
            existing_context = db.query(CulturalContext).first()
            if existing_context:
                logger.info("Cultural context data already exists, skipping seed")
                return
            
            # Seed Douala cultural context
            douala_context = CulturalContext(
                region="Douala",
                district="Bonamoussadi",
                neighborhood="Centre",
                primary_languages=["français", "english", "duala"],
                local_dialects=["duala", "pidgin", "ewondo"],
                common_expressions=[
                    "Comment ça va mon frère?",
                    "On est ensemble",
                    "C'est comment?",
                    "Tu es où?",
                    "Pas de souci",
                    "On va voir",
                    "Courage"
                ],
                greeting_patterns={
                    "morning": ["Bonjour", "Good morning", "Comment tu as dormi?"],
                    "afternoon": ["Bon après-midi", "Good afternoon", "Comment ça va?"],
                    "evening": ["Bonsoir", "Good evening", "Tu es rentré?"],
                    "formal": ["Monsieur", "Madame", "Chef", "Patron"]
                },
                respect_hierarchy={
                    "elders": "Use formal titles (Papa, Maman, Tonton, Tante)",
                    "authority": "Use professional titles (Chef, Docteur, Professeur)",
                    "community": "Show respect for community leaders and religious figures"
                },
                community_values={
                    "collective_focus": "Family and community welfare comes first",
                    "mutual_aid": "Helping neighbors and community members",
                    "respect_tradition": "Honor traditional customs and values",
                    "religious_observance": "Respect for Christian, Muslim, and traditional beliefs"
                },
                business_customs={
                    "greeting_importance": "Always greet before business",
                    "relationship_building": "Build trust through personal connection",
                    "time_flexibility": "Understand 'African time' concept",
                    "negotiation_style": "Respectful but persistent negotiation"
                },
                religious_considerations={
                    "christian_majority": "Predominantly Christian population",
                    "muslim_minority": "Significant Muslim community",
                    "traditional_beliefs": "Ancestral and traditional spiritual practices",
                    "religious_holidays": "Respect for all religious observances",
                    "sunday_significance": "Sunday as day of rest and worship"
                },
                economic_level="middle",
                education_level="secondary",
                technology_adoption="medium",
                service_expectations={
                    "punctuality": "Some flexibility expected",
                    "quality": "High quality work expected",
                    "communication": "Regular updates appreciated",
                    "respect": "Polite and respectful interaction required"
                }
            )
            
            db.add(douala_context)
            db.commit()
            logger.info("Seeded Douala cultural context")
            
            # Seed other regions
            regions_data = [
                {
                    "region": "Yaoundé",
                    "district": "Centre-ville",
                    "primary_languages": ["français", "english", "ewondo"],
                    "local_dialects": ["ewondo", "beti", "pidgin"],
                    "economic_level": "middle",
                    "education_level": "university"
                },
                {
                    "region": "Bafoussam",
                    "district": "Centre",
                    "primary_languages": ["français", "english", "bamileke"],
                    "local_dialects": ["bamileke", "fe'efe'", "pidgin"],
                    "economic_level": "middle",
                    "education_level": "secondary"
                }
            ]
            
            for region_data in regions_data:
                context = CulturalContext(
                    region=region_data["region"],
                    district=region_data["district"],
                    primary_languages=region_data["primary_languages"],
                    local_dialects=region_data["local_dialects"],
                    common_expressions=self.cameroon_cultural_data["common_expressions"],
                    greeting_patterns=self.cameroon_cultural_data["greeting_patterns"],
                    respect_hierarchy=self.cameroon_cultural_data["respect_hierarchy"],
                    community_values=self.cameroon_cultural_data["community_values"],
                    business_customs=self.cameroon_cultural_data["business_customs"],
                    religious_considerations=self.cameroon_cultural_data["religious_considerations"],
                    economic_level=region_data["economic_level"],
                    education_level=region_data["education_level"],
                    technology_adoption="medium",
                    service_expectations=self.cameroon_cultural_data["service_expectations"]
                )
                db.add(context)
            
            db.commit()
            logger.info("Seeded additional regional cultural contexts")
            
        except Exception as e:
            logger.error(f"Error seeding cultural contexts: {e}")
            db.rollback()

    def seed_cultural_calendar(self, db: Session) -> None:
        """Seed cultural calendar with Cameroon holidays and events"""
        
        try:
            existing_event = db.query(CulturalCalendar).first()
            if existing_event:
                logger.info("Cultural calendar already exists, skipping seed")
                return
            
            # Cameroon holidays and cultural events
            cultural_events = [
                {
                    "event_name": "Jour de l'An",
                    "event_type": "holiday",
                    "description": "New Year's Day celebration",
                    "start_date": "2025-01-01",
                    "is_recurring": True,
                    "recurrence_pattern": "yearly",
                    "religious_affiliation": "secular",
                    "celebration_level": "national",
                    "affects_business": True,
                    "service_modifications": ["Reduced service availability", "Emergency only"],
                    "communication_adjustments": ["New Year greetings", "Schedule adjustments"]
                },
                {
                    "event_name": "Fête de la Jeunesse",
                    "event_type": "holiday",
                    "description": "National Youth Day",
                    "start_date": "2025-02-11",
                    "is_recurring": True,
                    "recurrence_pattern": "yearly",
                    "religious_affiliation": "secular",
                    "celebration_level": "national",
                    "affects_business": True
                },
                {
                    "event_name": "Fête du Travail",
                    "event_type": "holiday",
                    "description": "Labor Day",
                    "start_date": "2025-05-01",
                    "is_recurring": True,
                    "recurrence_pattern": "yearly",
                    "religious_affiliation": "secular",
                    "celebration_level": "national",
                    "affects_business": True
                },
                {
                    "event_name": "Fête Nationale",
                    "event_type": "holiday",
                    "description": "National Day",
                    "start_date": "2025-05-20",
                    "is_recurring": True,
                    "recurrence_pattern": "yearly",
                    "religious_affiliation": "secular",
                    "celebration_level": "national",
                    "affects_business": True
                },
                {
                    "event_name": "Assomption",
                    "event_type": "religious",
                    "description": "Assumption of Mary",
                    "start_date": "2025-08-15",
                    "is_recurring": True,
                    "recurrence_pattern": "yearly",
                    "religious_affiliation": "Christian",
                    "celebration_level": "national",
                    "affects_business": True
                },
                {
                    "event_name": "Noël",
                    "event_type": "religious",
                    "description": "Christmas Day",
                    "start_date": "2025-12-25",
                    "is_recurring": True,
                    "recurrence_pattern": "yearly",
                    "religious_affiliation": "Christian",
                    "celebration_level": "national",
                    "affects_business": True,
                    "service_modifications": ["Emergency services only", "Family time priority"],
                    "communication_adjustments": ["Christmas greetings", "Holiday schedules"]
                },
                {
                    "event_name": "Ramadan",
                    "event_type": "religious",
                    "description": "Holy month of fasting",
                    "start_date": "2025-03-01",
                    "end_date": "2025-03-30",
                    "is_recurring": True,
                    "recurrence_pattern": "yearly",
                    "religious_affiliation": "Muslim",
                    "celebration_level": "regional",
                    "affects_business": False,
                    "service_modifications": ["Respect fasting hours", "Flexible scheduling"],
                    "communication_adjustments": ["Ramadan greetings", "Cultural sensitivity"]
                },
                {
                    "event_name": "Saison des pluies",
                    "event_type": "seasonal",
                    "description": "Rainy season",
                    "start_date": "2025-06-01",
                    "end_date": "2025-09-30",
                    "is_recurring": True,
                    "recurrence_pattern": "yearly",
                    "celebration_level": "regional",
                    "affects_business": True,
                    "service_modifications": ["Weather-dependent services", "Transport challenges"],
                    "communication_adjustments": ["Weather considerations", "Flexible timing"]
                }
            ]
            
            for event_data in cultural_events:
                start_date = datetime.strptime(event_data["start_date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
                end_date = None
                if event_data.get("end_date"):
                    end_date = datetime.strptime(event_data["end_date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
                
                calendar_event = CulturalCalendar(
                    event_name=event_data["event_name"],
                    event_type=event_data["event_type"],
                    description=event_data["description"],
                    start_date=start_date,
                    end_date=end_date,
                    is_recurring=event_data.get("is_recurring", False),
                    recurrence_pattern=event_data.get("recurrence_pattern"),
                    religious_affiliation=event_data.get("religious_affiliation"),
                    celebration_level=event_data.get("celebration_level"),
                    affects_business=event_data.get("affects_business", False),
                    service_modifications=event_data.get("service_modifications", []),
                    communication_adjustments=event_data.get("communication_adjustments", []),
                    regions=["Douala", "Yaoundé", "Bafoussam"],
                    urban_rural="both"
                )
                db.add(calendar_event)
            
            db.commit()
            logger.info("Seeded cultural calendar")
            
        except Exception as e:
            logger.error(f"Error seeding cultural calendar: {e}")
            db.rollback()

    def seed_emotional_responses(self, db: Session) -> None:
        """Seed emotional response templates"""
        
        try:
            existing_response = db.query(EmotionalResponse).first()
            if existing_response:
                logger.info("Emotional responses already exist, skipping seed")
                return
            
            # Emotional response templates
            response_templates = [
                {
                    "trigger_emotion": "frustration",
                    "trigger_situation": "service_delay",
                    "severity_level": "medium",
                    "language": "français",
                    "formality_level": "respectful",
                    "response_template": "Je comprends votre frustration. Nous faisons tout pour accélérer le processus. Votre satisfaction est notre priorité. 🙏",
                    "tone": "calming",
                    "urgency_level": "prompt",
                },
                {
                    "trigger_emotion": "anxiety",
                    "trigger_situation": "emergency",
                    "severity_level": "high",
                    "language": "français",
                    "formality_level": "urgent",
                    "response_template": "Nous comprenons l'urgence de votre situation. Un technicien vous contactera dans les 5 minutes. Restez calme. 🚨",
                    "tone": "urgent",
                    "urgency_level": "immediate",
                },
                {
                    "trigger_emotion": "joy",
                    "trigger_situation": "service_completion",
                    "severity_level": "low",
                    "language": "français",
                    "formality_level": "celebratory",
                    "response_template": "🎉 Félicitations ! Nous sommes ravis que tout se soit bien passé. Merci de nous faire confiance !",
                    "tone": "celebratory",
                    "urgency_level": "routine",
                },
                {
                    "trigger_emotion": "confusion",
                    "trigger_situation": "service_request",
                    "severity_level": "low",
                    "language": "français",
                    "formality_level": "respectful",
                    "response_template": "Pas de souci ! Je vais vous expliquer étape par étape. Nous sommes là pour vous aider. 😊",
                    "tone": "helpful",
                    "urgency_level": "routine",
                },
                {
                    "trigger_emotion": "satisfaction",
                    "trigger_situation": "feedback",
                    "severity_level": "low",
                    "language": "français",
                    "formality_level": "respectful",
                    "response_template": "Merci beaucoup pour vos commentaires positifs ! Cela nous motive à continuer. 🌟",
                    "tone": "appreciative",
                    "urgency_level": "routine",
                }
            ]
            
            # Add English versions
            english_templates = [
                {
                    "trigger_emotion": "frustration",
                    "trigger_situation": "service_delay",
                    "severity_level": "medium",
                    "language": "english",
                    "formality_level": "respectful",
                    "response_template": "I understand your frustration. We are doing everything to speed up the process. Your satisfaction is our priority. 🙏",
                    "tone": "calming",
                    "urgency_level": "prompt",
                },
                {
                    "trigger_emotion": "anxiety",
                    "trigger_situation": "emergency",
                    "severity_level": "high",
                    "language": "english",
                    "formality_level": "urgent",
                    "response_template": "We understand the urgency of your situation. A technician will contact you within 5 minutes. Stay calm. 🚨",
                    "tone": "urgent",
                    "urgency_level": "immediate",
                }
            ]
            
            all_templates = response_templates + english_templates
            
            for template_data in all_templates:
                response = EmotionalResponse(
                    trigger_emotion=template_data["trigger_emotion"],
                    trigger_situation=template_data["trigger_situation"],
                    severity_level=template_data["severity_level"],
                    language=template_data["language"],
                    formality_level=template_data["formality_level"],
                    response_template=template_data["response_template"],
                    tone=template_data["tone"],
                    urgency_level=template_data["urgency_level"],

                    created_by="system"
                )
                db.add(response)
            
            db.commit()
            logger.info("Seeded emotional response templates")
            
        except Exception as e:
            logger.error(f"Error seeding emotional responses: {e}")
            db.rollback()

    def seed_cultural_sensitivity_rules(self, db: Session) -> None:
        """Seed cultural sensitivity rules"""
        
        try:
            existing_rule = db.query(CulturalSensitivityRule).first()
            if existing_rule:
                logger.info("Cultural sensitivity rules already exist, skipping seed")
                return
            
            # Cultural sensitivity rules
            sensitivity_rules = [
                {
                    "rule_name": "Respect for Elders",
                    "rule_category": "social",
                    "description": "Always use respectful language when addressing older individuals",
                    "applicable_regions": ["Douala", "Yaoundé", "Bafoussam"],
                    "cultural_groups": ["all"],
                    "required_expressions": ["Monsieur", "Madame", "Papa", "Maman"],
                    "tone_requirements": ["respectful", "formal"],
                    "severity": "error",
                    "auto_correction": True,
                    "priority_level": 1
                },
                {
                    "rule_name": "Religious Sensitivity",
                    "rule_category": "religious",
                    "description": "Respect religious practices and beliefs",
                    "applicable_regions": ["Douala", "Yaoundé", "Bafoussam"],
                    "religious_groups": ["Christian", "Muslim", "traditional"],
                    "prohibited_words": ["blasphemy", "sacrilege"],
                    "timing_considerations": ["Sunday church", "Friday prayers", "Ramadan"],
                    "severity": "error",
                    "priority_level": 1
                },
                {
                    "rule_name": "Community Focus",
                    "rule_category": "social",
                    "description": "Emphasize community and family values",
                    "applicable_regions": ["Douala", "Yaoundé", "Bafoussam"],
                    "required_expressions": ["notre communauté", "ensemble", "famille"],
                    "tone_requirements": ["inclusive", "community-oriented"],
                    "severity": "warning",
                    "priority_level": 2
                },
                {
                    "rule_name": "Business Politeness",
                    "rule_category": "business",
                    "description": "Always maintain politeness in business interactions",
                    "applicable_regions": ["Douala", "Yaoundé", "Bafoussam"],
                    "required_expressions": ["s'il vous plaît", "merci", "avec plaisir"],
                    "prohibited_words": ["impossible", "jamais", "non"],
                    "alternative_suggestions": ["difficile mais possible", "nous allons voir", "permettez-moi de vérifier"],
                    "severity": "warning",
                    "priority_level": 2
                },
                {
                    "rule_name": "Language Mixing",
                    "rule_category": "linguistic",
                    "description": "Support natural French-English mixing",
                    "applicable_regions": ["Douala", "Yaoundé"],
                    "tone_requirements": ["natural", "accommodating"],
                    "severity": "warning",
                    "auto_correction": False,
                    "priority_level": 3
                }
            ]
            
            for rule_data in sensitivity_rules:
                rule = CulturalSensitivityRule(
                    rule_name=rule_data["rule_name"],
                    rule_category=rule_data["rule_category"],
                    description=rule_data["description"],
                    applicable_regions=rule_data.get("applicable_regions", []),
                    cultural_groups=rule_data.get("cultural_groups", []),
                    religious_groups=rule_data.get("religious_groups", []),
                    prohibited_words=rule_data.get("prohibited_words", []),
                    required_expressions=rule_data.get("required_expressions", []),
                    tone_requirements=rule_data.get("tone_requirements", []),
                    timing_considerations=rule_data.get("timing_considerations", []),
                    severity=rule_data["severity"],
                    auto_correction=rule_data.get("auto_correction", False),
                    alternative_suggestions=rule_data.get("alternative_suggestions", []),
                    priority_level=rule_data["priority_level"]
                )
                db.add(rule)
            
            db.commit()
            logger.info("Seeded cultural sensitivity rules")
            
        except Exception as e:
            logger.error(f"Error seeding cultural sensitivity rules: {e}")
            db.rollback()

    def seed_community_integration(self, db: Session) -> None:
        """Seed community integration data"""
        
        try:
            existing_community = db.query(CommunityIntegration).first()
            if existing_community:
                logger.info("Community integration data already exists, skipping seed")
                return
            
            # Community leaders and integration points
            community_data = [
                {
                    "entity_type": "leader",
                    "name": "Chef de Quartier Bonamoussadi",
                    "title": "Chef de Quartier",
                    "region": "Douala",
                    "districts": ["Bonamoussadi"],
                    "influence_radius": 2.0,
                    "specialties": ["community affairs", "local governance", "conflict resolution"],
                    "languages_spoken": ["français", "duala", "english"],
                    "cultural_affiliations": ["traditional", "modern"],
                    "partnership_type": "endorsement",
                    "partnership_status": "potential",
                    "community_trust_level": "high",
                    "endorsement_value": 0.9
                },
                {
                    "entity_type": "business",
                    "name": "Marché Bonamoussadi",
                    "title": "Marché Principal",
                    "region": "Douala",
                    "districts": ["Bonamoussadi"],
                    "influence_radius": 1.5,
                    "specialties": ["commerce", "community gathering", "local economy"],
                    "languages_spoken": ["français", "duala", "pidgin"],
                    "partnership_type": "collaboration",
                    "partnership_status": "potential",
                    "community_trust_level": "high",
                    "endorsement_value": 0.8
                },
                {
                    "entity_type": "organization",
                    "name": "Association des Femmes de Bonamoussadi",
                    "title": "Association Communautaire",
                    "region": "Douala",
                    "districts": ["Bonamoussadi"],
                    "influence_radius": 3.0,
                    "specialties": ["women empowerment", "community development", "social issues"],
                    "languages_spoken": ["français", "duala", "english"],
                    "cultural_affiliations": ["women's rights", "community development"],
                    "partnership_type": "referral",
                    "partnership_status": "potential",
                    "community_trust_level": "high",
                    "endorsement_value": 0.85
                }
            ]
            
            for community_item in community_data:
                integration = CommunityIntegration(
                    entity_type=community_item["entity_type"],
                    name=community_item["name"],
                    title=community_item["title"],
                    region=community_item["region"],
                    districts=community_item["districts"],
                    influence_radius=community_item["influence_radius"],
                    specialties=community_item["specialties"],
                    languages_spoken=community_item["languages_spoken"],
                    cultural_affiliations=community_item.get("cultural_affiliations", []),
                    partnership_type=community_item["partnership_type"],
                    partnership_status=community_item["partnership_status"],
                    community_trust_level=community_item["community_trust_level"],
                    endorsement_value=community_item["endorsement_value"]
                )
                db.add(integration)
            
            db.commit()
            logger.info("Seeded community integration data")
            
        except Exception as e:
            logger.error(f"Error seeding community integration: {e}")
            db.rollback()

    def seed_all_cultural_data(self, db: Session) -> None:
        """Seed all cultural data"""
        
        logger.info("Starting cultural data seeding process...")
        
        self.seed_cultural_contexts(db)
        self.seed_cultural_calendar(db)
        self.seed_emotional_responses(db)
        self.seed_cultural_sensitivity_rules(db)
        self.seed_community_integration(db)
        
        logger.info("Cultural data seeding completed successfully")

    def _get_cameroon_cultural_data(self) -> Dict:
        """Get general Cameroon cultural data"""
        
        return {
            "common_expressions": [
                "Comment ça va?", "Ça va bien", "Pas de souci", "On va voir",
                "C'est comment?", "Tu es où?", "On est ensemble", "Courage",
                "Doucement", "Petit à petit", "God go help us", "Na so"
            ],
            "greeting_patterns": {
                "morning": ["Bonjour", "Good morning", "Comment tu as dormi?"],
                "afternoon": ["Bon après-midi", "Good afternoon", "Comment ça va?"],
                "evening": ["Bonsoir", "Good evening", "Tu es rentré?"],
                "formal": ["Monsieur", "Madame", "Chef", "Patron", "Docteur"]
            },
            "respect_hierarchy": {
                "elders": "Use formal titles and show deference",
                "authority": "Respect professional and traditional authority",
                "community": "Value community leaders and religious figures"
            },
            "community_values": {
                "collective_focus": "Community welfare over individual needs",
                "mutual_aid": "Help neighbors and community members",
                "respect_tradition": "Honor traditional customs and values"
            },
            "business_customs": {
                "greeting_importance": "Always greet before conducting business",
                "relationship_building": "Build personal relationships first",
                "time_flexibility": "Understand flexible time concepts"
            },
            "religious_considerations": {
                "christian_majority": "Predominantly Christian population",
                "muslim_minority": "Significant Muslim community",
                "traditional_beliefs": "Respect for ancestral traditions"
            },
            "service_expectations": {
                "punctuality": "Some flexibility expected",
                "quality": "High quality work expected",
                "communication": "Regular communication appreciated",
                "respect": "Polite and respectful interaction required"
            }
        }

    def _get_douala_cultural_data(self) -> Dict:
        """Get Douala-specific cultural data"""
        
        return {
            "economic_characteristics": {
                "business_hub": "Major commercial center",
                "port_city": "International trade gateway",
                "diverse_population": "Mix of ethnic groups and cultures"
            },
            "social_characteristics": {
                "urban_lifestyle": "Fast-paced urban environment",
                "cultural_mixing": "Blend of traditional and modern values",
                "language_diversity": "French, English, Duala, Pidgin common"
            },
            "service_culture": {
                "quality_expectations": "High standards expected",
                "time_consciousness": "More time-aware than rural areas",
                "technology_adoption": "Moderate to high technology use"
            }
        }