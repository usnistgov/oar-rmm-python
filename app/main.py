from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from app.routers import paper, record, field, code, patent
from app.config import settings
import os

app = FastAPI()

app.include_router(record.router)
app.include_router(field.router)
app.include_router(paper.router) 
app.include_router(code.router)
app.include_router(patent.router)

@app.on_event("startup")
def startup_event():
    print(f"Connected to database: {settings.DB_NAME}")

@app.get("/", response_class=HTMLResponse)
async def root():
    # Construct the absolute path to the index.html file
    base_dir = os.path.dirname(os.path.abspath(__file__))
    html_path = os.path.join(base_dir, "index.html")
    
    # Read the HTML file
    with open(html_path, "r") as file:
        html_content = file.read()
    
    return HTMLResponse(content=html_content)