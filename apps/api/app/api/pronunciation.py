"""Pronunciation routes (specs/pronunciation/step-3.1.md): prompts and recordings."""

from typing import Any

from fastapi import APIRouter, Query, Request, Response

from app.services.recordings import MAX_BYTES, LabelsIn, Recordings

SLUG = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"


def create_router(recordings: Recordings) -> APIRouter:
    router = APIRouter(tags=["pronunciation"])

    @router.get("/pronunciation/prompts")
    def prompts(learner_id: str = Query(min_length=1, max_length=200)) -> dict[str, Any]:
        return {
            "can_record": recordings.can_record(learner_id),
            "consent": "voice-v1",
            "sounds": [s.model_dump() for s in recordings.sounds.values()],
            "prompts": [p.model_dump() for p in recordings.prompts],
        }

    @router.post("/recordings")
    async def record(
        request: Request,
        learner_id: str = Query(min_length=1, max_length=200),
        prompt_id: str = Query(min_length=1, max_length=10),
        consent: str = Query(min_length=1, max_length=20),
        keep: bool = Query(default=False),
    ) -> dict[str, Any]:
        audio = await request.body()
        if len(audio) > MAX_BYTES:
            return {"quality": {"ok": False, "problems": ["too_long"]}, "id": None}
        return recordings.store(learner_id, prompt_id, consent, keep, audio)

    @router.get("/recordings")
    def list_recordings(
        learner_id: str = Query(min_length=1, max_length=200),
    ) -> list[dict[str, Any]]:
        return recordings.list(learner_id)

    @router.get("/recordings/{recording_id}")
    def get_recording(
        recording_id: str, learner_id: str = Query(min_length=1, max_length=200)
    ) -> dict[str, Any]:
        return recordings.get(learner_id, recording_id)

    @router.get("/recordings/{recording_id}/audio")
    def recording_audio(
        recording_id: str, learner_id: str = Query(min_length=1, max_length=200)
    ) -> Response:
        return Response(
            recordings.audio(learner_id, recording_id),
            media_type="audio/wav",
            headers={"Cache-Control": "no-store"},
        )

    @router.post("/recordings/{recording_id}/labels", status_code=204)
    def label_recording(
        recording_id: str, body: LabelsIn, learner_id: str = Query(min_length=1, max_length=200)
    ) -> Response:
        recordings.label(learner_id, recording_id, body.labels)
        return Response(status_code=204)

    @router.delete("/recordings/{recording_id}", status_code=204)
    def delete_recording(
        recording_id: str, learner_id: str = Query(min_length=1, max_length=200)
    ) -> Response:
        recordings.delete(learner_id, recording_id)
        return Response(status_code=204)

    return router
