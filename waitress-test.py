from waitress import serve
from esg2.__init__ import create_app

serve(create_app(), host='0.0.0.0', port=8080, url_scheme='https')