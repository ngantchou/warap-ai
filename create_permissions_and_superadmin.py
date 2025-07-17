#!/usr/bin/env python3
"""
Script to create all permissions and roles from the frontend configuration
and create a super admin user with full access.
"""

import sys
import os
import uuid
import re
from datetime import datetime

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from app.database import get_db
from app.models.auth_models import User, UserRole, Permission, RolePermission
from sqlalchemy.exc import IntegrityError

def extract_permissions_from_config():
    """Extract all permissions from the config file"""
    config_file = "attached_assets/Pasted-import-PERMISSIONS-from-permissions-export-const-AUTH-CONFIG-API-BASE-URL-https--1752791813237_1752791813247.txt"
    
    permissions = set()
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Extract all PERMISSIONS.* references
        permission_pattern = r'PERMISSIONS\.([A-Z_]+)'
        matches = re.findall(permission_pattern, content)
        
        for match in matches:
            permissions.add(match)
            
        print(f"Found {len(permissions)} unique permissions")
        return sorted(list(permissions))
        
    except Exception as e:
        print(f"Error reading config file: {e}")
        return []

def parse_permission_name(perm_name):
    """Parse permission name to extract resource and action"""
    parts = perm_name.split('_')
    if len(parts) >= 2:
        resource = parts[0].lower()
        action = '_'.join(parts[1:]).lower()
        return resource, action
    else:
        return perm_name.lower(), 'access'

def create_permissions_in_db(permissions):
    """Create permissions in the database"""
    db = next(get_db())
    created_count = 0
    
    try:
        for perm_name in permissions:
            # Check if permission already exists
            existing = db.query(Permission).filter_by(name=perm_name).first()
            if not existing:
                # Parse resource and action from permission name
                resource, action = parse_permission_name(perm_name)
                
                # Create new permission
                permission = Permission(
                    name=perm_name,
                    description=f"Permission for {perm_name.lower().replace('_', ' ')}",
                    resource=resource,
                    action=action
                )
                db.add(permission)
                created_count += 1
                
        db.commit()
        print(f"Created {created_count} new permissions")
        return True
        
    except Exception as e:
        print(f"Error creating permissions: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def create_roles_in_db():
    """Create roles in the database"""
    db = next(get_db())
    created_count = 0
    
    roles = [
        ("super_admin", "Super Administrateur - Accès complet à toutes les fonctionnalités"),
        ("admin", "Administrateur - Gestion complète du système"),
        ("manager", "Manager - Gestion des équipes et des opérations"),
        ("operator", "Opérateur - Gestion des demandes et des prestataires"),
        ("viewer", "Lecteur - Consultation uniquement"),
        ("user", "Utilisateur - Accès utilisateur standard"),
        ("provider", "Prestataire - Accès prestataire de services")
    ]
    
    try:
        for role_name, description in roles:
            # Check if role already exists
            existing = db.query(UserRole).filter_by(name=role_name).first()
            if not existing:
                # Create new role
                role = UserRole(
                    name=role_name,
                    description=description
                )
                db.add(role)
                created_count += 1
                
        db.commit()
        print(f"Created {created_count} new roles")
        return True
        
    except Exception as e:
        print(f"Error creating roles: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def assign_super_admin_permissions():
    """Assign all permissions to super_admin role"""
    db = next(get_db())
    
    try:
        # Get super_admin role
        super_admin_role = db.query(UserRole).filter_by(name="super_admin").first()
        if not super_admin_role:
            print("Super admin role not found")
            return False
            
        # Get all permissions
        all_permissions = db.query(Permission).all()
        print(f"Found {len(all_permissions)} permissions to assign")
        
        assigned_count = 0
        
        for permission in all_permissions:
            # Check if assignment already exists
            existing = db.query(RolePermission).filter_by(
                role="super_admin",
                permission_id=permission.id
            ).first()
            
            if not existing:
                # Create new assignment
                role_permission = RolePermission(
                    role="super_admin",
                    permission_id=permission.id
                )
                db.add(role_permission)
                assigned_count += 1
                
        db.commit()
        print(f"Assigned {assigned_count} permissions to super_admin role")
        return True
        
    except Exception as e:
        print(f"Error assigning permissions: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    import bcrypt
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def create_super_admin_user():
    """Create a super admin user"""
    db = next(get_db())
    
    try:
        # Check if super admin user already exists
        existing_user = db.query(User).filter_by(email="superadmin@djobea.ai").first()
        if existing_user:
            print("Super admin user already exists")
            return {
                "email": "superadmin@djobea.ai",
                "password": "Contact admin for password",
                "role": "super_admin",
                "status": "already_exists"
            }
        
        # Create super admin user
        super_admin_user = User(
            id=str(uuid.uuid4()),
            username="superadmin",
            email="superadmin@djobea.ai",
            password_hash=hash_password("SuperAdmin2025!"),
            role="super_admin",
            first_name="Super",
            last_name="Admin",
            is_active=True,
            is_verified=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(super_admin_user)
        db.commit()
        
        print("Super admin user created successfully!")
        return {
            "email": "superadmin@djobea.ai",
            "password": "SuperAdmin2025!",
            "role": "super_admin",
            "status": "created"
        }
        
    except Exception as e:
        print(f"Error creating super admin user: {e}")
        db.rollback()
        return None
    finally:
        db.close()

def main():
    """Main function to set up permissions and super admin"""
    print("=== Djobea AI Permissions and Super Admin Setup ===")
    print()
    
    # Step 1: Extract permissions from config
    print("1. Extracting permissions from config file...")
    permissions = extract_permissions_from_config()
    if not permissions:
        print("❌ Failed to extract permissions")
        return
    
    print(f"✅ Extracted {len(permissions)} permissions")
    print()
    
    # Step 2: Create permissions in database
    print("2. Creating permissions in database...")
    if not create_permissions_in_db(permissions):
        print("❌ Failed to create permissions")
        return
    
    print("✅ Permissions created successfully")
    print()
    
    # Step 3: Create roles in database
    print("3. Creating roles in database...")
    if not create_roles_in_db():
        print("❌ Failed to create roles")
        return
    
    print("✅ Roles created successfully")
    print()
    
    # Step 4: Assign all permissions to super admin
    print("4. Assigning permissions to super admin role...")
    if not assign_super_admin_permissions():
        print("❌ Failed to assign permissions")
        return
    
    print("✅ Permissions assigned to super admin")
    print()
    
    # Step 5: Create super admin user
    print("5. Creating super admin user...")
    credentials = create_super_admin_user()
    if not credentials:
        print("❌ Failed to create super admin user")
        return
    
    print("✅ Super admin user setup complete!")
    print()
    
    # Display credentials
    print("=== SUPER ADMIN CREDENTIALS ===")
    print(f"Email: {credentials['email']}")
    print(f"Password: {credentials['password']}")
    print(f"Role: {credentials['role']}")
    print(f"Status: {credentials['status']}")
    print()
    
    if credentials['status'] == 'created':
        print("🎯 Super admin user created successfully!")
        print("🔒 Please store these credentials securely!")
    else:
        print("ℹ️  Super admin user already exists")
    
    print()
    print("=== SETUP COMPLETE ===")

if __name__ == "__main__":
    main()