from flask import Blueprint

# Blueprint for Email Module (web interface)
email_bp = Blueprint(
    'email', __name__,
    template_folder='templates',
    static_folder='static'
)

# Blueprint for Email API endpoints
email_api = Blueprint(
    'email_api', __name__,
    url_prefix='/api/email'
)

# Import and register routes
from . import routes_email
from . import logic_email
from . import api

# Initialize API routes
api.init_email_api_routes(email_api)