from flask import Flask, request, render_template_string
import os
import re
from datetime import datetime
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
SCOPES = ['https://www.googleapis.com/auth/drive.file']

HTML_FORM = open("templates/upload_form_with_preview.html", encoding="utf-8").read()

def clean_filename(name):
    name = name.replace(" ", "_")
    name = re.sub(r'["<>:\\|?*]', '', name)
    return name

def get_or_create_folder(service, folder_name, parent_id=None):
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'"
    if parent_id:
        query += f" and '{parent_id}' in parents"

    results = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    folders = results.get('files', [])
    if folders:
        return folders[0]['id']
    else:
        folder_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        if parent_id:
            folder_metadata['parents'] = [parent_id]

        folder = service.files().create(body=folder_metadata, fields='id').execute()
        return folder['id']

def upload_file_to_drive(service, filename, filepath, parent_folder_id):
    file_metadata = {
        'name': filename,
        'parents': [parent_folder_id]
    }
    media = MediaFileUpload(filepath, mimetype='image/jpeg')
    service.files().create(body=file_metadata, media_body=media, fields='id').execute()

@app.route('/', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        gan_name = request.form['gan_name']
        total = int(request.form.get('total', 0))

        creds = None
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
            with open('token.json', 'w') as token:
                token.write(creds.to_json())

        service = build('drive', 'v3', credentials=creds)

        base_folder_id = get_or_create_folder(service, 'תמונות גנים')
        gan_folder_id = get_or_create_folder(service, gan_name, parent_id=base_folder_id)

        for i in range(total):
            photo_key = f'photo_{i}'
            name_key = f'name_{i}'
            if photo_key in request.files:
                photo = request.files[photo_key]
                child_name = request.form.get(name_key, "").strip()

                if not child_name:
                    print(f"[אזהרה] לא נמסר שם עבור photo_{i}, משתמשים בשם קובץ מקורי")
                    child_name = os.path.splitext(photo.filename)[0] or f"ללא_שם_{i}"

                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"{clean_filename(child_name)}_{timestamp}.jpg"

                print(f"מעלים קובץ: {filename}")
                path = os.path.join(UPLOAD_FOLDER, filename)
                photo.save(path)
                upload_file_to_drive(service, filename, path, gan_folder_id)

        return f"🚀 גרסה 1.8: שמות בעברית תקינים נשמרים בדרייב! תיקיית '{gan_name}' עודכנה 🎯"

    return render_template_string(HTML_FORM)

if __name__ == '__main__':
    APP_VERSION = "v1.8 - 2025-06-04 13:14"
    print(f"🚀 Running PhotoUploader {APP_VERSION}")
    app.run(debug=True)
