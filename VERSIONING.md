# HYDRA Versioning & Stability Policy

## Philosophy
- **Semantic versioning** is used for the *public* API surface only.
- Minor releases may add functionality, deprecate internal APIs, or deprecate public APIs with a **six‑month notice** and a replacement.
- Major version bumps (e.g. v1.x → v2.0) are reserved for *incompatible* changes to public APIs or fundamental architectural shifts.

## Version History (as of v1.0‑freeze)
| Version | Date | Notes |
|---------|------|-------|
| **v1.0‑freeze** | 2026‑09‑04 | Freeze of the Google authentication architecture. All public APIs (BrowserManager, Google Auth, GoogleCapabilityRegistry) are declared stable. No breaking changes are planned until a future v2.0 release. |

## Release Guidelines
### Adding New Functionality (minor release)
1. **Extend** the Capability Registry or add a new `GoogleModule` subclass.
2. **Update** `ScopeManager` internals if the new module introduces new required capabilities, but **do not** change the signatures of `BrowserManager`, `GoogleAuth`, or `GoogleCapabilityRegistry`.
3. **Document** the new feature in `ARCHITECTURE.md` and release a minor version (e.g. v1.1, v1.2).

### Incompatible Change (major release)
1. Identify the public API that must change (e.g. a new parameter for `BrowserManager.start_bootstrap`).
2. **Deprecate** the old signature at least two minor releases before removal.
3. Release a **v2.0** with the new interface and a migration guide in `VERSIONING.md`.
4. Keep the old interface as deprecated wrappers for one minor release, then remove it.

### Deprecation Policy
- Any public API marked as “stable” in `ARCHITECTURE.md` will be **deprecated** only via a **formal deprecation cycle**:
  1. Announce deprecation in the project’s changelog.
  2. Keep the old API functional, but emit a `DeprecationWarning` (or equivalent log).
  3. After **six months**, remove the old API in the next major version.
- Users relying on a deprecated API must migrate to the replacement before the removal date.

## Compatibility Assurance
- **Binary compatibility**: Not applicable (pure Python package).
- **Source compatibility**: Guaranteed for all **public** interfaces listed in `ARCHITECTURE.md` up to the next major version.
- **Breaking change detection**: Any pull request that modifies a public API must include a compatibility matrix showing the before/after signatures and a justification why a major version bump is required.

## Tooling
- **CI pipeline** will run a `public_api_frozen_check` job that fails if any of the following files are modified without a corresponding version bump:
  - `src/hydra/browser/manager.py` (BrowserManager)
  - `src/hydra/google/auth.py` (Google Auth)
  - `src/hydra/google/capabilities.py` (GoogleCapabilityRegistry)
- The job also checks that no removed method appears in the public API diff.

---
*This file is part of the HYDRA v1.0 freeze and will be updated only through a formal major version release.*