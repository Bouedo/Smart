from flask import Blueprint, request, redirect, url_for
import openai
import re
import subprocess
import pandas as pd
import numpy as np
import io
import base64
import execnet

gpt = Blueprint("gpt", __name__)

dash_process = None

def execute_code(code):
    gw = execnet.makegateway()
    def remote_exec(channel):
        exec(channel.receive())
    try:
        channel = gw.remote_exec(remote_exec)
        return None
    except Exception as e:
        return str(e)

def analyze_data(contents):
    df = pd.read_csv(io.StringIO(contents.decode('utf-8')), nrows=10000)
    df = df.dropna()
    head = df.head(2)
    info = df.info()
    numeric_columns = df.select_dtypes(include=[np.number])
    column_info = {}
    for column in df.columns:
        if df[column].dtypes == 'object':
            column_info[column] = df[column].value_counts()
    prompt = f"I have a dataset with the following information:"
    prompt += f"\n\n{head}\n\n"
    prompt += f"\n{info}\n\n"
    prompt += f"\n{column_info}\n\n"
    return prompt, df


