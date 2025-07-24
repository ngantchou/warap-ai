"""
Knowledge Maintenance Service - Automated Content Management
"""
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc
import json
import re

from app.models.knowledge_base import (
    KnowledgeCategory, KnowledgeArticle, FAQ, PricingInformation,
    ServiceProcess, UserQuestion, ArticleFeedback
)
from app.database import get_db
from loguru import logger

class KnowledgeMaintenanceService:
    """Service for automated knowledge base maintenance"""
    
    def __init__(self, db: Session):
        self.db = db
        
    def update_pricing_information(self, service_data: List[Dict]) -> Dict[str, Any]:
        """Update pricing information automatically"""
        try:
            updated_count = 0
            created_count = 0
            
            for service in service_data:
                existing = self.db.query(PricingInformation).filter(
                    PricingInformation.service_type == service['service_type'],
                    PricingInformation.zone == service['zone']
                ).first()
                
                if existing:
                    # Update existing pricing
                    existing.min_price = service['min_price']
                    existing.max_price = service['max_price']
                    existing.average_price = service.get('average_price')
                    existing.factors = service.get('factors', {})
                    existing.last_updated = datetime.utcnow()
                    updated_count += 1
                else:
                    # Create new pricing entry
                    new_pricing = PricingInformation(
                        pricing_id=f"price_{uuid.uuid4().hex[:12]}",
                        service_type=service['service_type'],
                        zone=service['zone'],
                        min_price=service['min_price'],
                        max_price=service['max_price'],
                        average_price=service.get('average_price'),
                        factors=service.get('factors', {}),
                        currency=service.get('currency', 'XAF'),
                        unit=service.get('unit', 'service')
                    )
                    self.db.add(new_pricing)
                    created_count += 1
            
            self.db.commit()
            
            return {
                'success': True,
                'updated': updated_count,
                'created': created_count,
                'total_processed': len(service_data)
            }
            
        except Exception as e:
            logger.error(f"Error updating pricing information: {str(e)}")
            self.db.rollback()
            return {
                'success': False,
                'error': str(e),
                'updated': 0,
                'created': 0
            }
    
    def analyze_user_questions(self, days: int = 30) -> Dict[str, Any]:
        """Analyze user questions to identify content gaps"""
        try:
            since_date = datetime.utcnow() - timedelta(days=days)
            
            # Get unanswered questions
            unanswered = self.db.query(UserQuestion).filter(
                UserQuestion.created_at >= since_date,
                UserQuestion.was_answered == False
            ).all()
            
            # Group by service type and zone
            service_analysis = {}
            zone_analysis = {}
            topic_analysis = {}
            
            for question in unanswered:
                # Service type analysis
                service_type = question.service_type or 'unknown'
                if service_type not in service_analysis:
                    service_analysis[service_type] = {
                        'count': 0,
                        'questions': []
                    }
                service_analysis[service_type]['count'] += 1
                service_analysis[service_type]['questions'].append(question.question_text)
                
                # Zone analysis
                zone = question.zone or 'unknown'
                if zone not in zone_analysis:
                    zone_analysis[zone] = {
                        'count': 0,
                        'questions': []
                    }
                zone_analysis[zone]['count'] += 1
                zone_analysis[zone]['questions'].append(question.question_text)
                
                # Topic analysis using keywords
                topics = self._extract_topics(question.question_text)
                for topic in topics:
                    if topic not in topic_analysis:
                        topic_analysis[topic] = {
                            'count': 0,
                            'questions': []
                        }
                    topic_analysis[topic]['count'] += 1
                    topic_analysis[topic]['questions'].append(question.question_text)
            
            # Generate suggestions for new content
            suggestions = self._generate_content_suggestions(
                service_analysis, zone_analysis, topic_analysis
            )
            
            return {
                'success': True,
                'analysis_period': days,
                'total_unanswered': len(unanswered),
                'service_breakdown': service_analysis,
                'zone_breakdown': zone_analysis,
                'topic_breakdown': topic_analysis,
                'content_suggestions': suggestions
            }
            
        except Exception as e:
            logger.error(f"Error analyzing user questions: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'total_unanswered': 0,
                'content_suggestions': []
            }
    
    def update_content_versions(self) -> Dict[str, Any]:
        """Update content versions and track changes"""
        try:
            # Get articles that need version updates
            articles_to_update = self.db.query(KnowledgeArticle).filter(
                KnowledgeArticle.updated_at > KnowledgeArticle.created_at
            ).all()
            
            updated_articles = []
            
            for article in articles_to_update:
                # Create new version
                version_parts = article.version.split('.')
                minor_version = int(version_parts[1]) + 1
                new_version = f"{version_parts[0]}.{minor_version}"
                
                # Update version
                old_version = article.version
                article.version = new_version
                
                updated_articles.append({
                    'article_id': article.article_id,
                    'title': article.title,
                    'old_version': old_version,
                    'new_version': new_version
                })
            
            self.db.commit()
            
            return {
                'success': True,
                'updated_articles': len(updated_articles),
                'articles': updated_articles
            }
            
        except Exception as e:
            logger.error(f"Error updating content versions: {str(e)}")
            self.db.rollback()
            return {
                'success': False,
                'error': str(e),
                'updated_articles': 0
            }
    
    def optimize_content_performance(self) -> Dict[str, Any]:
        """Optimize content based on performance metrics"""
        try:
            # Get low-performing articles
            low_performing = self.db.query(KnowledgeArticle).filter(
                KnowledgeArticle.usefulness_score < 3.0,
                KnowledgeArticle.view_count > 10  # Has been viewed enough to be meaningful
            ).all()
            
            # Get high-performing articles for reference
            high_performing = self.db.query(KnowledgeArticle).filter(
                KnowledgeArticle.usefulness_score >= 4.0
            ).order_by(desc(KnowledgeArticle.usefulness_score)).limit(10).all()
            
            # Analyze feedback patterns
            feedback_analysis = self._analyze_feedback_patterns()
            
            # Generate optimization suggestions
            optimization_suggestions = []
            
            for article in low_performing:
                suggestions = self._generate_article_optimization_suggestions(
                    article, high_performing, feedback_analysis
                )
                optimization_suggestions.append({
                    'article_id': article.article_id,
                    'title': article.title,
                    'current_score': article.usefulness_score,
                    'suggestions': suggestions
                })
            
            return {
                'success': True,
                'low_performing_count': len(low_performing),
                'high_performing_count': len(high_performing),
                'optimization_suggestions': optimization_suggestions,
                'feedback_analysis': feedback_analysis
            }
            
        except Exception as e:
            logger.error(f"Error optimizing content performance: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'optimization_suggestions': []
            }
    
    def generate_faq_from_questions(self, threshold: int = 5) -> Dict[str, Any]:
        """Generate new FAQs from frequently asked questions"""
        try:
            # Get questions that appear frequently
            question_groups = self._group_similar_questions(threshold)
            
            generated_faqs = []
            
            for group in question_groups:
                if group['count'] >= threshold:
                    # Generate FAQ from question group
                    faq_data = self._generate_faq_from_group(group)
                    
                    if faq_data:
                        # Create FAQ entry
                        faq = FAQ(
                            faq_id=f"faq_{uuid.uuid4().hex[:12]}",
                            question=faq_data['question'],
                            answer=faq_data['answer'],
                            category_id=faq_data.get('category_id', 'general'),
                            service_type=faq_data.get('service_type'),
                            zone=faq_data.get('zone'),
                            keywords=faq_data.get('keywords', []),
                            priority=min(group['count'], 100)  # Priority based on frequency
                        )
                        
                        self.db.add(faq)
                        generated_faqs.append(faq_data)
            
            self.db.commit()
            
            return {
                'success': True,
                'generated_faqs': len(generated_faqs),
                'faqs': generated_faqs,
                'question_groups_analyzed': len(question_groups)
            }
            
        except Exception as e:
            logger.error(f"Error generating FAQs from questions: {str(e)}")
            self.db.rollback()
            return {
                'success': False,
                'error': str(e),
                'generated_faqs': 0
            }
    
    def cleanup_outdated_content(self, days: int = 90) -> Dict[str, Any]:
        """Clean up outdated or low-performing content"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Find outdated articles
            outdated_articles = self.db.query(KnowledgeArticle).filter(
                KnowledgeArticle.updated_at < cutoff_date,
                KnowledgeArticle.view_count < 5,
                KnowledgeArticle.usefulness_score < 2.0
            ).all()
            
            # Find outdated FAQs
            outdated_faqs = self.db.query(FAQ).filter(
                FAQ.updated_at < cutoff_date,
                FAQ.view_count < 3,
                FAQ.helpful_count < 2
            ).all()
            
            # Archive instead of delete
            archived_articles = 0
            archived_faqs = 0
            
            for article in outdated_articles:
                article.is_published = False
                archived_articles += 1
            
            for faq in outdated_faqs:
                faq.is_active = False
                archived_faqs += 1
            
            self.db.commit()
            
            return {
                'success': True,
                'archived_articles': archived_articles,
                'archived_faqs': archived_faqs,
                'cutoff_date': cutoff_date.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error cleaning up outdated content: {str(e)}")
            self.db.rollback()
            return {
                'success': False,
                'error': str(e),
                'archived_articles': 0,
                'archived_faqs': 0
            }
    
    def get_maintenance_analytics(self) -> Dict[str, Any]:
        """Get maintenance analytics and system health"""
        try:
            # Content statistics
            total_articles = self.db.query(KnowledgeArticle).count()
            published_articles = self.db.query(KnowledgeArticle).filter(
                KnowledgeArticle.is_published == True
            ).count()
            
            total_faqs = self.db.query(FAQ).count()
            active_faqs = self.db.query(FAQ).filter(FAQ.is_active == True).count()
            
            # Performance metrics
            avg_article_score = self.db.query(func.avg(KnowledgeArticle.usefulness_score)).scalar() or 0
            avg_faq_helpfulness = self.db.query(func.avg(FAQ.helpful_count)).scalar() or 0
            
            # Recent activity
            last_week = datetime.utcnow() - timedelta(days=7)
            recent_questions = self.db.query(UserQuestion).filter(
                UserQuestion.created_at >= last_week
            ).count()
            
            recent_feedback = self.db.query(ArticleFeedback).filter(
                ArticleFeedback.created_at >= last_week
            ).count()
            
            # Content gaps
            unanswered_questions = self.db.query(UserQuestion).filter(
                UserQuestion.was_answered == False
            ).count()
            
            return {
                'success': True,
                'content_stats': {
                    'total_articles': total_articles,
                    'published_articles': published_articles,
                    'total_faqs': total_faqs,
                    'active_faqs': active_faqs
                },
                'performance_metrics': {
                    'avg_article_score': round(avg_article_score, 2),
                    'avg_faq_helpfulness': round(avg_faq_helpfulness, 2)
                },
                'recent_activity': {
                    'questions_last_week': recent_questions,
                    'feedback_last_week': recent_feedback
                },
                'content_gaps': {
                    'unanswered_questions': unanswered_questions
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting maintenance analytics: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'content_stats': {},
                'performance_metrics': {},
                'recent_activity': {},
                'content_gaps': {}
            }
    
    def _extract_topics(self, text: str) -> List[str]:
        """Extract topics from question text"""
        topics = []
        
        # Common service-related keywords
        service_keywords = {
            'plomberie': ['plombier', 'fuite', 'tuyau', 'robinet', 'eau', 'douche', 'wc'],
            'électricité': ['électricien', 'panne', 'courant', 'lumière', 'prise', 'disjoncteur'],
            'électroménager': ['réfrigérateur', 'climatiseur', 'frigo', 'clim', 'machine', 'appareil'],
            'prix': ['prix', 'tarif', 'coût', 'combien', 'cher'],
            'délai': ['délai', 'temps', 'durée', 'rapidement', 'urgent'],
            'processus': ['comment', 'étapes', 'processus', 'procédure']
        }
        
        text_lower = text.lower()
        
        for topic, keywords in service_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                topics.append(topic)
        
        return topics
    
    def _generate_content_suggestions(self, service_analysis: Dict, 
                                    zone_analysis: Dict, topic_analysis: Dict) -> List[Dict]:
        """Generate suggestions for new content"""
        suggestions = []
        
        # Service-based suggestions
        for service_type, data in service_analysis.items():
            if data['count'] >= 3:  # At least 3 questions
                suggestions.append({
                    'type': 'article',
                    'title': f"Guide complet - {service_type}",
                    'reason': f"{data['count']} questions non résolues",
                    'priority': 'high' if data['count'] >= 5 else 'medium',
                    'service_type': service_type
                })
        
        # Topic-based suggestions
        for topic, data in topic_analysis.items():
            if data['count'] >= 2:
                suggestions.append({
                    'type': 'faq',
                    'title': f"FAQ - {topic}",
                    'reason': f"{data['count']} questions similaires",
                    'priority': 'medium',
                    'topic': topic
                })
        
        return suggestions
    
    def _analyze_feedback_patterns(self) -> Dict[str, Any]:
        """Analyze feedback patterns to identify improvement areas"""
        try:
            # Get feedback with comments
            feedback_with_comments = self.db.query(ArticleFeedback).filter(
                ArticleFeedback.comment.isnot(None)
            ).all()
            
            positive_patterns = []
            negative_patterns = []
            
            for feedback in feedback_with_comments:
                if feedback.is_helpful:
                    positive_patterns.append(feedback.comment)
                else:
                    negative_patterns.append(feedback.comment)
            
            return {
                'positive_feedback_count': len(positive_patterns),
                'negative_feedback_count': len(negative_patterns),
                'common_complaints': self._extract_common_phrases(negative_patterns),
                'common_praise': self._extract_common_phrases(positive_patterns)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing feedback patterns: {str(e)}")
            return {
                'positive_feedback_count': 0,
                'negative_feedback_count': 0,
                'common_complaints': [],
                'common_praise': []
            }
    
    def _extract_common_phrases(self, texts: List[str]) -> List[str]:
        """Extract common phrases from feedback texts"""
        if not texts:
            return []
        
        # Simple phrase extraction - in production, would use NLP
        word_counts = {}
        for text in texts:
            words = text.lower().split()
            for word in words:
                if len(word) > 3:  # Skip short words
                    word_counts[word] = word_counts.get(word, 0) + 1
        
        # Get most common words
        common_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        return [word for word, count in common_words if count > 1]
    
    def _generate_article_optimization_suggestions(self, article: KnowledgeArticle,
                                                 high_performing: List[KnowledgeArticle],
                                                 feedback_analysis: Dict) -> List[str]:
        """Generate optimization suggestions for an article"""
        suggestions = []
        
        # Length analysis
        if len(article.content) < 500:
            suggestions.append("Augmenter la longueur du contenu (actuellement < 500 caractères)")
        
        # Compare with high-performing articles
        if high_performing:
            avg_high_score = sum(a.usefulness_score for a in high_performing) / len(high_performing)
            if article.usefulness_score < avg_high_score * 0.7:
                suggestions.append("Revoir la structure et le contenu (score bien en dessous de la moyenne)")
        
        # Feedback-based suggestions
        if feedback_analysis['common_complaints']:
            suggestions.append("Vérifier les points mentionnés dans les commentaires négatifs")
        
        # View count analysis
        if article.view_count < 10:
            suggestions.append("Améliorer le titre et les mots-clés pour plus de visibilité")
        
        return suggestions
    
    def _group_similar_questions(self, threshold: int) -> List[Dict]:
        """Group similar questions together"""
        # Simple grouping by keywords - in production, would use NLP similarity
        questions = self.db.query(UserQuestion).filter(
            UserQuestion.was_answered == False
        ).all()
        
        groups = []
        
        # Group by service type and common keywords
        service_groups = {}
        for question in questions:
            service_type = question.service_type or 'general'
            if service_type not in service_groups:
                service_groups[service_type] = []
            service_groups[service_type].append(question)
        
        for service_type, service_questions in service_groups.items():
            if len(service_questions) >= threshold:
                groups.append({
                    'service_type': service_type,
                    'questions': [q.question_text for q in service_questions],
                    'count': len(service_questions),
                    'sample_question': service_questions[0].question_text
                })
        
        return groups
    
    def _generate_faq_from_group(self, group: Dict) -> Optional[Dict]:
        """Generate FAQ from a group of similar questions"""
        # Simple FAQ generation - in production, would use AI
        service_type = group['service_type']
        sample_question = group['sample_question']
        
        # Generate generic answer based on service type
        answers = {
            'plomberie': "Pour les problèmes de plomberie, nous recommandons de couper l'eau en premier lieu, puis de contacter un plombier qualifié via notre plateforme.",
            'électricité': "Pour les problèmes électriques, vérifiez d'abord les disjoncteurs et contactez un électricien qualifié si le problème persiste.",
            'électroménager': "Pour les réparations d'électroménager, contactez un technicien spécialisé via notre plateforme pour un diagnostic précis.",
            'general': "Contactez notre service client pour obtenir une assistance personnalisée selon vos besoins."
        }
        
        return {
            'question': sample_question,
            'answer': answers.get(service_type, answers['general']),
            'service_type': service_type,
            'keywords': self._extract_topics(sample_question)
        }