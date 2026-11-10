"""
Bot Discord pour assister l'équipe de développement sur le projet ft_transcendence (École 42).
Intégration de l'API Google Gemini via le SDK officiel google-genai.
"""

import asyncio
from datetime import datetime, timedelta
import json
import logging
import os
from pathlib import Path
import sys
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands
import dotenv
from google import genai
from google.genai import types
from google.genai.errors import APIError

# Configuration des logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("TranscendenceBot")

# Chemins des fichiers
BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
STATS_PATH = BASE_DIR / "usage_stats.json"

# Chargement immédiat du fichier .env
dotenv.load_dotenv(dotenv_path=ENV_PATH)

# Type de compte (pro / pay-as-you-go ou free)
ACCOUNT_TIER = os.getenv("ACCOUNT_TIER", "pro").lower()

# Suivi de la consommation (Session & Persistance)
SESSION_START_TIME = datetime.now()
SESSION_USAGE = {
    "requests": 0,
    "prompt_tokens": 0,
    "candidates_tokens": 0,
    "thoughts_tokens": 0,
    "total_tokens": 0,
    "last_request": None,
}


def load_total_usage() -> dict:
    default_stats = {
        "total_requests": 0,
        "total_prompt_tokens": 0,
        "total_candidates_tokens": 0,
        "total_thoughts_tokens": 0,
        "total_tokens": 0,
        "by_model": {},
        "last_request": None,
    }
    if not STATS_PATH.exists():
        return default_stats
    try:
        with open(STATS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {**default_stats, **data}
    except Exception as e:
        logger.error(f"Erreur lors du chargement de {STATS_PATH} : {e}")
        return default_stats


def save_total_usage() -> None:
    try:
        with open(STATS_PATH, "w", encoding="utf-8") as f:
            json.dump(TOTAL_USAGE, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Erreur lors de la sauvegarde de {STATS_PATH} : {e}")


TOTAL_USAGE = load_total_usage()


def record_usage(model_name: str, usage: Any, author: str) -> None:
    """Enregistre la consommation de tokens pour la session et de façon persistante."""
    prompt_tokens = getattr(usage, "prompt_token_count", 0) or 0
    candidates_tokens = getattr(usage, "candidates_token_count", 0) or 0
    thoughts_tokens = getattr(usage, "thoughts_token_count", 0) or 0
    total_tokens = getattr(usage, "total_token_count", 0) or (
        prompt_tokens + candidates_tokens + thoughts_tokens
    )

    # 1. Mise à jour de la session en cours
    SESSION_USAGE["requests"] += 1
    SESSION_USAGE["prompt_tokens"] += prompt_tokens
    SESSION_USAGE["candidates_tokens"] += candidates_tokens
    SESSION_USAGE["thoughts_tokens"] += thoughts_tokens
    SESSION_USAGE["total_tokens"] += total_tokens

    # 2. Mise à jour du total persistant
    TOTAL_USAGE["total_requests"] = TOTAL_USAGE.get("total_requests", 0) + 1
    TOTAL_USAGE["total_prompt_tokens"] = (
        TOTAL_USAGE.get("total_prompt_tokens", 0) + prompt_tokens
    )
    TOTAL_USAGE["total_candidates_tokens"] = (
        TOTAL_USAGE.get("total_candidates_tokens", 0) + candidates_tokens
    )
    TOTAL_USAGE["total_thoughts_tokens"] = (
        TOTAL_USAGE.get("total_thoughts_tokens", 0) + thoughts_tokens
    )
    TOTAL_USAGE["total_tokens"] = TOTAL_USAGE.get("total_tokens", 0) + total_tokens

    # Répartition par modèle
    if "by_model" not in TOTAL_USAGE:
        TOTAL_USAGE["by_model"] = {}
    m_stats = TOTAL_USAGE["by_model"].setdefault(
        model_name, {"requests": 0, "total_tokens": 0}
    )
    m_stats["requests"] += 1
    m_stats["total_tokens"] += total_tokens

    # Dernière requête
    last_req = {
        "timestamp": datetime.now().strftime("%d/%m %H:%M:%S"),
        "model": model_name,
        "author": author,
        "prompt_tokens": prompt_tokens,
        "candidates_tokens": candidates_tokens,
        "thoughts_tokens": thoughts_tokens,
        "total_tokens": total_tokens,
    }
    SESSION_USAGE["last_request"] = last_req
    TOTAL_USAGE["last_request"] = last_req

    save_total_usage()


def format_duration(td: timedelta) -> str:
    total_seconds = int(td.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours > 0:
        return f"{hours}h {minutes}m"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"


def estimate_cost(prompt_tokens: int, candidates_tokens: int, model_name: str = "") -> float:
    """Calcule une estimation du coût en USD basée sur les tarifs officiels Gemini Pay-as-you-go."""
    m = model_name.lower()
    if "lite" in m:
        input_rate = 0.0375
        output_rate = 0.15
    elif "pro" in m or "3.8" in m:
        input_rate = 0.10
        output_rate = 0.40
    else:  # Flash standard (ex: gemini-3.5-flash)
        input_rate = 0.075
        output_rate = 0.30
    return (prompt_tokens / 1_000_000.0 * input_rate) + (candidates_tokens / 1_000_000.0 * output_rate)


def build_usage_embed() -> discord.Embed:
    """Génère l'embed d'affichage de la consommation de tokens, coûts et quotas."""
    is_pro = os.getenv("ACCOUNT_TIER", "pro").lower() in ["pro", "paid", "cloud", "true"]

    embed = discord.Embed(
        title="📊 Consommation API Gemini (Tokens & Quotas)",
        description=(
            f"Statistiques d'utilisation en temps réel pour l'équipe **ft_transcendence**.\n"
            f"💎 **Niveau de Compte :** `{'Professionnel (Pay-as-you-go)' if is_pro else 'Gratuit (Free Tier)'}`\n"
            f"🤖 **Modèle actif actuel :** `{ACTIVE_MODEL}`"
        ),
        color=discord.Color.from_rgb(46, 204, 113) if is_pro else discord.Color.from_rgb(66, 133, 244),
    )

    # 1. Dernière requête
    last_req = SESSION_USAGE.get("last_request") or TOTAL_USAGE.get("last_request")
    if last_req:
        author = last_req.get("author", "Anonyme")
        m_used = last_req.get("model", ACTIVE_MODEL)
        p_tok = last_req.get("prompt_tokens", 0)
        c_tok = last_req.get("candidates_tokens", 0)
        t_tok = last_req.get("total_tokens", 0)
        time_str = last_req.get("timestamp", "Récemment")
        req_cost = estimate_cost(p_tok, c_tok, m_used)
        embed.add_field(
            name="⚡ Dernière Requête Traitée",
            value=(
                f"• **Auteur** : `{author}` ({time_str})\n"
                f"• **Modèle utilisé** : `{m_used}`\n"
                f"• **Input (Prompt + Contexte)** : `{p_tok:,}` tokens\n"
                f"• **Output (Réponse)** : `{c_tok:,}` tokens\n"
                f"• **Total requête** : **`{t_tok:,}`** tokens"
                + (f"\n• **Coût estimé** : `~${req_cost:.5f} USD`" if is_pro else "")
            ),
            inline=False,
        )
    else:
        embed.add_field(
            name="⚡ Dernière Requête Traitée",
            value="*Aucune requête enregistrée depuis le lancement.*",
            inline=False,
        )

    # 2. Session en cours
    uptime_str = format_duration(datetime.now() - SESSION_START_TIME)
    session_p = SESSION_USAGE["prompt_tokens"]
    session_c = SESSION_USAGE["candidates_tokens"]
    session_cost = estimate_cost(session_p, session_c, ACTIVE_MODEL)
    embed.add_field(
        name=f"⏱️ Session en cours ({uptime_str})",
        value=(
            f"• **Requêtes** : `{SESSION_USAGE['requests']}`\n"
            f"• **Tokens Input** : `{session_p:,}`\n"
            f"• **Tokens Output** : `{session_c:,}`\n"
            f"• **Total session** : **`{SESSION_USAGE['total_tokens']:,}`**"
            + (f"\n• **Coût session** : **`~${session_cost:.4f} USD`**" if is_pro else "")
        ),
        inline=True,
    )

    # 3. Total cumulé (persistant)
    total_p = TOTAL_USAGE.get("total_prompt_tokens", 0)
    total_c = TOTAL_USAGE.get("total_candidates_tokens", 0)
    total_cost = estimate_cost(total_p, total_c, ACTIVE_MODEL)
    embed.add_field(
        name="💾 Total Cumulé (Historique)",
        value=(
            f"• **Requêtes totales** : `{TOTAL_USAGE.get('total_requests', 0)}`\n"
            f"• **Tokens Input** : `{total_p:,}`\n"
            f"• **Tokens Output** : `{total_c:,}`\n"
            f"• **Grand Total** : **`{TOTAL_USAGE.get('total_tokens', 0):,}`**"
            + (f"\n• **Coût total estimé** : **`~${total_cost:.4f} USD`**" if is_pro else "")
        ),
        inline=True,
    )

    # 4. Quotas et Débit autorisés
    if is_pro:
        embed.add_field(
            name="💎 Quotas Compte Professionnel (Facturation active)",
            value=(
                "• **Débit autorisé** : jusqu'à **2 000 à 4 000 RPM** & **4 000 000+ TPM**\n"
                "• **Requêtes par jour** : **Illimitées** (aucune restriction journalière)\n"
                "• **Priorité réseau** : Traitement haute priorité sans file d'attente gratuite"
            ),
            inline=False,
        )
    else:
        embed.add_field(
            name="ℹ️ Quotas Gratuits Google AI Studio (Free Tier)",
            value=(
                "• **15 RPM** (Requêtes par minute max)\n"
                "• **1 000 000 TPM** (Tokens par minute max)\n"
                "• **1 500 RPD** (Requêtes par jour max)"
            ),
            inline=False,
        )

    embed.set_footer(text="Google GenAI SDK • Suivi de consommation ft_transcendence")
    embed.timestamp = datetime.now()
    return embed


# Variables d'état modifiables en cours d'exécution
ACTIVE_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
try:
    HISTORY_LIMIT: int = int(os.getenv("HISTORY_LIMIT", "35"))
except ValueError:
    HISTORY_LIMIT = 35

# Modèles recommandés (Google Gemini 3.x)
AVAILABLE_MODELS = [
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.8-flash",
    "gemini-3.7-flash",
]

# Instruction système polyvalente avec expertise École 42
SYSTEM_INSTRUCTION = """Tu es un assistant IA technique, polyvalent, brillant et bienveillant, créé pour assister les développeurs et étudiants (notamment dans l'écosystème de l'École 42).

Domaines d'expertise et compétences :
- Développement logiciel & Programmation : C, C++, Python, TypeScript, JavaScript, Go, Rust, Shell/Bash, etc.
- Architecture Web & Systèmes : Frontend (SPA, React, Vue, Vanilla JS), Backend (NestJS, Django, FastAPI, Express), Bases de données (PostgreSQL, SQLite, ORMs, SQL), WebSockets, REST, Docker & conteneurisation.
- Projets et culture de l'École 42 : Tu as une excellente connaissance des projets du cursus 42 (ft_transcendence, webserv, minishell, ft_irc, cub3d, push_swap, etc.).
  IMPORTANT : Ne ramène JAMAIS la discussion sur ft_transcendence ou sur l'École 42 si l'utilisateur ne le mentionne pas ou que sa question porte sur un autre sujet. Réponds précisément et directement à ce qui t'est demandé.

Consignes de réponse :
- Réponds en français (sauf pour les extraits de code et termes techniques standards, ou si l'utilisateur te parle dans une autre langue).
- Sois concis, clair, pédagogue et orienté solution. Privilégie le code propre et les explications logiques.
- En Message Privé (MP) comme en salon de serveur, adapte-toi à la demande : questions de dev, explications théoriques, aide au débogage, ou même questions diverses du quotidien.
- Tiens compte du contexte des messages précédents dans l'historique de la conversation.
"""


def update_active_model(new_model: str) -> None:
    """Met à jour le modèle actif en mémoire et dans le fichier .env."""
    global ACTIVE_MODEL
    ACTIVE_MODEL = new_model
    os.environ["GEMINI_MODEL"] = new_model
    try:
        dotenv.set_key(str(ENV_PATH), "GEMINI_MODEL", new_model, quote_mode="never")
        logger.info(f"Modèle actif mis à jour : {new_model} (sauvegardé dans {ENV_PATH})")
    except Exception as e:
        logger.error(f"Impossible de sauvegarder GEMINI_MODEL dans {ENV_PATH} : {e}")


def update_history_limit(new_limit: int) -> None:
    """Met à jour la limite d'historique en mémoire et dans le fichier .env."""
    global HISTORY_LIMIT
    HISTORY_LIMIT = new_limit
    os.environ["HISTORY_LIMIT"] = str(new_limit)
    try:
        dotenv.set_key(str(ENV_PATH), "HISTORY_LIMIT", str(new_limit), quote_mode="never")
        logger.info(f"HISTORY_LIMIT mis à jour : {new_limit} (sauvegardé dans {ENV_PATH})")
    except Exception as e:
        logger.error(f"Impossible de sauvegarder HISTORY_LIMIT dans {ENV_PATH} : {e}")


def get_gemini_client() -> genai.Client:
    """Récupère une instance du client Gemini à partir de la clé d'API."""
    api_key = os.getenv("GEMINI_API_KEY")
    # Si la clé n'est pas définie ou est le placeholder par défaut, recharger le fichier .env
    if not api_key or api_key == "votre_cle_api_gemini_ici":
        dotenv.load_dotenv(dotenv_path=ENV_PATH, override=True)
        api_key = os.getenv("GEMINI_API_KEY")

    if not api_key or api_key == "votre_cle_api_gemini_ici":
        raise ValueError(
            "La variable GEMINI_API_KEY n'est pas renseignée ou contient la valeur par défaut dans le fichier .env."
        )

    return genai.Client(api_key=api_key)


def split_message(text: str, max_length: int = 1900) -> list[str]:
    """
    Découpe une réponse en plusieurs morceaux d'au maximum max_length caractères
    en respectant au mieux les retours à la ligne et les mots.
    """
    if not text:
        return []
    if len(text) <= max_length:
        return [text]

    chunks: list[str] = []
    remaining = text
    while remaining:
        if len(remaining) <= max_length:
            chunks.append(remaining)
            break

        # Recherche de coupure propre (retour à la ligne en priorité, puis espace)
        split_idx = remaining.rfind("\n", 0, max_length)
        if split_idx == -1 or split_idx < max_length // 2:
            split_idx = remaining.rfind(" ", 0, max_length)
        if split_idx == -1 or split_idx < max_length // 2:
            split_idx = max_length

        chunk = remaining[:split_idx].rstrip()
        if chunk:
            chunks.append(chunk)
        remaining = remaining[split_idx:].lstrip()

    return chunks


async def call_gemini_with_fallback(
    client: genai.Client,
    prompt: str,
    system_instruction: str,
    primary_model: str,
) -> tuple[str | None, str, Any | None]:
    """
    Appelle l'API Gemini avec timeout, gestion de nouvelle tentative (retry)
    et bascule automatique sur un modèle de secours en cas d'erreur 503 (haute demande)
    ou 404 (modèle non disponible).
    Retourne (texte_généré, modèle_utilisé, usage_metadata).
    """
    # Liste des modèles à essayer : modèle principal puis modèles de secours
    fallback_candidates = [m for m in AVAILABLE_MODELS if m != primary_model]
    models_to_try = [primary_model] + fallback_candidates

    last_error: Exception | None = None

    for i, model in enumerate(models_to_try):
        is_primary = (i == 0)
        # 2 tentatives pour le modèle principal, 1 pour les modèles de secours
        max_attempts = 2 if is_primary else 1

        for attempt in range(1, max_attempts + 1):
            try:
                # Timeout strict de 25 secondes par tentative pour éviter tout blocage
                response = await asyncio.wait_for(
                    client.aio.models.generate_content(
                        model=model,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            system_instruction=system_instruction,
                        ),
                    ),
                    timeout=25.0,
                )
                text = response.text if response and response.text else None
                usage = getattr(response, "usage_metadata", None)
                return text, model, usage

            except asyncio.TimeoutError as te:
                last_error = te
                logger.warning(
                    f"Timeout (25s) sur le modèle '{model}' (tentative {attempt}/{max_attempts})."
                )
                if is_primary and attempt < max_attempts:
                    await asyncio.sleep(1)
                    continue
                else:
                    break

            except APIError as err:
                last_error = err
                is_503 = (
                    getattr(err, "code", None) == 503
                    or "503" in str(err)
                    or getattr(err, "status", None) == "UNAVAILABLE"
                )
                is_404 = (
                    getattr(err, "code", None) == 404
                    or "404" in str(err)
                    or getattr(err, "status", None) == "NOT_FOUND"
                )

                if is_404:
                    logger.warning(
                        f"Modèle '{model}' obsolète ou non trouvé (404). "
                        "Bascule immédiate vers un modèle de secours..."
                    )
                    break

                if is_503:
                    if attempt < max_attempts:
                        logger.warning(
                            f"Modèle '{model}' en surcharge (503). Nouvelle tentative dans 2 secondes..."
                        )
                        await asyncio.sleep(2)
                        continue
                    else:
                        logger.warning(
                            f"Modèle '{model}' temporairement indisponible (503). "
                            "Tentative avec un modèle de secours..."
                        )
                        break
                else:
                    # Pour toute autre erreur API (ex: clé invalide 400), propager immédiatement
                    raise err

    if last_error:
        raise last_error

    return None, primary_model, None


# Configuration des intents Discord
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    """Événement déclenché lorsque le bot est connecté et prêt."""
    logger.info(f"Connecté avec succès en tant que {bot.user} (ID: {bot.user.id})")
    logger.info(f"Modèle Gemini actif : {ACTIVE_MODEL} | Limite d'historique : {HISTORY_LIMIT}")
    try:
        # 1. Synchronisation instantanée sur tous les serveurs où le bot est présent
        for guild in bot.guilds:
            bot.tree.copy_global_to(guild=guild)
            synced_guild = await bot.tree.sync(guild=guild)
            logger.info(
                f"Commandes slash synchronisées instantanément sur '{guild.name}' "
                f"({len(synced_guild)} commandes)."
            )

        # 2. Synchronisation globale (prend jusqu'à 1 heure pour se propager partout)
        synced_global = await bot.tree.sync()
        logger.info(f"Arbre global synchronisé ({len(synced_global)} commandes).")
    except Exception as e:
        logger.error(f"Erreur lors de la synchronisation de l'arbre de commandes slash : {e}")


# Commande slash /model
@bot.tree.command(name="model", description="Changer le modèle Gemini utilisé par le bot")
@app_commands.describe(nom="Sélectionnez le modèle Gemini souhaité")
@app_commands.choices(
    nom=[
        app_commands.Choice(name="gemini-3.5-flash (Recommandé - Stable & Rapide)", value="gemini-3.5-flash"),
        app_commands.Choice(name="gemini-3.5-flash-lite (Ultra-rapide & Haute disponibilité)", value="gemini-3.5-flash-lite"),
        app_commands.Choice(name="gemini-3.8-flash (Dernière génération haute puissance)", value="gemini-3.8-flash"),
        app_commands.Choice(name="gemini-3.7-flash (Modèle avancé)", value="gemini-3.7-flash"),
    ]
)
async def slash_model(interaction: discord.Interaction, nom: app_commands.Choice[str]):
    chosen_model = nom.value if isinstance(nom, app_commands.Choice) else str(nom)
    update_active_model(chosen_model)
    await interaction.response.send_message(
        f" Le modèle Gemini actif est désormais configuré sur : **`{ACTIVE_MODEL}`** "
        f"(enregistré dans `.env`)."
    )


# Commande slash /models (afficher tous les modèles)
@bot.tree.command(name="models", description="Afficher la liste des modèles Gemini disponibles et leurs spécificités")
async def slash_models(interaction: discord.Interaction):
    desc = [
        "🤖 **Modèles Gemini disponibles pour le bot :**\n",
        "• `gemini-3.5-flash` ⭐ **(Recommandé)** — Rapide, stable et haute disponibilité.",
        "• `gemini-3.5-flash-lite` ⚡ **(Ultra-rapide)** — Latence minimale, idéal en cas de pic de charge.",
        "• `gemini-3.8-flash` 🧠 **(Dernière génération)** — Très haute capacité de raisonnement.",
        "• `gemini-3.7-flash` 🚀 **(Avancé)** — Modèle intermédiaire de haute précision.",
        f"\n📌 **Modèle actuellement actif :** `{ACTIVE_MODEL}`",
        "\n💡 *Pour changer : utilisez `/model` ou `!model <nom_du_modele>`.*",
    ]
    await interaction.response.send_message("\n".join(desc))


# Commande slash /history
@bot.tree.command(name="history", description="Consulter ou modifier le nombre de messages d'historique envoyés")
@app_commands.describe(limite="Nombre de messages d'historique à analyser (entre 5 et 100)")
async def slash_history(interaction: discord.Interaction, limite: app_commands.Range[int, 5, 100] | None = None):
    if limite is None:
        await interaction.response.send_message(
            f"ℹ️ Limite actuelle d'historique : **{HISTORY_LIMIT}** messages."
        )
        return
    update_history_limit(limite)
    await interaction.response.send_message(
        f" Limite d'historique mise à jour à **{HISTORY_LIMIT}** messages (enregistrée dans `.env`)."
    )


# Commande slash /usage
@bot.tree.command(name="usage", description="Afficher les statistiques de consommation de tokens et de requêtes Gemini")
async def slash_usage(interaction: discord.Interaction):
    embed = build_usage_embed()
    await interaction.response.send_message(embed=embed)


# Commande préfixée de secours !model <nom_du_modele>
@bot.command(name="model", help="Changer le modèle Gemini actif (commande préfixée de secours)")
async def prefix_model(ctx: commands.Context, *, nom_du_modele: str | None = None):
    if not nom_du_modele:
        choices_str = ", ".join(f"`{m}`" for m in AVAILABLE_MODELS)
        await ctx.reply(
            f"ℹ️ Modèle actuellement actif : **`{ACTIVE_MODEL}`**\n"
            f"Modèles disponibles : {choices_str}\n"
            f"Utilisation : `!model <nom_du_modele>` (ou tapez `!models` pour voir les détails)",
            mention_author=False,
        )
        return

    chosen_model = nom_du_modele.strip()
    update_active_model(chosen_model)
    await ctx.reply(
        f" Le modèle Gemini actif est désormais : **`{ACTIVE_MODEL}`** (enregistré dans `.env`).",
        mention_author=False,
    )


# Commande préfixée !models
@bot.command(name="models", help="Lister tous les modèles Gemini disponibles et leurs spécificités")
async def prefix_models(ctx: commands.Context):
    desc = [
        "🤖 **Modèles Gemini disponibles pour le bot :**\n",
        "• `gemini-3.5-flash` ⭐ **(Recommandé)** — Rapide, stable et haute disponibilité.",
        "• `gemini-3.5-flash-lite` ⚡ **(Ultra-rapide)** — Latence minimale, idéal en cas de pic de charge.",
        "• `gemini-3.8-flash` 🧠 **(Dernière génération)** — Très haute capacité de raisonnement.",
        "• `gemini-3.7-flash` 🚀 **(Avancé)** — Modèle intermédiaire de haute précision.",
        f"\n📌 **Modèle actuellement actif :** `{ACTIVE_MODEL}`",
        "\n💡 *Pour changer : tapez `!model gemini-3.5-flash` ou utilisez la commande slash `/model`.*",
    ]
    await ctx.reply("\n".join(desc), mention_author=False)


# Commande préfixée !sync pour forcer la synchronisation slash instantanée
@bot.command(name="sync", help="Synchroniser immédiatement les commandes slash sur ce serveur")
async def prefix_sync(ctx: commands.Context):
    if ctx.guild:
        bot.tree.copy_global_to(guild=ctx.guild)
        synced = await bot.tree.sync(guild=ctx.guild)
        await ctx.reply(
            f"✅ **{len(synced)} commandes slash synchronisées avec succès sur ce serveur !**\n"
            f"Elles sont désormais disponibles immédiatement dans votre client Discord.",
            mention_author=False,
        )
    else:
        await ctx.reply("Cette commande doit être exécutée dans un salon de serveur.", mention_author=False)


# Commande préfixée !history <limite>
@bot.command(name="history", help="Consulter ou modifier la limite d'historique")
async def prefix_history(ctx: commands.Context, limite: int | None = None):
    if limite is None:
        await ctx.reply(
            f"ℹ️ Limite actuelle d'historique : **{HISTORY_LIMIT}** messages.",
            mention_author=False,
        )
        return
    if limite < 1 or limite > 100:
        await ctx.reply(
            "⚠️ La limite d'historique doit être comprise entre 1 et 100 messages.",
            mention_author=False,
        )
        return
    update_history_limit(limite)
    await ctx.reply(
        f" Limite d'historique mise à jour à **{HISTORY_LIMIT}** messages (enregistrée dans `.env`).",
        mention_author=False,
    )


# Commande préfixée !usage
@bot.command(name="usage", help="Afficher les statistiques de consommation de tokens et de requêtes")
async def prefix_usage(ctx: commands.Context, action: str | None = None):
    if action and action.lower() in ["reset", "clear"]:
        SESSION_USAGE["requests"] = 0
        SESSION_USAGE["prompt_tokens"] = 0
        SESSION_USAGE["candidates_tokens"] = 0
        SESSION_USAGE["thoughts_tokens"] = 0
        SESSION_USAGE["total_tokens"] = 0
        SESSION_USAGE["last_request"] = None
        await ctx.reply(
            "🔄 Les statistiques de la session en cours ont été réinitialisées.",
            mention_author=False,
        )
        return

    embed = build_usage_embed()
    await ctx.reply(embed=embed, mention_author=False)


@bot.event
async def on_message(message: discord.Message):
    """
    Gestion des messages :
    - Ignore les messages du bot lui-même.
    - Traite les commandes préfixées.
    - Se déclenche uniquement s'il est mentionné dans un salon ou un fil de discussion.
    """
    # Ignorer les messages provenant du bot lui-même
    if message.author == bot.user:
        return

    # Traiter les commandes préfixées (ex: !model)
    await bot.process_commands(message)

    # Si le message correspond à une commande valide, ne pas continuer vers l'analyse IA
    ctx = await bot.get_context(message)
    if ctx.valid:
        return

    # Vérifier s'il s'agit d'un message privé (MP / DM) ou d'un salon de serveur
    is_dm = message.guild is None or isinstance(message.channel, discord.DMChannel)

    # En salon de serveur : le bot reste passif et ne se déclenche que sur mention (@bot)
    # En message privé (MP) : le bot répond directement à chaque message (pas besoin de mentionner)
    if not is_dm and bot.user not in message.mentions:
        return

    location = "MP (Message Privé)" if is_dm else f"#{getattr(message.channel, 'name', 'salon')} ({message.guild})"
    logger.info(f"Message reçu de {message.author} dans {location}")

    # Afficher l'indicateur de frappe pendant le traitement
    async with message.channel.typing():
        try:
            # Récupérer les N derniers messages du salon/fil
            raw_messages = [msg async for msg in message.channel.history(limit=HISTORY_LIMIT)]
            # Remettre dans l'ordre chronologique (du plus ancien au plus récent)
            raw_messages.reverse()

            formatted_history: list[str] = []
            for msg in raw_messages:
                # Récupération propre du contenu textuel
                content = msg.clean_content.strip() if msg.clean_content else ""

                # Prise en compte des pièces jointes si le texte est vide
                if not content and msg.attachments:
                    content = f"[{len(msg.attachments)} pièce(s) jointe(s)]"

                # Ignorer les messages strictement vides
                if not content:
                    continue

                author_name = msg.author.display_name
                formatted_history.append(f"{author_name}: {content}")

            if not formatted_history:
                formatted_history.append(f"{message.author.display_name}: {message.clean_content}")

            history_block = "\n".join(formatted_history)

            # Préparation du prompt pour Gemini
            prompt = (
                "Voici l'historique récent de notre discussion (par ordre chronologique) :\n"
                "--- DÉBUT DE L'HISTORIQUE ---\n"
                f"{history_block}\n"
                "--- FIN DE L'HISTORIQUE ---\n\n"
                f"Dernière intervention de {message.author.display_name} à laquelle tu dois répondre :\n"
                f"{message.clean_content}"
            )

            # Initialisation du client et appel à l'API Gemini avec retry & fallback
            client = get_gemini_client()

            reply_text, used_model, usage = await call_gemini_with_fallback(
                client=client,
                prompt=prompt,
                system_instruction=SYSTEM_INSTRUCTION,
                primary_model=ACTIVE_MODEL,
            )

            # Enregistrement de la consommation de tokens
            if usage:
                record_usage(
                    model_name=used_model,
                    usage=usage,
                    author=message.author.display_name,
                )

            if not reply_text:
                await message.reply(
                    "⚠️ L'API Gemini n'a renvoyé aucune réponse textuelle (le contenu a peut-être été filtré par les paramètres de sécurité).",
                    mention_author=False,
                )
                return

            # Si un modèle de secours a été utilisé suite à une indisponibilité temporaire (503)
            if used_model != ACTIVE_MODEL:
                reply_text = (
                    f"*(⚡ Le modèle `{ACTIVE_MODEL}` étant temporairement surchargé chez Google, "
                    f"la réponse a été générée via `{used_model}`)*\n\n{reply_text}"
                )

            # Découpage en blocs de 1900 caractères maximum
            chunks = split_message(reply_text, max_length=1900)

            for index, chunk in enumerate(chunks):
                if index == 0:
                    try:
                        await message.reply(chunk, mention_author=False)
                        continue
                    except discord.HTTPException:
                        # Si le message d'origine a été supprimé entre-temps
                        pass
                await message.channel.send(chunk)

        except asyncio.TimeoutError:
            logger.error("Délai d'attente (timeout) dépassé lors de l'appel à l'API Gemini.")
            await message.reply(
                "⏱️ **Délai d'attente dépassé (timeout) :** L'API Gemini n'a pas répondu dans le temps imparti (25s).\n"
                "💡 Essayez de retaper votre question ou basculez sur un modèle ultra-rapide avec `!model gemini-3.5-flash-lite`.",
                mention_author=False,
            )
        except ValueError as ve:
            logger.warning(f"Configuration manquante : {ve}")
            await message.reply(
                f"⚙️ **Configuration requise :** {ve}",
                mention_author=False,
            )
        except APIError as api_err:
            logger.error(f"Erreur API Gemini : {api_err}", exc_info=True)
            is_503 = (
                getattr(api_err, "code", None) == 503
                or "503" in str(api_err)
                or getattr(api_err, "status", None) == "UNAVAILABLE"
            )
            if is_503:
                await message.reply(
                    "⚠️ **Serveurs Google temporairement saturés (Erreur 503) :**\n"
                    "Les serveurs de Google rencontrent actuellement un pic de charge inhabituel sur ce modèle.\n\n"
                    "💡 **Comment débloquer la situation :**\n"
                    "• **Patientez 10 à 30 secondes** et réessayez (les pics durent rarement longtemps).\n"
                    "• Ou changez de modèle avec `!model gemini-3.5-flash-lite` ou `/model`.",
                    mention_author=False,
                )
            else:
                await message.reply(
                    f"❌ **Erreur API Gemini :**\n"
                    f"```text\n{str(api_err)[:1800]}\n```",
                    mention_author=False,
                )
        except Exception as e:
            logger.error(f"Erreur inattendue lors du traitement : {e}", exc_info=True)
            await message.reply(
                f"❌ **Une erreur inattendue est survenue :**\n"
                f"```text\n{str(e)[:1800]}\n```",
                mention_author=False,
            )


def main():
    """Point d'entrée principal pour démarrer le bot."""
    token = os.getenv("DISCORD_TOKEN")
    if not token or token == "votre_token_discord_ici":
        logger.error(
            "Le DISCORD_TOKEN n'est pas renseigné dans le fichier .env !\n"
            "Veuillez éditer le fichier .env et y ajouter votre token Discord avant de lancer le bot."
        )
        sys.exit(1)

    logger.info("Démarrage du bot Discord...")
    try:
        bot.run(token)
    except discord.LoginFailure:
        logger.error("Échec de connexion : Le token Discord fourni dans .env est invalide.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Erreur fatale lors de l'exécution du bot : {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
