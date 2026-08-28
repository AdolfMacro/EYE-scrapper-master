# ==========================================================
# EYES MASTER — MODELS PACKAGE
# ==========================================================
#
# FILE:
#     models/__init__.py
#
# STATUS:
#     CANONICAL / CORE
#
# ROLE:
#     Public API for the EYES domain models package.
#
# ARCHITECTURE:
#
#     models/
#         │
#         ├── business.py
#         │       └── Business
#         │
#         └── __init__.py
#                 └── Public Model API
#
# RESPONSIBILITIES
# ----------------------------------------------------------
# 1. Expose canonical domain models
# 2. Provide a stable import interface
# 3. Hide internal module structure from consumers
# 4. Define the public model API through __all__
#
# IMPORTANT:
#
#     This package initializer must NOT:
#
#         - access the database
#         - create database connections
#         - execute scraping
#         - manage providers
#         - manage workers
#         - contain GUI logic
#         - perform application startup
#         - create runtime state
#
#     It is intentionally lightweight.
#
# PUBLIC API
# ----------------------------------------------------------
#
#     from models import Business
#
# is the preferred public import.
#
# INTERNAL MODULES
# ----------------------------------------------------------
#
#     from models.business import Business
#
# remains valid for direct module-level imports.
#
# ==========================================================

from __future__ import annotations


# ==========================================================
# CANONICAL DOMAIN MODELS
# ==========================================================

from .business import Business


# ==========================================================
# PUBLIC API
# ==========================================================

__all__ = (
    "Business",
)


# ==========================================================
# PACKAGE METADATA
# ==========================================================

__version__ = "1.0.0"

__status__ = "canonical"

__package_name__ = "models"


# ==========================================================
# REPRESENTATION
# ==========================================================

def __repr__() -> str:
    """
    Return a developer-friendly representation of the
    models package.
    """

    return (
        "<EYES Models "
        f"version={__version__!r} "
        f"status={__status__!r}>"
    )