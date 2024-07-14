from flask import Blueprint, request, session, render_template
from uuid import uuid4
import boto3
import os
import psycopg2
from datetime import datetime
from flask import session
from flask import redirect, Flask, jsonify
from .gpt import analyze_data
import re
import openai
import subprocess


db_manager = Blueprint('db_manager', __name__)

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

def upload_file_to_s3(user_id, file, bucket_name):
    # Generate a unique file_id
    file_id = str(uuid4())
    
    s3.upload_fileobj(file, bucket_name, file_id)
    
    current_time = datetime.utcnow()

    # Stockage user_id, file_id, filename, database
    cursor.execute(
        "INSERT INTO files (id, user_id, filename, date) VALUES (%s, %s, %s, %s)",
        (file_id, user_id, file.filename, current_time)
    )
    conn.commit()
    
    return file_id

def get_user_files(user_id):
    cursor.execute(
        "SELECT filename, id FROM files WHERE user_id = %s",
        (user_id,)
    )
    return cursor.fetchall()


@db_manager.before_request
def before_request():
    if session.get("new_login"):
        user_info = session.get("user_info")
        user_id = user_info["sub"]
        name = user_info.get("name", "")  
        email = user_info.get("email", "")  
        cursor.execute(
            "INSERT INTO users (id, name, email) VALUES (%s, %s, %s) ON CONFLICT (id) DO NOTHING",
            (user_id, name, email)
        )
        conn.commit()
        
        # Supprimez le marqueur new_login de la session
        session.pop("new_login", None)

dash_process = None

@db_manager.route("/upload", methods=["GET", "POST"])
def upload():
    global dash_process
    user_info = session.get("user_info", {})
    user_id = user_info.get('sub')

    if request.method == "POST":
        if dash_process is not None:
            dash_process.terminate()
        file = request.files["file"]
        contents = file.read() 
        file.seek(0)  
        prompt, df = analyze_data(contents)  # Analyser le contenu du fichier
        file_id = upload_file_to_s3(user_id, file, "dataapp821ab")
        user_files = get_user_files(user_id)  # Mettre à jour la liste des fichiers après avoir téléchargé un nouveau fichier
        # appel à la fonction 'analyze'
        analyze_result = analyze(file_id, contents)
        return render_template("dashboard0.html", file_id=file_id, filename=file.filename, user_info=user_info, user_files=user_files, analysis=analyze_result)
    else:
        user_files = get_user_files(user_id)  # Obtenir la liste des fichiers de l'utilisateur si ce n'est pas une requête POST
        return render_template("dashboard0.html", user_info=user_info, user_files=user_files)


def analyze(file_id, contents):  
    global dash_process
    if dash_process is not None:
        dash_process.terminate()
    prompt, df = analyze_data(contents)
    openai.api_key = os.getenv('OPENAI_API_KEY')
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-16k",
            messages=[
                {"role": "system", "content": "As a data scientist, I need powerful visualizations. Please suggest unique, independent and interactive graphs for the data. It is necessary to take into account the characteristics of the variables in order to propose graphs easily realizable with a dash application"},
                {"role": "user", "content": prompt},
        ],
        temperature=0.6
    )
    analysis = response['choices'][0]['message']['content']
    prompt1 = "Given the dataset provided, and considering the previous suggestions, select the 6 best visualizations suitable for this analysis. It is vital to use the exact column names from the dataset and distinguish between numeric and non-numeric variables using 'numeric_columns = df.select_dtypes(include=[np.number])'. Generate an interactive Dash application code that can embed these charts on a web page, ensuring accuracy in column names."
    response = openai.ChatCompletion.create(
    model="gpt-3.5-turbo-16k",
        messages=[
            {"role": "system", "content": "You are an intelligent assistant."},
            {"role": "user", "content": prompt},
            {"role": "user", "content": analysis},
            {"role": "user", "content": prompt1},
        ],
        temperature=0.1
    )
    response_content = response['choices'][0]['message']['content']
    code_match = re.search('```python(.*)```', response_content, re.DOTALL)
    code = None
    if code_match:
        print("Code match found!")  # Ajouté pour le débogage
        code = code_match.group(1).strip()
        start_index = code.find("app = dash.Dash(__name__)")
        end_index = code.find("if __name__ == '__main__':")
        if start_index != -1 and end_index != -1:
            code = code[start_index:end_index]
        code = re.sub(r'#[^\n]*', '', code)
        with open(f"{file_id}.py", "w") as file:
            file.write("import dash\n")
            file.write("import io\n")
            file.write("import os\n")
            file.write("import sys\n")
            file.write("from waitress import serve\n")
            file.write("import base64\n")
            file.write("import numpy as np\n")
            file.write("from dash import dcc, html\n")
            file.write("from dash.dependencies import Input, Output, State\n")
            file.write("import pandas as pd\n")
            file.write("import plotly.graph_objs as go\n")
            file.write("import plotly.figure_factory as ff\n")
            file.write("import plotly.express as px\n")
            file.write("import openai\n")
            file.write("import re\n")
            file.write("import boto3\n")
            file.write("import execnet\n")
            file.write("import subprocess\n")
            file.write("file_id = os.path.splitext(os.path.basename(__file__))[0]\n")
            file.write("s3 = boto3.client('s3', aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'), aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'))\n")
            file.write("obj = s3.get_object(Bucket='dataapp821ab', Key=file_id)\n")
            file.write("df = pd.read_csv(io.BytesIO(obj['Body'].read()))\n")
            file.write("df = df.dropna()\n")
            file.write("numeric_columns = df.select_dtypes(include=[np.number])\n")
            file.write(code)
            file.write("if __name__ == '__main__':\n")
            file.write("    serve(app.server, host='0.0.0.0', port=8052)\n")
        dash_process = subprocess.Popen(["python", f"{file_id}.py", file_id])
    return "Analysis completed successfully. Please check dash_app.py file"

dash_process = None

@db_manager.route('/start_dash/<file_id>')
def start_dash(file_id):
    global dash_process
    if dash_process is not None:
        dash_process.terminate()

    dash_script_path = os.path.join(os.getcwd(), f"{file_id}.py")

    if not os.path.exists(dash_script_path):
        return jsonify({"error": "No Dash script found for this file."}), 404

    dash_process = subprocess.Popen(["python", dash_script_path])

    return redirect(f"http://localhost:8052?file_id={file_id}", code=302)




