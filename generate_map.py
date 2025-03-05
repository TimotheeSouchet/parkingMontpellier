import folium
import requests

# Charger les données des parkings voitures et vélos depuis les API
response = requests.get("https://portail-api-data.montpellier3m.fr/offstreetparking?limit=1000")
data_car = response.json()

respon1 = requests.get("https://portail-api-data.montpellier3m.fr/bikestation?limit=1000")
data_bike = respon1.json()

# Créer une carte centrée sur Montpellier
montpellier_map = folium.Map(location=[43.6117, 3.8777], zoom_start=12)

# Fonction pour déterminer la couleur en fonction du taux d'occupation
def get_color(occupancyrate):
    if occupancyrate == 0:
        return 'lightgray'  # 0% d'occupation
    elif occupancyrate > 75:
        return 'green'
    elif occupancyrate > 50:
        return 'orange'
    elif occupancyrate > 25:
        return 'red'
    else:
        return 'blue'

# Ajouter les parkings voitures à la carte
for parking in data_car:
    name = parking['name']['value']
    available_spots = parking['availableSpotNumber']['value']
    total_spots = parking['totalSpotNumber']['value']
    coordinates = parking['location']['value']['coordinates']
    
    # Calculer le taux d'occupation
    #occupancy_rate = (available_spots / total_spots) * 100
    
    # Déterminer la couleur en fonction du taux d'occupation
    color = get_color(occupancy_rate)
    
    # Créer une info popup
    #popup_info = f"Parking voiture: {name}<br>Disponibles: {available_spots}/{total_spots} places<br>Taux d'occupation: {occupancy_rate:.2f}%"
    
    # Ajouter un marqueur à la carte
    folium.Marker(
        location=[coordinates[1], coordinates[0]],
        popup=popup_info,
        icon=folium.Icon(color=color, icon='info-sign')
    ).add_to(montpellier_map)

# Ajouter les parkings vélos à la carte
for parking in data_bike:
    name = parking["address"]["value"]["streetAddress"]
    available = parking["availableBikeNumber"]["value"]
    total = parking["totalSlotNumber"]["value"]
    coordinates = parking["location"]["value"]["coordinates"]
    
    # Calculer le taux d'occupation
    occupancy_rate = (available / total) * 100
    
    # Déterminer la couleur en fonction du taux d'occupation
    color = get_color(occupancy_rate)
    
    # Créer une info popup
    #popup_info = f"Parking vélo: {name}<br>Disponibles: {available}/{total} places<br>Taux d'occupation: {occupancy_rate:.2f}%"
    
    # Ajouter un marqueur à la carte
    folium.Marker(
        location=[coordinates[1], coordinates[0]],
        popup=popup_info,
        icon=folium.Icon(color=color, icon='info-sign')
    ).add_to(montpellier_map)

# Sauvegarder la carte en fichier HTML
montpellier_map.save("MontpellierParking.html")
print("Carte générée : MontpellierParking.html")
