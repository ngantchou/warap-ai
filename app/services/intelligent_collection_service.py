"""
Intelligent Collection Service - Advanced information gathering system
Handles missing information detection, contextual questioning, and real-time validation
"""
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import logging
from datetime import datetime
import json
import re

from app.services.ai_service import AIService
from app.services.dialogue_flow_manager import DialogueContext, InformationField, InformationPriority

logger = logging.getLogger(__name__)

class CollectionMode(Enum):
    """Information collection modes"""
    SEQUENTIAL = "sequential"      # Ask one question at a time
    PARALLEL = "parallel"          # Ask multiple questions together
    ADAPTIVE = "adaptive"          # Adapt based on user behavior
    OPTIMIZED = "optimized"        # Minimize total questions

class ValidationLevel(Enum):
    """Validation strictness levels"""
    BASIC = "basic"           # Simple format checks
    STANDARD = "standard"     # Format + business rules
    STRICT = "strict"         # All validations + AI verification
    REAL_TIME = "real_time"   # Immediate validation on input

@dataclass
class CollectionStrategy:
    """Collection strategy configuration"""
    mode: CollectionMode = CollectionMode.ADAPTIVE
    validation_level: ValidationLevel = ValidationLevel.STANDARD
    max_questions_per_turn: int = 3
    enable_suggestions: bool = True
    enable_auto_completion: bool = True
    enable_context_hints: bool = True
    prioritize_critical_info: bool = True

@dataclass
class QuestionContext:
    """Context for question generation"""
    missing_fields: List[str]
    collected_info: Dict[str, Any]
    user_profile: Dict[str, Any]
    conversation_history: List[Dict]
    current_priority: InformationPriority
    retry_count: int = 0
    previous_questions: List[str] = None

@dataclass
class ValidationResult:
    """Validation result with details"""
    is_valid: bool
    confidence: float
    issues: List[str]
    suggestions: List[str]
    corrected_value: Optional[str] = None
    needs_clarification: bool = False

class IntelligentCollectionService:
    """
    Advanced information collection service with smart questioning and validation
    """
    
    def __init__(self):
        self.ai_service = AIService()
        self.collection_strategy = CollectionStrategy()
        
        # Question templates by field and context
        self.question_templates = self._initialize_question_templates()
        
        # Validation rules
        self.validation_rules = self._initialize_validation_rules()
        
        # Auto-completion suggestions
        self.auto_completion_data = self._initialize_auto_completion_data()
        
        # Collection metrics
        self.metrics = {
            "total_questions_asked": 0,
            "successful_extractions": 0,
            "validation_failures": 0,
            "auto_completions_used": 0,
            "average_turns_per_field": 0.0
        }
    
    def _initialize_question_templates(self) -> Dict[str, Dict[str, List[str]]]:
        """Initialize question templates for different contexts"""
        return {
            "service_type": {
                "initial": [
                    "🔧 Quel type de service vous faut-il ?",
                    "🏠 De quel service avez-vous besoin pour votre domicile ?",
                    "⚡ Que puis-je faire pour vous aider aujourd'hui ?"
                ],
                "clarification": [
                    "Pouvez-vous préciser le type de service ?",
                    "S'agit-il de plomberie, électricité ou électroménager ?",
                    "Quel domaine technique vous pose problème ?"
                ],
                "retry": [
                    "Je ne suis pas sûr d'avoir compris le service demandé. Pouvez-vous choisir parmi :",
                    "Pour mieux vous aider, précisez le type de service :"
                ]
            },
            "location": {
                "initial": [
                    "📍 Où êtes-vous situé ?",
                    "🗺️ Quelle est votre adresse à Bonamoussadi ?",
                    "📌 Dans quel quartier de Bonamoussadi habitez-vous ?"
                ],
                "clarification": [
                    "Pouvez-vous donner une adresse plus précise ?",
                    "Dans quel quartier de Bonamoussadi exactement ?",
                    "Avez-vous une adresse complète (rue, numéro) ?"
                ],
                "retry": [
                    "J'ai besoin d'une localisation précise dans Bonamoussadi.",
                    "Pouvez-vous me donner votre adresse complète ?"
                ]
            },
            "description": {
                "initial": [
                    "🔍 Pouvez-vous décrire votre problème ?",
                    "📝 Expliquez-moi ce qui se passe exactement.",
                    "🔧 Que se passe-t-il avec votre {service_type} ?"
                ],
                "clarification": [
                    "Pouvez-vous donner plus de détails sur le problème ?",
                    "Que se passe-t-il exactement ?",
                    "Depuis quand avez-vous ce problème ?"
                ],
                "retry": [
                    "Une description plus détaillée m'aiderait à mieux vous orienter.",
                    "Pouvez-vous expliquer le problème étape par étape ?"
                ]
            },
            "urgency": {
                "initial": [
                    "⏰ Quand souhaitez-vous l'intervention ?",
                    "🚨 C'est urgent ?",
                    "📅 Quel délai vous convient ?"
                ],
                "clarification": [
                    "Dans combien de temps avez-vous besoin du service ?",
                    "Est-ce que ça peut attendre ou c'est urgent ?",
                    "Préférez-vous aujourd'hui, demain ou plus tard ?"
                ],
                "retry": [
                    "Aidez-moi à comprendre l'urgence de votre demande.",
                    "Quand avez-vous besoin que ce soit fait ?"
                ]
            },
            "contact_info": {
                "initial": [
                    "📞 Quel est le meilleur moyen de vous contacter ?",
                    "📱 Le prestataire peut-il vous joindre sur ce numéro ?",
                    "☎️ Avez-vous un numéro de téléphone préféré ?"
                ],
                "clarification": [
                    "Comment préférez-vous être contacté ?",
                    "Ce numéro WhatsApp convient-il ?",
                    "Avez-vous un autre numéro de téléphone ?"
                ],
                "retry": [
                    "J'ai besoin d'un moyen de contact pour le prestataire.",
                    "Confirmez-moi votre numéro de téléphone."
                ]
            }
        }
    
    def _initialize_validation_rules(self) -> Dict[str, Dict[str, Any]]:
        """Initialize validation rules for each field"""
        return {
            "service_type": {
                "allowed_values": ["plomberie", "électricité", "réparation électroménager", "électroménager"],
                "synonyms": {
                    "plomberie": ["plombier", "eau", "robinet", "tuyau", "fuite", "wc", "toilette", "douche"],
                    "électricité": ["électricien", "courant", "lumière", "prise", "disjoncteur", "panne", "cable"],
                    "électroménager": ["frigo", "réfrigérateur", "machine", "lave-linge", "climatiseur", "four"]
                },
                "patterns": [
                    r"probl[eè]me\s+de\s+(\w+)",
                    r"(\w+)\s+ne\s+marche\s+pas",
                    r"(\w+)\s+en\s+panne"
                ]
            },
            "location": {
                "required_contains": ["bonamoussadi", "douala"],
                "optional_contains": ["village", "carrefour", "ndokoti", "rue", "quartier"],
                "patterns": [
                    r"bonamoussadi\s+(\w+)",
                    r"rue\s+([^,]+)",
                    r"quartier\s+([^,]+)"
                ],
                "min_length": 10,
                "max_length": 100
            },
            "description": {
                "min_length": 10,
                "max_length": 500,
                "required_elements": ["problem", "location_in_house"],
                "quality_indicators": ["specific_symptoms", "duration", "context"]
            },
            "urgency": {
                "allowed_values": ["urgent", "aujourd'hui", "demain", "cette semaine", "pas pressé", "flexible"],
                "patterns": [
                    r"(urgent|très\s+urgent|super\s+urgent)",
                    r"(aujourd'hui|maintenant|tout\s+de\s+suite)",
                    r"(demain|dans\s+\d+\s+jours?)",
                    r"(cette\s+semaine|pas\s+pressé)"
                ]
            },
            "contact_info": {
                "patterns": [
                    r"(\+?237\s*\d{9})",
                    r"(\d{9})",
                    r"(\+?237\s*\d{3}\s*\d{3}\s*\d{3})"
                ],
                "validation": "cameroon_phone_number"
            }
        }
    
    def _initialize_auto_completion_data(self) -> Dict[str, List[str]]:
        """Initialize auto-completion suggestions"""
        return {
            "service_type": [
                "Plomberie - Fuites, canalisations, robinetterie",
                "Électricité - Pannes, installations, réparations",
                "Électroménager - Réfrigérateur, machine à laver, climatiseur"
            ],
            "location_bonamoussadi": [
                "Bonamoussadi Village",
                "Bonamoussadi Carrefour",
                "Bonamoussadi Ndokoti",
                "Bonamoussadi Marché",
                "Bonamoussadi Lycée"
            ],
            "urgency_options": [
                "Urgent - Dans l'heure",
                "Aujourd'hui - Avant ce soir",
                "Demain - Dans les 24h",
                "Cette semaine - Pas pressé",
                "Flexible - Quand vous voulez"
            ],
            "common_plumbing_issues": [
                "Robinet qui fuit",
                "Tuyau cassé",
                "Toilette bouchée",
                "Pas d'eau",
                "Chauffe-eau en panne"
            ],
            "common_electrical_issues": [
                "Panne de courant",
                "Prise qui ne marche pas",
                "Lumière qui clignote",
                "Disjoncteur qui saute",
                "Installation électrique"
            ],
            "common_appliance_issues": [
                "Frigo qui ne refroidit pas",
                "Machine à laver en panne",
                "Climatiseur qui ne marche pas",
                "Four qui ne chauffe pas",
                "Lave-vaisselle bloqué"
            ]
        }
    
    async def detect_missing_information(
        self,
        dialogue_context: DialogueContext,
        required_fields: List[str] = None
    ) -> Dict[str, Any]:
        """
        Detect missing information and prioritize collection
        """
        if required_fields is None:
            required_fields = ["service_type", "location", "description", "urgency"]
        
        collected_info = dialogue_context.collected_info
        missing_fields = []
        
        # Check each required field
        for field in required_fields:
            if field not in collected_info or not collected_info[field]:
                missing_fields.append(field)
        
        # Prioritize missing fields
        prioritized_fields = self._prioritize_missing_fields(missing_fields, dialogue_context)
        
        # Analyze information quality
        quality_analysis = await self._analyze_information_quality(collected_info)
        
        # Determine collection strategy
        collection_strategy = self._determine_collection_strategy(
            prioritized_fields, dialogue_context
        )
        
        return {
            "missing_fields": missing_fields,
            "prioritized_fields": prioritized_fields,
            "quality_analysis": quality_analysis,
            "collection_strategy": collection_strategy,
            "next_questions": await self._generate_next_questions(
                prioritized_fields[:self.collection_strategy.max_questions_per_turn],
                dialogue_context
            )
        }
    
    def _prioritize_missing_fields(
        self,
        missing_fields: List[str],
        dialogue_context: DialogueContext
    ) -> List[str]:
        """Prioritize missing fields based on context and strategy"""
        field_priorities = {
            "service_type": 1,
            "location": 2,
            "description": 3,
            "urgency": 4,
            "contact_info": 5
        }
        
        # Adjust priorities based on context
        if dialogue_context.collected_info.get("service_type") == "urgent":
            field_priorities["urgency"] = 1
        
        # Consider user profile
        if dialogue_context.user_profile.get("prefers_location_first"):
            field_priorities["location"] = 1
        
        # Sort by priority
        return sorted(missing_fields, key=lambda x: field_priorities.get(x, 10))
    
    async def _analyze_information_quality(
        self,
        collected_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze quality of collected information"""
        quality_scores = {}
        improvement_suggestions = {}
        
        for field, value in collected_info.items():
            if field in self.validation_rules:
                score, suggestions = await self._calculate_field_quality(field, value)
                quality_scores[field] = score
                if suggestions:
                    improvement_suggestions[field] = suggestions
        
        overall_quality = sum(quality_scores.values()) / len(quality_scores) if quality_scores else 0
        
        return {
            "overall_quality": overall_quality,
            "field_scores": quality_scores,
            "improvement_suggestions": improvement_suggestions,
            "completeness": len(collected_info) / 5  # Assume 5 total fields
        }
    
    async def _calculate_field_quality(
        self,
        field: str,
        value: Any
    ) -> Tuple[float, List[str]]:
        """Calculate quality score for a specific field"""
        if field not in self.validation_rules:
            return 0.8, []
        
        rules = self.validation_rules[field]
        score = 1.0
        suggestions = []
        
        # Check length requirements
        if "min_length" in rules:
            if len(str(value)) < rules["min_length"]:
                score -= 0.3
                suggestions.append(f"Pouvez-vous donner plus de détails ?")
        
        if "max_length" in rules:
            if len(str(value)) > rules["max_length"]:
                score -= 0.1
                suggestions.append(f"Pouvez-vous résumer ?")
        
        # Check allowed values
        if "allowed_values" in rules:
            value_lower = str(value).lower()
            if not any(allowed in value_lower for allowed in rules["allowed_values"]):
                # Check synonyms
                found_synonym = False
                if "synonyms" in rules:
                    for service, synonyms in rules["synonyms"].items():
                        if any(synonym in value_lower for synonym in synonyms):
                            found_synonym = True
                            break
                
                if not found_synonym:
                    score -= 0.4
                    suggestions.append(f"Précisez parmi : {', '.join(rules['allowed_values'])}")
        
        # Check required contains
        if "required_contains" in rules:
            value_lower = str(value).lower()
            if not any(required in value_lower for required in rules["required_contains"]):
                score -= 0.5
                suggestions.append(f"Veuillez inclure : {', '.join(rules['required_contains'])}")
        
        return max(score, 0.0), suggestions
    
    def _determine_collection_strategy(
        self,
        prioritized_fields: List[str],
        dialogue_context: DialogueContext
    ) -> Dict[str, Any]:
        """Determine optimal collection strategy"""
        # Analyze user behavior
        user_response_pattern = self._analyze_user_response_pattern(dialogue_context)
        
        # Determine mode
        if user_response_pattern.get("prefers_single_questions"):
            mode = CollectionMode.SEQUENTIAL
            max_questions = 1
        elif user_response_pattern.get("provides_detailed_responses"):
            mode = CollectionMode.PARALLEL
            max_questions = 3
        else:
            mode = CollectionMode.ADAPTIVE
            max_questions = 2
        
        return {
            "mode": mode,
            "max_questions_per_turn": max_questions,
            "should_provide_examples": user_response_pattern.get("needs_examples", True),
            "should_use_suggestions": user_response_pattern.get("uses_suggestions", True),
            "validation_level": ValidationLevel.STANDARD
        }
    
    def _analyze_user_response_pattern(
        self,
        dialogue_context: DialogueContext
    ) -> Dict[str, Any]:
        """Analyze user response patterns"""
        history = dialogue_context.conversation_history
        
        if not history:
            return {"needs_examples": True, "uses_suggestions": True}
        
        # Analyze response characteristics
        avg_response_length = sum(len(msg.get("message", "")) for msg in history) / len(history)
        
        return {
            "prefers_single_questions": avg_response_length < 20,
            "provides_detailed_responses": avg_response_length > 50,
            "needs_examples": len(history) > 2,
            "uses_suggestions": True  # Default to true
        }
    
    async def _generate_next_questions(
        self,
        prioritized_fields: List[str],
        dialogue_context: DialogueContext
    ) -> List[Dict[str, Any]]:
        """Generate contextual questions for missing fields"""
        questions = []
        
        for field in prioritized_fields:
            question_data = await self._generate_field_question(field, dialogue_context)
            questions.append(question_data)
        
        return questions
    
    async def _generate_field_question(
        self,
        field: str,
        dialogue_context: DialogueContext
    ) -> Dict[str, Any]:
        """Generate contextual question for a specific field"""
        collected_info = dialogue_context.collected_info
        retry_count = dialogue_context.retry_count
        
        # Get appropriate question template
        question_type = "retry" if retry_count > 1 else "initial"
        if field in self.question_templates:
            templates = self.question_templates[field].get(question_type, 
                                                         self.question_templates[field]["initial"])
            base_question = templates[0]  # Use first template
        else:
            base_question = f"Pouvez-vous me donner {field} ?"
        
        # Contextualize question
        contextualized_question = self._contextualize_question(
            base_question, field, collected_info
        )
        
        # Generate suggestions
        suggestions = self._generate_field_suggestions(field, collected_info)
        
        # Generate examples
        examples = self._generate_field_examples(field, collected_info)
        
        return {
            "field": field,
            "question": contextualized_question,
            "suggestions": suggestions,
            "examples": examples,
            "priority": self._get_field_priority(field),
            "validation_rules": self.validation_rules.get(field, {}),
            "auto_completion": self._get_auto_completion_data(field)
        }
    
    def _contextualize_question(
        self,
        base_question: str,
        field: str,
        collected_info: Dict[str, Any]
    ) -> str:
        """Contextualize question based on collected information"""
        # Replace placeholders
        contextualized = base_question.format(**collected_info)
        
        # Add context based on collected info
        if field == "description" and "service_type" in collected_info:
            service_type = collected_info["service_type"]
            if service_type == "plomberie":
                contextualized += "\n\nPar exemple : robinet qui fuit, toilette bouchée, pas d'eau..."
            elif service_type == "électricité":
                contextualized += "\n\nPar exemple : panne de courant, prise qui ne marche pas..."
            elif service_type == "électroménager":
                contextualized += "\n\nPar exemple : frigo qui ne refroidit pas, machine en panne..."
        
        if field == "urgency" and "description" in collected_info:
            description = collected_info["description"].lower()
            if any(word in description for word in ["fuite", "panne", "plus", "ne marche pas"]):
                contextualized += "\n\n⚠️ Cela semble important, avez-vous besoin d'une intervention rapide ?"
        
        return contextualized
    
    def _generate_field_suggestions(
        self,
        field: str,
        collected_info: Dict[str, Any]
    ) -> List[str]:
        """Generate suggestions for a field"""
        if not self.collection_strategy.enable_suggestions:
            return []
        
        suggestions = []
        
        if field == "service_type":
            suggestions = ["Plomberie", "Électricité", "Électroménager"]
        
        elif field == "location":
            suggestions = ["Bonamoussadi Village", "Bonamoussadi Carrefour", "Bonamoussadi Ndokoti"]
        
        elif field == "urgency":
            suggestions = ["Urgent", "Aujourd'hui", "Demain", "Cette semaine"]
        
        elif field == "description" and "service_type" in collected_info:
            service_type = collected_info["service_type"]
            if service_type == "plomberie":
                suggestions = ["Robinet qui fuit", "Toilette bouchée", "Pas d'eau"]
            elif service_type == "électricité":
                suggestions = ["Panne de courant", "Prise ne marche pas", "Lumière clignote"]
            elif service_type == "électroménager":
                suggestions = ["Frigo ne refroidit pas", "Machine en panne", "Climatiseur cassé"]
        
        return suggestions
    
    def _generate_field_examples(
        self,
        field: str,
        collected_info: Dict[str, Any]
    ) -> List[str]:
        """Generate examples for a field"""
        if field in self.auto_completion_data:
            return self.auto_completion_data[field][:3]  # Return first 3 examples
        return []
    
    def _get_field_priority(self, field: str) -> int:
        """Get priority for a field"""
        priorities = {
            "service_type": 1,
            "location": 2,
            "description": 3,
            "urgency": 4,
            "contact_info": 5
        }
        return priorities.get(field, 10)
    
    def _get_auto_completion_data(self, field: str) -> List[str]:
        """Get auto-completion data for a field"""
        if not self.collection_strategy.enable_auto_completion:
            return []
        
        return self.auto_completion_data.get(field, [])
    
    async def validate_real_time(
        self,
        field: str,
        value: str,
        context: Dict[str, Any] = None
    ) -> ValidationResult:
        """
        Perform real-time validation of field input
        """
        if field not in self.validation_rules:
            return ValidationResult(
                is_valid=True,
                confidence=0.8,
                issues=[],
                suggestions=[]
            )
        
        rules = self.validation_rules[field]
        issues = []
        suggestions = []
        confidence = 1.0
        corrected_value = None
        
        # Length validation
        if "min_length" in rules and len(value) < rules["min_length"]:
            issues.append(f"Trop court (minimum {rules['min_length']} caractères)")
            confidence -= 0.3
        
        if "max_length" in rules and len(value) > rules["max_length"]:
            issues.append(f"Trop long (maximum {rules['max_length']} caractères)")
            confidence -= 0.1
        
        # Format validation
        if "patterns" in rules:
            pattern_matched = False
            for pattern in rules["patterns"]:
                if re.search(pattern, value, re.IGNORECASE):
                    pattern_matched = True
                    break
            
            if not pattern_matched:
                issues.append("Format non reconnu")
                confidence -= 0.2
        
        # Business logic validation
        if field == "service_type":
            corrected_value = await self._validate_service_type(value, rules)
            if corrected_value != value:
                suggestions.append(f"Voulez-vous dire '{corrected_value}' ?")
        
        elif field == "location":
            location_validation = await self._validate_location(value, rules)
            if not location_validation["valid"]:
                issues.extend(location_validation["issues"])
                suggestions.extend(location_validation["suggestions"])
                confidence -= 0.4
        
        elif field == "contact_info":
            phone_validation = self._validate_phone_number(value)
            if not phone_validation["valid"]:
                issues.extend(phone_validation["issues"])
                suggestions.extend(phone_validation["suggestions"])
                confidence -= 0.3
        
        is_valid = len(issues) == 0 and confidence > 0.5
        needs_clarification = len(issues) > 0 or confidence < 0.7
        
        return ValidationResult(
            is_valid=is_valid,
            confidence=max(confidence, 0.0),
            issues=issues,
            suggestions=suggestions,
            corrected_value=corrected_value,
            needs_clarification=needs_clarification
        )
    
    async def _validate_service_type(
        self,
        value: str,
        rules: Dict[str, Any]
    ) -> str:
        """Validate and potentially correct service type"""
        value_lower = value.lower()
        
        # Check direct matches
        for allowed in rules["allowed_values"]:
            if allowed in value_lower:
                return allowed
        
        # Check synonyms
        if "synonyms" in rules:
            for service, synonyms in rules["synonyms"].items():
                for synonym in synonyms:
                    if synonym in value_lower:
                        return service
        
        # Try AI-based correction
        correction_prompt = f"""
        Corriger ce type de service pour qu'il corresponde à l'un de ces choix :
        - plomberie
        - électricité
        - réparation électroménager
        
        Entrée utilisateur : "{value}"
        
        Répondre uniquement par le service correct ou "non_identifié" si impossible.
        """
        
        try:
            corrected = await self.ai_service.generate_response(
                messages=[{"role": "user", "content": correction_prompt}],
                max_tokens=50
            )
            
            corrected = corrected.strip().lower()
            if corrected in rules["allowed_values"]:
                return corrected
        except Exception as e:
            logger.error(f"AI correction failed: {e}")
        
        return value
    
    async def _validate_location(
        self,
        value: str,
        rules: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate location information"""
        value_lower = value.lower()
        issues = []
        suggestions = []
        
        # Check required contains
        if "required_contains" in rules:
            required_found = any(req in value_lower for req in rules["required_contains"])
            if not required_found:
                issues.append("Doit être dans la zone couverte (Bonamoussadi, Douala)")
                suggestions.append("Précisez 'Bonamoussadi' dans votre adresse")
        
        # Check if it's specific enough
        if len(value) < 15:
            issues.append("Adresse trop vague")
            suggestions.append("Ajoutez le quartier, la rue ou des points de repère")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "suggestions": suggestions
        }
    
    def _validate_phone_number(self, value: str) -> Dict[str, Any]:
        """Validate Cameroon phone number"""
        issues = []
        suggestions = []
        
        # Remove spaces and special characters
        cleaned = re.sub(r'[^\d+]', '', value)
        
        # Check Cameroon phone number patterns
        valid_patterns = [
            r'^\+?237\d{9}$',  # +237XXXXXXXXX
            r'^\d{9}$',        # XXXXXXXXX
            r'^237\d{9}$'      # 237XXXXXXXXX
        ]
        
        valid = any(re.match(pattern, cleaned) for pattern in valid_patterns)
        
        if not valid:
            issues.append("Format de numéro non valide")
            suggestions.append("Utilisez le format : +237XXXXXXXXX ou 237XXXXXXXXX")
        
        return {
            "valid": valid,
            "issues": issues,
            "suggestions": suggestions
        }
    
    async def generate_auto_completion(
        self,
        field: str,
        partial_input: str,
        context: Dict[str, Any] = None
    ) -> List[str]:
        """
        Generate auto-completion suggestions based on partial input
        """
        if not self.collection_strategy.enable_auto_completion:
            return []
        
        partial_lower = partial_input.lower()
        suggestions = []
        
        # Get base suggestions for field
        base_suggestions = self.auto_completion_data.get(field, [])
        
        # Filter based on partial input
        for suggestion in base_suggestions:
            if partial_lower in suggestion.lower():
                suggestions.append(suggestion)
        
        # Add contextual suggestions
        if field == "description" and context and "service_type" in context:
            service_type = context["service_type"]
            contextual_key = f"common_{service_type.replace(' ', '_')}_issues"
            if contextual_key in self.auto_completion_data:
                for suggestion in self.auto_completion_data[contextual_key]:
                    if partial_lower in suggestion.lower():
                        suggestions.append(suggestion)
        
        # Limit results
        return suggestions[:5]
    
    def optimize_collection_flow(
        self,
        dialogue_context: DialogueContext
    ) -> Dict[str, Any]:
        """
        Optimize collection flow to reduce question count
        """
        # Analyze current conversation
        collected_info = dialogue_context.collected_info
        missing_info = dialogue_context.missing_info
        conversation_history = dialogue_context.conversation_history
        
        # Calculate efficiency metrics
        turns_taken = len(conversation_history)
        info_collected = len(collected_info)
        efficiency = info_collected / turns_taken if turns_taken > 0 else 0
        
        # Suggest optimizations
        optimizations = []
        
        # Multi-field extraction opportunity
        if len(missing_info) > 2:
            optimizations.append({
                "type": "multi_field_extraction",
                "description": "Poser plusieurs questions en même temps",
                "potential_reduction": min(len(missing_info) - 1, 2)
            })
        
        # Context-aware questioning
        if "service_type" in collected_info:
            optimizations.append({
                "type": "context_aware_questions",
                "description": "Utiliser le contexte pour des questions plus précises",
                "potential_reduction": 1
            })
        
        # Smart suggestions
        if efficiency < 0.5:
            optimizations.append({
                "type": "smart_suggestions",
                "description": "Proposer des suggestions automatiques",
                "potential_reduction": 1
            })
        
        return {
            "current_efficiency": efficiency,
            "optimizations": optimizations,
            "estimated_remaining_turns": max(len(missing_info) - len(optimizations), 1),
            "optimization_score": min(efficiency + 0.1 * len(optimizations), 1.0)
        }
    
    def get_collection_metrics(self) -> Dict[str, Any]:
        """Get collection performance metrics"""
        return {
            "metrics": self.metrics,
            "collection_strategy": {
                "mode": self.collection_strategy.mode.value,
                "validation_level": self.collection_strategy.validation_level.value,
                "max_questions_per_turn": self.collection_strategy.max_questions_per_turn,
                "features_enabled": {
                    "suggestions": self.collection_strategy.enable_suggestions,
                    "auto_completion": self.collection_strategy.enable_auto_completion,
                    "context_hints": self.collection_strategy.enable_context_hints
                }
            },
            "validation_rules": {
                field: {
                    "required_elements": rules.get("required_elements", []),
                    "allowed_values": rules.get("allowed_values", [])
                }
                for field, rules in self.validation_rules.items()
            }
        }