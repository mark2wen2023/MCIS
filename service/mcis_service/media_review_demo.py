"""Explicit isolated review demo. No model-enabling arguments or default app wiring."""


def create_media_review_demo(settings):
    """Caller must supply isolated settings; this factory never starts OCR/ASR."""
    # Importing this factory must not initialize application/seed dependencies.
    # Explicit invocation retains the original import and registration order.
    from .main import create_app
    from .image_review.app import register_image_review
    from .audio_review.app import register_audio_review

    app = create_app(settings)
    register_image_review(app)
    register_audio_review(app)
    return app
