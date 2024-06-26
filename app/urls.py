from django.conf import settings
from django.conf.urls.static import static
from django.urls import path

from . import views
from .views import (
    clear_history,
    get_evaluation,
    initialize_session,
    process_audio,
    process_audio_and_openai,
    process_user_audio,
    send_email_to_candidate,
)

urlpatterns = [
    path("process/", process_audio, name="process_audio"),
    path(
        "process_audio_and_openai/<int:audio_file_id>/",
        process_audio_and_openai,
        name="process_audio_and_openai",
    ),
    # path('transcribe/<int:audio_file_id>/', views.transcribe_view, name='transcribe_view'),
    # path('get_openai_response/', get_openai_response, name='get_openai_response'),
    path("", views.index, name="index"),
    path("initialize_session/", initialize_session, name="initialize_session"),
    path("post_audio/", process_user_audio, name="post_audio"),
    path("end/", clear_history, name="end"),
    path("evaluate/<str:id>", get_evaluation, name="evaluate"),
    path("mail/", send_email_to_candidate, name="mail"),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
