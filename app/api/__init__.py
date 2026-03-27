from fastapi import APIRouter

from app.api.routes_datasets import router as datasets_router
from app.api.routes_generation import router as generation_router
from app.api.routes_integrations import router as integrations_router
from app.api.routes_prompt_templates import router as prompt_templates_router
from app.api.routes_review import router as review_router
from app.api.routes_samples import router as samples_router

api_router = APIRouter()
api_router.include_router(samples_router)
api_router.include_router(generation_router)
api_router.include_router(datasets_router)
api_router.include_router(review_router)
api_router.include_router(integrations_router)
api_router.include_router(prompt_templates_router)
