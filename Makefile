# Define the location of the source code
FRAMEWORK := fuzzsdn
APP_SRC_DIR := src/fuzzsdn-app
FUZZER_SRC_DIR := src/fuzzsdn-fuzzer
VERSION := $(shell cat VERSION)

POETRY := $(shell command -v poetry 2> /dev/null)
MVN := $(shell command -v mvn 2> /dev/null)

USER_HOME := $(shell echo ~)
BIN_PATH  := $(USER_HOME)/.local/bin

# ======================================================================================================================
# Default target
# ======================================================================================================================

.DEFAULT_GOAL := help

# ======================================================================================================================
# Help target
# ======================================================================================================================

.PHONY: help
## Display this help message {FRAMEWORK}
help:
	@printf "Usage:\n"
	@printf "	make [target]\n\n"
	@printf "Available targets:\n"
	@awk '/^[a-zA-Z\-_0-9%:\\]+/ { \
		helpMessage = match(lastLine, /^## (.*)/); \
		if (helpMessage) { \
			helpCommand = $$1; \
			helpMessage = substr(lastLine, RSTART + 3, RLENGTH); \
			gsub("\\\\", "", helpCommand); \
			gsub(":+$$", "", helpCommand); \
			printf "  \x1b[32;01m%-35s\x1b[0m %s\n", helpCommand, helpMessage; \
		} \
	} \
	{ lastLine = $$0 }' $(MAKEFILE_LIST) | sed -e s/\{FRAMEWORK\}/$(FRAMEWORK)/g | sort -u
	@printf "\n"

# ======================================================================================================================
# Clean target
# ======================================================================================================================

.PHONY: clean
## Clean up the project directories
clean:
	@echo "Cleaning up generated files and artifacts..."
	rm -rf $(APP_SRC_DIR)/__pycache__
	rm -rf $(APP_SRC_DIR)/*.egg-info
	rm -rf $(APP_SRC_DIR)/venv
	rm -rf $(APP_SRC_DIR)/dist
	rm -rf $(FUZZER_SRC_DIR)/target
	rm -rf dist
	@echo "Done"

# ======================================================================================================================
# Install
# ======================================================================================================================

.PHONY: install
## Install {FRAMEWORK}'s dependencies
install:

	@echo "Installing the dependencies for the application..."
	cd $(APP_SRC_DIR) && poetry install

	@echo "Installing dependencies using for the fuzzer..."
	cd $(FUZZER_SRC_DIR) && mvn clean install

	@echo "Done"
# End of install target

.PHONY: uninstall
## Uninstall {FRAMEWORK}'s dependencies
uninstall:
	@echo "Uninstalling the dependencies for the application..."
	cd $(APP_SRC_DIR) && poetry uninstall -y

	@echo "Uninstalling dependencies using for the fuzzer..."
	cd $(FUZZER_SRC_DIR) && mvn clean

	@echo "Done"

# ======================================================================================================================
# Test targets
# ======================================================================================================================

.PHONY: fuzzer/test
## Run tests for {FRAMEWORK}'s fuzzer
fuzzer/test:
	@echo "Running tests for $(FRAMEWORK)'s fuzzer..."
	cd $(FUZZER_SRC_DIR) && mvn test
	@echo "Done"

.PHONY: test
## Run all tests
test: fuzzer/test
# End of test target

# ======================================================================================================================
# Build targets
# ======================================================================================================================

app_dist        := dist/$(FRAMEWORK)-$(VERSION)-py3-none-any.whl
app_src_dist    := $(APP_SRC_DIR)/dist/$(FRAMEWORK)-$(VERSION)-py3-none-any.whl
fuzzer_dist     := dist/$(FRAMEWORK)-fuzzer-$(VERSION).jar
fuzzer_src_dist := $(FUZZER_SRC_DIR)/target/$(FRAMEWORK)-fuzzer-$(VERSION).jar

.PHONY: build
## Build {FRAMEWORK}'s application and fuzzer artifacts and place them in the dist directory
build: $(app_dist) $(fuzzer_dist)

.PHONY: app/build
## Build {FRAMEWORK}'s application artifact and place it in the dist directory
app/build: $(app_dist)

.PHONY: fuzzer/build
## Build {FRAMEWORK}'s fuzzer artifact and place it in the dist directory
fuzzer/build: $(fuzzer_dist)

$(app_dist): $(app_src_dist)
	mkdir -p dist
	cp $< $@

$(app_src_dist):
	cd $(APP_SRC_DIR) && poetry run pip install --upgrade pip
	cd $(APP_SRC_DIR) && poetry run pip install --upgrade setuptools
	cd $(APP_SRC_DIR) && poetry run pip install setuptools_rust
	cd $(APP_SRC_DIR) && poetry run pip install numpy
	cd $(APP_SRC_DIR) && poetry run pip install python-javabridge
	cd $(APP_SRC_DIR) && poetry build

$(fuzzer_dist): $(fuzzer_src_dist)
	mkdir -p dist
	cp $< $@

$(fuzzer_src_dist):
	cd $(FUZZER_SRC_DIR) && mvn package -DskipTests

# ======================================================================================================================
# Deploy targets
# ======================================================================================================================

.PHONY: deploy
## Deploy {FRAMEWORK} to the local environment
deploy: app/deploy fuzzer/deploy


.PHONY: app/deploy
## Deploy {FRAMEWORK}'s application to the local environment. Requires app/build to be run before.
app/deploy:
	bash ./scripts/deploy-app.sh

.PHONY: fuzzer/deploy
## Deploy {FRAMEWORK}'s fuzzer to the local environment. Requires fuzzer/build to be run before.
fuzzer/deploy:
	bash ./scripts/deploy-fuzzer.sh