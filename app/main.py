from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import firebase_admin
from firebase_admin import credentials
import os

from .database import Base, engine
from .routers import ai, auth, notes, payments, tasks, subscriptions, friends, calendar, habits, challenges
from .scheduler import deactivate_expired_subscriptions, send_task_reminders
from .utils.cleanup_old_habit_events import cleanup_old_habit_events
from .utils.maintain_habit_schedules import maintain_habit_schedules
from .utils.challenge_scheduler import process_expired_challenges

scheduler = AsyncIOScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Application startup...")
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")
    
    # Initialize Firebase Admin SDK
    # Prioritize initializing from environment variable (for Vercel)
    firebase_cred_json_str = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
    if firebase_cred_json_str:
        try:
            import json
            cred_json = json.loads(firebase_cred_json_str)
            cred = credentials.Certificate(cred_json)
            if not firebase_admin._apps:
                firebase_admin.initialize_app(cred, {
                    'storageBucket': os.getenv("FIREBASE_STORAGE_BUCKET", f"{cred_json.get('project_id')}.appspot.com")
                })
            print("Firebase Admin SDK initialized successfully from environment variable.")
        except (json.JSONDecodeError, ValueError) as e:
            print(f"ERROR: Failed to initialize Firebase from env var: {e}")
    else:
        # Fallback to local file (for local development)
        service_account_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "firebase-service-account.json")
        if os.path.exists(service_account_path):
            cred = credentials.Certificate(service_account_path)
            if not firebase_admin._apps:
                # Load JSON to get project_id for bucket name fallback
                import json
                with open(service_account_path) as f:
                    sa_json = json.load(f)
                
                firebase_admin.initialize_app(cred, {
                    'storageBucket': os.getenv("FIREBASE_STORAGE_BUCKET", f"{sa_json.get('project_id')}.appspot.com")
                })
            print("Firebase Admin SDK initialized successfully from local file.")
        else:
            print("WARNING: Firebase credentials not found in env var or local file. Firebase features will be disabled.")
    
    # Add scheduled jobs
    scheduler.add_job(deactivate_expired_subscriptions, 'interval', hours=24)
    scheduler.add_job(send_task_reminders, 'interval', minutes=5)
    
    # Habit management jobs
    scheduler.add_job(cleanup_old_habit_events, 'cron', hour=0, minute=0)  # Daily at midnight
    scheduler.add_job(maintain_habit_schedules, 'cron', hour=1, minute=0)  # Daily at 1 AM
    scheduler.add_job(process_expired_challenges, 'interval', minutes=15) # Check every 15 mins
    
    scheduler.start()
    print("Scheduler started...")
    
    yield
    
    print("Application shutdown...")
    scheduler.shutdown()
    print("Scheduler shut down.")

app = FastAPI(
    title="TaskAI Backend API",
    description="واجهة برمجية خلفية لإدارة المهام والعادات والملاحظات",
    version="1.0.0",
    lifespan=lifespan
)

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
        "https://admagh.vercel.app",
        "https://admagh-back-rf3.vercel.app",
        "*"
    ],
    allow_origin_regex="https?://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(tasks.router)
app.include_router(notes.router)
app.include_router(payments.router)
app.include_router(subscriptions.router)
app.include_router(friends.router)
app.include_router(calendar.router)
app.include_router(habits.router)
app.include_router(challenges.router)
app.include_router(ai.router)


@app.get("/")
def read_root():
    return {"message": "مبارك لقد تم تهكيرك بنجاح!"}
