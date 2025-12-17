"""
API endpoints package.

This package contains all Flask blueprint definitions for the REST API.
Each module defines endpoints for a specific feature area.
"""

from flask import Blueprint

__all__ = [
    "endpoints_users",
    "endpoints_chat",
    "endpoints_planner",
    "endpoints_quiz",
    "endpoints_codequest",
]
