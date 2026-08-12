from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routes.skills import router as skills_router

from backend.routes.student_profile import router as student_profile_router
from backend.routes.auth import router as auth_router
from backend.routes.recommendation import router as recommendation_router
from backend.routes.quiz import router as quiz_router
from backend.routes.tutor import router as tutor_router
from backend.routes.assessment import router as assessment_router
from backend.routes.roadmap import router as roadmap_router
from backend.routes.skill_analysis import router as skill_analysis_router

app = FastAPI(
    title="AI Student Mentor API",
    description="Backend API for the AI Student Mentor",
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "message": "AI Student Mentor API is running",
    }


app.include_router(assessment_router)
app.include_router(roadmap_router)
app.include_router(tutor_router)
app.include_router(quiz_router)
app.include_router(recommendation_router)
app.include_router(skill_analysis_router)
app.include_router(auth_router)
app.include_router(student_profile_router)
app.include_router(skills_router)