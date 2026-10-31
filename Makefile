# SPDX-FileCopyrightText: 2026 roolrz
# SPDX-License-Identifier: Apache-2.0

# Build this module within a repo workspace; all generated files belong to OUT.
HYPER_BUILD_SYSTEM ?= $(shell python3 -c 'from pathlib import Path; p=Path.cwd(); print(next((str(r) for r in (p,*p.parents) if (r/"scripts/buildsystem/model.py").is_file()), ""))')
ifeq ($(strip $(HYPER_BUILD_SYSTEM)),)
include mk/build.mk
else
include $(HYPER_BUILD_SYSTEM)/mk/entry.mk
endif
