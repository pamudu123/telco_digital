"""Vercel entrypoint for the single-project POC deployment."""

from telco_digital.api.app import app

__all__ = ["app"]
