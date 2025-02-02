# FastAPI server (server.py)
from fastapi import FastAPI, WebSocket
import asyncio
from ollama import AsyncClient

app = FastAPI()

@app.websocket("/chat")
async def chat_stream(websocket: WebSocket):
    await websocket.accept()
    async def chat(user_prompt):
        response = ""
        messages = [
            {
                'role': 'user',
                'content': user_prompt,
            },
        ]
        async for part in await AsyncClient().chat(model="deepseek-r1:14b", messages=messages, stream=True):
            response += part['message']['content']
            await websocket.send_text(response)
            
    while True:
        user_prompt = await websocket.receive_text()
        
        await chat(user_prompt)