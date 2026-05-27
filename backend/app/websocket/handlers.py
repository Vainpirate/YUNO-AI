from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.websocket.broadcaster import broadcaster

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/logs/{workflow_id}")
async def ws_logs(websocket: WebSocket, workflow_id: str):
    await broadcaster.subscribe_workflow(workflow_id, websocket)
    await websocket.send_json({"workflow_id": workflow_id, "status": "connected"})
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await broadcaster.unsubscribe(websocket)


@router.websocket("/ws/agent-status/{agent_id}")
async def ws_agent_status(websocket: WebSocket, agent_id: str):
    await broadcaster.subscribe_agent(agent_id, websocket)
    await websocket.send_json({"agent_id": agent_id, "status": "connected"})
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await broadcaster.unsubscribe(websocket)
