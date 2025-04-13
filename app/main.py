from fastapi import FastAPI, Form, UploadFile, File, Request, Depends
from fastapi.responses import RedirectResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os, shutil, uuid, json
import qrcode

app = FastAPI()
templates = Jinja2Templates(directory=\"app/templates\")

with open(\"app/config.json\") as f:
    config = json.load(f)

if not os.path.exists(\"app/static/qrcodes\"):
    os.makedirs(\"app/static/qrcodes\")

app.mount(\"/static\", StaticFiles(directory=\"app/static\"), name=\"static\")

def check_password(request: Request):
    if not config.get(\"password_enabled\", True):
        return True
    return request.cookies.get(\"auth\") == config[\"admin_password\"]

@app.get(\"/\", response_class=HTMLResponse)
def home(request: Request):
    if not check_password(request):
        return templates.TemplateResponse(\"index.html\", {\"request\": request, \"auth_required\": True})
    return templates.TemplateResponse(\"index.html\", {\"request\": request, \"auth_required\": False})

@app.post(\"/auth\")
def auth(request: Request, password: str = Form(...)):
    if password == config[\"admin_password\"]:
        response = RedirectResponse(url=\"/\", status_code=302)
        response.set_cookie(\"auth\", password)
        return response
    return RedirectResponse(url=\"/\", status_code=302)

@app.post(\"/paste\")
def paste(request: Request, text: str = Form(...)):
    short_id = uuid.uuid4().hex[:6]
    path = f\"app/pastes/{short_id}.txt\"
    with open(path, \"w\") as f:
        f.write(text)
    return templates.TemplateResponse(\"paste_success.html\", {\"request\": request, \"url\": f\"/r/{short_id}\"})

@app.post(\"/upload\")
def upload(request: Request, file: UploadFile = File(...)):
    short_id = uuid.uuid4().hex[:6]
    dest = f\"app/uploads/{short_id}_{file.filename}\"
    with open(dest, \"wb\") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Generate QR code
    link = f\"/r/{short_id}\"
    qr = qrcode.make(link)
    qr_path = f\"app/static/qrcodes/{short_id}.png\"
    qr.save(qr_path)

    return templates.TemplateResponse(\"upload_success.html\", {
        \"request\": request,
        \"url\": link,
        \"qr_path\": f\"/static/qrcodes/{short_id}.png\"
    })

@app.get(\"/r/{short_id}\")
def redirect(short_id: str):
    # Try file
    for fname in os.listdir(\"app/uploads\"):
        if fname.startswith(short_id):
            return FileResponse(f\"app/uploads/{fname}\")
    # Try paste
    fpath = f\"app/pastes/{short_id}.txt\"
    if os.path.exists(fpath):
        with open(fpath) as f:
            content = f.read()
        return HTMLResponse(f\"<pre>{content}</pre>\")
    return HTMLResponse(\"Not found\", status_code=404)
