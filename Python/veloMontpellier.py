from TP1_TimotheeSOUCHET import *
from math import *
import requests
import json
import time
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns


def SuiviParkingMontpellier():
    # On demande ici a l'utilisateur de saisir  d'abord combien veut-il qu'il sécoule de temps entre chaque scans. Ensuite on lui demande
    # la durée de l'analyse et finalement comment va s'appeler son fichier.
    PeriodeEchantillon = input("Saisisez un entier qui est la periode de repetition du scan ? (ex: 1 sec, 15 sec, 15 min, 15 heure) : ")
    DurerAcquisition = input("Saisisez un entier qui est la durée de l'analise ? (ex: 1 min, 1 heure, 1 jour) : ")
    Fichier = input("Precisé comment voulais vous que se nomme votre fichier ? : ")

    # Ce split ici permet de de separer le nombre ou chiffre entrer de son unité ce qui nous permettra de le trier plus tard.
    TempsTe = int(PeriodeEchantillon.split()[0])
    TempsTa = int(DurerAcquisition.split()[0])

    # Ici on initialise quelques variables qui nous permettra d'ecrire dans un autre fichier si le temps est trop long.
    index = ""
    ChangementFichier = 0
    y = 0

    # Cela permet d'adapter le temps d'echantillonage et la durée d'acquisition selon l'unité rentrer dans l'input
    if PeriodeEchantillon.split()[1] == 'min' or PeriodeEchantillon.split()[1] == 'mins':
        TempsTe = TempsTe*60
    elif PeriodeEchantillon.split()[1] == 'heure' or PeriodeEchantillon.split()[1] == 'heures':
        TempsTe = TempsTe*3600
    if DurerAcquisition.split()[1] == 'min' or DurerAcquisition.split()[1] == 'mins':
        TempsTa = TempsTa*60
    elif DurerAcquisition.split()[1] == 'heure' or DurerAcquisition.split()[1] == 'heures':
        TempsTa = TempsTa*3600
    elif DurerAcquisition.split()[1] == 'jour' or DurerAcquisition.split()[1] == 'jours':
        TempsTa = TempsTa*86400
    if TempsTe != 0:
        Ta = int(TempsTa // TempsTe)  # Calcul du nombre de boucles
        Parkings = []  # Liste pour stocker les données de chaque itération

        for i in range(Ta):
            response = requests.get("https://portail-api-data.montpellier3m.fr/bikestation?limit=1000")
            data = response.json()
            iteration_data = {}  # Nouveau dictionnaire pour cette itération

            with open(f"{Fichier + index}.txt", "a", encoding="utf-8") as f, open(f"{Fichier + index}_data.json", "w", encoding="utf-8") as json_file:
                count = 0
                pourcentage_tot = 0
                for parking in data:
                    Nom = parking["address"]["value"]["streetAddress"]
                    available = parking["availableBikeNumber"]["value"]
                    total = parking["totalSlotNumber"]["value"]
                    date = parking["availableBikeNumber"]["metadata"]["timestamp"]["value"]
                    coordonnee = parking["location"]["value"]["coordinates"]
                    pourcentage = (available / total) * 100

                    # Ajout des données au dictionnaire pour cette itération
                    iteration_data[Nom] = {
                        'libre': available,
                        'total': total,
                        'coordonne': coordonnee,
                        'date': date
                    }

                    # Écriture dans le fichier texte
                    f.write(
                        f"{Nom} - {available}/{total} places soit {round(pourcentage, 2)}% des places sont disponibles.\n")
                    pourcentage_tot += pourcentage
                    count += 1

                # Ajout des données de cette itération à la liste principale
                Parkings.append(iteration_data)

                # Calcul du pourcentage total
                PourcentageTotale = pourcentage_tot / count
                f.write(
                    f"\nLe pourcentage total de place disponible dans les parkings de Montpellier est de : {round(PourcentageTotale, 2)}% \n\n")

                # Écriture dans le fichier JSON avec la liste complète
                json.dump(Parkings, json_file, indent=4)

            # Gestion des fichiers si dépassement d'une heure
            ChangementFichier += TempsTe
            """if ChangementFichier >= 3600:  # Création d'un nouveau fichier toutes les heures
                y += 1
                index = f"{y}"
                ChangementFichier = 0"""

            time.sleep(TempsTe)  # Pause avant la prochaine itération
    else:
        print("Vous avez saisi de mauvaise informations.")

SuiviParkingMontpellier()
