.PHONY: up down migrate createsuperadmin logs backup shell

# Start all containers in the background
up:
	docker-compose up -d

# Stop and remove all containers
down:
	docker-compose down

# Run database migrations
migrate:
	docker-compose exec backend flask db upgrade

# Create a superadmin user
createsuperadmin:
	docker-compose exec backend flask create-admin

# View logs of all containers
logs:
	docker-compose logs -f

# Trigger a manual backup
backup:
	docker-compose exec backend flask backup

# Open a Flask shell in the backend container
shell:
	docker-compose exec backend flask shell
