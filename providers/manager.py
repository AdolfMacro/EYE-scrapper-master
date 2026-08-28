# ==========================================================
# EYES MASTER — PROVIDER MANAGER
# ==========================================================
#
# FILE:
#     providers/manager.py
#
# STATUS:
#     CANONICAL / CORE
#
# ROLE:
#     Lifecycle manager for SearchProvider instances.
#
# RESPONSIBILITY:
#     - Initialize registered Providers
#     - Keep Provider instances alive
#     - Resolve Providers
#     - Expose Provider metadata
#     - Run health checks
#     - Remove Providers
#     - Reload Providers
#     - Pass Provider-specific configuration
#
# DOES NOT:
#     - generate queries
#     - manage keywords
#     - manage cities
#     - create jobs
#     - manage database
#     - extract School objects
#     - persist results
#
# ==========================================================

from __future__ import annotations

from typing import Any, Mapping, Optional

from providers.base import SearchProvider

from providers.registry import (
    create_provider,
    list_providers,
)


class ProviderManager:
    """
    Canonical lifecycle manager for SearchProvider instances.

    Registry
        Knows which Providers exist.

    Manager
        Owns initialized Provider instances.

    Provider
        Performs actual search work.

    Provider configuration is isolated by Provider name.

    Example
    -------

    manager = ProviderManager(
        provider_options={
            "neshan": {
                "api_key": "...",
            },
            "google": {
                "api_key": "...",
            },
        }
    )
    """

    DEFAULT_PROVIDER = "google"

    def __init__(
        self,
        auto_initialize: bool = True,
        provider_options: Optional[
            Mapping[str, Mapping[str, Any]]
        ] = None,
        **legacy_options: Any,
    ) -> None:

        # --------------------------------------------------
        # Provider-specific configuration
        # --------------------------------------------------

        self.provider_options: dict[
            str,
            dict[str, Any],
        ] = self._normalize_provider_options(
            provider_options
        )

        # --------------------------------------------------
        # Backward compatibility
        #
        # Allows old code such as:
        #
        # ProviderManager(
        #     api_key="..."
        # )
        #
        # to continue working for Providers that accept it.
        #
        # New code should use provider_options.
        # --------------------------------------------------

        self.legacy_options: dict[
            str,
            Any,
        ] = dict(
            legacy_options
        )

        # --------------------------------------------------
        # Live Provider instances
        # --------------------------------------------------

        self.providers: dict[
            str,
            SearchProvider,
        ] = {}

        if auto_initialize:
            self.initialize()

    # ======================================================
    # INITIALIZE
    # ======================================================

    def initialize(self) -> None:
        """
        Initialize every Provider registered in the registry.

        Existing instances are preserved.
        """

        for registered_name in self.registered():

            if registered_name in self.providers:
                continue

            provider = self._create(
                registered_name
            )

            if provider is not None:

                self.providers[
                    registered_name
                ] = provider

    # ======================================================
    # CREATE
    # ======================================================

    def _create(
        self,
        name: str,
    ) -> Optional[SearchProvider]:
        """
        Create one Provider through the registry.

        Provider-specific options are passed only to the
        requested Provider.

        This prevents configuration intended for Neshan,
        Google, etc. from being blindly passed to every
        Provider.
        """

        normalized_name = (
            self._normalize_name(name)
        )

        if not normalized_name:
            return None

        options = self._options_for(
            normalized_name
        )

        try:

            provider = create_provider(
                normalized_name,
                **options,
            )

        except TypeError:

            # ------------------------------------------------
            # Compatibility fallback.
            #
            # A Provider may expose a constructor without
            # configurable options.
            # ------------------------------------------------

            try:

                provider = create_provider(
                    normalized_name
                )

            except Exception:

                return None

        except Exception:

            return None

        # --------------------------------------------------
        # Canonical Provider contract.
        # --------------------------------------------------

        if not isinstance(
            provider,
            SearchProvider,
        ):

            return None

        return provider

    # ======================================================
    # OPTIONS
    # ======================================================

    def _options_for(
        self,
        name: str,
    ) -> dict[str, Any]:
        """
        Resolve configuration for exactly one Provider.

        Preferred format:

            provider_options={
                "neshan": {
                    "api_key": "...",
                }
            }

        Legacy keyword arguments are used only when no
        Provider-specific configuration exists.
        """

        normalized_name = (
            self._normalize_name(name)
        )

        configured = (
            self.provider_options.get(
                normalized_name
            )
        )

        if configured is not None:

            return dict(
                configured
            )

        # --------------------------------------------------
        # Legacy compatibility
        #
        # This intentionally remains isolated here.
        # --------------------------------------------------

        if self.legacy_options:

            return dict(
                self.legacy_options
            )

        return {}

    # ======================================================
    # SET OPTIONS
    # ======================================================

    def set_provider_options(
        self,
        name: str,
        options: Mapping[str, Any],
        *,
        reload: bool = False,
    ) -> None:
        """
        Set or replace configuration for one Provider.

        Parameters
        ----------
        name:
            Provider identifier.

        options:
            Provider-specific configuration.

        reload:
            Recreate the Provider immediately when True.
        """

        normalized_name = (
            self._normalize_name(name)
        )

        if not normalized_name:

            raise ValueError(
                "Provider name cannot be empty."
            )

        if not isinstance(
            options,
            Mapping,
        ):

            raise TypeError(
                "Provider options must be a mapping."
            )

        self.provider_options[
            normalized_name
        ] = dict(options)

        if reload:

            self.reload_provider(
                normalized_name
            )

    # ======================================================
    # GET OPTIONS
    # ======================================================

    def get_provider_options(
        self,
        name: str,
    ) -> dict[str, Any]:
        """
        Return a copy of one Provider's configuration.
        """

        normalized_name = (
            self._normalize_name(name)
        )

        return dict(
            self.provider_options.get(
                normalized_name,
                {},
            )
        )

    # ======================================================
    # GET
    # ======================================================

    def get(
        self,
        name: Optional[str] = None,
    ) -> SearchProvider:
        """
        Return an initialized Provider.

        If no name is supplied, DEFAULT_PROVIDER is used.

        Supports lazy initialization for Providers that
        were registered after Manager initialization.
        """

        normalized_name = (
            self._normalize_name(name)
        )

        if not normalized_name:

            normalized_name = (
                self.DEFAULT_PROVIDER
            )

        provider = self.providers.get(
            normalized_name
        )

        # --------------------------------------------------
        # Lazy initialization
        # --------------------------------------------------

        if provider is None:

            provider = self._create(
                normalized_name
            )

            if provider is not None:

                self.providers[
                    normalized_name
                ] = provider

        # --------------------------------------------------
        # Failed resolution
        # --------------------------------------------------

        if provider is None:

            available = self.registered()

            if available:

                raise ValueError(
                    f"Unknown or unavailable provider: "
                    f"{normalized_name}. "
                    f"Available: "
                    f"{', '.join(available)}"
                )

            raise ValueError(
                f"Unknown provider: "
                f"{normalized_name}. "
                "No providers are registered."
            )

        return provider

    # ======================================================
    # HAS
    # ======================================================

    def has(
        self,
        name: str,
    ) -> bool:
        """
        Return True when a Provider instance is initialized.
        """

        normalized_name = (
            self._normalize_name(name)
        )

        return (
            normalized_name
            in self.providers
        )

    # ======================================================
    # LIST
    # ======================================================

    def list(
        self,
    ) -> list[str]:
        """
        Return initialized Provider names.
        """

        return list(
            self.providers.keys()
        )

    # ======================================================
    # REGISTERED
    # ======================================================

    def registered(
        self,
    ) -> list[str]:
        """
        Return all Provider names registered in the registry.
        """

        result: list[str] = []

        for name in list_providers():

            normalized_name = (
                self._normalize_name(name)
            )

            if not normalized_name:
                continue

            if normalized_name in result:
                continue

            result.append(
                normalized_name
            )

        return result

    # ======================================================
    # INFO
    # ======================================================

    def info(
        self,
    ) -> dict[str, dict[str, Any]]:
        """
        Return metadata for all initialized Providers.
        """

        result: dict[
            str,
            dict[str, Any],
        ] = {}

        for name, provider in (
            self.providers.items()
        ):

            try:

                metadata = provider.info()

                if isinstance(
                    metadata,
                    dict,
                ):

                    result[name] = metadata

                else:

                    result[name] = {
                        "name": name,
                        "error": (
                            "Provider.info() "
                            "must return dict."
                        ),
                    }

            except Exception as exc:

                result[name] = {
                    "name": name,
                    "error": str(exc),
                }

        return result

    # ======================================================
    # PROVIDER INFO
    # ======================================================

    def provider_info(
        self,
        name: str,
    ) -> dict[str, Any]:
        """
        Return metadata for one Provider.
        """

        provider = self.get(name)

        metadata = provider.info()

        if not isinstance(
            metadata,
            dict,
        ):

            raise TypeError(
                "Provider.info() must return dict."
            )

        return metadata

    # ======================================================
    # HEALTH CHECK
    # ======================================================

    def health_check(
        self,
    ) -> dict[str, bool]:
        """
        Run health checks for all initialized Providers.
        """

        result: dict[str, bool] = {}

        for name, provider in (
            self.providers.items()
        ):

            try:

                result[name] = bool(
                    provider.health_check()
                )

            except Exception:

                result[name] = False

        return result

    # ======================================================
    # CHECK ONE
    # ======================================================

    def check(
        self,
        name: str,
    ) -> bool:
        """
        Run health check for one Provider.
        """

        provider = self.get(name)

        try:

            return bool(
                provider.health_check()
            )

        except Exception:

            return False

    # ======================================================
    # REMOVE
    # ======================================================

    def remove(
        self,
        name: str,
    ) -> bool:
        """
        Remove one initialized Provider instance.

        Registry entry remains untouched.
        """

        normalized_name = (
            self._normalize_name(name)
        )

        provider = self.providers.pop(
            normalized_name,
            None,
        )

        if provider is None:
            return False

        self._close_provider(
            provider
        )

        return True

    # ======================================================
    # CLEAR
    # ======================================================

    def clear(
        self,
    ) -> None:
        """
        Remove all initialized Provider instances.
        """

        for provider in list(
            self.providers.values()
        ):

            self._close_provider(
                provider
            )

        self.providers.clear()

    # ======================================================
    # RELOAD ALL
    # ======================================================

    def reload(
        self,
    ) -> None:
        """
        Recreate all currently registered Providers.
        """

        self.clear()
        self.initialize()

    # ======================================================
    # RELOAD ONE
    # ======================================================

    def reload_provider(
        self,
        name: str,
    ) -> SearchProvider:
        """
        Recreate one Provider instance.

        The Provider remains registered.
        """

        normalized_name = (
            self._normalize_name(name)
        )

        if not normalized_name:

            raise ValueError(
                "Provider name cannot be empty."
            )

        self.remove(
            normalized_name
        )

        provider = self._create(
            normalized_name
        )

        if provider is None:

            raise ValueError(
                f"Unable to initialize provider: "
                f"{normalized_name}"
            )

        self.providers[
            normalized_name
        ] = provider

        return provider

    # ======================================================
    # CLOSE
    # ======================================================

    @staticmethod
    def _close_provider(
        provider: SearchProvider,
    ) -> None:
        """
        Safely close a Provider when it exposes close().
        """

        close = getattr(
            provider,
            "close",
            None,
        )

        if not callable(close):
            return

        try:

            close()

        except Exception:

            pass

    # ======================================================
    # NORMALIZE
    # ======================================================

    @staticmethod
    def _normalize_name(
        name: Optional[str],
    ) -> str:
        """
        Normalize Provider identifier.
        """

        if name is None:
            return ""

        return (
            str(name)
            .strip()
            .casefold()
        )

    # ======================================================
    # NORMALIZE OPTIONS
    # ======================================================

    @classmethod
    def _normalize_provider_options(
        cls,
        provider_options: Optional[
            Mapping[str, Mapping[str, Any]]
        ],
    ) -> dict[
        str,
        dict[str, Any],
    ]:
        """
        Normalize Provider-specific configuration.

        Invalid entries are ignored here so configuration
        validation remains the responsibility of the Provider.
        """

        if provider_options is None:
            return {}

        if not isinstance(
            provider_options,
            Mapping,
        ):

            raise TypeError(
                "provider_options must be a mapping."
            )

        result: dict[
            str,
            dict[str, Any],
        ] = {}

        for name, options in (
            provider_options.items()
        ):

            normalized_name = (
                cls._normalize_name(name)
            )

            if not normalized_name:
                continue

            if not isinstance(
                options,
                Mapping,
            ):

                raise TypeError(
                    f"Options for provider "
                    f"'{normalized_name}' "
                    "must be a mapping."
                )

            result[
                normalized_name
            ] = dict(options)

        return result

    # ======================================================
    # LENGTH
    # ======================================================

    def __len__(
        self,
    ) -> int:

        return len(
            self.providers
        )

    # ======================================================
    # CONTAINS
    # ======================================================

    def __contains__(
        self,
        name: str,
    ) -> bool:

        return self.has(name)

    # ======================================================
    # ITERATION
    # ======================================================

    def __iter__(self):

        return iter(
            self.providers
        )

    # ======================================================
    # REPRESENTATION
    # ======================================================

    def __repr__(
        self,
    ) -> str:

        names = ", ".join(
            self.list()
        )

        return (
            "ProviderManager("
            f"providers=[{names}]"
            ")"
        )


__all__ = [
    "ProviderManager",
]