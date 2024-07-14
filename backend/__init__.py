from flask import Flask
from .auth import auth, init_auth
from .db_manager import db_manager
from .gpt import gpt
from authlib.integrations.flask_client import OAuth
import os

oauth = OAuth()

def create_app():
    app = Flask(__name__, template_folder='../templates', static_folder='../static')

    app.secret_key = os.getenv('APP_SECRET_KEY') 

    # initialize Authlib
    oauth.init_app(app)

    # initialize auth with the oauth object
    init_auth(oauth)

    app.register_blueprint(auth)
    app.register_blueprint(db_manager)
    app.register_blueprint(gpt)



    return app
