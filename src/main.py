from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from src.schemas.api import ResearchRequest, ResearchResponse
from src.graph.builder import build_research_graph, build_deep_research_graph
from src.config import settings
import os
import json
import asyncio

app = FastAPI(title="Research Agent")

# Get the base directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Mount static files
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

# Setup templates
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Compile both graphs at startup ────────────────────────────────────────────
basic_graph = build_research_graph()
deep_graph = build_deep_research_graph()


def _select_graph(mode: str):
    """Return the compiled graph for the given research mode."""
    return deep_graph if mode == "deep" else basic_graph


def _initial_state(request: ResearchRequest) -> dict:
    """Build the initial LangGraph state from the request."""
    base = {
        "question": request.question,
        "research_mode": request.mode,
        "model": request.model,
        "iteration_count": 0,
    }
    if request.mode == "deep":
        base.update({
            "react_step": 0,
            "react_trace": [],
            "accumulated_evidence": [],
            "pending_action": None,
        })
    return base


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse(
        request, "index.html", {"model_name": settings.bedrock_model}
    )


@app.post("/research/stream")
async def research_stream(request: ResearchRequest):

    graph = _select_graph(request.mode)

    async def event_generator():
        loop = asyncio.get_event_loop()
        queue: asyncio.Queue = asyncio.Queue()

        def run_graph():
            try:
                for event in graph.stream(
                    _initial_state(request),
                    stream_mode="updates",
                ):
                    node_name = list(event.keys())[0]
                    state_update = event[node_name]

                    # ── Stream react_trace steps for deep mode ────────────
                    if node_name == "reasoner" and request.mode == "deep":
                        react_trace = state_update.get("react_trace", [])
                        if react_trace:
                            last_step = react_trace[-1]
                            react_payload = json.dumps({
                                "type": "react_step",
                                "step": last_step.get("step"),
                                "coverage": last_step.get("coverage", {}),
                                "thought": last_step.get("thought", ""),
                                "action": last_step.get("action", ""),
                                "action_input": last_step.get("action_input", {}),
                            })
                            loop.call_soon_threadsafe(
                                queue.put_nowait,
                                f"data: {react_payload}\n\n"
                            )

                    # ── Stream executor observation for deep mode ─────────
                    elif node_name == "executor" and request.mode == "deep":
                        react_trace = state_update.get("react_trace", [])
                        if react_trace:
                            last_step = react_trace[-1]
                            obs_payload = json.dumps({
                                "type": "react_observation",
                                "step": last_step.get("step"),
                                "observation": last_step.get("observation", ""),
                                "results": last_step.get("results"),
                                "evidence_count": len(state_update.get("accumulated_evidence", [])),
                            })
                            loop.call_soon_threadsafe(
                                queue.put_nowait,
                                f"data: {obs_payload}\n\n"
                            )

                    # ── Standard node progress event ──────────────────────
                    # Strip raw_content from SSE payload to reduce bandwidth
                    sanitized_update = {
                        k: v for k, v in state_update.items()
                        if k != "accumulated_evidence"  # full evidence sent at end only
                    }
                    payload = json.dumps({
                        "type": "progress",
                        "node": node_name,
                        "state": sanitized_update,
                    })
                    loop.call_soon_threadsafe(queue.put_nowait, f"data: {payload}\n\n")

                loop.call_soon_threadsafe(
                    queue.put_nowait,
                    f"data: {json.dumps({'type': 'done'})}\n\n"
                )
            except Exception as e:
                payload = json.dumps({"type": "error", "detail": str(e)})
                loop.call_soon_threadsafe(queue.put_nowait, f"data: {payload}\n\n")
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, None)  # sentinel

        # Run blocking graph in thread pool — event loop stays free
        loop.run_in_executor(None, run_graph)

        while True:
            chunk = await queue.get()
            if chunk is None:
                break
            yield chunk

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/research", response_model=ResearchResponse)
def research(request: ResearchRequest):
    graph = _select_graph(request.mode)
    try:
        result = graph.invoke(_initial_state(request))

        return ResearchResponse(
            question=result.get("question", request.question),
            plan=result.get("plan", ""),
            sub_questions=result.get("sub_questions", []),
            search_results=result.get("search_results", result.get("accumulated_evidence", [])),
            verification_notes=result.get("verification_notes", ""),
            confidence_score=result.get("confidence_score", 0.0),
            reflection_notes=result.get("reflection_notes", ""),
            final_answer=result.get("final_answer", ""),
            citations=result.get("citations", []),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
