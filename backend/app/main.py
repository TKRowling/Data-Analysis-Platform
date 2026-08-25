from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.router import router
from app.core.exceptions import AnalysisError, DatasetNotFoundError

app=FastAPI(title="Data Analysis Platform API",version="0.1.0",description="Deterministic analytics APIs with agent-assisted interpretation")
app.add_middleware(CORSMiddleware,allow_origins=["http://localhost:5173","http://localhost:3000"],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])
app.include_router(router,prefix="/api")

@app.exception_handler(DatasetNotFoundError)
async def missing_dataset(_:Request,exc:DatasetNotFoundError): return JSONResponse(status_code=404,content={"detail":f"Dataset not found: {exc.args[0]}"})

@app.exception_handler(AnalysisError)
async def analysis_error(_:Request,exc:AnalysisError): return JSONResponse(status_code=422,content={"detail":str(exc)})

