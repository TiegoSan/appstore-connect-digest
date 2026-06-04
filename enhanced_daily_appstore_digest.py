#!/usr/bin/env python3
"""Run the daily digest with an added sales strategy layer."""

from __future__ import annotations

import argparse
from html import escape
from typing import Any

import daily_appstore_digest as base

_ORIGINAL_RENDER_HTML = base.render_html

SALES_PROFILES: dict[str, dict[str, str]] = {
    "coupez": {
        "line": "pro-postproduction",
        "promise": "conform audio et detection de coupes image",
        "sale": "vendre du temps gagne, moins d'erreurs de conform, moins de stress avant livraison",
        "asset": "premier screenshot avant/apres: video source, cuts detectes, export AAF vers Pro Tools",
    },
    "glass-master": {
        "line": "pro-postproduction",
        "promise": "controle loudness, true peak, LRA et conformite technique",
        "sale": "vendre la reduction du risque de refus diffuseur/plateforme et la securisation des livrables",
        "asset": "mettre en avant un rapport clair: conforme / non conforme / actions a corriger",
    },
    "odile": {
        "line": "pro-postproduction",
        "promise": "generation d'EDL et extraction structuree depuis les sessions Pro Tools",
        "sale": "vendre la transformation d'un geste assistant en sortie fiable et partageable",
        "asset": "montrer une timeline Pro Tools qui devient Excel/CSV exploitable",
    },
    "feedbacks": {
        "line": "pro-postproduction",
        "promise": "conversion de retours client en markers timeline",
        "sale": "vendre la disparition du copier-coller manuel et des oublis entre notes et DAW",
        "asset": "screenshot en trois etapes: texte client, parsing, markers dans Pro Tools",
    },
    "bouncedatracks": {
        "line": "pro-postproduction",
        "promise": "automation autour des bounces et exports audio",
        "sale": "vendre le gain de temps sur les livrables repetitifs et la reduction des erreurs de nommage",
        "asset": "prouver le batch: plusieurs pistes, plusieurs sorties, naming propre",
    },
    "bouclez": {
        "line": "music-production",
        "promise": "preparation ou transfert de boucles dans un workflow Pro Tools",
        "sale": "vendre la rapidite entre idee musicale, boucle et session exploitable",
        "asset": "clarifier la promesse exacte: entree, traitement, sortie",
    },
    "gogo-looping": {
        "line": "music-production",
        "promise": "outil de boucle ou d'experimentation musicale",
        "sale": "vendre l'immediatete creative, pas la technicite brute",
        "asset": "demontrer en une capture le plaisir d'usage et le resultat sonore",
    },
    "my-first-sampler": {
        "line": "consumer-music",
        "promise": "sampler simple et pedagogique",
        "sale": "vendre l'accessibilite: premier geste musical, apprentissage, jeu immediat",
        "asset": "screenshot tres lisible, promesse enfant/debutant/creation rapide a trancher",
    },
    "perroquet": {
        "line": "consumer-music",
        "promise": "analyse audio musicale, notes, BPM et reproduction au clavier",
        "sale": "vendre une promesse comprehensible par recherche: retrouver, comprendre, rejouer",
        "asset": "capitaliser sur les requetes App Store qui generent deja de la decouverte",
    },
}


def sales_profile(app: base.AppDigest) -> dict[str, str]:
    return SALES_PROFILES.get(
        app.key,
        {
            "line": "a-clarifier",
            "promise": "promesse produit a resserrer",
            "sale": "vendre un probleme concret plutot qu'une liste de fonctions",
            "asset": "definir une phrase de vente et un premier screenshot qui prouvent l'utilite",
        },
    )


def metric(app: base.AppDigest, field: str) -> int:
    return base.metric(app, field)


def rate(app: base.AppDigest, field: str) -> Any:
    return base.rate(app, field)


def pct(value: Any) -> str:
    return base.pct(value)


def funnel_diagnosis(app: base.AppDigest) -> str:
    downloads = metric(app, "standard_total")
    first = metric(app, "first_time_downloads")
    impressions = metric(app, "impressions")
    unique_impressions = metric(app, "unique_impressions") or impressions
    page_views = metric(app, "product_page_views")
    taps = metric(app, "taps")
    pv_rate = rate(app, "page_view_rate")
    tap_rate = rate(app, "tap_rate")
    conversion_rate = rate(app, "conversion_rate")

    if app.error:
        return f"Donnee absente: corriger l'acces API avant toute conclusion commerciale ({app.error})."
    if not app.data:
        return "Donnee absente: impossible de juger le funnel."
    if impressions == 0 and downloads == 0 and page_views == 0:
        return "Probleme de distribution ou de reporting: l'app n'entre pas encore dans le champ de decision commerciale."
    if impressions > 0 and page_views == 0:
        return (
            "Fuite en haut de funnel: l'app apparait mais ne donne pas envie d'ouvrir la fiche. "
            "Priorite a l'icone, au nom, au sous-titre, a la premiere ligne de promesse et au premier screenshot."
        )
    if page_views > 0 and first == 0:
        return (
            "Fuite sur la fiche produit: l'intention existe mais ne se transforme pas. "
            "Priorite aux preuves, captures, pricing, demo courte, avis, clarte du probleme resolu."
        )
    if first > 0 and impressions > 0:
        parts = [f"Funnel vivant: {first} first-time downloads depuis {impressions} impressions"]
        if unique_impressions:
            parts.append(f"conversion approx. {pct(conversion_rate)}")
        if pv_rate is not None:
            parts.append(f"PV rate {pct(pv_rate)}")
        if tap_rate is not None:
            parts.append(f"tap rate {pct(tap_rate)}")
        return "; ".join(parts) + ". Renforcer ce qui marche avant de multiplier les chantiers."
    if downloads > 0 and impressions == 0:
        return "Telechargements sans impressions visibles: verifier source externe, reporting ou decalage de fenetre; possible signal hors App Store Search."
    if taps > 0 and first == 0:
        return "Taps sans acquisition: verifier la friction de prix, d'achat integre, de compatibilite ou de confiance."
    return "Signal partiel: attendre plus de volume, mais formuler des tests metadata des maintenant."


def commercial_priority(app: base.AppDigest) -> int:
    profile = sales_profile(app)
    score = 0
    score += metric(app, "first_time_downloads") * 4
    score += metric(app, "standard_total") * 2
    score += metric(app, "product_page_views")
    score += min(metric(app, "impressions"), 100) // 10
    if profile["line"] == "pro-postproduction":
        score += 12
    elif profile["line"] == "consumer-music":
        score += 5
    return score


def render_sales_table(apps: list[base.AppDigest]) -> str:
    rows = []
    for app in sorted(apps, key=lambda item: (-commercial_priority(item), item.name)):
        profile = sales_profile(app)
        rows.append(
            "<tr>"
            f"<td><strong>{escape(app.name)}</strong><br><span class=\"muted\">{escape(profile['line'])}</span></td>"
            f"<td>{escape(profile['promise'])}</td>"
            f"<td>{escape(funnel_diagnosis(app))}</td>"
            f"<td>{escape(profile['sale'])}<br><span class=\"muted\">Asset: {escape(profile['asset'])}</span></td>"
            "</tr>"
        )
    return "\n".join(rows)


def render_sales_doctrine(apps: list[base.AppDigest]) -> str:
    ok_apps = [app for app in apps if app.data]
    pro_apps = [app for app in ok_apps if sales_profile(app)["line"] == "pro-postproduction"]
    consumer_apps = [app for app in ok_apps if sales_profile(app)["line"] == "consumer-music"]
    pro_downloads = sum(metric(app, "standard_total") for app in pro_apps)
    consumer_downloads = sum(metric(app, "standard_total") for app in consumer_apps)
    pro_impressions = sum(metric(app, "impressions") for app in pro_apps)
    consumer_impressions = sum(metric(app, "impressions") for app in consumer_apps)

    return f"""
    <div class="callout">
      <p><strong>These commerciale.</strong> GogoLabs ne doit pas vendre des petites apps. GogoLabs doit vendre du temps recupere, des erreurs evitees, des livrables plus propres et une baisse de charge mentale dans des workflows creatifs lourds.</p>
      <p><strong>Ligne pro.</strong> Les apps post-production totalisent {pro_downloads} telechargements et {pro_impressions} impressions sur cette fenetre. Leur potentiel economique ne se mesure pas seulement au volume: une seule vente pro peut valoir plus qu'une masse d'installations grand public si la douleur est nette.</p>
      <p><strong>Ligne grand public / musique.</strong> Les apps musique-consumer totalisent {consumer_downloads} telechargements et {consumer_impressions} impressions. Leur role peut etre double: capter du volume App Store Search et servir de porte d'entree vers la marque.</p>
      <p><strong>Regle de prix.</strong> Si une app economise trente minutes dans un contexte professionnel paye, elle ne doit pas etre presentee comme un jouet a bas prix. Le prix doit cadrer la valeur: temps gagne, risque evite, fiabilite, workflow plus controlable.</p>
    </div>
    """


def render_deep_sales_reflection(apps: list[base.AppDigest]) -> str:
    ok_apps = [app for app in apps if app.data]
    leader = max(ok_apps, key=lambda app: metric(app, "standard_total"), default=None)
    impression_leader = max(ok_apps, key=lambda app: metric(app, "impressions"), default=None)
    leader_text = f"{escape(leader.name)} prouve qu'une intention lisible peut generer du volume." if leader else ""
    impression_text = f"{escape(impression_leader.name)} est le meilleur thermometre actuel de decouverte App Store." if impression_leader else ""

    return f"""
    <div class="strategy">
      <h3>1. Separateur mental: outil utile vs produit vendable</h3>
      <p>Un outil utile resout un probleme. Un produit vendable rend ce probleme visible avant meme l'installation. Le travail commercial prioritaire n'est donc pas d'ajouter des fonctions, mais de rendre chaque app achetable en quelques secondes: nom, sous-titre, screenshot 1, promesse, preuve, prix.</p>
      <h3>2. Ce que les donnees doivent decider</h3>
      <p>Les impressions mesurent l'exposition. Les vues page produit mesurent la force du packaging App Store. Les taps mesurent l'intention d'action. Les first-time downloads mesurent le passage a l'acte. Tant que les volumes sont faibles, le rapport ne doit pas chercher une certitude statistique; il doit identifier le goulot le plus probable et imposer un test simple.</p>
      <h3>3. Lecture du portefeuille</h3>
      <p>{leader_text} {impression_text} Mais la strategie GogoLabs ne doit pas etre pilotee seulement par le volume brut. Les apps professionnelles doivent etre jugees par valeur par vente, clarte de douleur, capacite a etre recommandees entre professionnels et potentiel de bundle.</p>
      <h3>4. Direction de vente</h3>
      <p>La meilleure promesse commerciale est celle-ci: des apps macOS premium pour professionnels de la creation, concues pour economiser du temps, reduire les erreurs et rendre les workflows plus controlables. Chaque fiche App Store doit etre reconstruite autour de cette promesse, avec une variante precise par app.</p>
      <h3>5. Bundling</h3>
      <p>Coupez, Glass Master, Odile, FeedBacks et BounceDaTracks peuvent former une ligne "post-production workflow tools". L'objectif n'est pas seulement vendre une app isolee: c'est installer l'idee qu'un professionnel peut acheter plusieurs petits outils GogoLabs parce qu'ils comblent les trous entre Pro Tools, l'image, les retours client et les livrables.</p>
      <h3>6. Risque principal</h3>
      <p>Le risque n'est pas le manque de fonctions. Le risque est la dispersion: trop d'apps, chacune avec une promesse insuffisamment tranchee. Le rapport doit donc forcer une discipline: une app, une douleur, une phrase, une capture decisive, un prix coherent.</p>
    </div>
    """


def render_sales_actions(apps: list[base.AppDigest]) -> str:
    priority_apps = sorted(apps, key=lambda app: (-commercial_priority(app), app.name))[:5]
    priority_items = []
    for app in priority_apps:
        profile = sales_profile(app)
        priority_items.append(
            f"<li><strong>{escape(app.name)}</strong>: {escape(profile['asset'])}. Diagnostic: {escape(funnel_diagnosis(app))}</li>"
        )

    return f"""
    <ol>
      <li><strong>Reecrire la promesse App Store de chaque app en une phrase vendable.</strong> Forme imposee: "Cette app aide [personne precise] a [resultat concret] sans [douleur actuelle]".</li>
      <li><strong>Refaire le premier screenshot autour du resultat.</strong> Pas une interface seule. Montrer le probleme avant, l'action, puis la sortie utile.</li>
      <li><strong>Segmenter les prix.</strong> Apps pro: prix base sur temps gagne et risque evite. Apps grand public/musique: friction basse, volume, eventuel achat integre simple.</li>
      <li><strong>Creer un bundle mental GogoLabs.</strong> Meme si l'App Store ne vend pas encore un bundle formel, les descriptions doivent se repondre: outils macOS premium pour workflows creatifs reels.</li>
      <li><strong>Exploiter les signaux faibles.</strong> Si impressions sans page views: ASO visuel. Si page views sans downloads: preuve/prix/confiance. Si downloads sans impressions: chercher la source externe.</li>
    </ol>
    <h3>Priorites calculees sur cette fenetre</h3>
    <ul>{''.join(priority_items)}</ul>
    """


def sales_sections(apps: list[base.AppDigest]) -> str:
    return f"""
    <h2>Lecture commerciale GogoLabs</h2>
    {render_sales_doctrine(apps)}

    <h2>Diagnostic vente par app</h2>
    <table>
      <thead>
        <tr>
          <th>App</th><th>Promesse vendable</th><th>Diagnostic funnel</th><th>Levier commercial</th>
        </tr>
      </thead>
      <tbody>{render_sales_table(apps)}</tbody>
    </table>

    <h2>Reflexion approfondie pour ameliorer les ventes</h2>
    {render_deep_sales_reflection(apps)}

    <h2>Actions commerciales recommandees</h2>
    {render_sales_actions(apps)}
    """


def render_html(apps: list[base.AppDigest], report_date: str) -> str:
    html = _ORIGINAL_RENDER_HTML(apps, report_date)
    extra_css = """
    .callout { background:#fff; border:1px solid #d6d6d0; border-left:5px solid #1f6f8b; border-radius:8px; padding:14px 16px; }
    .strategy { background:#fff; border:1px solid #deded8; border-radius:8px; padding:14px 16px; }
    h3 { margin:18px 0 8px; font-size:15px; }
    ol { padding-left:22px; }
    """
    html = html.replace("  </style>", f"{extra_css}\n  </style>")
    return html.replace("    <h2>Erreurs</h2>", f"{sales_sections(apps)}\n\n    <h2>Erreurs</h2>")


def main() -> None:
    base.render_html = render_html
    parser = argparse.ArgumentParser(description="Generate and email the enhanced App Store Connect HTML digest")
    parser.add_argument("--recipient", default=base.DEFAULT_RECIPIENT)
    parser.add_argument("--no-send", action="store_true", help="genere le HTML sans envoyer de mail")
    parser.add_argument("--only-paris-hour", type=int, help="ne lance le digest que si l'heure Europe/Paris correspond")
    args = parser.parse_args()
    raise SystemExit(base.generate_digest(args.recipient, should_send=not args.no_send, only_paris_hour=args.only_paris_hour))


if __name__ == "__main__":
    main()
