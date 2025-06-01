from flask import Flask, render_template, request, jsonify, make_response
import requests
from datetime import date, timedelta

app = Flask(__name__)

# Для получения координат по названию города
GEO_API = "https://geocoding-api.open-meteo.com/v1/search"
# Для получения погоды по координатам
WEATHER_API = "https://api.open-meteo.com/v1/forecast"


@app.route('/autocomplete')
def autocomplete():
    query = request.args.get('q', '')
    if not query:
        return jsonify([])

    geo_resp = requests.get(GEO_API, params={
        "name": query,
        "count": 5,
        "language": "ru",
        "format": "json"
    })

    geo_data = geo_resp.json()
    results = geo_data.get("results", [])
    suggestions = [f"{r['name']}".strip(', ') for r in results]
    return jsonify(suggestions)

@app.route("/", methods=["GET", "POST"])
def index():
    current_weather = None
    forecast = []
    error = None
    city_name = None
    #берем из куки последний город
    last_city = request.cookies.get("last_city")
    if request.method == "POST":
        city = request.form.get("city")

        # Запрос координат по названию города
        geo_resp = requests.get(GEO_API, params={
            "name": city,
            "count": 1,
            "language": "ru",
            "format": "json"
        })

        geo_answer = geo_resp.json()
        if "results" in geo_answer and geo_answer["results"]:
            geo_info = geo_answer["results"][0]
            lat = geo_info["latitude"]
            lon = geo_info["longitude"]
            city_name = geo_info["name"]

            today = date.today()
            end_date = today + timedelta(days=4)

            # Запрос прогноза погоды
            weather_resp = requests.get(WEATHER_API, params={
                "latitude": lat,
                "longitude": lon,
                "current_weather": "true",
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,windspeed_10m_max",
                "timezone": "auto",
                "start_date": today.isoformat(),
                "end_date": end_date.isoformat()
            })

            weather_data = weather_resp.json()
            current_weather = weather_data.get("current_weather", {})
            current_weather["time"] = current_weather["time"][-5:] #Читаемый вид времени

            daily = weather_data.get("daily", {})
            dates = daily.get("time", [])
            temps_max = daily.get("temperature_2m_max", [])
            temps_min = daily.get("temperature_2m_min", [])
            precipitation = daily.get("precipitation_sum", [])
            windspeed = daily.get("windspeed_10m_max", [])

            for i in range(len(dates)):
                forecast.append({
                    "date": dates[i],
                    "temp_max": temps_max[i],
                    "temp_min": temps_min[i],
                    "precipitation": precipitation[i],
                    "windspeed": windspeed[i]
                })
        else:
            error = "Город не найден. Попробуйте снова."
    response = make_response(render_template(
        "index.html",
        weather=current_weather,
        forecast=forecast,
        error=error,
        city_name=city_name,
        last_city=last_city
    ))
    #заполняем куки на день городом.
    if city_name:
        response.set_cookie("last_city", city_name, max_age=60 * 60 * 24 )
    return response

if __name__ == '__main__':
    app.run(debug=True)
