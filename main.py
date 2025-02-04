# FastAPI server (server.py)
from fastapi import FastAPI, WebSocket
import asyncio
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, MessagesState, StateGraph

app = FastAPI()
llm = ChatOllama(model="deepseek-r1:14b")
workflow = StateGraph(state_schema=MessagesState)

async def call_model(state: MessagesState):
    response = await llm.ainvoke(state["messages"])
    return {"messages": response}

workflow.add_edge(START, "model")
workflow.add_node("model", call_model)

memory = MemorySaver()
lang_app = workflow.compile(checkpointer=memory)

@app.websocket("/chat")
async def chat_stream(websocket: WebSocket):
    await websocket.accept()
    config = {"configurable": {"thread_id": "and123"}}
        

    while True:
        user_prompt = await websocket.receive_text()
        input_messages = [HumanMessage(user_prompt)]
        response = ""
        async for chunk, metadata in lang_app.astream(
            {"messages": input_messages},
            config,
            stream_mode="messages",
        ):
            if isinstance(chunk, AIMessage):  # Filter to just model responses
                response += chunk.content
                await websocket.send_text(response)
    