# SPDX-FileCopyrightText: 2026 roolrz
# SPDX-License-Identifier: Apache-2.0

.DEFAULT_GOAL := all
OUT ?= $(CURDIR)/out
PROFILE ?= io-bringup
SOURCE ?= $(HYPER_WORKSPACE)
.PHONY: all image checkout test
all: image
image:
	python3 scripts/build.py --profile "$(PROFILE)" --out "$(OUT)" $(if $(SOURCE),--source "$(SOURCE)",)
checkout:
	python3 scripts/build.py --checkout-only --out "$(OUT)" $(if $(SOURCE),--source "$(SOURCE)",)
test:
	python3 -m unittest discover -s tests
