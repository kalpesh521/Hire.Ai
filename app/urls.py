 
from django.urls import path
from . import views 
from django.conf import settings
from django.conf.urls.static import static
from .views import process_audio ,save_user_details,process_audio_and_openai
  
urlpatterns = [
    path('process/', process_audio, name='process_audio'),
    path('user/', save_user_details, name='save_user_details'),

    path('process_audio_and_openai/<int:audio_file_id>/', process_audio_and_openai, name='process_audio_and_openai'),
    # path('transcribe/<int:audio_file_id>/', views.transcribe_view, name='transcribe_view'),
    # path('get_openai_response/', get_openai_response, name='get_openai_response'),
    path('', views.index, name='index'),
] + static(settings.MEDIA_URL,document_root=settings.MEDIA_ROOT)
  