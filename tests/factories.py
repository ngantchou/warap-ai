"""
Test Data Factories
Provides factory functions for creating test data consistently across test suites
"""

import random
import faker
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from app.models.database_models import (
    User, Provider, ServiceRequest, Transaction, Conversation, AdminUser,
    RequestStatus, TransactionStatus
)


fake = faker.Faker(['fr_FR', 'en_US'])  # French and English for Cameroon context


class UserFactory:
    """Factory for creating User test instances"""
    
    @staticmethod
    def create(
        whatsapp_id: Optional[str] = None,
        name: Optional[str] = None,
        phone_number: Optional[str] = None,
        **kwargs
    ) -> User:
        """Create a User instance with realistic Cameroon data"""
        if not whatsapp_id:
            # Generate Cameroon phone number
            prefixes = ['690', '691', '692', '693', '694', '695', '696', '697', '698', '699',  # MTN
                       '650', '651', '652', '653', '654', '655', '656', '657', '658', '659',  # Orange
                       '670', '671', '672', '673', '674', '675', '676', '677', '678', '679']  # Other operators
            prefix = random.choice(prefixes)
            suffix = fake.numerify('######')
            whatsapp_id = f"+237{prefix}{suffix}"
        
        if not phone_number:
            phone_number = whatsapp_id
            
        if not name:
            # Common Cameroon names
            first_names = [
                'Jean', 'Marie', 'Paul', 'Pierre', 'Jacques', 'Michel', 'André', 'François',
                'Ange', 'Divine', 'Grace', 'Patience', 'Blessing', 'Emmanuel', 'Joseph',
                'Akono', 'Biya', 'Etame', 'Fouda', 'Mballa', 'Ndzana', 'Owona'
            ]
            last_names = [
                'Dupont', 'Martin', 'Bernard', 'Durand', 'Moreau', 'Laurent', 'Simon',
                'Akono', 'Biya', 'Etame', 'Fouda', 'Mballa', 'Ndzana', 'Owona',
                'Mengue', 'Essomba', 'Atangana', 'Bekono', 'Belinga'
            ]
            name = f"{random.choice(first_names)} {random.choice(last_names)}"
        
        return User(
            whatsapp_id=whatsapp_id,
            name=name,
            phone_number=phone_number,
            created_at=kwargs.get('created_at', datetime.now()),
            **{k: v for k, v in kwargs.items() if k not in ['whatsapp_id', 'name', 'phone_number', 'created_at']}
        )
    
    @staticmethod
    def create_batch(count: int, **common_kwargs) -> List[User]:
        """Create multiple users with unique identifiers"""
        users = []
        for i in range(count):
            user_kwargs = common_kwargs.copy()
            if 'whatsapp_id' not in user_kwargs:
                user_kwargs['whatsapp_id'] = f"+23769{i:07d}"
            if 'phone_number' not in user_kwargs:
                user_kwargs['phone_number'] = user_kwargs['whatsapp_id']
            users.append(UserFactory.create(**user_kwargs))
        return users


class ProviderFactory:
    """Factory for creating Provider test instances"""
    
    @staticmethod
    def create(
        name: Optional[str] = None,
        whatsapp_id: Optional[str] = None,
        phone_number: Optional[str] = None,
        services: Optional[List[str]] = None,
        coverage_areas: Optional[List[str]] = None,
        is_available: bool = True,
        is_active: bool = True,
        rating: Optional[float] = None,
        **kwargs
    ) -> Provider:
        """Create a Provider instance with realistic service provider data"""
        if not whatsapp_id:
            # Provider phone numbers
            prefixes = ['690', '691', '650', '651', '670', '671']
            prefix = random.choice(prefixes)
            suffix = fake.numerify('######')
            whatsapp_id = f"+237{prefix}{suffix}"
        
        if not phone_number:
            phone_number = whatsapp_id
        
        if not name:
            # Common provider business names in Cameroon
            business_types = ['Plomberie', 'Électricité', 'Réparation']
            owner_names = ['Jean', 'Marie', 'Paul', 'André', 'François', 'Joseph']
            areas = ['Douala', 'Bonamoussadi', 'Akwa', 'Bonapriso']
            
            business = random.choice(business_types)
            owner = random.choice(owner_names)
            area = random.choice(areas)
            name = f"{business} {owner} - {area}"
        
        if services is None:
            available_services = ['plomberie', 'électricité', 'réparation électroménager']
            services = [random.choice(available_services)]
        
        if coverage_areas is None:
            areas = ['Bonamoussadi', 'Akwa', 'Bonapriso', 'Deido', 'New Bell', 'Makepe']
            coverage_areas = [random.choice(areas)]
        
        if rating is None:
            rating = round(random.uniform(3.0, 5.0), 1)
        
        return Provider(
            name=name,
            whatsapp_id=whatsapp_id,
            phone_number=phone_number,
            services=services,
            coverage_areas=coverage_areas,
            is_available=is_available,
            is_active=is_active,
            rating=rating,
            total_jobs=kwargs.get('total_jobs', random.randint(0, 100)),
            successful_jobs=kwargs.get('successful_jobs', random.randint(0, kwargs.get('total_jobs', 50))),
            created_at=kwargs.get('created_at', datetime.now()),
            **{k: v for k, v in kwargs.items() if k not in [
                'name', 'whatsapp_id', 'phone_number', 'services', 'coverage_areas',
                'is_available', 'is_active', 'rating', 'total_jobs', 'successful_jobs', 'created_at'
            ]}
        )
    
    @staticmethod
    def create_batch(count: int, **common_kwargs) -> List[Provider]:
        """Create multiple providers with unique identifiers"""
        providers = []
        for i in range(count):
            provider_kwargs = common_kwargs.copy()
            if 'whatsapp_id' not in provider_kwargs:
                provider_kwargs['whatsapp_id'] = f"+23768{i:07d}"
            if 'phone_number' not in provider_kwargs:
                provider_kwargs['phone_number'] = provider_kwargs['whatsapp_id']
            providers.append(ProviderFactory.create(**provider_kwargs))
        return providers


class ServiceRequestFactory:
    """Factory for creating ServiceRequest test instances"""
    
    @staticmethod
    def create(
        user_id: Optional[int] = None,
        provider_id: Optional[int] = None,
        service_type: Optional[str] = None,
        description: Optional[str] = None,
        location: Optional[str] = None,
        status: RequestStatus = RequestStatus.PENDING,
        urgency: Optional[str] = None,
        **kwargs
    ) -> ServiceRequest:
        """Create a ServiceRequest instance with realistic request data"""
        if service_type is None:
            service_type = random.choice(['plomberie', 'électricité', 'réparation électroménager'])
        
        if description is None:
            descriptions = {
                'plomberie': [
                    'Fuite d\'eau dans la cuisine',
                    'Robinet cassé dans la salle de bain',
                    'Problème de drainage',
                    'Tuyau bouché',
                    'Installation nouvelle douche'
                ],
                'électricité': [
                    'Panne de courant dans la maison',
                    'Prise électrique qui ne marche pas',
                    'Installation nouveau compteur',
                    'Problème avec les ampoules',
                    'Court-circuit dans la cuisine'
                ],
                'réparation électroménager': [
                    'Réfrigérateur ne refroidit plus',
                    'Machine à laver fait du bruit',
                    'Climatiseur ne marche pas',
                    'Four micro-ondes cassé',
                    'Télévision écran noir'
                ]
            }
            description = random.choice(descriptions.get(service_type, ['Problème général']))
        
        if location is None:
            locations = ['Bonamoussadi', 'Akwa', 'Bonapriso', 'Deido', 'New Bell', 'Makepe']
            location = random.choice(locations)
        
        if urgency is None:
            urgency = random.choice(['normal', 'urgent', 'très urgent'])
        
        return ServiceRequest(
            user_id=user_id or 1,
            provider_id=provider_id,
            service_type=service_type,
            description=description,
            location=location,
            status=status,
            urgency=urgency,
            preferred_time=kwargs.get('preferred_time', 'maintenant'),
            final_cost=kwargs.get('final_cost'),
            created_at=kwargs.get('created_at', datetime.now()),
            accepted_at=kwargs.get('accepted_at'),
            completed_at=kwargs.get('completed_at'),
            **{k: v for k, v in kwargs.items() if k not in [
                'user_id', 'provider_id', 'service_type', 'description', 'location',
                'status', 'urgency', 'preferred_time', 'final_cost', 'created_at',
                'accepted_at', 'completed_at'
            ]}
        )


class TransactionFactory:
    """Factory for creating Transaction test instances"""
    
    @staticmethod
    def create(
        service_request_id: Optional[int] = None,
        customer_id: Optional[int] = None,
        provider_id: Optional[int] = None,
        amount: Optional[float] = None,
        status: TransactionStatus = TransactionStatus.PENDING,
        **kwargs
    ) -> Transaction:
        """Create a Transaction instance with realistic payment data"""
        if amount is None:
            # Common service costs in FCFA
            service_costs = {
                'plomberie': [5000, 8000, 12000, 15000, 20000, 25000],
                'électricité': [3000, 6000, 10000, 15000, 18000, 22000],
                'réparation électroménager': [8000, 12000, 18000, 25000, 30000, 35000]
            }
            amount = random.choice([5000, 8000, 10000, 12000, 15000, 18000, 20000, 25000])
        
        commission = amount * 0.15  # 15% commission
        provider_payout = amount - commission
        
        payment_reference = kwargs.get('payment_reference', 
                                     f"djobea_{service_request_id or random.randint(1000, 9999)}_{random.randint(100, 999)}")
        
        return Transaction(
            service_request_id=service_request_id or 1,
            customer_id=customer_id or 1,
            provider_id=provider_id or 1,
            amount=amount,
            commission=commission,
            provider_payout=provider_payout,
            status=status,
            payment_reference=payment_reference,
            monetbil_transaction_id=kwargs.get('monetbil_transaction_id'),
            failure_reason=kwargs.get('failure_reason'),
            created_at=kwargs.get('created_at', datetime.now()),
            completed_at=kwargs.get('completed_at'),
            **{k: v for k, v in kwargs.items() if k not in [
                'service_request_id', 'customer_id', 'provider_id', 'amount',
                'commission', 'provider_payout', 'status', 'payment_reference',
                'monetbil_transaction_id', 'failure_reason', 'created_at', 'completed_at'
            ]}
        )


class ConversationFactory:
    """Factory for creating Conversation test instances"""
    
    @staticmethod
    def create(
        user_id: Optional[int] = None,
        request_id: Optional[int] = None,
        message_type: str = 'incoming',
        message_content: Optional[str] = None,
        **kwargs
    ) -> Conversation:
        """Create a Conversation instance with realistic message data"""
        if message_content is None:
            if message_type == 'incoming':
                messages = [
                    'Bonjour, j\'ai un problème de plomberie',
                    'Mon robinet fuit dans la cuisine',
                    'C\'est urgent, il y a de l\'eau partout',
                    'Pouvez-vous m\'aider?',
                    'Merci beaucoup',
                    'À quelle heure pouvez-vous venir?',
                    'D\'accord, j\'attends',
                    'Le problème est résolu, merci!'
                ]
            else:  # outgoing
                messages = [
                    'Bonjour! Comment puis-je vous aider?',
                    'Je comprends votre problème de plomberie',
                    'Je cherche un plombier disponible dans votre zone',
                    'J\'ai trouvé un plombier qui peut vous aider',
                    'Il arrivera dans 30 minutes',
                    'Le plombier est en route',
                    'Votre demande a été complétée avec succès',
                    'N\'hésitez pas à nous contacter pour d\'autres services'
                ]
            message_content = random.choice(messages)
        
        return Conversation(
            user_id=user_id or 1,
            request_id=request_id,
            message_type=message_type,
            message_content=message_content,
            timestamp=kwargs.get('timestamp', datetime.now()),
            **{k: v for k, v in kwargs.items() if k not in [
                'user_id', 'request_id', 'message_type', 'message_content', 'timestamp'
            ]}
        )


class AdminUserFactory:
    """Factory for creating AdminUser test instances"""
    
    @staticmethod
    def create(
        username: Optional[str] = None,
        email: Optional[str] = None,
        password: str = "TestPassword123!",
        role: str = "admin",
        is_active: bool = True,
        **kwargs
    ) -> AdminUser:
        """Create an AdminUser instance for testing"""
        if username is None:
            username = fake.user_name()
        
        if email is None:
            email = fake.email()
        
        # Hash password (in real implementation, this would use bcrypt)
        hashed_password = f"$2b$12$hashed_{password}"
        
        return AdminUser(
            username=username,
            email=email,
            hashed_password=hashed_password,
            role=role,
            is_active=is_active,
            created_at=kwargs.get('created_at', datetime.now()),
            last_login=kwargs.get('last_login'),
            **{k: v for k, v in kwargs.items() if k not in [
                'username', 'email', 'hashed_password', 'role', 'is_active',
                'created_at', 'last_login'
            ]}
        )


class TestScenarioFactory:
    """Factory for creating complete test scenarios"""
    
    @staticmethod
    def create_complete_service_scenario(
        user_id: Optional[int] = None,
        provider_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Create a complete service scenario from user request to payment"""
        
        # Create user if not provided
        user = None
        if user_id is None:
            user = UserFactory.create()
            user_id = 1  # Assume ID 1 for testing
        
        # Create provider if not provided
        provider = None
        if provider_id is None:
            provider = ProviderFactory.create()
            provider_id = 1  # Assume ID 1 for testing
        
        # Create service request
        service_request = ServiceRequestFactory.create(
            user_id=user_id,
            provider_id=provider_id,
            status=RequestStatus.COMPLETED,
            final_cost=15000
        )
        
        # Create conversation history
        conversations = [
            ConversationFactory.create(
                user_id=user_id,
                request_id=1,  # Assume ID 1 for testing
                message_type='incoming',
                message_content='J\'ai une fuite d\'eau dans ma cuisine'
            ),
            ConversationFactory.create(
                user_id=user_id,
                request_id=1,
                message_type='outgoing',
                message_content='Je comprends votre problème. Je cherche un plombier disponible.'
            ),
            ConversationFactory.create(
                user_id=user_id,
                request_id=1,
                message_type='outgoing',
                message_content='J\'ai trouvé un plombier qui peut vous aider dans 30 minutes.'
            )
        ]
        
        # Create transaction
        transaction = TransactionFactory.create(
            service_request_id=1,  # Assume ID 1 for testing
            customer_id=user_id,
            provider_id=provider_id,
            amount=15000,
            status=TransactionStatus.COMPLETED
        )
        
        return {
            'user': user,
            'provider': provider,
            'service_request': service_request,
            'conversations': conversations,
            'transaction': transaction
        }
    
    @staticmethod
    def create_timeout_scenario() -> Dict[str, Any]:
        """Create a scenario where provider doesn't respond in time"""
        user = UserFactory.create()
        provider = ProviderFactory.create()
        
        service_request = ServiceRequestFactory.create(
            user_id=1,
            provider_id=1,
            status=RequestStatus.TIMEOUT,
            created_at=datetime.now() - timedelta(minutes=15)
        )
        
        conversations = [
            ConversationFactory.create(
                user_id=1,
                request_id=1,
                message_type='incoming',
                message_content='Service urgent requis'
            ),
            ConversationFactory.create(
                user_id=1,
                request_id=1,
                message_type='outgoing',
                message_content='Recherche d\'un prestataire...'
            ),
            ConversationFactory.create(
                user_id=1,
                request_id=1,
                message_type='outgoing',
                message_content='Le prestataire ne répond pas. Recherche d\'une alternative...'
            )
        ]
        
        return {
            'user': user,
            'provider': provider,
            'service_request': service_request,
            'conversations': conversations
        }
    
    @staticmethod
    def create_payment_failure_scenario() -> Dict[str, Any]:
        """Create a scenario where payment fails"""
        scenario = TestScenarioFactory.create_complete_service_scenario()
        
        # Modify transaction to failed status
        scenario['transaction'].status = TransactionStatus.FAILED
        scenario['transaction'].failure_reason = "Insufficient funds"
        
        return scenario


class MockDataGenerator:
    """Generate large datasets for performance testing"""
    
    @staticmethod
    def generate_users(count: int) -> List[User]:
        """Generate large number of users for load testing"""
        return UserFactory.create_batch(count)
    
    @staticmethod
    def generate_providers(count: int, services: Optional[List[str]] = None) -> List[Provider]:
        """Generate providers with specific services"""
        if services is None:
            services = ['plomberie', 'électricité', 'réparation électroménager']
        
        providers = []
        for i in range(count):
            provider_services = [random.choice(services)]
            provider = ProviderFactory.create(
                services=provider_services,
                whatsapp_id=f"+23768{i:07d}"
            )
            providers.append(provider)
        
        return providers
    
    @staticmethod
    def generate_service_requests(count: int, user_ids: List[int], provider_ids: List[int]) -> List[ServiceRequest]:
        """Generate service requests linking users and providers"""
        requests = []
        
        for i in range(count):
            user_id = random.choice(user_ids)
            provider_id = random.choice(provider_ids) if random.random() > 0.3 else None
            
            status_weights = [
                (RequestStatus.PENDING, 0.2),
                (RequestStatus.PROVIDER_NOTIFIED, 0.1),
                (RequestStatus.ASSIGNED, 0.15),
                (RequestStatus.IN_PROGRESS, 0.1),
                (RequestStatus.COMPLETED, 0.35),
                (RequestStatus.CANCELLED, 0.05),
                (RequestStatus.TIMEOUT, 0.05)
            ]
            
            status = random.choices(
                [s[0] for s in status_weights],
                weights=[s[1] for s in status_weights]
            )[0]
            
            request = ServiceRequestFactory.create(
                user_id=user_id,
                provider_id=provider_id,
                status=status,
                created_at=fake.date_time_between(start_date='-30d', end_date='now')
            )
            requests.append(request)
        
        return requests
    
    @staticmethod
    def generate_complete_dataset(
        users_count: int = 100,
        providers_count: int = 20,
        requests_count: int = 200
    ) -> Dict[str, List[Any]]:
        """Generate a complete dataset for comprehensive testing"""
        
        users = MockDataGenerator.generate_users(users_count)
        providers = MockDataGenerator.generate_providers(providers_count)
        
        user_ids = list(range(1, users_count + 1))
        provider_ids = list(range(1, providers_count + 1))
        
        requests = MockDataGenerator.generate_service_requests(
            requests_count, user_ids, provider_ids
        )
        
        # Generate transactions for completed requests
        transactions = []
        for i, request in enumerate(requests):
            if request.status == RequestStatus.COMPLETED and random.random() > 0.3:
                transaction = TransactionFactory.create(
                    service_request_id=i + 1,
                    customer_id=request.user_id,
                    provider_id=request.provider_id,
                    status=random.choice([
                        TransactionStatus.COMPLETED,
                        TransactionStatus.FAILED,
                        TransactionStatus.PENDING
                    ])
                )
                transactions.append(transaction)
        
        return {
            'users': users,
            'providers': providers,
            'service_requests': requests,
            'transactions': transactions
        }