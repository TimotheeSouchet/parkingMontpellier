from math import *
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

#Instants de la mesure ( h )
T=[0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23]

#Série 1 : températures ( °C )
L1=[3,3,4,3,2,5,8,9,13,16,18,18,19,21,22,22,21,17,17,12,10,8,7,4]

#Série 2 : températures ( °C )
L2=[103,203,4,3,2,5,8,9,13,16,18,18,19,21,22,22,21,17,17,12,10,-92,-93,-96]

L3=[]

Liste =[T, L1, L2]

def Moyenne(liste):
    """Calcul de la moyenne d'une liste."""
    count = 0
    for i in range(len(liste)):
        count += liste[i]
    if len(liste) != 0:
        MoyenneFinal = count / len(liste)
    else:
        return 0
    return round(MoyenneFinal, 2)

def Sigma(liste):
    """Calcule l'écart type d'une liste."""
    moyenne = Moyenne(liste)
    varianceElement = 0
    for i in range(len(liste)):
        varianceElement += (liste[i - 1] - moyenne)**2
    varianceTot = varianceElement / len(liste)
    EcartType = round(sqrt(varianceTot), 2)
    return EcartType

def Covariance(liste1, liste2):
    """Calcule la covariance entre deux listes."""
    moyenne1 = Moyenne(liste1)
    moyenne2 = Moyenne(liste2)
    CoVariance = 0
    if len(liste1) == len(liste2) and len(liste1) != 0:
        for i in range(len(liste1)):
            CoVarianceElement1 = (moyenne1 - liste1[i - 1])
            CoVarianceElement2 = (moyenne2 - liste2[i - 1])
            CoVariance += CoVarianceElement1 * CoVarianceElement2
        CoVarianceTot = CoVariance / len(liste1)
        return round(CoVarianceTot, 2)
    else:
        print("Vous ne pouvez pas faire la covariance de 2 listes qui n'ont pas le même nombres d'éléments.")

def Correlation(liste1, liste2):
    """Calcule la corrélation entre deux listes."""
    CoVarianceListes = Covariance(liste1, liste2)
    EcartType1 = Sigma(liste1)
    EcartType2 = Sigma(liste2)
    CorrelationTot = CoVarianceListes / (EcartType1*EcartType2)
    return round(CorrelationTot, 2)

def MatriceCorrelation(data):
    """Crée une matrice de corrélation pour un ensemble de données."""
    matrice = []
    for i in range(len(data)):
        L = []
        for y in range(len(data)):
            L.append(Correlation(data[i], data[y]))
        matrice.append(L)
    return matrice


def plotlibListe(Liste1, Liste2, titre: str, AxeX: str, AxeY: str):
    """Représente graphiquement deux listes avec des dates lisibles."""
    plt.figure(figsize=(12, 6))  # Augmenter la taille de la figure pour plus de clarté

    # Création du graphique
    plt.plot(Liste1, Liste2, marker='o')  # Ajouter des marqueurs pour plus de lisibilité
    plt.title(titre)
    plt.xlabel(AxeX)
    plt.ylabel(AxeY)
    plt.xticks(rotation=45)
    plt.xticks(rotation=45)

    plt.grid()  # Ajouter une grille pour plus de clarté
    plt.show()

def plotlibData(donnee):
    """Crée une heatmap basée sur les corrélations entre plusieurs séries de listes."""
    sns.heatmap(MatriceCorrelation(donnee), annot=True, cmap="coolwarm", fmt=".0f", linewidths=1, linecolor="white")
    plt.title("Heatmap basée sur des listes de nombres")
    plt.xlabel("Axe des X")
    plt.ylabel("Axe des Y")
    plt.show()

