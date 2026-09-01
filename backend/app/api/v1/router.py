from fastapi import APIRouter

from backend.app.api.v1.endpoints import (
    auth,
    wilayah,
    faskes,
    indikator,
    katalog,
    transaksi,
    statistik,
    ask,
)

api_router = APIRouter()

# Register all endpoint routers under /api/v1
api_router.include_router(auth.router)
api_router.include_router(wilayah.router)
api_router.include_router(faskes.router)
api_router.include_router(indikator.router)
api_router.include_router(katalog.router)
api_router.include_router(transaksi.router)
api_router.include_router(statistik.router)
api_router.include_router(ask.router)
