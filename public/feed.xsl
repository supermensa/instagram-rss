<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:media="http://search.yahoo.com/mrss/"
  xmlns:content="http://purl.org/rss/1.0/modules/content/"
  exclude-result-prefixes="media content">

  <xsl:output method="html" encoding="UTF-8" indent="yes"/>

  <xsl:template match="/rss">
    <html lang="da">
      <head>
        <meta charset="utf-8"/>
        <meta name="viewport" content="width=device-width, initial-scale=1"/>
        <title><xsl:value-of select="channel/title"/></title>
        <style>
          :root {
            color-scheme: light dark;
            --bg: #faf8f5;
            --card: #ffffff;
            --text: #1f2328;
            --muted: #6b7280;
            --border: #e5e7eb;
            --accent: #d9485f;
          }
          @media (prefers-color-scheme: dark) {
            :root {
              --bg: #111318;
              --card: #171a21;
              --text: #f3f4f6;
              --muted: #9ca3af;
              --border: #2b3140;
              --accent: #ff6b81;
            }
          }
          * { box-sizing: border-box; }
          body {
            margin: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.5;
          }
          .wrap {
            max-width: 920px;
            margin: 0 auto;
            padding: 24px 16px 48px;
          }
          header {
            margin-bottom: 24px;
            padding: 20px;
            border: 1px solid var(--border);
            border-radius: 18px;
            background: linear-gradient(135deg, rgba(217,72,95,0.12), rgba(217,72,95,0.02));
          }
          h1, h2, h3, p { margin: 0; }
          h1 { font-size: clamp(1.8rem, 4vw, 2.6rem); margin-bottom: 10px; }
          .meta { color: var(--muted); margin-top: 8px; }
          .links { margin-top: 14px; font-size: 0.95rem; }
          .links a, .item a { color: var(--accent); text-decoration: none; }
          .links a:hover, .item a:hover { text-decoration: underline; }
          .item {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 18px;
            padding: 18px;
            margin-bottom: 18px;
            box-shadow: 0 8px 22px rgba(0,0,0,0.04);
          }
          .topline {
            display: flex;
            flex-wrap: wrap;
            gap: 8px 12px;
            align-items: center;
            margin-bottom: 10px;
          }
          .badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 999px;
            background: rgba(217,72,95,0.14);
            color: var(--accent);
            font-size: 0.8rem;
            font-weight: 600;
          }
          .author, .date {
            color: var(--muted);
            font-size: 0.92rem;
          }
          .title {
            font-size: 1.15rem;
            margin-bottom: 12px;
          }
          .preview {
            margin: 12px 0;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 12px;
          }
          .preview img {
            width: 100%;
            height: auto;
            border-radius: 14px;
            border: 1px solid var(--border);
            display: block;
            background: #00000010;
          }
          .summary {
            color: var(--text);
          }
          .summary p {
            margin: 0 0 12px;
          }
          .summary img {
            width: 100%;
            height: auto;
            border-radius: 14px;
            border: 1px solid var(--border);
            display: block;
          }
          .summary a {
            color: var(--accent);
          }
          .footer-note {
            margin-top: 30px;
            color: var(--muted);
            font-size: 0.9rem;
          }
          code {
            font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
            padding: 0.1rem 0.35rem;
            background: rgba(127,127,127,0.12);
            border-radius: 6px;
          }
        </style>
      </head>
      <body>
        <div class="wrap">
          <header>
            <h1><xsl:value-of select="channel/title"/></h1>
            <p><xsl:value-of select="channel/description"/></p>
            <p class="meta">Denne browser-visning kommer fra <code>feed.xsl</code>. Selve RSS-feedet virker stadig normalt i RSS-læsere.</p>
            <p class="links">
              <a href="{channel/link}">Åbn kilde</a>
            </p>
          </header>

          <xsl:for-each select="channel/item">
            <article class="item">
              <div class="topline">
                <span class="badge"><xsl:value-of select="category"/></span>
                <span class="author">@<xsl:value-of select="author"/></span>
                <span class="date"><xsl:value-of select="pubDate"/></span>
              </div>

              <h2 class="title">
                <a href="{link}"><xsl:value-of select="title"/></a>
              </h2>

              <xsl:if test="not(contains(string(content:encoded), '&lt;img') or contains(string(description), '&lt;img'))">
                <div class="preview">
                  <xsl:choose>
                    <xsl:when test="media:group/media:content[@medium='image']">
                      <xsl:for-each select="media:group/media:content[@medium='image'][position() &lt;= 4]">
                        <img src="{@url}" alt="Slideshow preview"/>
                      </xsl:for-each>
                    </xsl:when>
                    <xsl:when test="media:thumbnail/@url">
                      <img src="{media:thumbnail/@url}" alt="Thumbnail"/>
                    </xsl:when>
                    <xsl:when test="enclosure/@url and starts-with(enclosure/@type, 'image/')">
                      <img src="{enclosure/@url}" alt="Billede"/>
                    </xsl:when>
                  </xsl:choose>
                </div>
              </xsl:if>

              <div class="summary">
                <xsl:choose>
                  <xsl:when test="content:encoded">
                    <xsl:value-of select="content:encoded" disable-output-escaping="yes"/>
                  </xsl:when>
                  <xsl:otherwise>
                    <xsl:value-of select="description" disable-output-escaping="yes"/>
                  </xsl:otherwise>
                </xsl:choose>
              </div>

              <p class="links" style="margin-top: 12px;">
                <a href="{link}">Se på Instagram</a>
                <xsl:if test="enclosure/@url and starts-with(enclosure/@type, 'video/')">
                  <xsl:text> · </xsl:text>
                  <a href="{enclosure/@url}">Åbn video</a>
                </xsl:if>
              </p>
            </article>
          </xsl:for-each>

          <p class="footer-note">
            Hvis du vil abonnere i en RSS-læser, så brug feed-URL'en direkte i stedet for browser-visningen.
          </p>
        </div>
      </body>
    </html>
  </xsl:template>
</xsl:stylesheet>
