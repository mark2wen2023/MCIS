"""Explicit isolated review demo. No model-enabling arguments or default app wiring."""
from .main import create_app
from .image_review.app import register_image_review
from .audio_review.app import register_audio_review


def create_media_review_demo(settings):
    """Caller must supply isolated settings; this factory never starts OCR/ASR."""
    app = create_app(settings)
    register_image_review(app)
    register_audio_review(app)
    return app
