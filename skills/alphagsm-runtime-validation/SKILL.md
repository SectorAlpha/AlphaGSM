---
name: alphagsm-runtime-validation
description: "Use when verifying AlphaGSM runtime families, branch-local images and process/Docker lifecycle parity."
---

# Validate runtimes

Apply the [approval gates](../alphagsm-server-requirements/references/approval-gates.md) before Docker first use, image acquisition/build or test dependency installation. Use only verified images published by or built from SectorAlpha/AlphaGSM. Inspect the selected test and installer for transitive dependencies before executing it; lifecycle validation that needs unapproved installs remains blocked.

Read [docker-runtime-wiring](../docker-runtime-wiring/SKILL.md), [runtime defaults](../../src/server/runtime.py), [family matrix](../../tests/backend_integration_tests/docker_family_matrix.py), [backend guide](../../tests/backend_integration_tests/README.md) and [Docker lifecycle tests](../../tests/backend_integration_tests/test_backend_docker.py). Inspect collection/selection before starting expensive cases.

Keep three declared representative cases for each java, quake-linux, service-console, simple-tcp, steamcmd-linux and wine-proton family; every active case needs CI coverage. Deferred cases remain explicitly explained, not converted to passes. Choose branch-local images from the matching docker family scaffold and explicit test image overrides rather than relying on stale latest tags.

Validate module-scope get_runtime_requirements/get_container_spec and process get_start_command. Static tests and spec validators establish metadata shape; only actual AlphaGSM lifecycles establish launch behavior.

Example: a java builder change needs representative wrapper/claim tests and an active branch-image backend lifecycle. Create/setup/start, protocol readiness, status/query/info/info JSON, stop and shutdown all run through AlphaGSM. Inspect doctor for effective Docker resolution; a manually launched container does not prove the manager path.

Use isolated config/data and sufficient work storage; do not mount production saves into validation containers. Capture image identity/build context, module/case, effective backend and protocol evidence. Clean up only owned temporary processes/containers. A missing daemon/image/network/asset is an accurately named unverified prerequisite. Finish with applicable unit/static/backend/process results and guide/changelog updates for changed runtime behavior.
