from fastapi import FastAPI, Form, UploadFile, File, Request, Depends
from fastapi.responses import RedirectResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os, shutil, uuid, json
import qrcode

app = FastAPI()
templates = Jinja2Templates(directory="app/templates")

with open("app/config.json") as f:
    config = json.load(f)

if not os.path.exists("app/static/qrcodes"):
    os.makedirs("app/static/qrcodes")

app.mount("/static", StaticFiles(directory="app/static"), name="static")


def check_password(request: Request):
    if not config.get("password_enabled", True):
        return True
    return request.cookies.get("auth") == config["admin_password"]


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    if not check_password(request):
        return templates.TemplateResponse("index.html", {"request": request, "auth_required": True})
    return templates.TemplateResponse("index.html", {"request": request, "auth_required": False})


@app.post("/auth")
def auth(request: Request, password: str = Form(...)):
    if password == config["admin_password"]:
        response = RedirectResponse(url="/", status_code=302)
        response.set_cookie("auth", password)
        return response
    return RedirectResponse(url="/", status_code=302)


@app.post("/paste")
def paste(request: Request, text: str = Form(...)):
    paste_id = str(uuid.uuid4())[:8]
    path = os.path.join("app/pastes", paste_id + ".txt")
    with open(path, "w") as f:
        f.write(text)

    return templates.TemplateResponse("paste_success.html", {"request": request, "paste_id": paste_id})


@app.post("/upload")
def upload(request: Request, file: UploadFile = File(...)):
    file_id = str(uuid.uuid4())[:8] + "_" + file.filename
    path = os.path.join("app/uploads", file_id)
    with open(path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Generate QR code
    file_url = f"/static/qrcodes/{file_id}.png"
    qr_img = qrcode.make(f"/uploads/{file_id}")
    qr_path = os.path.join("app/static/qrcodes", file_id + ".png")
    qr_img.save(qr_path)

    return templates.TemplateResponse("upload_success.html", {"request": request, "file_id": file_id, "qr_code": file_url})


@app.get("/uploads/{file_name}")
def serve_upload(file_name: str):
    path = os.path.join("app/uploads", file_name)
    return FileResponse(path)


@app.get("/pastes/{paste_id}", response_class=HTMLResponse)
def serve_paste(request: Request, paste_id: str):
    path = os.path.join("app/pastes", paste_id + ".txt")
    if os.path.exists(path):
        with open(path, "r") as f:
            content = f.read()
        return HTMLResponse(content=content)
    return HTMLResponse(content="Paste not found", status_code=404)
