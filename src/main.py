from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from src.schemas.api import ResearchRequest, ResearchResponse
from src.graph.builder import build_research_graph
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

research_graph = build_research_graph()


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse(
        request, "index.html", {"model_name": settings.bedrock_model}
    )


@app.post("/research/stream")
async def research_stream(request: ResearchRequest):

    async def event_generator():
        loop = asyncio.get_event_loop()
        queue: asyncio.Queue = asyncio.Queue()

        def run_graph():
            try:
                for event in research_graph.stream(
                    {
                        "question": request.question,
                        "research_mode": request.mode,
                        "model": request.model,
                        "iteration_count": 0,
                    },
                    stream_mode="updates",
                ):
                    node_name = list(event.keys())[0]
                    state_update = event[node_name]
                    payload = json.dumps({"type": "progress", "node": node_name, "state": state_update})
                    loop.call_soon_threadsafe(queue.put_nowait, f"data: {payload}\n\n")

                loop.call_soon_threadsafe(queue.put_nowait, f"data: {json.dumps({'type': 'done'})}\n\n")
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
    try:
        result = research_graph.invoke({
            "question": request.question,
            "research_mode": request.mode,
            "model": request.model,
            "iteration_count": 0
        })

        return ResearchResponse(
            question=result.get("question", request.question),
            plan=result.get("plan", ""),
            sub_questions=result.get("sub_questions", []),
            search_results=result.get("search_results", []),
            verification_notes=result.get("verification_notes", ""),
            confidence_score=result.get("confidence_score", 0.0),
            reflection_notes=result.get("reflection_notes", ""),
            final_answer=result.get("final_answer", ""),
            citations=result.get("citations", []),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
