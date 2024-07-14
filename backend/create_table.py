import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

# Variables d'environnement pour la connexion à la base de données
dbname = os.getenv('DB_NAME')
user = os.getenv('DB_USER')
password = os.getenv('DB_PASSWORD')
host = os.getenv('DB_HOST')
port = os.getenv('DB_PORT')

conn = psycopg2.connect(
    dbname=dbname,
    user=user,
    password=password,
    host=host,
    port=port
)

# Création d'un curseur
cur = conn.cursor()

# Exécution d'une requête pour créer la table 'users'
cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id VARCHAR(255) PRIMARY KEY,
        name VARCHAR(255),
        email VARCHAR(255)
    )
""")

# Exécution d'une requête pour créer la table 'files'
cur.execute("""
    CREATE TABLE IF NOT EXISTS files (
        id UUID PRIMARY KEY,
        user_id VARCHAR(255) REFERENCES users(id),
        filename VARCHAR(255),
        date TIMESTAMP
    )
""")

# Valide les transactions
conn.commit()

# Fermeture du curseur et de la connexion
cur.close()
conn.close()
