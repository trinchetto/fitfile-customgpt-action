from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse

from .models import BuildFitRequest, ParseFitResponse
from .services import build_fit_file, parse_fit_bytes

router = APIRouter()


@router.get("/healthz", response_class=JSONResponse, summary="Simple readiness probe.")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post(
    "/parse",
    response_model=ParseFitResponse,
    summary="Parse a FIT file into a JSON-friendly structure.",
)
async def parse_fit(file: UploadFile = File(...)) -> ParseFitResponse:
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="The provided FIT file is empty.")

    return parse_fit_bytes(data)


@router.post(
    "/produce",
    summary="Build a FIT file from a list of FIT messages.",
)
async def produce_fit(
    request: BuildFitRequest,
    filename: str = "generated.fit",
) -> StreamingResponse:
    stream = build_fit_file(request)
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(
        stream,
        media_type="application/octet-stream",
        headers=headers,
    )
