"""Dashboard module for the Quant Options Trading System."""
from .app import app, socketio, create_app

__all__ = ['app', 'socketio', 'create_app']
