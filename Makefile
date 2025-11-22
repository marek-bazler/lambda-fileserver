.PHONY: local-start local-setup local-stop test clean

local-start:
	@echo "Starting LocalStack..."
	docker-compose up -d
	@echo "Waiting for LocalStack to be ready..."
	@sleep 5
	@echo "Setting up local AWS resources..."
	./local/setup_local.sh
	@echo ""
	@echo "Starting local API server..."
	@echo "Open http://localhost:8080/index-local.html in your browser"
	@if [ -d .venv ]; then \
		cd local && ../.venv/bin/python run_local.py; \
	else \
		cd local && python3 run_local.py; \
	fi

local-setup:
	@echo "Creating virtual environment..."
	python3 -m venv .venv
	@echo "Installing local dependencies..."
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r local/requirements.txt
	@echo "Making scripts executable..."
	chmod +x local/setup_local.sh local/run_local.py
	@echo ""
	@echo "Setup complete! Virtual environment created in .venv/"

local-stop:
	@echo "Stopping services..."
	docker-compose down

clean:
	@echo "Cleaning up..."
	rm -rf localstack-data/
	rm -rf .venv/
	docker-compose down -v

test:
	@echo "Running tests..."
	@echo "Test user: username=test, password=test123"
	@echo "API: http://localhost:5000"
	@echo "Web: http://localhost:8080/index-local.html"
