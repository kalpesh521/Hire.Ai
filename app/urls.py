 
from django.urls import path
from . import views 
from django.conf import settings
from django.conf.urls.static import static
from .views import end, process_audio ,start,process_audio_and_openai, process_user_audio, next
  
urlpatterns = [
    path('process/', process_audio, name='process_audio'),
    path('start/', start, name='start'),

    path('process_audio_and_openai/<int:audio_file_id>/', process_audio_and_openai, name='process_audio_and_openai'),
    # path('transcribe/<int:audio_file_id>/', views.transcribe_view, name='transcribe_view'),
    # path('get_openai_response/', get_openai_response, name='get_openai_response'),
    path('', views.index, name='index'),
    
    path('post_audio/', process_user_audio, name='post_audio'),
    path('end/', end, name='end'),
    path('next/', next, name='next')
] + static(settings.MEDIA_URL,document_root=settings.MEDIA_ROOT)
  