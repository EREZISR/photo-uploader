from flask import Flask, request, render_template, redirect, url_for
import os
from werkzeug.utils import secure_filename
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import datetime

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

SCOPES = ["https://www.googleapis.com/auth/drive.file"]

creds = None
if os.path.exists("credentials.json"):
    flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
    creds = flow.run_local_server(port=0)
    service = build("drive", "v3", credentials=creds)
else:
    service = None

@app.route("/", methods=["GET", "POST"])
def upload_file():
    if request.method == "POST":
        garden_name = request.form.get("garden_name", "גן ללא שם")
        files = request.files.getlist("files[]")
        names = request.form.getlist("child_names[]")

        for file, name in zip(files, names):
            if file.filename:
                filename = secure_filename(name.strip().replace(" ", "_") + "_" +
                                           datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + ".jpg")
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)

                folder_id = get_or_create_folder("תמונות גנים", garden_name)
                upload_to_drive(file_path, filename, folder_id)

        return "הועלה בהצלחה!"
    return render_template("upload_form_with_preview.html")

def get_or_create_folder(parent_name, child_name):
    query = f"name='{parent_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    results = service.files().list(q=query, spaces='drive').execute()
    folders = results.get("files", [])
    if folders:
        parent_id = folders[0]["id"]
    else:
        file_metadata = {
            "name": parent_name,
            "mimeType": "application/vnd.google-apps.folder"
        }
        file = service.files().create(body=file_metadata, fields="id").execute()
        parent_id = file.get("id")

    query = f"'{parent_id}' in parents and name='{child_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    results = service.files().list(q=query, spaces='drive').execute()
    subfolders = results.get("files", [])
    if subfolders:
        return subfolders[0]["id"]

    metadata = {
        "name": child_name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id]
    }
    folder = service.files().create(body=metadata, fields="id").execute()
    return folder.get("id")

def upload_to_drive(path, name, folder_id):
    file_metadata = {
        "name": name,
        "parents": [folder_id]
    }
    media = MediaFileUpload(path, mimetype="image/jpeg")
    service.files().create(body=file_metadata, media_body=media, fields="id").execute()

if __name__ == "__main__":
    app.run(debug=True)
