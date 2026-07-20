"""
Database reset and seed script for RBAC redesign.
Run with: python reset_db.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.extensions import db
from app.models import User, UserRole, Project

app = create_app()

with app.app_context():
    print("Dropping all tables...")
    db.drop_all()
    print("Creating all tables...")
    db.create_all()

    # Create Main Admin
    admin = User(
        email="admin@southeast.com",
        full_name="Main Admin",
        role=UserRole.ADMIN,
        phone="+880-1700-000000",
        is_active=True,
        is_mfa_enabled=False,
        calendar_color="#6366f1",
        max_lead_capacity=999
    )
    admin.set_password("Admin@123")
    db.session.add(admin)

    # Create a sample Lead Owner
    lo1 = User(
        email="john@southeast.com",
        full_name="John Rahman",
        role=UserRole.LEAD_OWNER,
        phone="+880-1711-111111",
        is_active=True,
        is_mfa_enabled=False,
        calendar_color="#22c55e",  # Green
        max_lead_capacity=50
    )
    lo1.set_password("John@123")
    db.session.add(lo1)

    lo2 = User(
        email="sarah@southeast.com",
        full_name="Sarah Khan",
        role=UserRole.LEAD_OWNER,
        phone="+880-1722-222222",
        is_active=True,
        is_mfa_enabled=False,
        calendar_color="#f59e0b",  # Amber
        max_lead_capacity=50
    )
    lo2.set_password("Sarah@123")
    db.session.add(lo2)

    # Create a sample project
    project = Project(
        name="Elite Society",
        code="ELITE-SOC",
        description="Premium residential development in Dhaka",
        location="Bashundhara R/A, Dhaka",
        total_units=120,
        available_units=87,
        price_per_sqft=8500,
    )
    db.session.add(project)

    db.session.commit()
    print("\n[OK] Database reset complete!")
    print("\n=== Login Credentials ===")
    print("ADMIN:   admin@southeast.com  / Admin@123    -> goes to admin-dashboard.html")
    print("Owner 1: john@southeast.com   / John@123     -> goes to dashboard.html (Green)")
    print("Owner 2: sarah@southeast.com  / Sarah@123    -> goes to dashboard.html (Amber)")
    print("\nProject: Elite Society (ELITE-SOC)")
