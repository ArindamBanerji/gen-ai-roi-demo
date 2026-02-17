"""
SOC Copilot Demo - FastAPI Backend
Main application entry point with CORS and router registration.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI(
    title="SOC Copilot Demo API",
    description="AI-augmented Security Operations Center with Runtime Evolution",
    version="1.0.0",
)

# CORS configuration (allow all for demo/ngrok)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for demo purposes
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

# Health check endpoint
@app.get("/")
async def root():
    return {
        "service": "SOC Copilot Demo",
        "status": "operational",
        "version": "1.0.0"
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}

# Router imports
from app.routers import evolution, triage, soc, metrics

# Register routers
app.include_router(evolution.router, prefix="/api", tags=["Runtime Evolution"])
app.include_router(triage.router, prefix="/api", tags=["Alert Triage"])
app.include_router(soc.router, prefix="/api", tags=["SOC Analytics"])
app.include_router(metrics.router, prefix="/api", tags=["Compounding Metrics"])

# Lifecycle events
@app.on_event("startup")
async def startup_event():
    """Initialize connections on startup"""
    from app.db.neo4j import neo4j_client
    await neo4j_client.connect()
    print("✓ Connected to Neo4j")

@app.on_event("shutdown")
async def shutdown_event():
    """Close connections on shutdown"""
    from app.db.neo4j import neo4j_client
    await neo4j_client.close()
    print("✓ Disconnected from Neo4j")
