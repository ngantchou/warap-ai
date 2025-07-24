"""
Permission Service for Djobea AI
Manages user permissions and role-based access control
"""

from sqlalchemy.orm import Session
from typing import List, Dict, Any
from datetime import datetime

from app.database import get_db
from app.models.auth_models import UserRole, Permission, RolePermission

class PermissionService:
    """Service for managing permissions and roles"""
    
    def __init__(self):
        self.default_permissions = {
            "user": [
                "read:profile",
                "update:profile",
                "create:request",
                "read:request",
                "update:request",
                "cancel:request"
            ],
            "provider": [
                "read:profile",
                "update:profile",
                "read:provider_dashboard",
                "update:provider_profile",
                "read:requests",
                "accept:request",
                "update:request_status",
                "manage:availability"
            ],
            "admin": [
                "read:profile",
                "update:profile",
                "read:admin_dashboard",
                "manage:users",
                "manage:providers",
                "manage:requests",
                "manage:system",
                "read:analytics",
                "manage:permissions",
                "manage:roles"
            ]
        }
    
    def initialize_default_permissions(self, db: Session = None) -> bool:
        """Initialize default permissions and roles"""
        if not db:
            db = next(get_db())
        
        try:
            # Create default roles
            for role_name in self.default_permissions.keys():
                existing_role = db.query(UserRole).filter(UserRole.name == role_name).first()
                if not existing_role:
                    role = UserRole(
                        name=role_name,
                        description=f"Default {role_name} role",
                        is_active=True
                    )
                    db.add(role)
            
            # Create default permissions
            all_permissions = set()
            for perms in self.default_permissions.values():
                all_permissions.update(perms)
            
            for perm_name in all_permissions:
                existing_perm = db.query(Permission).filter(Permission.name == perm_name).first()
                if not existing_perm:
                    # Parse permission name to get resource and action
                    parts = perm_name.split(':')
                    action = parts[0]
                    resource = parts[1] if len(parts) > 1 else 'general'
                    
                    permission = Permission(
                        name=perm_name,
                        description=f"Permission to {action} {resource}",
                        resource=resource,
                        action=action,
                        is_active=True
                    )
                    db.add(permission)
            
            db.commit()
            
            # Assign permissions to roles
            for role_name, permissions in self.default_permissions.items():
                role = db.query(UserRole).filter(UserRole.name == role_name).first()
                if role:
                    for perm_name in permissions:
                        permission = db.query(Permission).filter(Permission.name == perm_name).first()
                        if permission:
                            # Check if role-permission mapping already exists
                            existing_mapping = db.query(RolePermission).filter(
                                RolePermission.role == role_name,
                                RolePermission.permission_id == permission.id
                            ).first()
                            
                            if not existing_mapping:
                                role_perm = RolePermission(
                                    role=role_name,
                                    permission_id=permission.id
                                )
                                db.add(role_perm)
            
            db.commit()
            return True
            
        except Exception as e:
            db.rollback()
            raise e
    
    def get_role_permissions(self, role_name: str, db: Session = None) -> List[str]:
        """Get permissions for a specific role"""
        if not db:
            db = next(get_db())
        
        role_permissions = db.query(RolePermission).join(Permission).filter(
            RolePermission.role == role_name,
            Permission.is_active == True
        ).all()
        
        return [rp.permission.name for rp in role_permissions]
    
    def check_permission(self, user_role: str, permission: str, db: Session = None) -> bool:
        """Check if a role has a specific permission"""
        if not db:
            db = next(get_db())
        
        role_permissions = self.get_role_permissions(user_role, db)
        return permission in role_permissions
    
    def add_permission_to_role(self, role_name: str, permission_name: str, db: Session = None) -> bool:
        """Add a permission to a role"""
        if not db:
            db = next(get_db())
        
        try:
            # Check if role exists
            role = db.query(UserRole).filter(UserRole.name == role_name).first()
            if not role:
                return False
            
            # Check if permission exists
            permission = db.query(Permission).filter(Permission.name == permission_name).first()
            if not permission:
                return False
            
            # Check if mapping already exists
            existing_mapping = db.query(RolePermission).filter(
                RolePermission.role == role_name,
                RolePermission.permission_id == permission.id
            ).first()
            
            if existing_mapping:
                return True  # Already exists
            
            # Create new mapping
            role_perm = RolePermission(
                role=role_name,
                permission_id=permission.id
            )
            db.add(role_perm)
            db.commit()
            return True
            
        except Exception as e:
            db.rollback()
            raise e
    
    def remove_permission_from_role(self, role_name: str, permission_name: str, db: Session = None) -> bool:
        """Remove a permission from a role"""
        if not db:
            db = next(get_db())
        
        try:
            permission = db.query(Permission).filter(Permission.name == permission_name).first()
            if not permission:
                return False
            
            mapping = db.query(RolePermission).filter(
                RolePermission.role == role_name,
                RolePermission.permission_id == permission.id
            ).first()
            
            if mapping:
                db.delete(mapping)
                db.commit()
                return True
            
            return False
            
        except Exception as e:
            db.rollback()
            raise e
    
    def create_custom_permission(self, name: str, description: str, resource: str, action: str, db: Session = None) -> Permission:
        """Create a custom permission"""
        if not db:
            db = next(get_db())
        
        try:
            # Check if permission already exists
            existing_perm = db.query(Permission).filter(Permission.name == name).first()
            if existing_perm:
                return existing_perm
            
            permission = Permission(
                name=name,
                description=description,
                resource=resource,
                action=action,
                is_active=True
            )
            db.add(permission)
            db.commit()
            db.refresh(permission)
            return permission
            
        except Exception as e:
            db.rollback()
            raise e
    
    def get_all_permissions(self, db: Session = None) -> List[Permission]:
        """Get all permissions"""
        if not db:
            db = next(get_db())
        
        return db.query(Permission).filter(Permission.is_active == True).all()
    
    def get_all_roles(self, db: Session = None) -> List[UserRole]:
        """Get all roles"""
        if not db:
            db = next(get_db())
        
        return db.query(UserRole).filter(UserRole.is_active == True).all()

# Global permission service instance
permission_service = PermissionService()