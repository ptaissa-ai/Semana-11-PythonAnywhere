"""Modelo do WSGI da Semana 11.A para o PythonAnywhere.

As credenciais de e-mail NÃO ficam neste arquivo. A aplicação carrega
API_URL, API_KEY, API_FROM e FLASKY_ADMIN a partir do arquivo .env.
"""

import sys

project_home = "/home/taissapieri/Semana-11-PythonAnywhere"

if project_home not in sys.path:
    sys.path.insert(0, project_home)

from app import app as application
