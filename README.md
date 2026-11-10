# 🤖 Gemini Discord Bot — Assistant Dev & École 42

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12%20%7C%203.13%20%7C%203.14-blue?logo=python&logoColor=white" alt="Python Version" />
  <img src="https://img.shields.io/badge/package%20manager-uv-8A2BE2?logo=astral&logoColor=white" alt="uv" />
  <img src="https://img.shields.io/badge/Discord.py-v2.7+-5865F2?logo=discord&logoColor=white" alt="Discord.py" />
  <img src="https://img.shields.io/badge/Google%20GenAI-v3.0+-4285F4?logo=google&logoColor=white" alt="Google GenAI" />
  <img src="https://img.shields.io/badge/42%20Projects-ft__transcendence%20%26%20Cursus-black?logo=42" alt="École 42" />
</p>

> Bot Discord intelligent, rapide et polyvalent propulsé par l'API officielle **Google Gemini** (`google-genai`).  
> Conçu pour être à la fois votre **pair-programmer personnel en Message Privé (MP)** et l'**assistant technique de votre équipe sur serveur** pour tous vos projets de dev (dont *ft_transcendence* de l'École 42).

---

## 📑 Sommaire

1. [Aperçu & Fonctionnalités](#-aperçu--fonctionnalités)
2. [Polyvalence & Domaines d'Expertise](#-polyvalence--domaines-dexpertise)
3. [Architecture du Projet](#-architecture-du-projet)
4. [Prérequis](#-prérequis)
5. [Configuration Initiale](#-configuration-initiale)
   - [1. Portail Développeur Discord](#1-portail-développeur-discord)
   - [2. Clé d'API Google Gemini](#2-clé-dapi-google-gemini)
   - [3. Fichier d'environnement (.env)](#3-fichier-denvironnement-env)
6. [Installation & Utilisation (Makefile)](#-installation--utilisation-makefile)
7. [Commandes Discord](#-commandes-discord)
8. [Deux Modes d'Utilisation : MP vs Serveur](#-deux-modes-dutilisation--mp-vs-serveur)
9. [Modèles Gemini Disponibles](#-modèles-gemini-disponibles)
10. [Suivi de Consommation (/usage)](#-suivi-de-consommation-usage)
11. [Dépannage & FAQ](#-dépannage--faq)

---

## ⚡ Aperçu & Fonctionnalités

- 💬 **Deux modes d'utilisation pensés pour le confort :**
  - **En Message Privé (MP / DM) :** Discutez en tête-à-tête comme avec ChatGPT/Claude, **sans avoir besoin de mentionner le bot**.
  - **Sur serveur :** Il reste silencieux et ne répond que lorsqu'il est explicitement **mentionné** (`@bot`).
- 🧠 **Polyvalent et sans obsession thématique :** Répond précisément à votre question (C, C++, Python, algorithmique, Docker, dev web...) sans jamais forcer un sujet spécifique si vous ne l'avez pas demandé.
- 📜 **Mémoire contextuelle continue :** Analyse automatiquement l'historique des **35 derniers messages** pour comprendre le contexte complet de votre session de code.
- 🔀 **Gestion dynamique des modèles Gemini :**
  - Changement à chaud via `/model` ou `!model <nom>`.
  - Sauvegarde immédiate dans le fichier `.env`.
  - Détection automatique et bascule de secours en cas de pic de charge (503) ou modèle indisponible.
- ⏱️ **Protection anti-blocage (Timeout 25s) :** Ne reste jamais bloqué indéfiniment en chargement.
- 📊 **Tableau de bord de consommation (`/usage`) :** Tokens d'entrée, tokens de sortie, estimations de coûts et quotas (Free Tier ou Pro).
- 🚀 **Gestion facile via `uv` et `Makefile` :** Démarrage, arrêt, restart et logs en arrière-plan avec `screen`.

---

## 🎯 Polyvalence & Domaines d'Expertise

L'instruction système du bot est calibrée pour le développement moderne et les exigences de l'École 42 :

| Domaine | Sujets maîtrisés |
|---|---|
| **Langages de programmation** | C, C++ (C++98 à C++20), Python, TypeScript, JavaScript, Go, Rust, Bash/Shell, SQL, etc. |
| **Architecture Web & SPA** | Routage côté client, réactivité, Vanilla JS, React, Vue, Next.js, gestion du state. |
| **Backend & Microservices** | NestJS, Django, FastAPI, Express, architecture MVC/modulaire, API REST, WebSockets temps réel. |
| **Bases de Données** | PostgreSQL, SQLite, Prisma, TypeORM, Django ORM, relations, migrations. |
| **Sécurité & Auth** | OAuth2 (Intranet 42), 2FA TOTP, JWT, sessions, protection CSRF, XSS, injection SQL. |
| **DevOps & Conteneurs** | Docker, Docker Compose, réseaux, volumes, reverse proxy Nginx. |
| **Projets École 42** | Connaissance de *ft_transcendence*, *webserv*, *minishell*, *ft_irc*, *cub3d*, *push_swap*, etc. *(uniquement abordés si vous en parlez !)*. |

---

## 📁 Architecture du Projet

```text
gemini_bot/
├── Makefile            # Gestion du cycle de vie (install, run, stop, restart, logs, clean)
├── pyproject.toml      # Métadonnées du projet et dépendances gérées par uv
├── uv.lock             # Fichier de verrouillage exact des dépendances
├── requirements.txt    # Rétro-compatibilité pip (discord.py, google-genai, python-dotenv)
├── .env.example        # Modèle de configuration
├── .env                # Fichier local de vos clés (ignoré par git)
├── .gitignore          # Exclusion stricte des secrets, de .venv et de usage_stats.json
├── main.py             # Point d'entrée exécuté par uv run main.py
├── bot.py              # Cœur du bot Discord, commandes, client Gemini et logique de retry
└── README.md           # Documentation du projet
```

---

## 📦 Prérequis

- **Python** $\ge$ 3.12 (testé et validé sous Python 3.14)
- **uv** (Gestionnaire de paquets ultra-rapide) :
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```
- **GNU Screen** (optionnel, pour faire tourner le bot en tâche de fond avec le Makefile) :
  - Ubuntu/Debian : `sudo apt install screen`
  - Arch Linux : `sudo pacman -S screen`

---

## 🔑 Configuration Initiale

### 1. Portail Développeur Discord

1. Rendez-vous sur le [Discord Developer Portal](https://discord.com/developers/applications).
2. Créez votre application (**New Application**).
3. Dans l'onglet **Bot** :
   - Cliquez sur **Reset Token** pour copier votre token.
   - **OBLIGATOIRE :** Dans la section **Privileged Gateway Intents**, cochez :
     - ✅ **MESSAGE CONTENT INTENT**
4. Invitez le bot :
   - Allez dans **OAuth2** > **URL Generator**.
   - Cochez les scopes `bot` et `applications.commands`.
   - Cochez les permissions : `Send Messages`, `Read Message History`, `View Channels`.
   - Ouvrez l'URL générée dans votre navigateur pour l'ajouter à votre serveur.

### 2. Clé d'API Google Gemini

1. Connectez-vous sur [Google AI Studio](https://aistudio.google.com/).
2. Cliquez sur **Get API key** et créez une clé (100% gratuite avec 1 500 requêtes/jour offertes).

### 3. Fichier d'environnement (`.env`)

Copiez le fichier d'exemple :
```bash
cp .env.example .env
```

Éditez votre `.env` :
```dotenv
# Token de votre bot Discord
DISCORD_TOKEN=votre_token_discord_ici

# Clé API Google Gemini (Google AI Studio)
GEMINI_API_KEY=votre_cle_api_gemini_ici

# Nombre de messages d'historique envoyés comme contexte (par défaut 35)
HISTORY_LIMIT=35

# Modèle actif (gemini-3.5-flash recommandé)
GEMINI_MODEL=gemini-3.5-flash

# Type de compte : 'free' (Niveau sans frais) ou 'pro' (Pay-as-you-go)
ACCOUNT_TIER=free
```

---

## 🛠️ Installation & Utilisation (Makefile)

Le `Makefile` fournit des commandes prêtes à l'emploi :

```bash
# 1. Installer l'environnement virtuel et synchroniser les dépendances avec uv
make install

# 2. Démarrer le bot en tâche de fond dans une session screen ('bot42')
make run

# 3. Voir les logs et la console du bot en direct
make logs
# (Pour détacher l'écran sans couper le bot : faites Ctrl + A puis D)

# 4. Redémarrer le bot
make restart

# 5. Arrêter le bot
make stop

# 6. Nettoyer le venv et les caches Python
make clean
```

> **Lancement direct en avant-plan (débogage) :**
> ```bash
> uv run main.py
> ```

---

## 💬 Commandes Discord

### Commandes Slash (Interactives)

| Commande | Description |
|---|---|
| `/model` | Menu déroulant pour basculer instantanément de modèle (`3.5-flash`, `3.5-flash-lite`, `3.8-flash`, `3.7-flash`). |
| `/models` | Affiche la liste détaillée des modèles disponibles et leurs spécificités. |
| `/usage` | Affiche le tableau de bord de consommation de tokens et de requêtes. |
| `/history` | Consulte ou modifie la limite d'historique (5 à 100 messages). |

### Commandes Préfixées (Secours & Instantané)

| Commande | Exemple | Description |
|---|---|---|
| `!model <nom>` | `!model gemini-3.5-flash-lite` | Change immédiatement de modèle actif sans attendre Discord. |
| `!models` | `!models` | Liste tous les modèles et indique le modèle actif. |
| `!usage` | `!usage` *(ou `!usage reset`)* | Affiche l'embed complet de consommation de tokens. |
| `!sync` | `!sync` | Force l'actualisation instantanée des commandes slash sur votre serveur. |
| `!history <n>` | `!history 50` | Modifie la limite d'historique en mémoire et dans le fichier `.env`. |

---

## 👥 Deux Modes d'Utilisation : MP vs Serveur

### 1. En Message Privé (MP / DM) — Comme ChatGPT
Ouvrez une conversation privée avec le bot et posez vos questions **sans aucune mention** :
```text
Peux-tu m'expliquer la différence entre std::unique_ptr et std::shared_ptr en C++ ?
```

### 2. Sur un Serveur d'Équipe — Silencieux
Pour ne pas polluer les salons de discussion, le bot ne répond que lorsqu'il est mentionné :
```text
@TranscendenceBot Comment organiser notre loop de jeu côté serveur pour que la physique du Pong soit autoritaire ?
```

Dans les deux cas, le bot analyse les **35 derniers messages** pour vous répondre avec tout le contexte nécessaire.

---

## 🧠 Modèles Gemini Disponibles

| Modèle | Performance | Usage recommandé |
|---|---|---|
| **`gemini-3.5-flash`** ⭐ *(Défaut)* | Ultra-rapide & Stable | **Choix n°1 :** Idéal pour 95% des besoins (code, explications, dev). |
| **`gemini-3.5-flash-lite`** ⚡ | Latence quasi nulle | Idéal lors des pics de charge ou pour des questions très rapides. |
| **`gemini-3.8-flash`** 🧠 | Raisonnement poussé | Dernière génération, pour les algorithmes et architectures complexes. |
| **`gemini-3.7-flash`** 🚀 | Haute précision | Revue de code critique et sécurité. |

---

## 📊 Suivi de Consommation (`/usage`)

La commande `/usage` génère un rapport complet en temps réel :

1. **Dernière requête :** Auteur, modèle, tokens de prompt, tokens de réponse et coût estimé.
2. **Session en cours :** Nombre de requêtes et tokens depuis le démarrage.
3. **Total cumulé :** Historique global conservé dans `usage_stats.json`.
4. **Quotas adaptés :**
   - **Niveau sans frais (`ACCOUNT_TIER=free`) :** Jauge 15 RPM et limite quotidienne de 1 500 requêtes.
   - **Compte Pro (`ACCOUNT_TIER=pro`) :** Débit jusqu'à 4 000 RPM, requêtes illimitées et estimation en dollars.

---

## ❓ Dépannage & FAQ

<details>
<summary><b>1. Le bot ne répond pas sur serveur</b></summary>

- Avez-vous bien mentionné `@bot` dans votre message ?
- Vérifiez que **MESSAGE CONTENT INTENT** est coché sur le [Discord Developer Portal](https://discord.com/developers/applications) (onglet *Bot*).
- Vérifiez les logs avec `make logs` ou regardez votre terminal.
</details>

<details>
<summary><b>2. Les commandes slash n'apparaissent pas</b></summary>

- Tapez simplement `!sync` dans un salon pour forcer la synchronisation immédiate sur votre serveur.
- Vous pouvez aussi utiliser directement les commandes préfixées (`!models`, `!model`, `!usage`).
</details>

<details>
<summary><b>3. Erreur 503 (Modèle temporairement saturé chez Google)</b></summary>

- Le bot bascule automatiquement sur un modèle alternatif si cela arrive.
- Vous pouvez aussi basculer manuellement sur le modèle ultra-léger : `!model gemini-3.5-flash-lite`.
</details>

<details>
<summary><b>4. `screen: command not found` avec le Makefile</b></summary>

- Installez screen (`sudo apt install screen` ou `sudo pacman -S screen`), ou lancez le bot directement en avant-plan :
  ```bash
  uv run main.py
  ```
</details>

---

<p align="center">
  <b>Conçu pour accompagner vos sessions de code et vos projets d'école</b> 🚀
</p>
