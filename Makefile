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
	cd local && python3 run_local.py

local-setup:
	@echo "Installing local dependencies..."
	pip install -r local/requirements.txt
	@echo "Making scripts executable..."
	chmod +x local/setup_local.sh local/run_local.py

local-stop:
	@echo "Stopping services..."
	docker-compose down

clean:
	@echo "Cleaning up..."
	rm -rf localstack-data/
	docker-compose down -v

test:
	@echo "Running tests..."
	@echo "Test user: username=test, password=test123"
	@echo "API: http://localhost:5000"
	@echo "Web: http://localhost:8080/index-local.html"
