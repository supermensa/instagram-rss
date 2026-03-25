#!/usr/bin/env python3
"""
Instagram → RSS generator
Kræver: pip install instagrapi
Kør: python instagram_rss.py
"""

import html
import json
import mimetypes
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlparse
from xml.dom import minidom
from xml.etree.ElementTree import Element, SubElement, tostring


def load_dotenv(dotenv_fil=".env"):
    """Læs simple KEY=VALUE linjer fra .env ind i miljøvariabler."""
    dotenv_sti = Path(dotenv_fil)
    if not dotenv_sti.exists():
        return

    for linje in dotenv_sti.read_text(encoding="utf-8").splitlines():
        linje = linje.strip()
        if not linje or linje.startswith("#") or "=" not in linje:
            continue

        nøgle, værdi = linje.split("=", 1)
        nøgle = nøgle.strip()
        værdi = værdi.strip().strip('"').strip("'")
        os.environ.setdefault(nøgle, værdi)


load_dotenv()

# ─── KONFIGURATION ───────────────────────────────────────────────
BRUGERNAVN = os.getenv("INSTAGRAM_USERNAME") or os.getenv("BRUGERNAVN", "")
BRUGERNAVN = BRUGERNAVN.strip()
ADGANGSKODE = os.getenv("INSTAGRAM_PASSWORD") or os.getenv("ADGANGSKODE", "")
ADGANGSKODE = ADGANGSKODE.strip()
PROFILER_FIL = "profiler.txt"
PUBLIC_MAPPE = "public"
OUTPUT_FIL = f"{PUBLIC_MAPPE}/instagram.xml"
OUTPUT_FIL_NY = f"{PUBLIC_MAPPE}/instagram-all.xml"
CACHE_FIL = "posts_cache.json"
SESSION_FIL = "session.json"
POSTS_PER_PROFIL = int(os.getenv("POSTS_PER_PROFILE", "5"))
FEED_POSTS_PER_PROFIL = int(os.getenv("FEED_POSTS_PER_PROFILE", "5"))
FEEDS_UNDERMAPPE = "feeds"
FEEDS_MAPPE = f"{PUBLIC_MAPPE}/{FEEDS_UNDERMAPPE}"
OPML_FIL = f"{PUBLIC_MAPPE}/instagram.opml"
OPML_FIL_NY = f"{PUBLIC_MAPPE}/instagram-by-profile.opml"
INDEX_FIL = f"{PUBLIC_MAPPE}/index.html"
STYLESHEET_FIL = f"{PUBLIC_MAPPE}/feed.xsl"
PAGES_BASE_URL = os.getenv("PAGES_BASE_URL", "https://supermensa.github.io/instagram-rss").rstrip("/")
PUBLIC_BASE_URL = f"{PAGES_BASE_URL}/{PUBLIC_MAPPE}"

DELAY_MIN_FIRST = 5
DELAY_MAX_FIRST = 10
DELAY_MIN_FAST = 2
DELAY_MAX_FAST = 4

# Spring over profiler hentet inden for de sidste X timer
MIN_TIMER_MELLEM_HENTNINGER = int(os.getenv("MIN_HOURS_BETWEEN_FETCHES", "23"))
# ─────────────────────────────────────────────────────────────────


def hent_klient(fast_mode=False):
    from instagrapi import Client

    def ny_klient():
        klient = Client()
        if fast_mode:
            klient.delay_range = [DELAY_MIN_FAST, DELAY_MAX_FAST]
            print("⚡ Fast mode: reducerede delays")
        else:
            klient.delay_range = [DELAY_MIN_FIRST, DELAY_MAX_FIRST]
            print("🐌 Første kørsel: sikre delays")
        return klient

    cl = ny_klient()

    if Path(SESSION_FIL).exists():
        print("📂 Genbruger gemt session...")
        try:
            cl.load_settings(SESSION_FIL)
            cl.login(BRUGERNAVN, ADGANGSKODE)
        except Exception as e:
            print(f"♻️  Gemt session virkede ikke længere ({e.__class__.__name__}). Logger ind igen...")
            try:
                Path(SESSION_FIL).unlink(missing_ok=True)
            except OSError:
                pass

            cl = ny_klient()
            cl.login(BRUGERNAVN, ADGANGSKODE)
            cl.dump_settings(SESSION_FIL)
            print(f"✅ Ny session gemt i {SESSION_FIL}")
    else:
        print("🔐 Logger ind på Instagram...")
        cl.login(BRUGERNAVN, ADGANGSKODE)
        cl.dump_settings(SESSION_FIL)
        print(f"✅ Session gemt i {SESSION_FIL}")

    return cl


def hent_profiler():
    if not Path(PROFILER_FIL).exists():
        print(f"❌ Filen '{PROFILER_FIL}' findes ikke.")
        print("Opret den med ét Instagram-brugernavn per linje, f.eks.:")
        print("  22teachings\n  natgeo\n  nasa")
        exit(1)

    profiler = []
    with open(PROFILER_FIL, "r", encoding="utf-8") as f:
        for linje in f:
            navn = linje.strip().lstrip("@").strip()
            if navn and not navn.startswith("#"):
                profiler.append(navn)

    print(f"📋 Fandt {len(profiler)} profiler i {PROFILER_FIL}")
    return profiler


def indlæs_cache():
    """Indlæs tidligere hentede posts og seneste timestamps."""
    if not Path(CACHE_FIL).exists():
        return {"posts": {}, "last_fetch": {}}

    try:
        with open(CACHE_FIL, "r", encoding="utf-8") as f:
            cache = json.load(f)
            for profil in cache.get("last_fetch", {}):
                if cache["last_fetch"][profil]:
                    cache["last_fetch"][profil] = datetime.fromisoformat(cache["last_fetch"][profil])
            return cache
    except Exception as e:
        print(f"⚠️  Kunne ikke læse cache: {e}")
        return {"posts": {}, "last_fetch": {}}


def gem_cache(cache):
    """Gem posts og timestamps til cache."""
    cache_kopi = {"posts": cache["posts"], "last_fetch": {}}
    for profil, ts in cache["last_fetch"].items():
        cache_kopi["last_fetch"][profil] = ts.isoformat() if ts else None

    with open(CACHE_FIL, "w", encoding="utf-8") as f:
        json.dump(cache_kopi, f, ensure_ascii=False, indent=2)


def hent_posts_fra_cache(cache, limit_per_profil=None, kun_profil=None):
    """Konverter cache til posts med datetime-objekter."""
    alle_posts = []
    profiler = [kun_profil] if kun_profil else cache.get("posts", {}).keys()

    for profil in profiler:
        cached_posts = cache.get("posts", {}).get(profil, [])
        posts_for_profil = cached_posts[:limit_per_profil] if limit_per_profil else cached_posts
        for cached_post in posts_for_profil:
            post_copy = cached_post.copy()
            post_copy["dato"] = datetime.fromisoformat(cached_post["dato"])
            alle_posts.append(post_copy)

    return alle_posts


def cache_post_har_mangelfulde_medier(post):
    """Gamle cacheposter havde kun ét billede og mangler slideshow/video-data."""
    if not post:
        return True

    if "medie_type" not in post or "ressourcer" not in post or "video" not in post:
        return True

    medie_type = post.get("medie_type")
    if medie_type == "slideshow" and not post.get("ressourcer"):
        return True

    if medie_type == "video" and not post.get("video"):
        return True

    return False


def berig_cache_post_medier(cached_post, medie_data):
    """Opdater en cachepost med nyere mediafelter uden at miste eksisterende data."""
    if not cached_post:
        return False

    nye_felter = {
        "billede": medie_data.get("billede"),
        "video": medie_data.get("video"),
        "medie_type": medie_data.get("medie_type", "billede"),
        "ressourcer": medie_data.get("ressourcer") or [],
    }

    ændret = False
    for nøgle, værdi in nye_felter.items():
        if nøgle not in cached_post or cached_post.get(nøgle) != værdi:
            cached_post[nøgle] = værdi
            ændret = True

    return ændret


def skriv_fil(sti, indhold):
    sti = Path(sti)
    sti.parent.mkdir(parents=True, exist_ok=True)
    with open(sti, "w", encoding="utf-8") as f:
        if sti.suffix in {".xml", ".opml"}:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write(indhold)


def profil_feed_filnavn(profil):
    return f"{profil}.xml"


def profil_feed_sti(profil):
    return Path(FEEDS_MAPPE) / profil_feed_filnavn(profil)


def profil_feed_url(profil):
    return f"{PUBLIC_BASE_URL}/{FEEDS_UNDERMAPPE}/{quote(profil_feed_filnavn(profil))}"


def stylesheet_url():
    return f"{PUBLIC_BASE_URL}/{Path(STYLESHEET_FIL).name}"


def public_relativ_sti(sti):
    path = Path(sti)
    try:
        return path.relative_to(PUBLIC_MAPPE).as_posix()
    except ValueError:
        return path.as_posix()


def media_type_navn(media_type):
    mapping = {
        1: "billede",
        2: "video",
        8: "slideshow",
    }
    return mapping.get(media_type, "ukendt")


def url_som_str(værdi):
    return str(værdi) if værdi else None


def udtræk_ressourcer(medie):
    ressourcer = []

    for resource in getattr(medie, "resources", []) or []:
        resource_type = media_type_navn(getattr(resource, "media_type", None))
        thumbnail = url_som_str(getattr(resource, "thumbnail_url", None))
        video_url = url_som_str(getattr(resource, "video_url", None))

        ressourcer.append({
            "type": resource_type,
            "thumbnail": thumbnail,
            "video": video_url,
        })

    return ressourcer


def udtræk_post_medier(medie):
    medie_type = media_type_navn(getattr(medie, "media_type", None))
    ressourcer = udtræk_ressourcer(medie)
    video_url = url_som_str(getattr(medie, "video_url", None))

    billede = url_som_str(getattr(medie, "thumbnail_url", None))
    if not billede and ressourcer:
        billede = ressourcer[0].get("thumbnail")

    if medie_type == "slideshow" and not billede:
        billede = next((res["thumbnail"] for res in ressourcer if res.get("thumbnail")), None)

    if medie_type == "video" and not video_url:
        video_url = next((res["video"] for res in ressourcer if res.get("video")), None)

    if medie_type == "ukendt":
        if video_url:
            medie_type = "video"
        elif len(ressourcer) > 1:
            medie_type = "slideshow"
        else:
            medie_type = "billede"

    return {
        "medie_type": medie_type,
        "billede": billede,
        "video": video_url,
        "ressourcer": ressourcer,
    }


def byg_og_gem_rss(cache):
    """Byg samlet feed, profil-feeds, OPML og oversigtsside."""
    alle_posts = hent_posts_fra_cache(cache)
    if not alle_posts:
        return

    samlet_feed = byg_rss(
        alle_posts,
        kanal_titel="Mine Instagram feeds",
        kanal_link=PUBLIC_BASE_URL,
        kanal_beskrivelse=f"Samlet feed genereret {datetime.now().strftime('%d-%m-%Y %H:%M')}",
    )
    skriv_fil(OUTPUT_FIL_NY, samlet_feed)
    skriv_fil(OUTPUT_FIL, samlet_feed)

    byg_og_gem_profilfeeds(cache)
    byg_og_gem_opml(cache)
    byg_og_gem_index(cache)


def byg_og_gem_profilfeeds(cache):
    profiler_med_posts = [profil for profil, posts in sorted(cache.get("posts", {}).items()) if posts]

    for profil in profiler_med_posts:
        posts = hent_posts_fra_cache(cache, limit_per_profil=FEED_POSTS_PER_PROFIL, kun_profil=profil)
        if not posts:
            continue

        feed = byg_rss(
            posts,
            kanal_titel=f"Instagram: @{profil}",
            kanal_link=f"https://www.instagram.com/{profil}/",
            kanal_beskrivelse=f"Seneste {len(posts)} posts fra @{profil}",
        )
        skriv_fil(profil_feed_sti(profil), feed)


def byg_og_gem_opml(cache):
    profiler_med_posts = [profil for profil, posts in sorted(cache.get("posts", {}).items()) if posts]
    generated = datetime.now().strftime("%Y-%m-%d %H:%M")

    outlines = []
    for profil in profiler_med_posts:
        outlines.append(
            "    "
            + f'<outline text="@{html.escape(profil)}" title="@{html.escape(profil)}" '
            + f'type="rss" xmlUrl="{html.escape(profil_feed_url(profil), quote=True)}" '
            + f'htmlUrl="https://www.instagram.com/{html.escape(profil)}/"/>'
        )

    opml = "\n".join([
        '<opml version="2.0">',
        '  <head>',
        '    <title>Instagram RSS feeds by profile</title>',
        f'    <dateCreated>{generated}</dateCreated>',
        '  </head>',
        '  <body>',
        '    <outline text="Instagram feeds by profile" title="Instagram feeds by profile">',
        *outlines,
        '    </outline>',
        '  </body>',
        '</opml>',
    ])

    skriv_fil(OPML_FIL_NY, opml)
    skriv_fil(OPML_FIL, opml)


def byg_og_gem_index(cache):
    profiler_med_posts = [profil for profil, posts in sorted(cache.get("posts", {}).items()) if posts]
    generated = datetime.now().strftime("%d-%m-%Y %H:%M")

    liste_items = []
    for profil in profiler_med_posts:
        antal_posts = min(len(cache["posts"][profil]), FEED_POSTS_PER_PROFIL)
        profil_link = public_relativ_sti(profil_feed_sti(profil))
        liste_items.append(
            "      <li>"
            + f'<a href="{html.escape(profil_link, quote=True)}">@{html.escape(profil)}</a> '
            + f'<span>({antal_posts} posts)</span>'
            + "</li>"
        )

    samlet_feed_link = public_relativ_sti(OUTPUT_FIL_NY)
    opml_link = public_relativ_sti(OPML_FIL_NY)

    html_indhold = "\n".join([
        '<!doctype html>',
        '<html lang="da">',
        '<head>',
        '  <meta charset="utf-8">',
        '  <meta name="viewport" content="width=device-width, initial-scale=1">',
        '  <title>Instagram RSS feeds</title>',
        '  <style>',
        '    body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; max-width: 820px; margin: 40px auto; padding: 0 16px; line-height: 1.5; }',
        '    h1, h2 { margin-bottom: 0.4rem; }',
        '    ul { padding-left: 1.2rem; }',
        '    li { margin: 0.35rem 0; }',
        '    code { background: #f3f3f3; padding: 0.15rem 0.35rem; border-radius: 4px; }',
        '  </style>',
        '</head>',
        '<body>',
        '  <h1>Instagram RSS feeds</h1>',
        f'  <p>Genereret {generated}.</p>',
        f'  <p><strong>Alt i én strøm:</strong> <a href="{html.escape(samlet_feed_link, quote=True)}">{html.escape(samlet_feed_link)}</a> <span>(tilføj som almindeligt feed)</span></p>',
        f'  <p><strong>Ét feed per profil:</strong> <a href="{html.escape(opml_link, quote=True)}">{html.escape(opml_link)}</a> <span>(importér som OPML)</span></p>',
        f'  <p><strong>Browser-viewer:</strong> Åbn et feed direkte i browseren, f.eks. <a href="{FEEDS_UNDERMAPPE}/scottkingstudio.xml">{FEEDS_UNDERMAPPE}/scottkingstudio.xml</a>.</p>',
        f'  <p>Alle publicerede filer ligger samlet i <code>{PUBLIC_MAPPE}/</code>.</p>',
        '  <h2>Profiler</h2>',
        '  <ul>',
        *liste_items,
        '  </ul>',
        '</body>',
        '</html>',
    ])

    skriv_fil(INDEX_FIL, html_indhold)


def byg_rss(alle_posts, kanal_titel, kanal_link, kanal_beskrivelse):
    rss = Element("rss", version="2.0")
    rss.set("xmlns:media", "http://search.yahoo.com/mrss/")
    rss.set("xmlns:content", "http://purl.org/rss/1.0/modules/content/")
    channel = SubElement(rss, "channel")

    SubElement(channel, "title").text = kanal_titel
    SubElement(channel, "link").text = kanal_link
    SubElement(channel, "description").text = kanal_beskrivelse
    SubElement(channel, "language").text = "da"

    alle_posts.sort(key=lambda p: p["dato"], reverse=True)

    for post in alle_posts:
        item = SubElement(channel, "item")

        SubElement(item, "title").text = byg_post_titel(post)
        SubElement(item, "link").text = post["url"]

        # Tilføj <video> tag til beskrivelsen hvis det er en video-post
        medie_type = post.get("medie_type", "billede")
        billede = post.get("billede")
        video_url = post.get("video")
        ressourcer = post.get("ressourcer") or []

        tekst = post["tekst"]
        if medie_type == "video" and video_url:
            video_html = f'<video controls style="max-width:100%;height:auto;" src="{html.escape(video_url)}"></video>'
            # Indsæt videoen i starten af teksten
            tekst = video_html + "\n" + tekst

        SubElement(item, "description").text = tekst
        SubElement(item, "content:encoded").text = tekst
        SubElement(item, "pubDate").text = post["dato"].strftime("%a, %d %b %Y %H:%M:%S +0000")
        SubElement(item, "guid").text = post["url"]
        SubElement(item, "author").text = post["profil"]
        SubElement(item, "category").text = f"instagram-{medie_type}"

        if medie_type == "video" and video_url:
            video_type = find_video_type(video_url)

            enclosure = SubElement(item, "enclosure")
            enclosure.set("url", video_url)
            enclosure.set("type", video_type)

            media = SubElement(item, "media:content")
            media.set("url", video_url)
            media.set("medium", "video")
            media.set("type", video_type)

            if billede:
                thumbnail = SubElement(item, "media:thumbnail")
                thumbnail.set("url", billede)

        elif medie_type == "slideshow" and ressourcer:
            media_group = SubElement(item, "media:group")
            for resource in ressourcer:
                if resource.get("type") == "video" and resource.get("video"):
                    media = SubElement(media_group, "media:content")
                    media.set("url", resource["video"])
                    media.set("medium", "video")
                    media.set("type", find_video_type(resource["video"]))
                elif resource.get("thumbnail"):
                    media = SubElement(media_group, "media:content")
                    media.set("url", resource["thumbnail"])
                    media.set("medium", "image")
                    media.set("type", find_billede_type(resource["thumbnail"]))

            if billede:
                thumbnail = SubElement(item, "media:thumbnail")
                thumbnail.set("url", billede)

        elif billede:
            billede_type = find_billede_type(billede)

            enclosure = SubElement(item, "enclosure")
            enclosure.set("url", billede)
            enclosure.set("type", billede_type)

            media = SubElement(item, "media:content")
            media.set("url", billede)
            media.set("medium", "image")
            media.set("type", billede_type)

            thumbnail = SubElement(item, "media:thumbnail")
            thumbnail.set("url", billede)

    xml_doc = minidom.parseString(tostring(rss, encoding="unicode"))

    for item_node, post in zip(xml_doc.getElementsByTagName("item"), alle_posts):
        html_indhold = byg_html_indhold(post)
        for tag_navn in ["description", "content:encoded"]:
            tag_nodes = item_node.getElementsByTagName(tag_navn)
            if not tag_nodes:
                continue

            tag_node = tag_nodes[0]
            while tag_node.firstChild:
                tag_node.removeChild(tag_node.firstChild)
            tag_node.appendChild(xml_doc.createCDATASection(html_indhold))

    xml_str = xml_doc.toprettyxml(indent="  ")
    linjer = xml_str.split("\n")
    return tilføj_xml_stylesheet("\n".join(linjer[1:]))


def tilføj_xml_stylesheet(xml_indhold):
    return f'<?xml-stylesheet type="text/xsl" href="{html.escape(stylesheet_url(), quote=True)}"?>\n{xml_indhold}'


def byg_post_titel(post, max_længde=80):
    """Lav en kort feed-titel uden at gentage profilnavnet."""
    tekst = " ".join((post.get("tekst") or "").split())
    if not tekst or tekst == "(ingen tekst)":
        return f"Post fra @{post['profil']}"

    return f"{tekst[:max_længde]}{'...' if len(tekst) > max_længde else ''}"


def byg_html_indhold(post):
    """Lav HTML fallback til RSS-læsere der kun viser billeder fra description/content."""
    tekst_html = html.escape(post["tekst"]).replace("\n", "<br/>\n")
    profil_html = html.escape(post["profil"])
    profil_label_html = f"<p><strong>@{profil_html}</strong></p>"
    medie_type = post.get("medie_type", "billede")
    billede = post.get("billede")
    video_url = post.get("video")
    ressourcer = post.get("ressourcer") or []

    badge_tekst = {
        "video": "🎬 Video",
        "slideshow": f"🖼️ Slideshow ({max(len(ressourcer), 1)} medier)",
        "billede": "📷 Billede",
    }.get(medie_type)

    if medie_type == "video":
        dele = []

        if billede:
            billede_url = html.escape(billede, quote=True)
            dele.append(
                f'<p><a href="{html.escape(post["url"], quote=True)}"><img src="{billede_url}" alt="Video-thumbnail fra @{profil_html}" /></a></p>'
            )

        if badge_tekst:
            dele.append(f"<p><strong>{html.escape(badge_tekst)}</strong></p>")

        dele.append(profil_label_html)
        dele.append(f"<p>{tekst_html}</p>")

        if video_url:
            dele.append(
                f'<p><a href="{html.escape(video_url, quote=True)}">▶️ Åbn video direkte</a> · '
                f'<a href="{html.escape(post["url"], quote=True)}">se på Instagram</a></p>'
            )
        else:
            dele.append(f'<p><a href="{html.escape(post["url"], quote=True)}">▶️ Se video på Instagram</a></p>')

        return "".join(dele)

    if medie_type == "slideshow" and ressourcer:
        dele = []
        preview_html = []
        for index, resource in enumerate(ressourcer[:4], start=1):
            if resource.get("thumbnail"):
                preview_html.append(
                    f'<img src="{html.escape(resource["thumbnail"], quote=True)}" '
                    f'alt="Slide {index} fra @{profil_html}" style="max-width: 48%; margin: 0 1% 8px 0;" />'
                )
            elif resource.get("video"):
                preview_html.append(
                    f'<p><a href="{html.escape(resource["video"], quote=True)}">▶️ Slide {index}: video</a></p>'
                )

        if preview_html:
            dele.append(f"<p>{''.join(preview_html)}</p>")

        if badge_tekst:
            dele.append(f"<p><strong>{html.escape(badge_tekst)}</strong></p>")

        dele.append(profil_label_html)
        dele.append(f"<p>{tekst_html}</p>")

        dele.append(f'<p><a href="{html.escape(post["url"], quote=True)}">Se slideshow på Instagram</a></p>')
        return "".join(dele)

    if billede:
        billede_url = html.escape(billede, quote=True)
        return (
            f'<p><img src="{billede_url}" alt="Instagram billede fra @{profil_html}" /></p>'
            f'{profil_label_html}'
            f'<p>{tekst_html}</p>'
        )

    return f"{profil_label_html}<p>{tekst_html}</p>"


def find_billede_type(billede_url):
    """Gæt MIME-type fra Instagram CDN-url, så RSS-læsere lettere kan vise billedet."""
    parsed = urlparse(billede_url)
    url_lower = billede_url.lower()

    if "dst-webp" in url_lower or parsed.path.lower().endswith(".webp"):
        return "image/webp"

    if any(markør in url_lower for markør in ["dst-jpg", "dst-jpeg", "dst-jpegr"]):
        return "image/jpeg"

    guessed_type, _ = mimetypes.guess_type(parsed.path)
    return guessed_type or "image/jpeg"


def find_video_type(video_url):
    parsed = urlparse(video_url)
    guessed_type, _ = mimetypes.guess_type(parsed.path)
    return guessed_type or "video/mp4"


def main():
    try:
        from instagrapi import Client
    except ImportError:
        print("❌ instagrapi er ikke installeret.")
        print("Kør: pip install instagrapi")
        exit(1)

    if not BRUGERNAVN or not ADGANGSKODE:
        print("❌ Mangler Instagram login-oplysninger.")
        print("Opret eller opdater .env med:")
        print("  INSTAGRAM_USERNAME=dit_brugernavn")
        print("  INSTAGRAM_PASSWORD=din_adgangskode")
        exit(1)

    start_idx = 0
    end_idx = None
    if len(sys.argv) > 1:
        try:
            start_idx = int(sys.argv[1])
            if len(sys.argv) > 2:
                end_idx = int(sys.argv[2])
            print(f"📦 Batch mode: Henter profiler {start_idx}-{end_idx if end_idx else 'slut'}")
        except ValueError:
            print("⚠️  Ugyldige argumenter. Brug: python instagram_rss.py [start] [slut]")
            print("Eksempel: python instagram_rss.py 0 50")
            exit(1)

    profiler = hent_profiler()

    if end_idx:
        profiler_batch = profiler[start_idx:end_idx]
        total_profiler = len(profiler)
    else:
        profiler_batch = profiler[start_idx:]
        total_profiler = len(profiler)

    if not profiler_batch:
        print(f"❌ Ingen profiler at hente i range {start_idx}-{end_idx}")
        exit(1)

    print(f"🎯 Vil hente {len(profiler_batch)} profiler (ud af {total_profiler} i alt)")

    cache = indlæs_cache()
    fast_mode = len(cache["posts"]) > 0

    if fast_mode:
        print("🚀 Cache fundet - kører i fast mode (kun nye posts)")
    else:
        print("🆕 Første kørsel - henter alle posts (kan tage lang tid)")

    # Filtrer profiler der blev hentet for nyligt
    nu = datetime.now(timezone.utc)
    profiler_at_hente = []
    profiler_springt_over = 0
    
    for brugernavn in profiler_batch:
        sidste_fetch = cache["last_fetch"].get(brugernavn)
        if sidste_fetch:
            tid_siden_sidste = (nu - sidste_fetch).total_seconds() / 3600  # timer
            if tid_siden_sidste < MIN_TIMER_MELLEM_HENTNINGER:
                profiler_springt_over += 1
                continue
        profiler_at_hente.append(brugernavn)
    
    if profiler_springt_over > 0:
        print(f"⏭️  Springer {profiler_springt_over} profiler over (hentet inden for {MIN_TIMER_MELLEM_HENTNINGER} timer)")
    
    if not profiler_at_hente:
        print("✅ Alle profiler er opdaterede - intet at hente")
        print("\n📝 Genererer feeds fra cache...")
        byg_og_gem_rss(cache)
        total_posts = sum(len(posts) for posts in cache.get("posts", {}).values())
        print(f"✅ Feeds opdateret fra cache med {total_posts} posts")
        return
    
    print(f"📥 Henter {len(profiler_at_hente)} profiler der skal opdateres")

    cl = hent_klient(fast_mode=fast_mode)

    nye_posts_count = 0
    profiler_hentet_total = len([p for p in cache["last_fetch"] if cache["last_fetch"][p]]) - len(profiler_at_hente)
    progress_file = Path("~/.sleepwatcher-jobs/instagram-rss.progress").expanduser()

    for idx, brugernavn in enumerate(profiler_at_hente, 1):
        profil_nr_total = profiler_hentet_total + idx
        
        # Skriv progress til fil så man kan tjekke status
        progress_file.write_text(f"{profil_nr_total}/{total_profiler} - Henter @{brugernavn}")
        
        print(f"\n📸 [{profil_nr_total}/{total_profiler}] Henter @{brugernavn} ({idx}/{len(profiler_at_hente)} i denne kørsel)...")
        sys.stdout.flush()  # Force output til log
        try:
            bruger_id = cl.user_id_from_username(brugernavn)
            medier = cl.user_medias(bruger_id, amount=POSTS_PER_PROFIL)

            sidste_fetch = cache["last_fetch"].get(brugernavn)

            if brugernavn not in cache["posts"]:
                cache["posts"][brugernavn] = []

            profil_nye_posts = 0
            seneste_dato = sidste_fetch

            for medie in medier:
                post_dato = medie.taken_at.replace(tzinfo=timezone.utc) if medie.taken_at.tzinfo is None else medie.taken_at
                post_url = f"https://www.instagram.com/p/{medie.code}/"
                medie_data = udtræk_post_medier(medie)

                cached_post = next(
                    (post for post in cache["posts"][brugernavn] if post.get("url") == post_url),
                    None,
                )

                if cached_post and cache_post_har_mangelfulde_medier(cached_post):
                    if berig_cache_post_medier(cached_post, medie_data):
                        print(f"  ♻️  Opdaterede mediedata for cachet post {post_url}")

                if sidste_fetch and post_dato <= sidste_fetch:
                    continue

                if not seneste_dato or post_dato > seneste_dato:
                    seneste_dato = post_dato

                tekst = medie.caption_text or "(ingen tekst)"

                post_data = {
                    "profil": brugernavn,
                    "tekst": tekst,
                    "url": post_url,
                    "dato": post_dato.isoformat(),
                    "billede": medie_data["billede"],
                    "video": medie_data["video"],
                    "medie_type": medie_data["medie_type"],
                    "ressourcer": medie_data["ressourcer"],
                }

                cache["posts"][brugernavn].insert(0, post_data)
                profil_nye_posts += 1

            cache["posts"][brugernavn] = cache["posts"][brugernavn][:50]
            cache["last_fetch"][brugernavn] = seneste_dato if seneste_dato else datetime.now(timezone.utc)
            nye_posts_count += profil_nye_posts

            gem_cache(cache)
            byg_og_gem_rss(cache)

            if profil_nye_posts > 0:
                print(f"  ✅ {profil_nye_posts} nye posts hentet og gemt")
            else:
                print(f"  ℹ️  Ingen nye posts (tjekket {len(medier)} posts)")

            if idx < len(profiler_at_hente):
                wait_time = (DELAY_MAX_FAST if fast_mode else DELAY_MAX_FIRST) + 2
                print(f"  ⏳ Venter {wait_time} sek. før næste profil...")
                time.sleep(wait_time)

        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "rate" in error_msg.lower():
                print(f"  ⚠️  Rate limit nået ved @{brugernavn}")
                print("  💤 Venter 60 sekunder før jeg prøver igen...")
                time.sleep(60)
            else:
                print(f"  ⚠️  Kunne ikke hente @{brugernavn}: {e}")

    print("\n📝 Genererer endelige feeds...")
    byg_og_gem_rss(cache)

    total_posts = sum(len(posts) for posts in cache.get("posts", {}).values())
    print(f"✅ Samlet feed opdateret: {OUTPUT_FIL_NY}")
    print(f"✅ Profil-feeds opdateret i: {FEEDS_MAPPE}/")
    print(f"✅ OPML-fil opdateret: {OPML_FIL_NY}")
    print(f"✅ Browser-oversigt opdateret: {INDEX_FIL}")
    print(f"   ├─ Total posts i cache: {total_posts}")
    if nye_posts_count > 0:
        print(f"   └─ Nye posts denne kørsel: {nye_posts_count}")
    print(f"\nℹ️  GitHub Pages oversigt: {PUBLIC_BASE_URL}/")

    if end_idx and end_idx < total_profiler:
        næste_slut = min(end_idx + (end_idx - start_idx), total_profiler)
        print(f"\n🔄 Næste batch: python instagram_rss.py {end_idx} {næste_slut}")


if __name__ == "__main__":
    main()
