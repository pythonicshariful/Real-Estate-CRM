"""
CLI commands for the CRM application.
Run via: flask <command>
"""

import click
from flask import current_app
from flask.cli import with_appcontext

from .extensions import db
from .models import User, Project


@click.command("create-admin")
@click.option("--email", prompt="Admin Email", help="Admin user email address")
@click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True, help="Admin password")
@click.option("--name", prompt="Full Name", default="System Administrator")
@with_appcontext
def create_admin_command(email, password, name):
    """Create a System Administrator account."""
    existing = User.query.filter_by(email=email).first()
    if existing:
        click.echo(f"❌ User with email '{email}' already exists.", err=True)
        return

    from app.utils.security import validate_password
    is_valid, msg = validate_password(password)
    if not is_valid:
        click.echo(f"❌ Invalid password: {msg}", err=True)
        return

    admin = User(
        email=email,
        full_name=name,
        role="ADMIN",
        is_active=True,
        is_mfa_enabled=True,
    )
    admin.set_password(password)
    db.session.add(admin)
    db.session.commit()
    click.echo(f"✅ Admin user '{email}' created successfully (Role: ADMIN)")
    click.echo("⚠️  Please set up MFA on first login.")


@click.command("create-sample-data")
@with_appcontext
def create_sample_data_command():
    """Seed the database with sample data for development/testing."""
    # Create sample project
    project = Project.query.filter_by(code="ELITE-SOC").first()
    if not project:
        project = Project(
            name="Elite Society",
            code="ELITE-SOC",
            description="Premium residential development in Dhaka",
            location="Bashundhara R/A, Dhaka",
            total_units=120,
            available_units=87,
            price_per_sqft=8500,
            status="ACTIVE",
        )
        db.session.add(project)

    # Create sample executive user
    exec_user = User.query.filter_by(email="exec@southeast.com").first()
    if not exec_user:
        exec_user = User(
            email="exec@southeast.com",
            full_name="Md. Rahim Executive",
            role="EXECUTIVE",
            phone="+8801712345678",
            is_active=True,
            is_mfa_enabled=False,
            max_lead_capacity=30,
        )
        exec_user.set_password("Executive@123")
        db.session.add(exec_user)

    # Create sample manager
    manager = User.query.filter_by(email="manager@southeast.com").first()
    if not manager:
        manager = User(
            email="manager@southeast.com",
            full_name="Ms. Fatema Manager",
            role="MANAGER",
            phone="+8801812345678",
            is_active=True,
            is_mfa_enabled=True,
            max_lead_capacity=50,
        )
        manager.set_password("Manager@123!")
        db.session.add(manager)

    db.session.commit()
    click.echo("✅ Sample data created:")
    click.echo("   Project: Elite Society (ELITE-SOC)")
    click.echo("   Executive: exec@southeast.com / Executive@123")
    click.echo("   Manager: manager@southeast.com / Manager@123!")
    click.echo("⚠️  Change all passwords before production use!")


@click.command("reset-db")
@click.option("--confirm", is_flag=True, help="Confirm database reset")
@with_appcontext
def reset_db_command(confirm):
    """Drop and recreate all database tables. USE WITH EXTREME CAUTION."""
    if not confirm:
        click.echo("❌ You must pass --confirm to reset the database", err=True)
        return

    if not current_app.debug:
        click.echo("❌ Database reset is only allowed in DEBUG mode", err=True)
        return

    click.echo("⚠️  Dropping all tables...")
    db.drop_all()
    click.echo("⚠️  Creating all tables...")
    db.create_all()
    click.echo("✅ Database reset complete.")


def register_commands(app):
    """Register all CLI commands with the Flask app."""
    app.cli.add_command(create_admin_command)
    app.cli.add_command(create_sample_data_command)
    app.cli.add_command(reset_db_command)
