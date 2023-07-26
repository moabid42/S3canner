BACKEND_DIR = ./terraform/remote-state
TERRAFORM_ROOT = ./terraform

GREEN	=\033[32m
RED		=\033[31m
RESET	=\033[0m

deploy: require latest_version_init banner
	@python3 main.py deploy 1> /dev/null;
	@echo "Deployment succeeded!";

latest_version_init:
	@bash ./utils/latest_version.sh 

banner:
	@python3 main.py banner 

test: banner
	@python3 main.py test > /dev/null;
	@echo "Testing succeeded!";

build: banner
	@python3 main.py build > /dev/null;
	@echo "Building succeeded!";

apply: banner
	@python3 main.py apply > /dev/null;
	@echo "Applying succeeded!";

require:
	@echo "Installing requirements ~"
	@pip install -r requirements.txt > /dev/null
	@echo "Requirements satisfied!"

terraform: backend
	@terraform -chdir=$(TERRAFORM_ROOT) init
	@terraform -chdir=$(TERRAFORM_ROOT) plan -out=tfplane "1-lock=false"
	@terraform -chdir=$(TERRAFORM_ROOT) apply -auto-approve "-lock=false" tfplane

backend:
	@terraform -chdir=$(BACKEND_DIR) init && \
	terraform -chdir=$(BACKEND_DIR) apply

help: banner
	@echo -e 'Help:'
	@echo 'make deploy or make		Deploy S3canner. Equivalent to test + build + apply.'
	@echo 'make test			Run unit tests.'
	@echo 'make build			Build Lambda packages (saves *.zip files in terraform/).'
	@echo 'make apply			Terraform validate and apply any configuration/package changes.'
	@echo 'make require			Install the dependencies and requirement.'
	@echo 'make destroy			Destroy and delete all the resources'
	@echo 'make backend-destroy		Destroy and delete the backend'

destroy:
	@terraform -chdir=$(TERRAFORM_ROOT) destroy

backend-destroy:
	@terraform -chdir=$(BACKEND_DIR) destroy

.PHONY: all deploy test build apply require terraform backend destroy banner
