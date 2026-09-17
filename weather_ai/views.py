from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from accounts.rbac import permission_required
from django.conf import settings
from chat_ai.services import ask_ollama
import requests
@login_required
@permission_required('weather.view')
def forecast(request):
    data={}; ai=''
    try:
        url='https://api.open-meteo.com/v1/forecast'
        params={'latitude':settings.FARM_LAT,'longitude':settings.FARM_LON,'current':'temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation','daily':'temperature_2m_max,temperature_2m_min,precipitation_probability_max','timezone':'Asia/Jakarta'}
        data=requests.get(url,params=params,timeout=15).json()
        if request.GET.get('ai'):
            ai=ask_ollama('Analisa dampak cuaca berikut untuk tambak udang vaname dan beri rekomendasi singkat: '+str(data.get('current',{})))
    except Exception as e: data={'error':str(e)}
    return render(request,'weather_ai/forecast.html',{'data':data,'ai':ai})
