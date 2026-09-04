"""
Vercel Serverless Entrypoint for AeroThermal
"""
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from app import AeroThermalHandler

class handler(AeroThermalHandler):
    pass
