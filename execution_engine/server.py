from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
import uvicorn
import os
import sys
from pydantic import BaseModel
from typing import Optional

# Importar nuestro Cerebro Real (No simulación)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from execution_engine.bot_manager import BotManager

# Instancia Global del Bot (El que tiene la IA y MT5)
bot = BotManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🔌 SERVIDOR API: INICIADO")
    yield
    print("🔌 SERVIDOR API: APAGADO")
    if bot.is_running:
        bot.stop()


app = FastAPI(lifespan=lifespan, title="Institutional PO3 Sniper")

# Configuración CORS (Vital para Flutter)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    # Mostramos el umbral real cargado del modelo JSON
    return {
        "status": "Online",
        "system": "PO3 Sniper Real",
        "ai_threshold": f"{bot.threshold:.2%}",
    }


# --- Modelos Pydantic ---
class LoginRequest(BaseModel):
    username: str
    password: str

class SettingsRequest(BaseModel):
    risk: float
    auto_trade: bool

# --- Endpoints de Control ---


@app.post("/bot/start")
async def start():
    if not bot.is_running:
        # Esto arranca el bucle REAL en bot_manager.py
        asyncio.create_task(bot.start_loop())
        return {"status": "started", "message": "Motor de Trading Iniciado"}
    return {"status": "already_running", "message": "El motor ya está rugiendo"}


@app.post("/bot/stop")
def stop():
    bot.stop()
    return {"status": "stopped", "message": "Motor Detenido"}


@app.post("/bot/panic")
def panic():
    bot.panic()  # Cierra posiciones en MT5 de verdad
    return {"status": "panic_executed", "message": "PROTOCOLO DE PÁNICO EJECUTADO"}

# --- Endpoint Auth ---
@app.post("/auth/login")
def login(req: LoginRequest):
    # Mock Auth para MVP
    if req.username == "admin" and req.password == "123":
        return {"token": "demo-token-xyz-999", "valid": True}
    return {"token": None, "valid": False}

# --- Settings ---
@app.post("/settings")
def update_settings(req: SettingsRequest):
    bot.update_settings(req.risk, req.auto_trade)
    return {"status": "ok", "settings": bot.get_settings()}


# --- WebSocket para Flutter ---
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # Enviamos datos reales a la App
            # Enviamos datos reales a la App
            # Payload enriquecido para Dashboard Móvil
            financials = bot.get_balance_equity()
            config = bot.get_settings()
            
            data = {
                "running": bot.is_running,
                "status_text": bot.latest_status,
                "logs": bot.logs[-15:],
                "account": financials,       # {balance, equity}
                "settings": config,          # {risk, auto_trade}
                "recent_trades": bot.trade_history[-5:] # Últimos 5
            }
            await websocket.send_json(data)
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        print("📱 Cliente Flutter desconectado")


# Simulacion
@app.post("/bot/simulate")
async def simulate():
    if not bot.is_running:
        asyncio.create_task(bot.simulate_winning_scenario())
        return {"status": "simulation_started", "message": "Modo Demo Iniciado"}
    return {"status": "error", "message": "Detén el bot antes de simular"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
