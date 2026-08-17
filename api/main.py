from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from simulation.scenario import bounds_manifest, validate_recommendation

from .gemini_service import (
    GeminiServiceError,
    GeminiUnavailableError,
    is_configured,
    recommend_policy,
)
from .optimizer_service import run_optimization
from .schemas import (
    OptimizeRequest,
    OptimizeResponse,
    PolicyRecommendation,
    ReasonRequest,
    ReasonResponse,
    SimulationRequest,
    SimulationResponse,
)
from .service import run_frontend_simulation, to_goal_config, to_scenario_diff


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
def health() -> dict[str, object]:
    return {
        "status": "ok",
        "service": "xinyi-simulation-api",
        "ai_configured": is_configured(),
    }


@app.post(
    "/api/simulations",
    response_model=SimulationResponse,
)
def simulate(
    request: SimulationRequest,
) -> SimulationResponse:
    return run_frontend_simulation(request)


@app.post(
    "/api/reason",
    response_model=ReasonResponse,
)
def reason(request: ReasonRequest) -> ReasonResponse:
    """Ask Gemini for the next policy patch. Never produces KPIs."""
    goals = to_goal_config(request.goals)

    if goals is None or goals.is_empty():
        raise HTTPException(
            status_code=400,
            detail="At least one goal is required for reasoning",
        )

    try:
        recommendation = recommend_policy(
            request.scenario,
            request.result,
            goals.to_dict(),
        )
    except GeminiUnavailableError as error:
        return ReasonResponse(
            status="ai_unavailable",
            message=str(error),
            bounds=bounds_manifest(),
        )
    except GeminiServiceError as error:
        return ReasonResponse(
            status="ai_error",
            message=str(error),
            bounds=bounds_manifest(),
        )

    validated = validate_recommendation(recommendation)

    return ReasonResponse(
        status="ok",
        recommendation=PolicyRecommendation(
            signal_green_seconds=validated.variables.signal_green_seconds,
            red_line_meters=validated.variables.red_line_meters,
            parking_spaces=validated.variables.parking_spaces,
            reasoning=recommendation.reasoning,
        ),
        reasoning=recommendation.reasoning,
        validation_notes=list(validated.notes),
        bounds=bounds_manifest(),
    )


@app.post(
    "/api/optimize",
    response_model=OptimizeResponse,
)
def optimize(request: OptimizeRequest) -> OptimizeResponse:
    goals = to_goal_config(request.goals)

    if goals is None or goals.is_empty():
        raise HTTPException(
            status_code=400,
            detail="At least one goal is required to run an optimisation",
        )

    initial = request.initial_scenario
    diff = to_scenario_diff(initial)

    run = run_optimization(
        diff,
        goals,
        day_type=initial.day_type,
        time_slot=initial.time_slot,
        random_seed=initial.random_seed,
        road_id=initial.road_id,
        road_name=initial.road_name,
        max_iterations=request.max_iterations,
    )

    return OptimizeResponse(**run.to_dict())
