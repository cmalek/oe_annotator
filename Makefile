VERSION = 0.1.0

PACKAGE = building_directory

DOCKER_REGISTRY = 131067624433.dkr.ecr.us-west-2.amazonaws.com/caltech-imss-ads
IN_CODEPIPELINE := $(if $(CODEBUILD_BUILD_ID),True,False)

.DEFAULT_GOAL := help

#======================================================================

clean::
	rm -rf *.tar.gz dist *.egg-info *.rpm
	find . -path './.venv' -prune -o -name "*.pyc" -exec rm '{}' ';'
	find . -path './.venv' -prune -o -name "__pycache__" -exec rm -rf '{}' ';'

dist:: clean
	@uv build --sdist

build::
	./build_macos.sh

dev::
	python -m oeapp.main

destroy-db::
	rm -f ~/Library/Application\ Support/oe_annotator/projects/*.db

show-db::
	ls -la ~/Library/Application\ Support/oe_annotator/projects/*.db

compile:: sync  ## Run sync to update uv.lock, then rebuild requirements.txt (delete first to ensure all updates are applied).
	rm requirements.txt
	uv pip compile pyproject.toml --group=docs --group=test -o requirements.txt

help:: ## Display this help.
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)
