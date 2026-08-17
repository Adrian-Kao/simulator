from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .schemas import SimulationRequest, SimulationResponse
from .service import run_frontend_simulation


app = FastAPI(title="Xinyi Policy Sandbox API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "xinyi-simulation-api",
    }


@app.post(
    "/api/simulations",
    response_model=SimulationResponse,
)
def simulate(
    request: SimulationRequest,
) -> SimulationResponse:
    return run_frontend_simulation(request)
