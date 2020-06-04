BASE_REPO=https://github.com/jupyter-on-openshift/jupyterhub-quickstart
BASE_REF=3.0.7
ODH_REPO=https://github.com/aicoe/jupyterhub-ocp-oauth
ODH_REF=master
COMMIT=$(shell git rev-parse --short HEAD)
REGISTRY=quay.io
REPO=odh-jupyterhub
VERSION=3.0.7
FINAL_IMG_VERSION=$(VERSION)-$(COMMIT)
FINAL_IMG_URL=$(REGISTRY)/$(REPO)/jupyterhub-img
FINAL_IMG_TAG=$(FINAL_IMG_URL):$(FINAL_IMG_VERSION)
FINAL_IMG_TAG_VERSION=$(FINAL_IMG_URL):$(VERSION)
FINAL_IMG_TAG_LATEST=$(FINAL_IMG_URL):latest
# Use value '--with-builder podman' to use podman with s2i, needs an s2i version with this PR: https://github.com/openshift/source-to-image/pull/996
S2I_ARGS=

all: build tag-jupyterhub-img  push-jupyterhub-img

build: build-jupyterhub build-jupyterhub-img

tag-all: tag-jupyterhub-img tag-latest tag-version
push-all: push-jupyterhub-img push-latest push-version

build-jupyterhub:
	$(eval TEMP_DIR := $(shell mktemp -d))
	git clone $(BASE_REPO) ${TEMP_DIR}/base
	cd $(TEMP_DIR)/base &&\
		git checkout $(BASE_REF) &&\
		s2i build $(S2I_ARGS) . registry.access.redhat.com/ubi7/python-36 jupyterhub:$(VERSION)

build-jupyterhub-img:
	s2i build $(S2I_ARGS) . jupyterhub:$(VERSION) jupyterhub-img:$(FINAL_IMG_VERSION)

tag-jupyterhub-img:
	podman tag jupyterhub-img:$(FINAL_IMG_VERSION) $(FINAL_IMG_TAG)
tag-latest:
	podman tag jupyterhub-img:$(FINAL_IMG_VERSION) $(FINAL_IMG_TAG_LATEST)
tag-version:
	podman tag jupyterhub-img:$(FINAL_IMG_VERSION) $(FINAL_IMG_TAG_VERSION)
push-jupyterhub-img:
	podman push $(FINAL_IMG_TAG)
push-latest:
	podman push $(FINAL_IMG_TAG_LATEST)
push-version:
	podman push $(FINAL_IMG_TAG_VERSION)

clean:
	rm -rf upload