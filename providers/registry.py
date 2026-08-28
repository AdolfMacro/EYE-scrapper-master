
# ==========================================================
# EYES MASTER — PROVIDER REGISTRY
# ==========================================================
#
# FILE:
#     providers/registry.py
#
# STATUS:
#     CANONICAL / CORE
#
# ROLE:
#     Central registry and factory for SearchProvider classes.
#
# RESPONSIBILITY:
#     - Register Providers
#     - Resolve Provider classes
#     - Create Provider instances
#     - List registered Providers
#     - Normalize Provider names
#
# BUILT-IN PROVIDERS:
#     - google
#     - duckduckgo
#     - osm
#     - balad
#     - neshan
#
# DOES NOT:
#     - execute searches
#     - manage Provider lifecycle
#     - manage queries
#     - manage jobs
#     - manage database
#
# ==========================================================

from __future__ import annotations

from typing import Any, Dict, Type

from providers.base import SearchProvider


# ==========================================================
# REGISTRY
# ==========================================================

_PROVIDER_REGISTRY: Dict[
    str,
    Type[SearchProvider],
] = {}


# ==========================================================
# NORMALIZATION
# ==========================================================

def normalize_provider_name(
    name: Any,
) -> str:
    """
    Normalize a Provider identifier.
    """

    if name is None:
        return ""

    return str(name).strip().casefold()


# ==========================================================
# REGISTER
# ==========================================================

def register_provider(
    name: str,
    provider_class: Type[SearchProvider],
) -> Type[SearchProvider]:
    """
    Register one SearchProvider class.
    """

    normalized_name = normalize_provider_name(
        name
    )

    if not normalized_name:
        raise ValueError(
            "Provider name cannot be empty."
        )

    if not isinstance(
        provider_class,
        type,
    ):
        raise TypeError(
            "provider_class must be a class."
        )

    if not issubclass(
        provider_class,
        SearchProvider,
    ):
        raise TypeError(
            f"Provider '{normalized_name}' must "
            "inherit from SearchProvider."
        )

    _PROVIDER_REGISTRY[
        normalized_name
    ] = provider_class

    return provider_class


# ==========================================================
# UNREGISTER
# ==========================================================

def unregister_provider(
    name: str,
) -> bool:
    """
    Remove one Provider from the registry.
    """

    normalized_name = normalize_provider_name(
        name
    )

    if normalized_name not in _PROVIDER_REGISTRY:
        return False

    del _PROVIDER_REGISTRY[
        normalized_name
    ]

    return True


# ==========================================================
# HAS
# ==========================================================

def has_provider(
    name: str,
) -> bool:
    """
    Check whether a Provider is registered.
    """

    normalized_name = normalize_provider_name(
        name
    )

    return (
        normalized_name
        in _PROVIDER_REGISTRY
    )


# ==========================================================
# GET CLASS
# ==========================================================

def get_provider_class(
    name: str,
) -> Type[SearchProvider]:
    """
    Resolve a registered Provider class.
    """

    normalized_name = normalize_provider_name(
        name
    )

    provider_class = _PROVIDER_REGISTRY.get(
        normalized_name
    )

    if provider_class is None:

        available = ", ".join(
            list_providers()
        )

        if available:

            raise ValueError(
                f"Unknown provider: "
                f"{normalized_name}. "
                f"Available: {available}"
            )

        raise ValueError(
            f"Unknown provider: "
            f"{normalized_name}. "
            "No providers are registered."
        )

    return provider_class


# ==========================================================
# CREATE
# ==========================================================

def create_provider(
    name: str,
    **options: Any,
) -> SearchProvider:
    """
    Create one Provider instance.
    """

    provider_class = get_provider_class(
        name
    )

    try:

        provider = provider_class(
            **options
        )

    except TypeError:

        # Compatibility fallback for Providers
        # that do not accept constructor options.
        provider = provider_class()

    if not isinstance(
        provider,
        SearchProvider,
    ):
        raise TypeError(
            f"Provider '{name}' returned an "
            "invalid SearchProvider instance."
        )

    return provider


# ==========================================================
# LIST
# ==========================================================

def list_providers() -> list[str]:
    """
    Return all registered Provider names.
    """

    return list(
        _PROVIDER_REGISTRY.keys()
    )


# ==========================================================
# CLASSES
# ==========================================================

def provider_classes() -> Dict[
    str,
    Type[SearchProvider],
]:
    """
    Return a copy of the Provider registry.
    """

    return dict(
        _PROVIDER_REGISTRY
    )


# ==========================================================
# CLEAR
# ==========================================================

def clear_registry() -> None:
    """
    Clear the Provider registry.

    Primarily useful for tests.
    """

    _PROVIDER_REGISTRY.clear()


# ==========================================================
# BUILT-IN PROVIDERS
# ==========================================================

def _register_builtin_providers() -> None:
    """
    Register all built-in EYES Providers.
    """

    # ------------------------------------------------------
    # SEARCH PROVIDERS
    # ------------------------------------------------------

    from providers.google import GoogleProvider
    from providers.duckduckgo import DuckDuckGoProvider

    # ------------------------------------------------------
    # MAP / PLACE PROVIDERS
    # ------------------------------------------------------

    from providers.osm import OSMProvider
    from providers.balad import BaladProvider
    from providers.neshan import NeshanProvider

    # ------------------------------------------------------
    # GOOGLE
    # ------------------------------------------------------

    register_provider(
        "google",
        GoogleProvider,
    )

    # ------------------------------------------------------
    # DUCKDUCKGO
    # ------------------------------------------------------

    register_provider(
        "duckduckgo",
        DuckDuckGoProvider,
    )

    # ------------------------------------------------------
    # OSM
    # ------------------------------------------------------

    register_provider(
        "osm",
        OSMProvider,
    )

    # ------------------------------------------------------
    # BALAD
    # ------------------------------------------------------

    register_provider(
        "balad",
        BaladProvider,
    )

    # ------------------------------------------------------
    # NESHAN
    # ------------------------------------------------------

    register_provider(
        "neshan",
        NeshanProvider,
    )


# ==========================================================
# INITIALIZATION
# ==========================================================

_register_builtin_providers()


# ==========================================================
# EXPORTS
# ==========================================================

__all__ = [
    "register_provider",
    "unregister_provider",
    "has_provider",
    "get_provider_class",
    "create_provider",
    "list_providers",
    "provider_classes",
    "normalize_provider_name",
    "clear_registry",
]
