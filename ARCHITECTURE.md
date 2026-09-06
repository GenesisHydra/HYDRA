# HYDRA Architecture – v1.0 (frozen)

## 1. Overall Vision
HYDRA is a modular, extensible automation platform that integrates with Google services (Gmail, YouTube, Drive, Calendar, Sheets, Docs, etc.) via a **single OAuth 2.0 authentication surface** and a **Capability‑based permission model**.

## 2. Core Components (stable v1.0)
| Layer | Responsibility | Stability |
|-------|----------------|-----------|
| **BrowserManager** | Human‑interactive OAuth flow (once‑only bootstrap). Exported as a public API. | **Public API – stable** |
| **Google Auth** | Core OAuth 2.0 handling: token acquisition, refresh, Vault storage, capability‑to‑scope translation. Exported as a public API. | **Public API – stable** |
| **GoogleCapabilityRegistry** | Maps semantic capabilities (e.g. `upload_video`, `read_mail`) to OAuth scopes and stores the registry of per‑service capabilities. Exported as a public API. | **Public API – stable** |
| **GoogleModule** (internal) | Each service (Gmail, YouTube, …) implements `capabilities`, `optional_capabilities`, `future_capabilities`. | Internal – may evolve with minor version bumps, but public surface stays unchanged. |
| **ScopeManager** | Translates capabilities → OAuth scopes, checks token completeness, triggers re‑auth if needed. | Internal API, but **no breaking changes** in v1.0. |
| **Connectors** (Gmail, YouTube, TradingView, …) | Thin wrappers that use `Google Auth` to obtain a service object (`build(...)`). | New functionality added via extension, never by modifying public interfaces. |

## 3. Versioning & Stability Policy
- **v1.0** is the *frozen* baseline. All public interfaces defined in this version must not be altered in a backward‑incompatible way without a **major version** bump (e.g. v2.0).
- **Public APIs** (BrowserManager, Google Auth, GoogleCapabilityRegistry) are considered **stable**: third‑party code or internal subsystems (e.g. ARGOS) may rely on them without fear of sudden breakage.
- **Extension‑only additions**: New features (new Google services, extra scopes, new connector capabilities) are added by:
  1. Extending the **Capability Registry** (`GoogleCapabilityRegistry`).
  2. Adding a new **GoogleModule** subclass.
  3. Updating **ScopeManager** logic if necessary, but *without* changing the signatures of the public APIs.
- **Incompatible changes**: If a change inevitably breaks a public interface, a new major version (e.g. v2.0) must be released, accompanied by a migration guide.
- **Deprecation policy**: Any planned deprecation of a public API must be announced at least two minor releases (or 6 months) before removal, with a replacement API provided.

## 4. Public API Surface (v1.0)
### 4.1 BrowserManager
```python
# hydra.browser.manager (example)
class BrowserManager:
    def start_bootstrap(self) -> None:
        """Launch the one‑time OAuth flow. Must be run on a machine with a browser."""
        ...

    def is_bootstrap_complete(self) -> bool:
        """Returns True after the refresh token has been stored in the Vault."""
        ...
```
### 4.2 Google Auth
```python
# hydra.google.auth (example)
class GoogleAuth:
    def get_credentials(self) -> Credentials:
        """Return the stored Credentials (access_token, refresh_token, …)."""
        ...

    def refresh_if_needed(self) -> None:
        """Refresh the access token using the stored refresh token if it is expired."""
        ...

    def revoke(self) -> None:
        """Revoke the current refresh token and clear the Vault entry."""
        ...
```
### 4.3 GoogleCapabilityRegistry
```python
# hydra.google.capabilities (example)
class GoogleCapabilityRegistry:
    def list_services(self) -> Dict[str, FrozenSet[str]]:
        """Return {service_name: frozenset of semantic capabilities}."""

    def get_capabilities(self, service: str) -> FrozenSet[str]:
        """Return the capabilities for *service* (or raise KeyError)."""

    def scopes_for_capabilities(self, activated: FrozenSet[str]) -> Set[str]:
        """Given a set of activated capabilities, return the minimal OAuth scopes needed."""
        ...
```
All three classes above are **public**; their method signatures must not change in v1.x without a major version bump.

## 5. Internal Details (may change minor versions)
- `GoogleModule` base class and its `capabilities` property.
- `ScopeManager` internals (`_required_scopes_for_modules`, `missing_scopes`, etc.).
- Connector implementations (Gmail, YouTube, TradingView, …) – **these are *extensions*** and are expected to be added/removed without touching the public surface.

## 5. Migration Guidance (for future major versions)
Whenever a breaking change is inevitable, a `VERSIONING.md` file (see below) will contain:
- A diff of the changed interfaces.
- Steps to adapt existing code.
- A timeline for the deprecation period.

---
*Document generated for HYDRA v1.0 – architecture frozen. No further breaking changes to the listed public APIs will be made until a v2.0 release.*