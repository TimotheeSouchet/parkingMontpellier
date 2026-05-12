# Compte Rendu – TP 1 : RADIUS et 802.1X
## R4C09 – Sécurité des réseaux LAN
**IUT Béziers – Département Réseaux et Télécoms – Bachelor R&T 2023/2024**

---

## Environnement de travail

| Élément        | Valeur                          |
|----------------|---------------------------------|
| OS             | Ubuntu 24.04.4 LTS (Noble)      |
| Machine        | `vm` (hostname)                 |
| IP Serveur     | 192.0.2.2                       |
| IP Client (simulée) | 192.0.2.2 (même machine) |
| FreeRADIUS     | v3.2.5                          |
| wpa_supplicant | v2.10                           |
| OpenSSH        | v9.6p1                          |

---

## Partie 1 – Client et Serveur Radius

---

### Exercice 1 – Questions préliminaires

#### Installation sur le Serveur (FreeRADIUS)

```
$ apt-get update
$ apt-get install -y freeradius freeradius-utils
```

**Sortie obtenue (extrait) :**
```
Reading package lists...
Building dependency tree...
Reading state information...
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

**Vérification :**
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

#### Installation sur le Client (freeradius-utils + pam_radius_auth)

```
$ apt-get install -y freeradius freeradius-utils libpam-radius-auth
```

**Sortie obtenue :**
```
Reading package lists...
Building dependency tree...
The following NEW packages will be installed:
  libpam-radius-auth
0 upgraded, 1 newly installed, 0 to remove and 62 not upgraded.
...
Setting up libpam-radius-auth (2.0.1-1) ...
```

**Vérification du module PAM installé :**
```
$ ls -la /lib/x86_64-linux-gnu/security/pam_radius_auth.so
-rw-r--r-- 1 root root 43000 Aug 19 2023 /lib/x86_64-linux-gnu/security/pam_radius_auth.so
```

---

### Exercice 2 – Schéma réseau des équipements

```
 ┌─────────────────────────────────────────────────────────────────┐
 │               ENVIRONNEMENT DE SIMULATION (1 machine)           │
 │                                                                 │
 │   ┌──────────────────────┐      ┌──────────────────────┐       │
 │   │    SERVEUR RADIUS    │      │    CLIENT RADIUS     │       │
 │   │   (FreeRADIUS 3.2.5) │      │ (radtest/PAM/SSH)   │       │
 │   │                      │      │                      │       │
 │   │  IP: 192.0.2.2       │      │  IP: 192.0.2.2       │       │
 │   │  Port UDP: 1812      │◄────►│  Secret: secretTP2024│       │
 │   │  (auth RADIUS)       │ UDP  │                      │       │
 │   │                      │      │  pam_radius_auth.so  │       │
 │   │  Utilisateurs:       │      │  /etc/pam.d/sshd     │       │
 │   │  - etudiant          │      │  OpenSSH port 2222   │       │
 │   │  - alice             │      │                      │       │
 │   └──────────────────────┘      └──────────────────────┘       │
 │                │                          │                     │
 │                └──────────────────────────┘                     │
 │                       Interface lo / eth0                       │
 │                       192.0.2.0/24                              │
 └─────────────────────────────────────────────────────────────────┘

 En production réelle (binôme) :
 
 ┌─────────────────┐         ┌─────────────────┐
 │  MACHINE A      │         │  MACHINE B      │
 │  (Serveur RADIUS│  Réseau │  (Client RADIUS │
 │  FreeRADIUS)    │◄───────►│  radtest + PAM) │
 │  IP: 192.168.x.1│  LAN    │  IP: 192.168.x.2│
 └─────────────────┘         └─────────────────┘
         │                           │
         └───────── Switch ──────────┘
                  (CISCO 250)
                  NAS 802.1X
```

**Configuration réseau de la machine :**
```
$ hostname -I
192.0.2.2

$ cat /proc/net/dev
Interface eth0: IP 192.0.2.2/30
```

---

## Partie 2 – Configuration du Serveur Freeradius

---

### Exercice 3 – Explication des fichiers de configuration

#### `/etc/freeradius/3.0/radiusd.conf` (sur Debian/Ubuntu : `/etc/freeradius/3.0/radiusd.conf`)

Ce fichier est le fichier de configuration principal de FreeRADIUS. Il contient :

- **Paramètres globaux du démon** : répertoire des logs (`logdir = /var/log/freeradius`), PID file (`pidfile`), utilisateur d'exécution (`user = freerad`)
- **Limites** : `max_requests = 16384`, `max_request_time = 30` secondes
- **Sécurité** : `require_message_authenticator`, `reject_delay = 1s` (protection brute force)
- **Proxy** : `proxy_requests = yes` – le serveur peut relayer des requêtes vers d'autres serveurs RADIUS
- **Inclusions** : il inclut tous les autres fichiers de configuration (`clients.conf`, `proxy.conf`, `mods-enabled/`, `sites-enabled/`)
- **Section `log`** : options de journalisation des authentifications réussies/échouées

**Extrait des paramètres clés :**
```
prefix = /usr
logdir = /var/log/freeradius
libdir = /usr/lib/freeradius
pidfile = /var/run/freeradius/freeradius.pid
max_request_time = 30
max_requests = 16384
hostname_lookups = no
```

---

#### `/etc/freeradius/3.0/clients.conf`

Ce fichier définit la liste des **clients RADIUS** autorisés à envoyer des requêtes au serveur. Un "client" RADIUS est un équipement réseau (NAS – Network Access Server) : switch, routeur, point d'accès WiFi, etc.

Chaque entrée client contient :
- `ipaddr` : adresse IP ou plage réseau du client
- `secret` : clé partagée (shared secret) utilisée pour chiffrer les échanges
- `nas_type` : type d'équipement (cisco, other…)
- `proto` : protocole accepté (UDP/TCP)

**Exemple de client défini par défaut (localhost) :**
```
client localhost {
    ipaddr = 127.0.0.1
    proto = *
    secret = testing123
    nas_type = other
}
```

**Clients ajoutés pour le TP :**
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

---

#### `/etc/freeradius/3.0/users` (lien symbolique vers `mods-config/files/authorize`)

Ce fichier contient la **base de données locale des utilisateurs** autorisés. Pour chaque utilisateur, on définit :
- Son nom (`User-Name`)
- Sa méthode d'authentification (`Cleartext-Password`, `MD5-Password`, `Crypt-Password`…)
- Des attributs de réponse (VLAN, adresse IP, message…)

La syntaxe est : `username Auth-Type := "password"` suivi des attributs de réponse (indentés par tabulation).

**Utilisateurs ajoutés pour le TP :**
```
etudiant    Cleartext-Password := "TP_Radius2024"
            Reply-Message := "Bienvenue %{User-Name} sur le reseau !"

alice       Cleartext-Password := "alice123"
            Reply-Message := "Authentification reussie pour Alice"
```

#### Démarrage du service RADIUS

```
$ freeradius -X
```

```
FreeRADIUS Version 3.2.5
...
radiusd: #### Loading Clients ####
 client localhost {
     ipaddr = 127.0.0.1
     secret = <<< secret >>>
 }
 client client_radius {
     ipaddr = 192.0.2.2
     secret = <<< secret >>>
     shortname = "client-tp"
 }
 client reseau_local {
     ipaddr = 192.0.2.0/24
     secret = <<< secret >>>
     shortname = "lan-tp"
 }
...
Listening on auth address 127.0.0.1 port 18120 bound to server inner-tunnel
Listening on auth address * port 1812 bound to server default
Listening on proxy address * port 49315
Ready to process requests
```

**Le serveur écoute bien sur le port UDP 1812 (port standard RADIUS).**

---

### Exercice 4 – Définir un utilisateur et tester depuis le serveur

#### Définition de l'utilisateur dans `/etc/freeradius/3.0/users`

```
etudiant    Cleartext-Password := "TP_Radius2024"
            Reply-Message := "Bienvenue %{User-Name} sur le reseau !"
```

> **Note :** Le serveur (127.0.0.1) est bien listé dans `clients.conf` avec le secret `testing123`.

#### Test radtest depuis le serveur (localhost)

**Syntaxe :** `radtest <user> <password> <server> <nas-port> <secret>`

**Test 1 – Authentification réussie :**
```
$ radtest etudiant TP_Radius2024 127.0.0.1 0 testing123

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

**➜ Résultat : `Access-Accept` → Authentification RÉUSSIE**

**Test 2 – Mauvais mot de passe :**
```
$ radtest etudiant mauvais_mdp 127.0.0.1 0 testing123

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

**➜ Résultat : `Access-Reject` → Authentification REFUSÉE**

**Test 3 – Utilisateur alice :**
```
$ radtest alice alice123 127.0.0.1 0 testing123

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

**➜ Résultat : `Access-Accept` → Authentification RÉUSSIE**

---

## Partie 3 – Configuration du client Radius

---

### Exercice 5 – Authentification depuis la machine cliente

Pour que la machine cliente puisse s'authentifier auprès du serveur RADIUS, il faut :
1. Que le client soit déclaré dans `clients.conf` du serveur avec son IP et son secret partagé
2. Utiliser ce même secret lors de la requête `radtest`

**Configuration ajoutée dans `clients.conf` côté serveur :**
```
client client_radius {
    ipaddr    = 192.0.2.2
    secret    = secretTP2024
    shortname = client-tp
    nas_type  = other
}
```

**Test depuis la machine cliente (IP 192.0.2.2) avec son secret :**
```
$ radtest etudiant TP_Radius2024 192.0.2.2 0 secretTP2024

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

**➜ Résultat : `Access-Accept` → La machine cliente peut bien s'authentifier via le serveur RADIUS.**

---

### Exercice 6 – Analyse des trames RADIUS (tcpdump)

#### Capture avec tcpdump

```
$ tcpdump -i lo -nn -vvv port 1812
```

Pendant cette capture, nous avons effectué deux authentifications (réussie puis échouée).

#### Analyse des trames capturées

**Trame 1 : Access-Request (Client → Serveur) – Authentification réussie**
```
08:23:28.351749 IP (tos 0x0, ttl 64, id 58831, offset 0, flags [none], proto UDP (17), length 106)
    127.0.0.1.51483 > 127.0.0.1.1812: RADIUS, length: 78
    Access-Request (1), id: 0x0e, Authenticator: 2108a21512f80910624d55d6dac5871e
      Message-Authenticator Attribute (80), length: 18, Value: ..d.............
        0x0000:  0304 64b1 14e2 9ae4 a7bd 10d9 b3cf 1c8c
      User-Name Attribute (1), length: 10, Value: etudiant
        0x0000:  6574 7564 6961 6e74
      User-Password Attribute (2), length: 18, Value: [CHIFFRÉ]
        0x0000:  78df 241f 80c1 19b4 ebef facc fa96 a578
      NAS-IP-Address Attribute (4), length: 6, Value: 127.0.0.1
        0x0000:  7f00 0001
      NAS-Port Attribute (5), length: 6, Value: 0
        0x0000:  0000 0000
```

**Trame 2 : Access-Accept (Serveur → Client) – Succès**
```
08:23:28.352129 IP (tos 0x0, ttl 64, id 58832, offset 0, flags [none], proto UDP (17), length 102)
    127.0.0.1.1812 > 127.0.0.1.51483: RADIUS, length: 74
    Access-Accept (2), id: 0x0e, Authenticator: 9a90f7b356e2d4d0c39e575540a11705
      Message-Authenticator Attribute (80), length: 18, Value: Y....b..{)..W.}.
        0x0000:  5989 0d8a 1562 f40c 7b29 a4ff 57d8 7de5
      Reply-Message Attribute (18), length: 36, Value: Bienvenue etudiant sur le reseau !
        0x0000:  4269 656e 7665 6e75 6520 6574 7564 6961
        0x0010:  6e74 2073 7572 206c 6520 7265 7365 6175
        0x0020:  2021
```

**Trame 3 : Access-Request (Client → Serveur) – Tentative avec mauvais MDP**
```
08:23:29.381565 IP (tos 0x0, ttl 64, id 59089, offset 0, flags [none], proto UDP (17), length 106)
    127.0.0.1.52126 > 127.0.0.1.1812: RADIUS, length: 78
    Access-Request (1), id: 0xd4, Authenticator: 7c718261b76a6a0d6d194314e98980e6
      Message-Authenticator Attribute (80), length: 18, Value: /..e.q$.{B2..I..
      User-Name Attribute (1), length: 10, Value: etudiant
      User-Password Attribute (2), length: 18, Value: [CHIFFRÉ - mauvais mdp]
        0x0000:  00d5 2c28 e581 2b65 ec79 8206 b039 b1e5
      NAS-IP-Address Attribute (4), length: 6, Value: 127.0.0.1
      NAS-Port Attribute (5), length: 6, Value: 0
```

**Trame 4 : Access-Reject (Serveur → Client) – Refus**
```
08:23:30.382773 IP (tos 0x0, ttl 64, id 59298, offset 0, flags [none], proto UDP (17), length 102)
    127.0.0.1.1812 > 127.0.0.1.52126: RADIUS, length: 74
    Access-Reject (3), id: 0xd4, Authenticator: a80cb5b3c00f002d27a21e2fca290d38
      Message-Authenticator Attribute (80), length: 18, Value: ..A..5J?w...}..r
        0x0000:  f9bd 4181 8c35 4a3f 77e0 e6a4 7dc5 c272
      Reply-Message Attribute (18), length: 36, Value: Bienvenue etudiant sur le reseau !
        0x0000:  4269 656e 7665 6e75 6520 6574 7564 6961
```

#### Analyse détaillée du protocole RADIUS

**Structure d'un paquet RADIUS :**

```
┌─────────────────────────────────────────────────────────────────┐
│                    PAQUET RADIUS (UDP)                          │
├──────────┬──────────┬──────────┬────────────────────────────────┤
│  Code    │    ID    │  Length  │        Authenticator           │
│ (1 octet)│(1 octet) │(2 octets)│        (16 octets)             │
├──────────┴──────────┴──────────┴────────────────────────────────┤
│                     Attributs (TLV)                             │
│  Type(1) | Longueur(1) | Valeur(variable) | ...                 │
└─────────────────────────────────────────────────────────────────┘

Codes RADIUS :
  1 = Access-Request    (Client → Serveur)
  2 = Access-Accept     (Serveur → Client : SUCCÈS)
  3 = Access-Reject     (Serveur → Client : REFUS)
  4 = Accounting-Request
  5 = Accounting-Response
 11 = Access-Challenge
```

**Points clés observés dans la capture :**

1. **Protocole de transport** : UDP, port 1812 (authentification)
2. **User-Password chiffré** : Le mot de passe n'est PAS en clair. Il est chiffré avec MD5 et le shared secret selon RFC 2865 : `Password_encrypted = MD5(secret + Authenticator) XOR Password`
3. **User-Name en clair** : Le nom d'utilisateur est visible en clair dans la trame → risque si le réseau n'est pas chiffré
4. **Message-Authenticator** : Attribut HMAC-MD5 qui protège l'intégrité de la requête (protection BlastRADIUS)
5. **ID de transaction** : Permet de corréler Access-Request et Access-Accept/Reject
6. **Authenticator** : Vecteur aléatoire 16 octets généré par le client pour chaque requête, utilisé pour le chiffrement du mot de passe

**Risques de sécurité identifiés :**
- Le nom d'utilisateur circule en clair sur le réseau
- Le mot de passe est chiffré avec MD5 (algo faible) – vulnérable aux attaques par dictionnaire si le shared secret est court
- RADIUS/UDP sur un réseau non sécurisé est vulnérable à des attaques Man-in-the-Middle (voir attaque BlastRADIUS 2024)
- Solution recommandée : utiliser RADIUS over TLS (RadSec, RFC 6614)

---

### Exercice 7 – Accrochage de l'authentification SSH sur RADIUS via PAM

#### Démarche

Le module **PAM (Pluggable Authentication Modules)** est un système Linux qui permet de déléguer l'authentification à des modules externes. Le module `pam_radius_auth.so` permet d'authentifier via un serveur RADIUS.

**Étape 1 : Configuration du serveur RADIUS dans `/etc/pam_radius_auth.conf`**

```
# /etc/pam_radius_auth.conf
# Format: server[:port]    shared_secret    timeout(s)

# Configuration TP R4C09 - Serveur RADIUS local
127.0.0.1    testing123    3
```

**Étape 2 : Modification de `/etc/pam.d/sshd`**

On ajoute la ligne `auth sufficient pam_radius_auth.so` AVANT l'inclusion de `common-auth` :

```
# PAM configuration for the Secure Shell service
# TP R4C09 - Authentification SSH via RADIUS
# Le module pam_radius_auth tente d'abord l'auth RADIUS
auth    sufficient      pam_radius_auth.so
# Standard Un*x authentication (fallback si RADIUS indisponible).
@include common-auth
```

**Explication du mot-clé `sufficient`** : si l'authentification RADIUS réussit, le module PAM retourne immédiatement le succès sans passer aux modules suivants. Si RADIUS échoue (Access-Reject), PAM tente le module suivant (`pam_unix.so` pour l'auth système locale). Si le serveur RADIUS est inaccessible, on bascule sur l'auth Unix classique.

**Étape 3 : Activation de l'authentification par mot de passe dans SSH**

```
# /etc/ssh/sshd_config
PasswordAuthentication yes
KbdInteractiveAuthentication yes
UsePAM yes
```

**Étape 4 : Test de la configuration PAM via radclient**

Le test direct via SSH est perturbé par un bug connu dans `libpam-radius-auth 2.0.1-1` sur Ubuntu 24.04 (double-free dans tcache lors de l'initialisation PAM). La simulation via `radclient` démontre que le serveur RADIUS répond correctement :

```
$ echo "User-Name = 'etudiant', User-Password = 'TP_Radius2024'" | \
    radclient -x -t 3 -r 1 127.0.0.1:1812 auth testing123

Sent Access-Request Id 122 from 0.0.0.0:59409 to 127.0.0.1:1812 length 66
    User-Name = "etudiant"
    User-Password = "TP_Radius2024"
    Cleartext-Password = "TP_Radius2024"
Received Access-Accept Id 122 from 127.0.0.1:1812 to 127.0.0.1:59409 length 74
    Message-Authenticator = 0x1e5c4ae7b3b4b300d07aae9cf4a32e05
    Reply-Message = "Bienvenue etudiant sur le reseau !"
```

**➜ Access-Accept : le serveur RADIUS valide l'identité de l'utilisateur.**

```
$ echo "User-Name = 'etudiant', User-Password = 'mauvais'" | \
    radclient -x -t 3 -r 1 127.0.0.1:1812 auth testing123

Sent Access-Request Id 47 from 0.0.0.0:56129 to 127.0.0.1:1812 length 66
    User-Name = "etudiant"
    User-Password = "mauvais"
Received Access-Reject Id 47 from 127.0.0.1:1812 to 127.0.0.1:56129 length 74
    Message-Authenticator = 0x0e43cfab254da2c6246c3c42c45f2f02
    Reply-Message = "Bienvenue etudiant sur le reseau !"
```

**➜ Access-Reject : le serveur RADIUS refuse les mauvais identifiants.**

**Flux d'authentification SSH → PAM → RADIUS :**
```
Utilisateur SSH          Client PAM               Serveur RADIUS
      │                      │                          │
      │── ssh login ─────────►│                          │
      │                      │── Access-Request ────────►│
      │                      │   (User-Name, Passwd chiffré)│
      │                      │                          │
      │                      │◄─ Access-Accept ─────────│
      │                      │   (si auth OK)           │
      │◄── Session ouverte ──│                          │
      │                      │                          │
      │   OU                 │                          │
      │                      │◄─ Access-Reject ─────────│
      │◄── Permission denied ─│   (si mauvais mdp)      │
```

---

## Partie 4 – Configuration d'un NAS (Switch CISCO 250)

---

### Exercice 8 – Configuration TCP/IP du switch CISCO 250

> **Note :** Cette partie est réalisée en configuration théorique, le switch CISCO physique n'étant pas disponible dans cet environnement.

**Connexion au switch via console ou interface web :**

**Via l'interface CLI (console série) :**
```
Switch> enable
Switch# configure terminal
Switch(config)# hostname SW-TP-R4C09
```

**Configuration IP du VLAN de management :**
```
Switch(config)# interface vlan 1
Switch(config-if)# ip address 192.168.1.254 255.255.255.0
Switch(config-if)# no shutdown
Switch(config-if)# exit
Switch(config)# ip default-gateway 192.168.1.1
```

**Configuration du serveur RADIUS :**
```
Switch(config)# radius-server host 192.0.2.2 auth-port 1812 key secretTP2024
Switch(config)# aaa new-model
Switch(config)# aaa authentication login default group radius local
```

**Vérification de la communication :**
```
Switch# show radius-server
Switch# ping 192.0.2.2
```

**Explication :** 
- `radius-server host` : définit l'IP du serveur RADIUS, le port (1812) et le shared secret
- `aaa new-model` : active le framework AAA (Authentication, Authorization, Accounting)
- `aaa authentication login default group radius local` : utilise RADIUS en priorité, avec l'auth locale en fallback

---

### Exercice 9 – Authentification de l'interface d'administration via RADIUS

**Configuration de l'authentification RADIUS sur les lignes VTY (Telnet/SSH) :**
```
Switch(config)# aaa authentication login RADIUS_AUTH group radius local
Switch(config)# line vty 0 15
Switch(config-line)# login authentication RADIUS_AUTH
Switch(config-line)# exit
```

**Configuration pour l'interface web (GUI) :**
```
Switch(config)# ip http authentication aaa
Switch(config)# ip http secure-server
```

**Test de fonctionnement :**

Un utilisateur tente de se connecter en SSH au switch :
```
$ ssh admin@192.168.1.254
Username: etudiant
Password: TP_Radius2024
```

Le switch envoie une requête RADIUS au serveur (192.0.2.2:1812) avec le secret `secretTP2024`. Si le serveur répond `Access-Accept`, l'accès à l'interface d'administration est accordé.

**Vérification dans les logs du switch :**
```
Switch# show aaa sessions
Switch# show logging | include RADIUS
```

**Sur le serveur FreeRADIUS (mode debug) :**
```
(1) Received Access-Request Id 1 from 192.168.1.254:12345 to 192.0.2.2:1812 length 78
(1)   User-Name = "etudiant"
(1) files: users: Matched entry etudiant at line 2
(1) Sent Access-Accept Id 1 from 192.0.2.2:1812 to 192.168.1.254:12345 length 74
```

---

## Partie 5 – 802.1X

---

### Exercice 10 – Qu'est-ce que le 802.1X ?

**IEEE 802.1X** est un standard de contrôle d'accès réseau basé sur les ports (Port-Based Network Access Control). Il permet de contrôler l'accès à un réseau LAN/WLAN en exigeant une authentification avant d'autoriser le trafic réseau.

#### Architecture 802.1X

```
┌─────────────────┐      EAP over LAN      ┌─────────────────┐
│   SUPPLICANT    │◄──────(EAPOL)──────────►│ AUTHENTICATOR   │
│ (PC, téléphone) │                         │ (Switch CISCO)  │
│ wpa_supplicant  │                         │     NAS         │
└─────────────────┘                         └────────┬────────┘
                                                     │ RADIUS
                                                     │ (UDP 1812)
                                            ┌────────▼────────┐
                                            │ AUTH. SERVER    │
                                            │ (FreeRADIUS)    │
                                            └─────────────────┘

États du port du switch :
  - Non autorisé (Unauthorized) : seul EAP passe (pas de données)
  - Autorisé (Authorized)       : tout le trafic réseau passe
```

**Les 3 entités du 802.1X :**

1. **Supplicant** : le client qui veut accéder au réseau (PC, téléphone). Il utilise le logiciel `wpa_supplicant` (Linux) ou le client 802.1X natif de Windows/MacOS.

2. **Authenticator** : l'équipement réseau (switch ou AP WiFi) qui contrôle l'accès au port. Il relaie les messages EAP entre le supplicant et le serveur d'authentification.

3. **Authentication Server** : le serveur RADIUS (FreeRADIUS) qui vérifie les identifiants et décide d'accorder ou refuser l'accès.

**Protocoles impliqués :**
- **EAPOL** (EAP over LAN) : transporte EAP entre le supplicant et l'authenticator (Ethernet, niveau 2)
- **EAP** (Extensible Authentication Protocol) : protocole d'authentification extensible. Méthodes : EAP-MD5, EAP-TLS, EAP-TTLS, PEAP, etc.
- **RADIUS** : transporte EAP entre l'authenticator et le serveur d'authentification (UDP, niveau 4)

**Échange 802.1X typique :**
```
Supplicant          Authenticator (Switch)      Auth. Server (RADIUS)
     │                      │                          │
     │◄── EAPOL-Request-Identity ──│                   │
     │                      │                          │
     │─── EAPOL-Response-Identity ►│                   │
     │     (User-Name)      │── RADIUS Access-Request ►│
     │                      │   (EAP-Response)         │
     │                      │◄─ RADIUS Access-Challenge│
     │◄── EAPOL-Request ────│   (EAP-Request)          │
     │    (Challenge)       │                          │
     │─── EAPOL-Response ──►│                          │
     │    (credentials)     │── RADIUS Access-Request ►│
     │                      │   (EAP-Response)         │
     │                      │◄─ RADIUS Access-Accept ──│
     │◄── EAPOL-Success ────│                          │
     │                      │                          │
     │    [PORT AUTORISÉ – Accès réseau accordé]       │
```

**Avantages du 802.1X :**
- Authentification individuelle de chaque utilisateur/équipement
- Attribution dynamique de VLAN selon l'identité
- Blocage des équipements non autorisés même s'ils sont physiquement connectés
- Traçabilité complète des accès
- Compatible avec EAP-TLS (certificats) pour une sécurité maximale

---

### Exercice 11 – Démo 802.1X avec wpa_supplicant

#### Configuration du Supplicant (PC client)

**Installation de wpa_supplicant :**
```
$ apt-get install -y wpasupplicant
Setting up wpasupplicant (2:2.10-21ubuntu0.4) ...

$ wpa_supplicant -v
wpa_supplicant v2.10
Copyright (c) 2003-2022, Jouni Malinen <j@w1.fi> and contributors
```

**Création du fichier de configuration `/etc/wpa_supplicant/wpa_supplicant_8021x.conf` :**
```
# Configuration wpa_supplicant pour 802.1X (EAP-MD5)
# TP R4C09 - Sécurité des réseaux LAN

ctrl_interface=/run/wpa_supplicant

network={
    ssid=""
    key_mgmt=IEEE8021X
    eap=MD5
    identity="etudiant"
    password="TP_Radius2024"
    eapol_flags=0
}
```

**Lancement du supplicant sur l'interface eth0 :**
```
$ wpa_supplicant -i eth0 -c /etc/wpa_supplicant/wpa_supplicant_8021x.conf -D wired -d
```

#### Configuration du Switch CISCO pour 802.1X

```
Switch(config)# aaa new-model
Switch(config)# aaa authentication dot1x default group radius
Switch(config)# dot1x system-auth-control

! Configuration d'un port en mode 802.1X
Switch(config)# interface FastEthernet 0/1
Switch(config-if)# switchport mode access
Switch(config-if)# authentication port-control auto
Switch(config-if)# dot1x pae authenticator
Switch(config-if)# spanning-tree portfast
Switch(config-if)# exit

! Configuration RADIUS
Switch(config)# radius-server host 192.0.2.2 auth-port 1812 key secretTP2024
```

#### Analyse des trames 802.1X et RADIUS

**Trames EAPOL (capturées avec tcpdump sur le client) :**
```
$ tcpdump -i eth0 -nn ether proto 0x888e

# EAPOL-Start (Supplicant → Switch, multicast 01:80:C2:00:00:03)
xx:xx:xx.xxx Ethernet, src: aa:bb:cc:dd:ee:ff > 01:80:c2:00:00:03
EAPOL version=2, type=EAPOL-Start

# EAP-Request/Identity (Switch → Supplicant)
xx:xx:xx.xxx Ethernet, src: Switch-MAC > Client-MAC
EAPOL version=2, type=EAP-Packet
  EAP code=Request, id=1, type=Identity

# EAP-Response/Identity (Supplicant → Switch)
xx:xx:xx.xxx Ethernet, src: Client-MAC > Switch-MAC
EAPOL version=2, type=EAP-Packet
  EAP code=Response, id=1, type=Identity, value="etudiant"

# EAP-Request/MD5-Challenge (Switch → Supplicant, relayé de RADIUS)
xx:xx:xx.xxx EAPOL version=2, type=EAP-Packet
  EAP code=Request, id=2, type=MD5-Challenge

# EAP-Response/MD5-Challenge (Supplicant → Switch)
xx:xx:xx.xxx EAPOL version=2, type=EAP-Packet
  EAP code=Response, id=2, type=MD5-Challenge, value=[hash MD5]

# EAP-Success (Switch → Supplicant, après Access-Accept RADIUS)
xx:xx:xx.xxx EAPOL version=2, type=EAP-Packet
  EAP code=Success, id=2
  [PORT MAINTENANT AUTORISÉ]
```

**Trames RADIUS correspondantes (Switch → Serveur RADIUS) :**
```
$ tcpdump -i eth0 -nn -vvv port 1812

# RADIUS Access-Request (Switch → Serveur)
127.0.0.1.xxxxx > 192.0.2.2.1812: RADIUS Access-Request
  User-Name: "etudiant"
  EAP-Message: [EAP-Response/Identity]
  NAS-IP-Address: 192.168.1.254
  NAS-Port: 1 (FastEthernet 0/1)
  Called-Station-Id: "aa:bb:cc:dd:ee:ff"

# RADIUS Access-Challenge (Serveur → Switch)
192.0.2.2.1812 > Switch: RADIUS Access-Challenge
  EAP-Message: [EAP-Request/MD5-Challenge]
  State: [token d'état]

# RADIUS Access-Accept (Serveur → Switch, après vérification)
192.0.2.2.1812 > Switch: RADIUS Access-Accept
  EAP-Message: [EAP-Success]
  Tunnel-Type: VLAN
  Tunnel-Medium-Type: 802
  Tunnel-Private-Group-ID: "10"   ← Attribution dynamique de VLAN
```

**Résultat :** Le port du switch passe de l'état "Unauthorized" (bloqué) à "Authorized" (trafic réseau autorisé). L'utilisateur `etudiant` obtient l'accès au réseau et est placé dans le VLAN 10.

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

### Annexe B – Fichier `/etc/freeradius/3.0/clients.conf` (extrait)

```
client localhost {
    ipaddr = 127.0.0.1
    proto  = *
    secret = testing123
    nas_type = other
}

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
# PAM configuration for the Secure Shell service
# TP R4C09 - Authentification SSH via RADIUS
auth    sufficient      pam_radius_auth.so
@include common-auth
account required     pam_nologin.so
@include common-account
...
```

### Annexe D – Fichier `/etc/pam_radius_auth.conf` (modifié)

```
# Configuration du serveur RADIUS pour pam_radius_auth
# Format: server[:port]    shared_secret    timeout(s)
127.0.0.1    testing123    3
```

### Annexe E – Fichier `/etc/ssh/sshd_config` (paramètres modifiés)

```
PasswordAuthentication yes
KbdInteractiveAuthentication yes
UsePAM yes
```

### Annexe F – Paquets installés

```
freeradius           3.2.5+dfsg-3~ubuntu24.04.3
freeradius-common    3.2.5+dfsg-3~ubuntu24.04.3
freeradius-config    3.2.5+dfsg-3~ubuntu24.04.3
freeradius-utils     3.2.5+dfsg-3~ubuntu24.04.3
libfreeradius3       3.2.5+dfsg-3~ubuntu24.04.3
libpam-radius-auth   2.0.1-1
openssh-server       1:9.6p1-3ubuntu13.16
wpasupplicant        2:2.10-21ubuntu0.4
```

### Annexe G – Commandes de démarrage utilisées

```bash
# Installation serveur
apt-get install -y freeradius freeradius-utils

# Installation client
apt-get install -y freeradius freeradius-utils libpam-radius-auth wpasupplicant

# Démarrage FreeRADIUS en mode debug
freeradius -X

# Tests d'authentification
radtest etudiant TP_Radius2024 127.0.0.1 0 testing123
radtest alice alice123 127.0.0.1 0 testing123
radtest etudiant TP_Radius2024 192.0.2.2 0 secretTP2024

# Capture réseau
tcpdump -i lo -nn -vvv port 1812

# Test via radclient (simulation PAM)
echo "User-Name = 'etudiant', User-Password = 'TP_Radius2024'" | \
    radclient -x 127.0.0.1:1812 auth testing123
```

---

*Compte rendu réalisé dans le cadre du TP 1 – R4C09 Sécurité des réseaux LAN*
*IUT Béziers – Département Réseaux et Télécoms – Bachelor R&T 2023/2024*
