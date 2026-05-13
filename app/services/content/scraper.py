import asyncio
import httpx
from typing import List, Optional
from bs4 import BeautifulSoup
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound


class ContentScraper:
    """
    Scrapes language learning content from multiple free sources:

    1. YouTube subtitles   — documentaries, language lessons, cultural content
    2. Wikipedia           — encyclopedic content in any language
    3. Generic web pages   — any URL with readable text

    All content is returned as plain text chunks ready for embedding.
    No API keys required — all sources are free.
    """

    def __init__(self):
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }

    # ── YOUTUBE ───────────────────────────────────────────────────────────────

    async def scrape_youtube(
        self,
        video_id:      str,
        language_code: str = "en",
    ) -> Optional[dict]:
        """
        Fetches subtitles from a YouTube video.
        No API key needed — uses public subtitle endpoint.

        Args:
            video_id      — the YouTube video ID e.g. "dQw4w9WgXcQ"
                            (the part after ?v= in the URL)
            language_code — ISO code of the subtitle language to fetch

        Returns dict:
            {
                "title":       "Video title",
                "text":        "Full transcript text...",
                "source_url":  "https://youtube.com/watch?v=...",
                "source_type": "youtube",
                "chunks":      ["chunk1", "chunk2", ...]
            }
        """
        try:
            loop = asyncio.get_event_loop()

            # Run in thread pool — youtube_transcript_api is synchronous
            transcript_list = await loop.run_in_executor(
                None,
                lambda: YouTubeTranscriptApi.get_transcript(
                    video_id,
                    languages=[language_code, "en"],
                )
            )

            # Join all subtitle segments into one text
            full_text = " ".join(
                segment["text"] for segment in transcript_list
            ).strip()

            if not full_text:
                return None

            return {
                "title":       f"YouTube Video {video_id}",
                "text":        full_text,
                "source_url":  f"https://www.youtube.com/watch?v={video_id}",
                "source_type": "youtube",
                "chunks":      self._chunk_text(full_text),
            }

        except (TranscriptsDisabled, NoTranscriptFound):
            print(f"[Scraper] No subtitles for YouTube video: {video_id}")
            return None
        except Exception as e:
            print(f"[Scraper] YouTube error for {video_id}: {e}")
            return None

    # ── WIKIPEDIA ─────────────────────────────────────────────────────────────

    async def scrape_wikipedia(
        self,
        topic:         str,
        language_code: str = "en",
    ) -> Optional[dict]:
        """
        Fetches a Wikipedia article about a topic.
        Wikipedia has articles in 300+ languages — perfect for your platform.

        Args:
            topic         — search term e.g. "Yoruba language", "French cuisine"
            language_code — Wikipedia subdomain e.g. "fr", "yo", "sw", "en"

        Returns same dict format as scrape_youtube.
        """
        try:
            # Wikipedia API endpoint
            api_url = f"https://{language_code}.wikipedia.org/w/api.php"
            params  = {
                "action":      "query",
                "format":      "json",
                "titles":      topic,
                "prop":        "extracts",
                "exintro":     True,     # only intro section for conciseness
                "explaintext": True,     # plain text, no HTML
                "redirects":   True,
            }

            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    api_url, params=params, headers=self.headers
                )
                resp.raise_for_status()
                data = resp.json()

            pages = data.get("query", {}).get("pages", {})
            if not pages:
                return None

            page    = next(iter(pages.values()))
            extract = page.get("extract", "")
            title   = page.get("title", topic)

            if not extract or len(extract) < 100:
                return None

            return {
                "title":       title,
                "text":        extract,
                "source_url":  f"https://{language_code}.wikipedia.org/wiki/{title.replace(' ', '_')}",
                "source_type": "wikipedia",
                "chunks":      self._chunk_text(extract),
            }

        except Exception as e:
            print(f"[Scraper] Wikipedia error for '{topic}': {e}")
            return None

    # ── GENERIC WEB PAGE ──────────────────────────────────────────────────────

    async def scrape_url(self, url: str) -> Optional[dict]:
        """
        Scrapes readable text from any web page.
        Strips HTML tags, navigation, ads, and returns clean body text.

        Args:
            url — full URL including https://

        Returns same dict format.
        """
        try:
            async with httpx.AsyncClient(
                timeout=20, follow_redirects=True
            ) as client:
                resp = await client.get(url, headers=self.headers)
                resp.raise_for_status()
                html = resp.text

            soup  = BeautifulSoup(html, "lxml")

            # Remove script, style, nav, footer tags
            for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                tag.decompose()

            # Get clean text
            text = soup.get_text(separator=" ", strip=True)
            text = " ".join(text.split())  # collapse whitespace

            if len(text) < 100:
                return None

            # Try to get page title
            title_tag = soup.find("title")
            title     = title_tag.get_text().strip() if title_tag else url

            return {
                "title":       title,
                "text":        text[:50000],  # cap at 50k chars
                "source_url":  url,
                "source_type": "website",
                "chunks":      self._chunk_text(text),
            }

        except Exception as e:
            print(f"[Scraper] URL error for {url}: {e}")
            return None

    # ── BATCH SCRAPING ────────────────────────────────────────────────────────

    async def scrape_language_content(
        self,
        language_name: str,
        language_code: str,
        youtube_ids:   List[str] = None,
        wiki_topics:   List[str] = None,
        extra_urls:    List[str] = None,
    ) -> List[dict]:
        """
        Scrapes all content sources for a language at once.
        Called when a new language is added to the platform.

        Returns a flat list of content dicts ready for embedding.
        """
        results = []

        # Default Wikipedia topics if none provided
        if not wiki_topics:
            wiki_topics = [
                f"{language_name} language",
                f"{language_name} culture",
                f"{language_name} grammar",
                f"History of {language_name}",
            ]

        # Scrape Wikipedia articles
        for topic in wiki_topics:
            content = await self.scrape_wikipedia(topic, language_code)
            if content:
                results.append(content)
                print(f"[Scraper] ✅ Wikipedia: {topic}")

        # Scrape YouTube videos
        if youtube_ids:
            for vid_id in youtube_ids:
                content = await self.scrape_youtube(vid_id, language_code)
                if content:
                    results.append(content)
                    print(f"[Scraper] ✅ YouTube: {vid_id}")

        # Scrape extra URLs
        if extra_urls:
            for url in extra_urls:
                content = await self.scrape_url(url)
                if content:
                    results.append(content)
                    print(f"[Scraper] ✅ URL: {url}")

        print(f"[Scraper] Done — {len(results)} sources scraped for {language_name}")
        return results

    # ── TEXT CHUNKING ─────────────────────────────────────────────────────────

    def _chunk_text(
        self,
        text:       str,
        chunk_size: int = 500,
        overlap:    int = 50,
    ) -> List[str]:
        """
        Splits a long text into overlapping chunks.

        Why chunks?
          - Embedding models have a token limit (~512 tokens)
          - Smaller chunks = more precise retrieval
          - Overlap = no context lost at chunk boundaries

        Args:
            text       — the full text to split
            chunk_size — target words per chunk
            overlap    — words shared between consecutive chunks

        Returns list of text chunks.
        """
        words  = text.split()
        chunks = []
        start  = 0

        while start < len(words):
            end   = min(start + chunk_size, len(words))
            chunk = " ".join(words[start:end])
            if len(chunk.strip()) > 50:  # skip tiny chunks
                chunks.append(chunk)
            start += chunk_size - overlap

        return chunks


# Single instance
content_scraper = ContentScraper()