#!/usr/bin/env python3
"""
Script to create the default admin user for Djobea AI
Run this after setting up the database to create the initial admin account
"""

import os
import sys
import getpass
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import get_db, engine
from app.models.database_models import init_db, AdminRole
from app.services.auth_service import AuthService


def create_default_admin():
    """Create the default admin user"""
    print("🔐 Djobea AI Admin User Creation")
    print("=" * 40)
    
    # Initialize database
    print("Initializing database...")
    init_db(engine)
    
    # Get database session
    db = next(get_db())
    auth_service = AuthService(db)
    
    # Check if any admin users exist
    existing_admin = db.query(auth_service.get_user_by_username.__self__.__class__).first()
    if existing_admin:
        print("⚠️  Admin users already exist in the database.")
        choice = input("Do you want to create another admin user? (y/N): ").lower()
        if choice != 'y':
            print("Exiting...")
            return
    
    print("\nCreating admin user...")
    print("Please provide the following information:")
    
    # Get user input
    while True:
        username = input("Username: ").strip()
        if username and len(username) >= 3:
            # Check if username exists
            existing = auth_service.get_user_by_username(username)
            if existing:
                print("❌ Username already exists. Please choose another.")
                continue
            break
        print("❌ Username must be at least 3 characters long.")
    
    while True:
        email = input("Email: ").strip()
        if email and "@" in email and "." in email:
            break
        print("❌ Please enter a valid email address.")
    
    while True:
        password = getpass.getpass("Password: ")
        if len(password) >= 8:
            confirm_password = getpass.getpass("Confirm password: ")
            if password == confirm_password:
                break
            print("❌ Passwords do not match.")
        else:
            print("❌ Password must be at least 8 characters long.")
    
    while True:
        print("\nRole options:")
        print("1. Admin (can manage system)")
        print("2. Super Admin (can manage system and create users)")
        role_choice = input("Choose role (1 or 2): ").strip()
        
        if role_choice == "1":
            role = AdminRole.ADMIN
            break
        elif role_choice == "2":
            role = AdminRole.SUPER_ADMIN
            break
        else:
            print("❌ Please choose 1 or 2.")
    
    try:
        # Create the admin user
        admin_user = auth_service.create_admin_user(
            username=username,
            email=email,
            password=password,
            role=role
        )
        
        print(f"\n✅ Admin user created successfully!")
        print(f"   Username: {admin_user.username}")
        print(f"   Email: {admin_user.email}")
        print(f"   Role: {admin_user.role}")
        print(f"   ID: {admin_user.id}")
        
        print(f"\n🔗 You can now login at: http://localhost:5000/auth/login")
        print(f"   Or admin dashboard: http://localhost:5000/admin/")
        
    except Exception as e:
        print(f"❌ Error creating admin user: {e}")
        return False
    
    finally:
        db.close()
    
    return True


def setup_security_environment():
    """Setup security environment variables"""
    print("\n🔧 Security Environment Setup")
    print("=" * 40)
    
    # Check for required environment variables
    required_vars = [
        "JWT_SECRET_KEY",
        "ANTHROPIC_API_KEY", 
        "TWILIO_ACCOUNT_SID",
        "TWILIO_AUTH_TOKEN",
        "TWILIO_PHONE_NUMBER"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("⚠️  Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        
        print("\nPlease set these environment variables before running the application.")
        print("You can add them to your .env file or set them in your environment.")
        
        if "JWT_SECRET_KEY" in missing_vars:
            import secrets
            jwt_secret = secrets.token_urlsafe(32)
            print(f"\n💡 Suggestion for JWT_SECRET_KEY:")
            print(f"   JWT_SECRET_KEY={jwt_secret}")
        
        return False
    
    print("✅ All required environment variables are set.")
    return True


def main():
    """Main function"""
    print("🚀 Djobea AI Security Setup")
    print("=" * 50)
    
    # Check environment setup
    if not setup_security_environment():
        print("\n❌ Please fix environment setup first.")
        return
    
    print("\n" + "=" * 50)
    
    # Create admin user
    if create_default_admin():
        print("\n🎉 Setup completed successfully!")
        print("\nNext steps:")
        print("1. Start the application: python run.py")
        print("2. Visit the admin login page")
        print("3. Login with your admin credentials")
        print("4. Configure providers and start using the system")
    else:
        print("\n❌ Setup failed. Please check the errors above.")


if __name__ == "__main__":
    main()