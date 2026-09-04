# Shared Terraform modules

Per-cloud stacks under `../aws`, `../azure`, `../gcp` are intentionally
self-contained for reviewability. Extract shared patterns here as the
footprint grows (naming/tags, backup policies, secret wiring). No shared
modules yet — add them when a second consumer needs the same block.
