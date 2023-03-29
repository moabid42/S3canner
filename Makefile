BACKEND_DIR = ./terraform/remote_state
TERRAFORM_ROOT = ./terraform

GREEN	=\033[32m
RED		=\033[31m
RESET	=\033[0m

deploy: require
	@if python3 main.py deploy; then \
		echo "Deployment succeeded!"; \
	else \
		echo "Deployment failed. You may have forgotten to set your credentials."; \
	fi

test:
	@if python3 main.py test; then \
		echo "Testing succeeded!"; \
	else \
		echo "Testing failed. You may have forgotten to set your credentials."; \
	fi

build:
	@if python3 main.py build; then \
		echo "Building succeeded!"; \
	else \
		echo "Building failed. You may have forgotten to set your credentials."; \
	fi

apply:
	@if python3 main.py apply; then \
		echo "Applying succeeded!"; \
	else \
		echo "Applying failed. You may have forgotten to set your credentials."; \
	fi

require:
	@pip install -r requirements.txt > /dev/null
	@echo "Requirements satisfied!"

terraform: backend
	terraform -chdir=$(TERRAFORM_ROOT) init
	terraform -chdir=$(TERRAFORM_ROOT) plan -out=tfplane
	terraform -chdir=$(TERRAFORM_ROOT) apply tfplane

backend:
	terraform -chdir=$(BACKEND_DIR) init && \
	terraform -chdir=$(BACKEND_DIR) apply

fclean:
	terraform -chdir=$(TERRAFORM_ROOT) destroy

.PHONY: all deploy test build apply require terraform backend flcean
