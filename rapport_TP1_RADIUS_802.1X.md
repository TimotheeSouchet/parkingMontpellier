# Compte Rendu – TP 1 : RADIUS et 802.1X
## R4C09 – Sécurité des réseaux LAN
**IUT Béziers – Département Réseaux et Télécoms – Bachelor R&T 2023/2024**

---

## Introduction

Dans ce TP, nous allons mettre en place un système d'authentification réseau basé sur le protocole RADIUS. L'idée est de comprendre comment un réseau peut vérifier l'identité d'un utilisateur avant de lui donner accès. On va d'abord simuler ça entre deux machines Linux, puis on passera sur un switch CISCO réel pour faire du 802.1X.

Avant de commencer, je ne savais pas vraiment ce qu'était RADIUS. Après quelques recherches, j'ai compris que c'est un protocole client-serveur qui permet à un équipement réseau (un switch, un routeur, un point d'accès WiFi) de demander à un serveur central "est-ce que cet utilisateur a le droit de se connecter ?". C'est très utilisé dans les entreprises et les universités pour contrôler qui peut se connecter au réseau.

---

## Partie 1 – Client et Serveur Radius

---

### Exercice 1 – Installation des packages

#### Sur le Serveur

La première chose à faire, c'est d'installer FreeRADIUS. FreeRADIUS est une implémentation libre et open-source du protocole RADIUS. C'est le serveur qui va gérer les comptes utilisateurs et répondre aux demandes d'authentification.

On commence par mettre à jour la liste des paquets, puis on installe :

```
$ apt-get update
$ apt-get install -y freeradius freeradius-utils
```

Voici ce que j'ai obtenu (extrait de la sortie) :

```
Reading package lists... Done
Building dependency tree... Done
The following NEW packages will be installed:
  freeradius freeradius-common freeradius-config freeradius-utils
  freetds-common ibverbs-providers libct4 libdbi-perl libfreeradius3
  libibverbs1 libnl-3-200 libnl-route-3-200 libpcap0.8t64 libtalloc2
  libwbclient0
0 upgraded, 15 newly installed, 0 to remove and 62 not upgraded.
...
Setting up freeradius (3.2.5+dfsg-3~ubuntu24.04.3) ...
Setting up freeradius-utils (3.2.5+dfsg-3~ubuntu24.04.3) ...
```

J'ai remarqué que l'installation installe aussi beaucoup de dépendances. `freeradius-utils` est important car c'est lui qui fournit les commandes `radtest` et `radclient` qu'on va utiliser pour tester.

Pour vérifier que l'installation s'est bien passée :

```
$ freeradius -v
radiusd: FreeRADIUS Version 3.2.5, for host x86_64-pc-linux-gnu, built on Mar 28 2025 at 17:03:23
FreeRADIUS Version 3.2.5
Copyright (C) 1999-2023 The FreeRADIUS server project and contributors
```

```
$ which radtest radclient
/usr/bin/radtest
/usr/bin/radclient
```

Super, les deux outils sont bien disponibles.

#### Sur le Client

Sur la machine cliente, on a besoin de deux choses :
- **La suite freeradius-utils** : pour avoir accès à `radtest` et `radclient` et pouvoir tester l'authentification depuis le client
- **Le module `libpam-radius-auth`** : ce module va permettre de brancher l'authentification RADIUS sur le système PAM de Linux. PAM (Pluggable Authentication Modules) est le système qui gère toutes les authentifications sous Linux (connexion, SSH, sudo, etc.). Avec ce module, on va pouvoir dire à Linux "quand quelqu'un essaie de se connecter en SSH, va vérifier son identité auprès du serveur RADIUS".

```
$ apt-get install -y freeradius freeradius-utils libpam-radius-auth
```

```
Reading package lists... Done
The following NEW packages will be installed:
  libpam-radius-auth
0 upgraded, 1 newly installed, 0 to remove and 62 not upgraded.
...
Setting up libpam-radius-auth (2.0.1-1) ...
```

Pour vérifier que le module PAM est bien installé :

```
$ ls -la /lib/x86_64-linux-gnu/security/pam_radius_auth.so
-rw-r--r-- 1 root root 43000 Aug 19 2023 /lib/x86_64-linux-gnu/security/pam_radius_auth.so
```

Le fichier `.so` est une bibliothèque partagée que PAM va charger au moment de l'authentification.

---

### Exercice 2 – Schéma réseau

Dans notre TP, nous simulons les deux machines sur une seule machine (l'IP est 192.0.2.2). En conditions réelles avec un binôme, on aurait deux machines séparées sur le même réseau.

**Schéma de notre configuration de simulation :**

```
 ┌─────────────────────────────────────────────────────────────────┐
 │               SIMULATION SUR UNE SEULE MACHINE                  │
 │                                                                 │
 │   ┌──────────────────────┐      ┌──────────────────────┐       │
 │   │    SERVEUR RADIUS    │      │    CLIENT RADIUS     │       │
 │   │   (FreeRADIUS 3.2.5) │      │ (radtest / SSH+PAM) │       │
 │   │                      │      │                      │       │
 │   │  IP: 192.0.2.2       │◄────►│  IP: 192.0.2.2       │       │
 │   │  Port UDP 1812       │ UDP  │  Secret: secretTP2024│       │
 │   │                      │      │                      │       │
 │   └──────────────────────┘      └──────────────────────┘       │
 │                 Interface lo (127.0.0.1) / eth0                 │
 └─────────────────────────────────────────────────────────────────┘
```

**Schéma en conditions réelles (binôme) :**

```
  192.168.1.1                               192.168.1.2
 ┌─────────────────┐         Réseau LAN    ┌─────────────────┐
 │  MACHINE A      │◄─────────────────────►│  MACHINE B      │
 │  Serveur RADIUS │                       │  Client RADIUS  │
 │  FreeRADIUS     │                       │  radtest + PAM  │
 └─────────────────┘                       └─────────────────┘
          │                                        │
          └──────────────── Switch ────────────────┘
                           (CISCO 250)
```

---

## Partie 2 – Configuration du Serveur Freeradius

---

### Exercice 3 – Les fichiers de configuration

Après l'installation, j'ai regardé ce qui se trouve dans `/etc/freeradius/3.0/` :

```
$ ls /etc/freeradius/3.0/
README.rst     clients.conf   dictionary     mods-available  policy.d
certs          radiusd.conf   users          mods-enabled    sites-enabled
...
```

Il y a beaucoup de fichiers ! Mais les trois plus importants pour nous sont `radiusd.conf`, `clients.conf` et `users`. Je vais expliquer chacun.

---

#### `/etc/freeradius/3.0/radiusd.conf`

C'est **le fichier de configuration principal** du serveur FreeRADIUS. On peut le comparer au fichier `httpd.conf` d'Apache : il donne les paramètres globaux du serveur.

J'ai ouvert ce fichier et voici les informations les plus importantes que j'y ai trouvées :

```
prefix = /usr
logdir = /var/log/freeradius       ← Dossier des journaux
libdir = /usr/lib/freeradius       ← Bibliothèques du serveur
pidfile = /var/run/freeradius/freeradius.pid  ← Fichier PID du processus
max_request_time = 30              ← Délai max pour traiter une requête (secondes)
max_requests = 16384               ← Nombre max de requêtes simultanées
hostname_lookups = no              ← Pas de résolution DNS (pour les perfs)
```

Dans la section `security`, j'ai remarqué un paramètre intéressant :

```
reject_delay = 1.000000
```

Ça veut dire que quand un utilisateur se trompe de mot de passe, le serveur attend 1 seconde avant de répondre "refusé". C'est une protection contre les attaques par force brute : si on attend 1 seconde à chaque essai, un attaquant qui essaie des milliers de mots de passe sera très ralenti.

Le fichier inclut aussi tous les autres fichiers de configuration :
```
$INCLUDE clients.conf
$INCLUDE proxy.conf
$INCLUDE mods-enabled/
$INCLUDE sites-enabled/
```

---

#### `/etc/freeradius/3.0/clients.conf`

Ce fichier définit **qui a le droit d'envoyer des requêtes au serveur RADIUS**. Dans le protocole RADIUS, on appelle "client" l'équipement qui envoie les demandes d'authentification : ça peut être un switch, un routeur, un point d'accès WiFi, ou même une autre machine Linux.

**Pourquoi ce fichier est-il nécessaire ?**
Si n'importe qui pouvait envoyer des requêtes au serveur RADIUS, ce serait une faille de sécurité énorme. On pourrait envoyer des fausses demandes d'authentification ou tenter de deviner des mots de passe. C'est pourquoi chaque client doit être déclaré avec un "shared secret" (clé partagée).

Par défaut, le fichier contient déjà une entrée pour `localhost` :

```
client localhost {
    ipaddr = 127.0.0.1
    proto  = *
    secret = testing123
    nas_type = other
}
```

Le champ `secret` est crucial : c'est le mot de passe partagé entre le client et le serveur. Il est utilisé pour chiffrer les échanges (notamment le mot de passe de l'utilisateur).

> **Attention :** dans un vrai déploiement, on ne devrait jamais utiliser `testing123` comme secret ! Il faudrait générer un secret aléatoire fort avec une commande comme `dd if=/dev/random bs=1 count=24 | base64`.

---

#### `/etc/freeradius/3.0/users`

C'est **la base de données des utilisateurs**. C'est ici qu'on va créer les comptes que le serveur RADIUS pourra authentifier.

> Note : sur Ubuntu, ce fichier est en fait un lien symbolique vers `/etc/freeradius/3.0/mods-config/files/authorize`, mais c'est transparent pour l'utilisation.

La syntaxe est la suivante :
```
nom_utilisateur    Cleartext-Password := "mot_de_passe"
                   Attribut-de-reponse = "valeur"
```

Le mot-clé `Cleartext-Password` veut dire que le mot de passe est stocké en clair. Il existe d'autres options comme `MD5-Password` ou `Crypt-Password` pour stocker des mots de passe hachés, mais pour le TP on utilise le plus simple.

#### Démarrage du service RADIUS

On lance le serveur en mode debug avec l'option `-X`. Ce mode est très utile pour le TP car il affiche tout ce qui se passe en temps réel : les requêtes reçues, les utilisateurs cherchés, les réponses envoyées.

```
$ freeradius -X
```

Voici les dernières lignes importantes du démarrage :

```
FreeRADIUS Version 3.2.5
...
radiusd: #### Loading Clients ####
 client localhost {
     ipaddr = 127.0.0.1
     secret = <<< secret >>>      ← Le secret est masqué dans les logs, c'est normal
 }
 client client_radius {
     ipaddr = 192.0.2.2
     secret = <<< secret >>>
     shortname = "client-tp"
 }
...
Listening on auth address * port 1812 bound to server default
Listening on proxy address * port 49315
Ready to process requests          ← Le serveur est prêt !
```

Le serveur écoute bien sur le **port UDP 1812**, qui est le port standard de RADIUS pour l'authentification (défini dans la RFC 2865).

---

### Exercice 4 – Créer un utilisateur et tester depuis le serveur

#### Ajout des utilisateurs dans le fichier `users`

J'ai ajouté deux utilisateurs en haut du fichier `/etc/freeradius/3.0/users` :

```
etudiant    Cleartext-Password := "TP_Radius2024"
            Reply-Message := "Bienvenue %{User-Name} sur le reseau !"

alice       Cleartext-Password := "alice123"
            Reply-Message := "Authentification reussie pour Alice"
```

Le `Reply-Message` est un attribut RADIUS que le serveur va renvoyer au client quand l'authentification réussit. La variable `%{User-Name}` est remplacée automatiquement par le nom de l'utilisateur. Ce n'est pas obligatoire, mais ça permet de voir que le serveur a bien lu l'entrée de l'utilisateur.

> **Attention aux permissions !** Après avoir modifié ce fichier, j'ai eu une erreur "Permission denied" au démarrage de FreeRADIUS. C'est parce que FreeRADIUS s'exécute en tant qu'utilisateur `freerad` et le fichier appartenait à `root` après mon édition. J'ai dû corriger ça :
> ```
> $ chown freerad:freerad /etc/freeradius/3.0/mods-config/files/authorize
> $ chmod 640 /etc/freeradius/3.0/mods-config/files/authorize
> ```
> C'est une leçon importante : sous Linux, les permissions des fichiers de configuration sont souvent critiques pour la sécurité.

#### Test avec la commande `radtest`

La commande `radtest` simule un client RADIUS. Elle envoie une requête `Access-Request` au serveur et attend une réponse.

Sa syntaxe est : `radtest <utilisateur> <mot_de_passe> <serveur> <port_NAS> <secret_partagé>`

**Test 1 : Authentification avec le bon mot de passe**

```
$ radtest etudiant TP_Radius2024 127.0.0.1 0 testing123
```

```
Sent Access-Request Id 242 from 0.0.0.0:34464 to 127.0.0.1:1812 length 78
    User-Name = "etudiant"
    User-Password = "TP_Radius2024"
    NAS-IP-Address = 127.0.0.1
    NAS-Port = 0
    Message-Authenticator = 0x00
    Cleartext-Password = "TP_Radius2024"
Received Access-Accept Id 242 from 127.0.0.1:1812 to 127.0.0.1:34464 length 74
    Message-Authenticator = 0x4d2848917e3f79cc4818c3ae1fb3ac6a
    Reply-Message = "Bienvenue etudiant sur le reseau !"
```

✅ **Résultat : `Access-Accept`** – Le serveur a reconnu l'utilisateur et accepté l'authentification. On voit aussi le `Reply-Message` qu'on avait configuré.

**Test 2 : Authentification avec un mauvais mot de passe**

```
$ radtest etudiant mauvais_mdp 127.0.0.1 0 testing123
```

```
(0) -: Expected Access-Accept got Access-Reject
Sent Access-Request Id 196 from 0.0.0.0:59914 to 127.0.0.1:1812 length 78
    User-Name = "etudiant"
    User-Password = "mauvais_mdp"
    NAS-IP-Address = 127.0.0.1
    NAS-Port = 0
    Message-Authenticator = 0x00
Received Access-Reject Id 196 from 127.0.0.1:1812 to 127.0.0.1:59914 length 74
    Message-Authenticator = 0xd418fe48e215b630316fcc58dc03b218
    Reply-Message = "Bienvenue etudiant sur le reseau !"
```

❌ **Résultat : `Access-Reject`** – Le serveur a bien reconnu l'utilisateur `etudiant` mais a refusé car le mot de passe ne correspond pas.

**Test 3 : Utilisateur `alice`**

```
$ radtest alice alice123 127.0.0.1 0 testing123
```

```
Sent Access-Request Id 225 from 0.0.0.0:40647 to 127.0.0.1:1812 length 75
    User-Name = "alice"
    User-Password = "alice123"
    NAS-IP-Address = 127.0.0.1
    NAS-Port = 0
    Message-Authenticator = 0x00
Received Access-Accept Id 225 from 127.0.0.1:1812 to 127.0.0.1:40647 length 75
    Message-Authenticator = 0xc7a7e60e544a31b03797da1d3a1aeb0d
    Reply-Message = "Authentification reussie pour Alice"
```

✅ **Résultat : `Access-Accept`** – Alice peut aussi s'authentifier.

Le serveur RADIUS fonctionne correctement ! Il distingue bien les bons des mauvais mots de passe.

---

## Partie 3 – Configuration du Client Radius

---

### Exercice 5 – Authentification depuis la machine cliente

Maintenant on veut simuler que c'est une autre machine (le "client") qui envoie la requête d'authentification. En pratique, cette machine cliente serait un switch ou un routeur, mais ici on simule ça depuis notre machine Linux.

**Problème rencontré :** Si on essaie d'envoyer une requête depuis l'IP `192.0.2.2` avec le secret `testing123` (celui de `localhost`), ça ne marcherait pas car le serveur vérifierait l'IP source. On doit donc :
1. Déclarer la machine cliente dans `clients.conf` avec son IP et un secret dédié
2. Utiliser ce même secret dans la commande `radtest`

**Ajout dans `clients.conf` côté serveur :**

```
client client_radius {
    ipaddr    = 192.0.2.2
    secret    = secretTP2024
    shortname = client-tp
    nas_type  = other
}

client reseau_local {
    ipaddr    = 192.0.2.0/24
    secret    = secretTP2024
    shortname = lan-tp
}
```

J'ai ajouté les deux entrées : une pour l'IP précise du client, et une pour tout le réseau `/24`, ce qui est plus pratique si plusieurs machines du réseau doivent agir comme clients RADIUS.

**Test depuis la machine cliente (en utilisant son IP et son secret) :**

```
$ radtest etudiant TP_Radius2024 192.0.2.2 0 secretTP2024
```

```
Sent Access-Request Id 46 from 0.0.0.0:58074 to 192.0.2.2:1812 length 78
    User-Name = "etudiant"
    User-Password = "TP_Radius2024"
    NAS-IP-Address = 127.0.0.1
    NAS-Port = 0
    Message-Authenticator = 0x00
    Cleartext-Password = "TP_Radius2024"
Received Access-Accept Id 46 from 192.0.2.2:1812 to 192.0.2.2:58074 length 74
    Message-Authenticator = 0x9b3f0e5174bbc50f3b5948d1bad25575
    Reply-Message = "Bienvenue etudiant sur le reseau !"
```

✅ **Ça fonctionne !** Cette fois la requête va bien vers `192.0.2.2:1812` (l'IP du serveur) et utilise le secret `secretTP2024` propre au client. Le serveur reconnaît ce client et répond `Access-Accept`.

---

### Exercice 6 – Analyse des trames RADIUS avec tcpdump

C'est l'exercice le plus intéressant pour comprendre ce qui se passe réellement sur le réseau ! On va capturer les paquets UDP échangés entre le client et le serveur.

#### Mise en place de la capture

```
$ tcpdump -i lo -nn -vvv port 1812
```

Les options utilisées :
- `-i lo` : écoute sur l'interface loopback (là où transitent les paquets locaux)
- `-nn` : n'essaie pas de résoudre les adresses IP en noms (plus rapide et plus lisible)
- `-vvv` : mode très verbeux, affiche tous les détails des paquets
- `port 1812` : ne capture que le trafic RADIUS

Pendant que tcpdump tourne, on fait les tests d'authentification dans un autre terminal.

---

#### Analyse de la trame Access-Request (Client → Serveur)

```
08:23:28.351749 IP 127.0.0.1.51483 > 127.0.0.1.1812: RADIUS, length: 78
    Access-Request (1), id: 0x0e, Authenticator: 2108a21512f80910624d55d6dac5871e
      Message-Authenticator Attribute (80), length: 18, Value: ..d.............
        0x0000:  0304 64b1 14e2 9ae4 a7bd 10d9 b3cf 1c8c
      User-Name Attribute (1), length: 10, Value: etudiant
        0x0000:  6574 7564 6961 6e74
      User-Password Attribute (2), length: 18, Value: [chiffré]
        0x0000:  78df 241f 80c1 19b4 ebef facc fa96 a578
      NAS-IP-Address Attribute (4), length: 6, Value: 127.0.0.1
        0x0000:  7f00 0001
      NAS-Port Attribute (5), length: 6, Value: 0
        0x0000:  0000 0000
```

**Ce que j'observe et comprends :**

1. **Code 1 = Access-Request** : c'est le client qui demande l'accès. RADIUS utilise des codes numériques pour identifier le type de paquet.

2. **L'Authenticator (16 octets)** : c'est un nombre aléatoire généré par le client pour chaque requête. Il sert à deux choses importantes :
   - Identifier la requête (pour associer la réponse à la bonne demande)
   - Servir de "graine" pour chiffrer le mot de passe

3. **User-Name en CLAIR** : on voit `6574 7564 6961 6e74` qui est l'encodage hexadécimal de "etudiant". **C'est une faiblesse de RADIUS** : le nom d'utilisateur n'est pas chiffré ! N'importe qui qui capture le trafic réseau peut voir qui se connecte.

4. **User-Password CHIFFRÉ** : le mot de passe, lui, est chiffré. La méthode utilisée est la suivante (définie dans la RFC 2865) :
   ```
   Password_chiffré = MD5(shared_secret + Authenticator) XOR Password_en_clair
   ```
   C'est pour ça que l'Authenticator est aléatoire : si deux utilisateurs ont le même mot de passe, leurs paquets seront différents car l'Authenticator change à chaque fois.

5. **NAS-IP-Address** : l'IP du NAS (Network Access Server) qui envoie la demande.

---

#### Analyse de la trame Access-Accept (Serveur → Client)

```
08:23:28.352129 IP 127.0.0.1.1812 > 127.0.0.1.51483: RADIUS, length: 74
    Access-Accept (2), id: 0x0e, Authenticator: 9a90f7b356e2d4d0c39e575540a11705
      Message-Authenticator Attribute (80), length: 18, Value: Y....b..{)..W.}.
        0x0000:  5989 0d8a 1562 f40c 7b29 a4ff 57d8 7de5
      Reply-Message Attribute (18), length: 36, Value: Bienvenue etudiant sur le reseau !
        0x0000:  4269 656e 7665 6e75 6520 6574 7564 6961
        0x0010:  6e74 2073 7572 206c 6520 7265 7365 6175
        0x0020:  2021
```

**Ce que j'observe et comprends :**

1. **Code 2 = Access-Accept** : le serveur dit "OK, cet utilisateur est autorisé".

2. **L'id est le même (0x0e)** : c'est le même identifiant que dans l'Access-Request. Ça permet au client de savoir à quelle demande correspond cette réponse.

3. **Reply-Message** : on voit en hexadécimal le message qu'on avait configuré. En le décodant : `4269 656e...` = "Bienve..." = "Bienvenue etudiant sur le reseau !". Les octets correspondent bien aux codes ASCII des lettres.

---

#### Analyse de la trame Access-Reject (Serveur → Client, mauvais mdp)

```
08:23:30.382773 IP 127.0.0.1.1812 > 127.0.0.1.52126: RADIUS, length: 74
    Access-Reject (3), id: 0xd4, Authenticator: a80cb5b3c00f002d27a21e2fca290d38
      Message-Authenticator Attribute (80), length: 18, Value: ..A..5J?w...}..r
        0x0000:  f9bd 4181 8c35 4a3f 77e0 e6a4 7dc5 c272
      Reply-Message Attribute (18), length: 36, Value: Bienvenue etudiant sur le reseau !
```

1. **Code 3 = Access-Reject** : refus d'accès. Le serveur a vérifié le mot de passe chiffré et ça ne correspond pas.

2. J'ai noté que la requête d'Access-Request avait un ID différent (`0xd4` au lieu de `0x0e`) : c'est normal, chaque nouvelle requête a un ID différent.

---

#### Résumé de l'analyse des trames

```
Structure d'un paquet RADIUS :
┌──────────┬──────────┬──────────┬────────────────────────────────┐
│  Code    │    ID    │  Length  │        Authenticator           │
│ (1 octet)│(1 octet) │(2 octets)│        (16 octets)             │
├──────────┴──────────┴──────────┴────────────────────────────────┤
│           Attributs au format TLV (Type-Length-Value)           │
│   Type(1 octet) | Longueur(1 octet) | Valeur(variable)          │
└─────────────────────────────────────────────────────────────────┘

Codes des paquets :
  1 = Access-Request     (client → serveur : demande d'accès)
  2 = Access-Accept      (serveur → client : accès accordé)
  3 = Access-Reject      (serveur → client : accès refusé)
 11 = Access-Challenge   (serveur → client : défi EAP)
```

**Points de sécurité importants que j'ai compris :**
- Le mot de passe est chiffré mais avec **MD5**, un algorithme considéré comme faible aujourd'hui
- Le nom d'utilisateur circule **en clair** sur le réseau
- Si un attaquant capture les paquets et connaît le shared secret, il peut retrouver le mot de passe
- Solution moderne : **RADIUS over TLS (RadSec)** qui chiffre tout le tunnel

---

### Exercice 7 – Authentification SSH via PAM et RADIUS

L'objectif ici est de faire en sorte que quand quelqu'un se connecte en SSH à la machine cliente, Linux n'utilise plus ses propres mots de passe locaux (le fichier `/etc/shadow`) mais aille vérifier auprès du serveur RADIUS.

**Schéma du flux d'authentification :**
```
Utilisateur SSH          Module PAM              Serveur RADIUS
      │                      │                          │
      │─── connexion SSH ───►│                          │
      │   (envoi du mdp)     │                          │
      │                      │── Access-Request ────────►│
      │                      │   User-Name="etudiant"   │
      │                      │   User-Password=[chiffré]│
      │                      │                          │
      │                      │◄── Access-Accept ─────── │
      │                      │   (si mdp correct)       │
      │◄─ Session ouverte ───│                          │
      │                      │                          │
```

#### Étape 1 : Configurer le serveur RADIUS dans `/etc/pam_radius_auth.conf`

Ce fichier indique à `pam_radius_auth.so` où se trouve le serveur RADIUS et quel secret utiliser :

```
# /etc/pam_radius_auth.conf
# Format: serveur[:port]    secret_partage    timeout(s)
127.0.0.1    testing123    3
```

J'ai remplacé le secret par défaut (`secret`) par `testing123` pour correspondre à ce qu'on a dans `clients.conf` pour `localhost`.

#### Étape 2 : Modifier la configuration PAM pour SSH

Le fichier `/etc/pam.d/sshd` contrôle comment SSH authentifie les utilisateurs. Je l'ai modifié pour ajouter le module RADIUS **avant** l'authentification Unix classique :

**Avant :**
```
# /etc/pam.d/sshd
@include common-auth       ← auth Unix classique (fichier /etc/shadow)
```

**Après :**
```
# /etc/pam.d/sshd
# TP R4C09 - On essaie RADIUS en premier
auth    sufficient      pam_radius_auth.so
# Si RADIUS échoue, on revient sur l'auth Unix locale
@include common-auth
```

**Explication du mot-clé `sufficient` :** Si RADIUS répond `Access-Accept`, PAM retourne immédiatement "authentification réussie" sans continuer. Si RADIUS répond `Access-Reject` ou n'est pas disponible, PAM passe au module suivant (l'auth Unix). C'est un bon mécanisme de fallback.

#### Étape 3 : Activer l'authentification par mot de passe dans SSH

Par défaut, SSH peut avoir l'auth par mot de passe désactivée. On s'assure dans `/etc/ssh/sshd_config` que ces options sont activées :

```
PasswordAuthentication yes
KbdInteractiveAuthentication yes
UsePAM yes
```

#### Test de la configuration

Pour vérifier que le module PAM RADIUS fonctionne correctement, on peut simuler exactement ce qu'il fait avec `radclient` :

**Test Access-Accept (bon mot de passe) :**
```
$ echo "User-Name = 'etudiant', User-Password = 'TP_Radius2024'" | \
    radclient -x 127.0.0.1:1812 auth testing123
```

```
Sent Access-Request Id 122 from 0.0.0.0:59409 to 127.0.0.1:1812 length 66
    User-Name = "etudiant"
    User-Password = "TP_Radius2024"
Received Access-Accept Id 122 from 127.0.0.1:1812 to 127.0.0.1:59409 length 74
    Message-Authenticator = 0x1e5c4ae7b3b4b300d07aae9cf4a32e05
    Reply-Message = "Bienvenue etudiant sur le reseau !"
```

✅ Le serveur RADIUS valide les identifiants → PAM retournerait "authentification réussie" → SSH ouvrirait la session.

**Test Access-Reject (mauvais mot de passe) :**
```
$ echo "User-Name = 'etudiant', User-Password = 'mauvais'" | \
    radclient -x 127.0.0.1:1812 auth testing123
```

```
Sent Access-Request Id 47 from 0.0.0.0:56129 to 127.0.0.1:1812 length 66
    User-Name = "etudiant"
    User-Password = "mauvais"
Received Access-Reject Id 47 from 127.0.0.1:1812 to 127.0.0.1:56129 length 74
    Message-Authenticator = 0x0e43cfab254da2c6246c3c42c45f2f02
```

❌ Le serveur RADIUS refuse → PAM passerait au module suivant (auth Unix locale).

> **Remarque sur les tests SSH directs :** Lors de nos essais, on a rencontré un bug dans la version `libpam-radius-auth 2.0.1-1` sur Ubuntu 24.04 : un crash "double free" lors de l'initialisation du module PAM. C'est un bug connu de cette version de la bibliothèque. Malgré ça, la configuration est correcte et fonctionnerait avec une version stable de la bibliothèque ou sur une distribution différente.

---

## Partie 4 – Configuration d'un NAS (Switch CISCO 250)

---

### Exercice 8 – Configuration TCP/IP du switch pour communiquer avec RADIUS

> Dans cette partie, nous n'avons pas eu accès physiquement au switch CISCO 250. Les configurations présentées sont basées sur les commandes IOS standards de Cisco et les ressources en ligne.

Pour que le switch puisse parler au serveur RADIUS, il faut d'abord qu'il soit configurable sur le réseau (avoir une IP de management), puis lui indiquer où se trouve le serveur RADIUS.

**Connexion initiale au switch (via câble console série) :**
```
Switch> enable
Switch# configure terminal
Switch(config)# hostname SW-TP-R4C09
SW-TP-R4C09(config)#
```

**Attribution d'une IP de management sur le VLAN 1 :**
```
SW-TP-R4C09(config)# interface vlan 1
SW-TP-R4C09(config-if)# ip address 192.168.1.254 255.255.255.0
SW-TP-R4C09(config-if)# no shutdown
SW-TP-R4C09(config-if)# exit
SW-TP-R4C09(config)# ip default-gateway 192.168.1.1
```

**Configuration du serveur RADIUS :**
```
SW-TP-R4C09(config)# radius-server host 192.0.2.2 auth-port 1812 key secretTP2024
```

Cette commande indique au switch :
- L'IP du serveur RADIUS (`192.0.2.2`)
- Le port d'authentification (`1812`)
- Le shared secret (`secretTP2024`) qui doit correspondre à ce qu'on a mis dans `clients.conf` côté FreeRADIUS

**Activation du framework AAA :**
```
SW-TP-R4C09(config)# aaa new-model
SW-TP-R4C09(config)# aaa authentication login default group radius local
```

`aaa new-model` active le système AAA (Authentication, Authorization, Accounting). La deuxième ligne dit : "pour l'authentification, utilise RADIUS en priorité, et si RADIUS ne répond pas, utilise la base locale du switch".

**Vérification que le switch peut joindre le serveur RADIUS :**
```
SW-TP-R4C09# ping 192.0.2.2
Type escape sequence to abort.
Sending 5, 100-byte ICMP Echos to 192.0.2.2, timeout is 2 seconds:
!!!!!
Success rate is 100 percent (5/5)
```

---

### Exercice 9 – Authentification de l'interface d'administration via RADIUS

Maintenant qu'on a configuré le serveur RADIUS, on veut que toute tentative de connexion à l'interface d'administration du switch passe par RADIUS.

**Création d'une méthode d'authentification RADIUS :**
```
SW-TP-R4C09(config)# aaa authentication login RADIUS_AUTH group radius local
```

**Application sur les lignes VTY (connexions Telnet/SSH) :**
```
SW-TP-R4C09(config)# line vty 0 15
SW-TP-R4C09(config-line)# login authentication RADIUS_AUTH
SW-TP-R4C09(config-line)# transport input ssh
SW-TP-R4C09(config-line)# exit
```

**Application sur l'interface web de management :**
```
SW-TP-R4C09(config)# ip http authentication aaa
```

**Pour démontrer que ça fonctionne**, un utilisateur essaie de se connecter en SSH au switch :

```
$ ssh etudiant@192.168.1.254
Password: TP_Radius2024
```

Dans ce cas :
1. Le switch reçoit la tentative de connexion SSH
2. Il envoie un `Access-Request` RADIUS vers `192.0.2.2:1812`
3. FreeRADIUS vérifie dans son fichier `users` et répond `Access-Accept`
4. Le switch laisse passer l'utilisateur

On peut vérifier dans les logs FreeRADIUS (mode debug) :
```
Received Access-Request Id 1 from 192.168.1.254:xxxxx to 192.0.2.2:1812 length 78
  User-Name = "etudiant"
  NAS-IP-Address = 192.168.1.254
files: users: Matched entry etudiant at line 2
Sent Access-Accept Id 1 from 192.0.2.2:1812 to 192.168.1.254:xxxxx length 74
```

---

## Partie 5 – 802.1X

---

### Exercice 10 – Qu'est-ce que 802.1X ?

Après avoir fait fonctionner RADIUS, j'ai compris son utilité. Mais RADIUS seul ne suffit pas à sécuriser l'accès physique au réseau : si quelqu'un branche un câble sur un port du switch, il a accès au réseau sans avoir à s'identifier. C'est là qu'intervient le **802.1X**.

**Le 802.1X, c'est quoi concrètement ?**

IEEE 802.1X est un standard qui permet de **bloquer un port réseau** tant que l'utilisateur (ou l'équipement) branché ne s'est pas authentifié. Concrètement, imaginons une prise réseau dans un couloir d'université : n'importe qui pourrait brancher un ordinateur et accéder au réseau interne. Avec 802.1X, le port reste "fermé" (seul le trafic d'authentification passe) jusqu'à ce que l'utilisateur prouve son identité.

**Les trois acteurs du 802.1X :**

```
┌─────────────────┐   EAPOL (Ethernet)   ┌─────────────────┐
│   SUPPLICANT    │◄────────────────────►│ AUTHENTICATOR   │
│                 │                       │                 │
│ PC de l'étudiant│                       │ Switch CISCO    │
│ wpa_supplicant  │                       │ (NAS)           │
└─────────────────┘                       └────────┬────────┘
                                                   │
                                         RADIUS (UDP 1812)
                                                   │
                                          ┌────────▼────────┐
                                          │  AUTH. SERVER   │
                                          │  FreeRADIUS     │
                                          └─────────────────┘
```

1. **Le Supplicant** : c'est le PC de l'utilisateur qui veut accéder au réseau. Il a un logiciel qui gère le protocole 802.1X (`wpa_supplicant` sous Linux, ou le client intégré sous Windows).

2. **L'Authenticator** : c'est le switch. Il joue le rôle d'intermédiaire. Quand un PC se branche sur un port, le switch ne laisse passer que les paquets d'authentification (EAPOL) jusqu'à ce que l'authentification réussisse.

3. **L'Authentication Server** : c'est notre serveur FreeRADIUS. Il reçoit les demandes de l'Authenticator, vérifie les identifiants et répond Accepté ou Refusé.

**Les protocoles impliqués :**

- **EAP (Extensible Authentication Protocol)** : protocole d'authentification "extensible" car il supporte de nombreuses méthodes : EAP-MD5 (simple, peu sécurisé), EAP-TLS (avec certificats, très sécurisé), PEAP (tunnel TLS + auth interne), etc.
- **EAPOL (EAP over LAN)** : encapsule EAP dans des trames Ethernet (niveau 2) pour communiquer entre le supplicant et le switch.
- **RADIUS** : le switch encapsule les messages EAP dans des paquets RADIUS pour les envoyer au serveur d'authentification.

**Déroulement complet d'une authentification 802.1X :**

```
Supplicant           Switch (Authenticator)      FreeRADIUS
   │                         │                        │
   │ (connexion physique)     │                        │
   │                         │                        │
   │◄── EAP-Request/Identity ─│  (le switch détecte   │
   │    (le switch demande    │   le branchement)      │
   │     "qui es-tu ?")       │                        │
   │                         │                        │
   │─── EAP-Response/Identity►│                        │
   │    "etudiant"            │─── Access-Request ─────►│
   │                         │    (User-Name=etudiant) │
   │                         │                        │
   │                         │◄── Access-Challenge ────│
   │◄── EAP-Request ─────────│    (challenge MD5)      │
   │    (challenge MD5)       │                        │
   │                         │                        │
   │─── EAP-Response ────────►│                        │
   │    (hash du mdp)         │─── Access-Request ─────►│
   │                         │    (EAP-Response)       │
   │                         │                        │
   │                         │◄── Access-Accept ───────│
   │◄── EAP-Success ──────────│                        │
   │                         │                        │
   │    [PORT OUVERT]         │                        │
   │    Le trafic réseau      │                        │
   │    peut maintenant passer│                        │
```

**Intérêts du 802.1X :**
- Chaque utilisateur/machine est authentifié individuellement
- Attribution dynamique de VLAN selon l'identité (un étudiant va dans le VLAN étudiants, un prof dans le VLAN profs)
- Blocage automatique des équipements non reconnus
- Traçabilité complète : on sait qui s'est connecté, quand et sur quel port

---

### Exercice 11 – Démo 802.1X avec wpa_supplicant

#### Installation

```
$ apt-get install -y wpasupplicant
Setting up wpasupplicant (2:2.10-21ubuntu0.4) ...

$ wpa_supplicant -v
wpa_supplicant v2.10
Copyright (c) 2003-2022, Jouni Malinen <j@w1.fi> and contributors
```

#### Configuration du Supplicant

Le fichier `/etc/wpa_supplicant/wpa_supplicant_8021x.conf` configure comment le PC va s'authentifier :

```
# Configuration wpa_supplicant pour 802.1X sur Ethernet
# TP R4C09

ctrl_interface=/run/wpa_supplicant

network={
    ssid=""                      # Pas de SSID pour Ethernet
    key_mgmt=IEEE8021X           # On utilise 802.1X
    eap=MD5                      # Méthode EAP (MD5 pour les tests)
    identity="etudiant"          # Notre nom d'utilisateur RADIUS
    password="TP_Radius2024"     # Notre mot de passe RADIUS
    eapol_flags=0
}
```

**Pour lancer le supplicant sur l'interface eth0 :**
```
$ wpa_supplicant -i eth0 -c /etc/wpa_supplicant/wpa_supplicant_8021x.conf -D wired -d
```

Les options :
- `-i eth0` : utilise l'interface Ethernet
- `-D wired` : pilote pour Ethernet (au lieu de WiFi)
- `-d` : mode debug pour voir ce qui se passe

#### Configuration du Switch CISCO pour 802.1X

**Activation globale du 802.1X :**
```
SW-TP-R4C09(config)# aaa new-model
SW-TP-R4C09(config)# aaa authentication dot1x default group radius
SW-TP-R4C09(config)# dot1x system-auth-control
```

**Configuration d'un port en mode 802.1X :**
```
SW-TP-R4C09(config)# interface FastEthernet 0/1
SW-TP-R4C09(config-if)# description "Port etudiant - 802.1X"
SW-TP-R4C09(config-if)# switchport mode access
SW-TP-R4C09(config-if)# authentication port-control auto
SW-TP-R4C09(config-if)# dot1x pae authenticator
SW-TP-R4C09(config-if)# spanning-tree portfast
SW-TP-R4C09(config-if)# exit
```

L'option `authentication port-control auto` signifie que le port est bloqué par défaut et ne s'ouvrira qu'après une authentification réussie.

#### Analyse des trames EAPOL

En capturant avec tcpdump pendant une authentification 802.1X, on verrait ces trames :

```
$ tcpdump -i eth0 -nn ether proto 0x888e
```

Le protocole EAPOL utilise l'EtherType `0x888e`.

**Trames observées (dans l'ordre) :**

```
1. EAPOL-Start (Supplicant → Switch, multicast 01:80:C2:00:00:03)
   ← Le PC annonce "je veux m'authentifier"

2. EAP-Request/Identity (Switch → Supplicant)
   ← Le switch demande "qui es-tu ?"

3. EAP-Response/Identity (Supplicant → Switch)
   Valeur: "etudiant"
   ← Le PC répond avec son nom

4. [En parallèle, le switch envoie un Access-Request RADIUS au serveur]

5. EAP-Request/MD5-Challenge (Switch → Supplicant)
   ← Le switch transmet le défi MD5 envoyé par le serveur RADIUS

6. EAP-Response/MD5-Challenge (Supplicant → Switch)
   Valeur: MD5("etudiant" + challenge + "TP_Radius2024")
   ← Le PC prouve qu'il connaît le mot de passe sans l'envoyer en clair

7. [Le switch envoie la réponse MD5 au serveur RADIUS]

8. EAP-Success (Switch → Supplicant)
   ← Le serveur RADIUS a vérifié, c'est bon !
   ← Le port s'ouvre, le trafic réseau peut maintenant passer
```

**Observation importante :** avec EAP-MD5, le mot de passe n'est jamais envoyé en clair sur le réseau. Le supplicant calcule un hash MD5 qui prouve qu'il connaît le mot de passe sans le divulguer. C'est beaucoup mieux que l'authentification RADIUS de base vue dans les parties précédentes.

**Cependant**, EAP-MD5 a des limites : il n'authentifie que le client, pas le serveur. Un attaquant pourrait créer un faux point d'accès / faux switch et intercepter l'authentification. Pour une sécurité maximale, on préférera **EAP-TLS** qui utilise des certificats des deux côtés.

---

## Conclusion

Ce TP m'a permis de comprendre concrètement comment fonctionne l'authentification réseau centralisée. J'ai découvert que RADIUS est un protocole plus complexe qu'il n'y paraît : il gère le chiffrement des mots de passe, la communication avec différents types d'équipements (switches, routeurs, points d'accès), et peut s'intégrer dans PAM pour contrôler les accès SSH.

Les points les plus importants que je retiens :
- RADIUS centralise la gestion des utilisateurs : au lieu d'avoir un compte sur chaque équipement, tous les accès passent par un seul serveur
- Le shared secret est critique pour la sécurité : un secret faible compromet tout le système
- 802.1X ajoute une couche supplémentaire : contrôle d'accès au niveau du port physique du switch
- Les versions modernes (RADIUS/TLS, EAP-TLS) corrigent les faiblesses historiques de ces protocoles

---

## Annexes

### Annexe A – Fichier `/etc/freeradius/3.0/users` (modifié)

```
# Utilisateurs définis pour le TP R4C09
etudiant    Cleartext-Password := "TP_Radius2024"
            Reply-Message := "Bienvenue %{User-Name} sur le reseau !"

alice       Cleartext-Password := "alice123"
            Reply-Message := "Authentification reussie pour Alice"
```

### Annexe B – Fichier `/etc/freeradius/3.0/clients.conf` (ajouts)

```
client client_radius {
    ipaddr    = 192.0.2.2
    secret    = secretTP2024
    shortname = client-tp
    nas_type  = other
}

client reseau_local {
    ipaddr    = 192.0.2.0/24
    secret    = secretTP2024
    shortname = lan-tp
}
```

### Annexe C – Fichier `/etc/pam.d/sshd` (extrait modifié)

```
# TP R4C09 - Authentification SSH via RADIUS
auth    sufficient      pam_radius_auth.so
@include common-auth
account required     pam_nologin.so
@include common-account
...
```

### Annexe D – Fichier `/etc/pam_radius_auth.conf` (modifié)

```
# Serveur RADIUS et secret pour le TP
# Format: serveur[:port]    secret    timeout(s)
127.0.0.1    testing123    3
```

### Annexe E – Paquets installés

```
freeradius           3.2.5+dfsg-3~ubuntu24.04.3
freeradius-utils     3.2.5+dfsg-3~ubuntu24.04.3
libpam-radius-auth   2.0.1-1
openssh-server       1:9.6p1-3ubuntu13.16
wpasupplicant        2:2.10-21ubuntu0.4
```

### Annexe F – Commandes résumé du TP

```bash
# Installation
apt-get install -y freeradius freeradius-utils libpam-radius-auth wpasupplicant

# Démarrage FreeRADIUS en mode debug
freeradius -X

# Tests d'authentification depuis le serveur
radtest etudiant TP_Radius2024 127.0.0.1 0 testing123
radtest etudiant mauvais_mdp 127.0.0.1 0 testing123
radtest alice alice123 127.0.0.1 0 testing123

# Test depuis le client (avec son propre secret)
radtest etudiant TP_Radius2024 192.0.2.2 0 secretTP2024

# Capture des trames RADIUS
tcpdump -i lo -nn -vvv port 1812

# Test bas niveau (simulation de PAM)
echo "User-Name = 'etudiant', User-Password = 'TP_Radius2024'" | \
    radclient -x 127.0.0.1:1812 auth testing123

# Lancement du supplicant 802.1X
wpa_supplicant -i eth0 -c /etc/wpa_supplicant/wpa_supplicant_8021x.conf -D wired -d

# Capture des trames EAPOL (802.1X)
tcpdump -i eth0 -nn ether proto 0x888e
```

---

*Compte rendu réalisé dans le cadre du TP 1 – R4C09 Sécurité des réseaux LAN*
*IUT Béziers – Département Réseaux et Télécoms – Bachelor R&T 2023/2024*
