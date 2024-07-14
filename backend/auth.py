from flask import Blueprint, render_template, redirect, url_for, session
from authlib.integrations.flask_client import OAuth
from urllib.parse import urlencode
from dotenv import load_dotenv, find_dotenv
import os
import psycopg2
import boto3

# Charger le fichier .env
load_dotenv(find_dotenv())

# Créer le blueprint
auth = Blueprint("auth", __name__)

# Configurer Authlib
oauth = None
auth0 = None

def init_auth(oauth_obj):
    global oauth
    global auth0
    oauth = oauth_obj

    # Configurer Auth0
    auth0 = oauth.register(
        "auth0",
        client_id=os.getenv("AUTH0_CLIENT_ID"),
        client_secret=os.getenv("AUTH0_CLIENT_SECRET"),
        api_base_url=f"https://{os.getenv('AUTH0_DOMAIN')}",
        access_token_url=f"https://{os.getenv('AUTH0_DOMAIN')}/oauth/token",
        server_metadata_url=f"https://{os.getenv('AUTH0_DOMAIN')}/.well-known/openid-configuration",
        authorize_url=f"https://{os.getenv('AUTH0_DOMAIN')}/authorize",
        client_kwargs={"scope": "openid profile email"},
    )

s3 = boto3.client('s3',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),  
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
)

conn = psycopg2.connect(
    dbname=os.getenv('DB_NAME'),  
    user=os.getenv('DB_USER'),  
    password=os.getenv('DB_PASSWORD'), 
    host=os.getenv('DB_HOST'),  
    port=os.getenv('DB_PORT')  
)
cursor = conn.cursor()

@auth.route("/")
def home():
    return render_template("home.html")

@auth.route("/login")
def login():
    return auth0.authorize_redirect(redirect_uri=url_for("auth.callback", _external=True, _scheme="http"))

@auth.route("/callback")
def callback():
    auth0.authorize_access_token()
    resp = auth0.get("userinfo")
    user_info = resp.json()
    print(f"User info: {user_info}")

    # Stocker les informations de l'utilisateur dans la session
    session["user_id"] = user_info["sub"]
    session["user_info"] = user_info

    # Ajoutez cette ligne pour signaler qu'un nouvel utilisateur s'est connecté
    session["new_login"] = True

    # Rediriger l'utilisateur vers la page d'upload à la place du tableau de bord
    return redirect("/dashboard")

def get_user_files(user_id):
    cursor.execute(
        "SELECT filename FROM files WHERE user_id = %s",
        (user_id,)
    )
    return cursor.fetchall()

@auth.route("/dashboard")
def dashboard():
    user_info = session.get("user_info")
    if user_info is None:
        return redirect("/login")

    # Récupérez l'ID de l'utilisateur
    user_id = user_info.get('sub')

    # Récupérez la liste des fichiers de l'utilisateur
    user_files = get_user_files(user_id)

    # Passez la liste des fichiers au template
    return render_template("dashboard0.html", user_info=user_info, user_files=user_files)

@auth.route("/logout")
def logout():
    # Supprimer les informations de l'utilisateur de la session
    session.pop("user_info", None)
    # Fournir un redirect_uri à logout_url si votre application est déployée à une adresse autre que localhost
    params = {"returnTo": url_for("auth.home", _external=True, _scheme="https")}
    return redirect(auth0.api_base_url + "/v2/logout?" + urlencode(params))
