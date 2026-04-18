from fastapi import FastAPI
from models.connect import connect

app = FastAPI()

@app.get("/")
def root():
    return {"message": "Hello World"}