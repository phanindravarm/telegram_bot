from fastapi import FastAPI, Request

app = FastAPI()

@app.get("/")
def home():
    return {"message": "Server is working"}

@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    print("Received:", data)
    return {"status": "ok"}

@app.get("/favicon.ico")
def favicon():
    return {}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)