from flask import Flask, request, render_template, redirect
import os
import io
import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

SCOPES = ['https://www.googleapis.com/auth/drive']
SERVICE_ACCOUNT_FILE = 'credentials.json'

app = Flask(__name__)
creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
service = build('drive', 'v3', credentials=creds)

def get_or_create_folder(parent_name, child_name):
    query = f"name='{parent_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    results = service.files().list(q=query, spaces='drive').execute()
    items = results.get('files', [])

    if items:
        parent_id = items[0]['id']
    else:
        file_metadata = {'name': parent_name, 'mimeType': 'application/vnd.google-apps.folder'}
        parent_id = service.files().create(body=file_metadata, fields='id').execute()['id']

    query = f"name='{child_name}' and mimeType='application/vnd.google-apps.folder' and '{parent_id}' in parents and trashed=false"
    results = service.files().list(q=query, spaces='drive').execute()
    items = results.get('files', [])

    if items:
        return items[0]['id']
    else:
        file_metadata = {
            'name': child_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [parent_id]
        }
        file = service.files().create(body=file_metadata, fields='id').execute()
        return file.get('id')

@app.route('/', methods=['GET'])
def index():
    return render_template('upload_form_with_preview.html')

@app.route('/', methods=['POST'])
def upload_file():
    garden_name = request.form.get('garden')
    files = request.files.getlist('photos')
    names = request.form.getlist('child_names')

    folder_id = get_or_create_folder("תמונות גנים", garden_name)

    for file, name in zip(files, names):
        if file:
            filename = f"{name}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            file_metadata = {
                'name': filename,
                'parents': [folder_id]
            }
            media = MediaIoBaseUpload(io.BytesIO(file.read()), mimetype='image/jpeg')
            service.files().create(body=file_metadata, media_body=media, fields='id').execute()

    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)