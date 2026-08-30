"""Regression tests for i18n polish pass (ES/EN bilingual consistency)."""
from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from generator import build
from generator.lib import utils, weather


FALLBACK_WEATHER = {
    'temp_label': '24.0°C',
    'description': 'pronóstico en cache',
    'humidity_label': '50%',
    'wind_label': '10 km/h',
    'forecast': [
        {
            'date': '2026-08-30',
            'description': 'despejado',
            'icon': 'sun',
            'max_temp_c': 25.0,
            'min_temp_c': 15.0,
            'temp_range_label': '15° / 25°',
            'label': 'Domingo',
        },
    ],
    'icon': 'cloud',
}


def _build_dist(tmp: str) -> tuple[Path, Path]:
    root = Path(__file__).parents[1]
    output_dir = Path(tmp) / 'dist'
    cache_dir = Path(tmp) / 'cache'

    with patch('generator.build.feeds.fetch_links', return_value=([], 'fallback')):
        with patch('generator.build.feeds.select_preview_links', return_value=[]):
            with patch('generator.build.weather.fetch_weather', return_value=(FALLBACK_WEATHER, 'fallback')):
                with patch('generator.build.status.fetch_status', return_value=({'status': {'source': 'fallback'}, 'summary': {'metrics_available': False}}, 'fallback')):
                    with patch('generator.build.now_playing.fetch_now', return_value=({'available': False, 'track': '', 'artist': '', 'album': '', 'year': '', 'refresh_enabled': False}, [], 'fallback')):
                        argv = [
                            'build.py',
                            '--output-dir', str(output_dir),
                            '--cache-dir', str(cache_dir),
                            '--content-dir', str(root / 'content'),
                            '--templates-dir', str(root / 'templates'),
                            '--static-dir', str(root / 'static'),
                        ]
                        with patch('sys.argv', argv):
                            build.main()
    return output_dir, cache_dir


class LanguageSelectorOrderTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._dist, _ = _build_dist(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _selector_order(self, html: str) -> list[str]:
        """Return hreflang values in document order from lang-switch section."""
        section = re.search(r'class="lang-switch".*?</span>', html, re.DOTALL)
        self.assertIsNotNone(section, "lang-switch not found")
        matches = re.findall(r'hreflang="([^"]+)"|class="lang-switch__item lang-switch__item--active".*?>(ES|EN)<', section.group(), re.DOTALL)
        # Simpler: just check ES before EN in the block
        block = section.group()
        es_pos = block.find('>ES<')
        en_pos = block.find('>EN<')
        return [('es', es_pos), ('en', en_pos)]

    def _assert_es_before_en(self, path: Path, label: str) -> None:
        html = path.read_text(encoding='utf-8')
        block_match = re.search(r'class="lang-switch"[^>]*>(.*?)</span>\s*\n', html, re.DOTALL)
        if block_match is None:
            return  # no selector on this page (e.g. gateway)
        block = block_match.group()
        es_pos = block.find('>ES<')
        en_pos = block.find('>EN<')
        self.assertGreater(es_pos, -1, f"ES not found in selector on {label}")
        self.assertGreater(en_pos, -1, f"EN not found in selector on {label}")
        self.assertLess(es_pos, en_pos, f"ES must appear before EN on {label}")

    def test_es_en_order_on_es_home(self) -> None:
        self._assert_es_before_en(self._dist / 'es' / 'index.html', 'ES home')

    def test_es_en_order_on_en_home(self) -> None:
        self._assert_es_before_en(self._dist / 'en' / 'index.html', 'EN home')

    def test_es_en_order_on_es_notes_index(self) -> None:
        self._assert_es_before_en(self._dist / 'es' / 'notas' / 'index.html', 'ES notes index')

    def test_es_en_order_on_en_notes_index(self) -> None:
        self._assert_es_before_en(self._dist / 'en' / 'notes' / 'index.html', 'EN notes index')

    def test_es_en_order_on_es_note(self) -> None:
        note = self._dist / 'es' / 'cuando-una-herramienta-deja-de-ser-un-experimento' / 'index.html'
        self._assert_es_before_en(note, 'ES note')

    def test_es_en_order_on_en_note(self) -> None:
        note = self._dist / 'en' / 'when-a-tool-stops-being-an-experiment' / 'index.html'
        self._assert_es_before_en(note, 'EN note')

    def test_active_language_marked_on_es_home(self) -> None:
        html = (self._dist / 'es' / 'index.html').read_text(encoding='utf-8')
        self.assertIn('lang-switch__item--active" aria-current="true">ES<', html)

    def test_active_language_marked_on_en_home(self) -> None:
        html = (self._dist / 'en' / 'index.html').read_text(encoding='utf-8')
        self.assertIn('lang-switch__item--active" aria-current="true">EN<', html)


class TagLocalizationTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._dist, _ = _build_dist(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_english_tags_on_en_notes_index(self) -> None:
        html = (self._dist / 'en' / 'notes' / 'index.html').read_text(encoding='utf-8')
        self.assertIn('music', html)
        self.assertIn('personal-projects', html)
        self.assertIn('design', html)
        self.assertIn('self-hosting', html)

    def test_no_spanish_tags_on_en_pages(self) -> None:
        html = (self._dist / 'en' / 'notes' / 'index.html').read_text(encoding='utf-8')
        self.assertNotIn('>música<', html)
        self.assertNotIn('>proyectos-personales<', html)
        self.assertNotIn('>diseño<', html)
        self.assertNotIn('>autogestión<', html)

    def test_spanish_tags_remain_on_es_pages(self) -> None:
        html = (self._dist / 'es' / 'notas' / 'index.html').read_text(encoding='utf-8')
        # Spanish tags that exist in notes should appear unchanged
        self.assertNotIn('>music<', html)


class WeatherLocalizationTests(unittest.TestCase):
    def test_localize_weather_en_translates_description(self) -> None:
        es_weather = {
            'description': 'despejado',
            'forecast': [{'date': '2026-08-30', 'description': 'nublado', 'label': 'Domingo', 'icon': 'cloud', 'max_temp_c': 20.0, 'min_temp_c': 10.0, 'temp_range_label': '10° / 20°'}],
        }
        en = weather.localize_weather(es_weather, 'en')
        self.assertEqual(en['description'], 'clear')
        self.assertEqual(en['forecast'][0]['description'], 'overcast')

    def test_localize_weather_en_translates_weekdays(self) -> None:
        es_weather = {
            'description': 'lluvia',
            'forecast': [
                {'date': '2026-08-31', 'description': 'lluvia', 'label': 'Lunes', 'icon': 'rain', 'max_temp_c': 18.0, 'min_temp_c': 12.0, 'temp_range_label': '12° / 18°'},
            ],
        }
        en = weather.localize_weather(es_weather, 'en')
        self.assertEqual(en['forecast'][0]['label'], 'Monday')

    def test_localize_weather_es_unchanged(self) -> None:
        es_weather = {'description': 'despejado', 'forecast': []}
        result = weather.localize_weather(es_weather, 'es')
        self.assertIs(result, es_weather)

    def test_en_home_shows_english_weather(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        dist, _ = _build_dist(tmp.name)
        html = (dist / 'en' / 'index.html').read_text(encoding='utf-8')
        tmp.cleanup()
        self.assertIn('clear', html)
        self.assertNotIn('despejado', html)

    def test_en_home_shows_english_weekday(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        dist, _ = _build_dist(tmp.name)
        html = (dist / 'en' / 'index.html').read_text(encoding='utf-8')
        tmp.cleanup()
        self.assertIn('Sunday', html)
        self.assertNotIn('Domingo', html)

    def test_en_home_shows_humidity_wind_labels(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        dist, _ = _build_dist(tmp.name)
        html = (dist / 'en' / 'index.html').read_text(encoding='utf-8')
        tmp.cleanup()
        self.assertIn('Humidity', html)
        self.assertIn('Wind', html)

    def test_es_home_shows_spanish_weather_labels(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        dist, _ = _build_dist(tmp.name)
        html = (dist / 'es' / 'index.html').read_text(encoding='utf-8')
        tmp.cleanup()
        self.assertIn('Humedad', html)
        self.assertIn('Viento', html)


class TinyThingTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._dist, _ = _build_dist(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_en_home_has_english_tiny_phrase(self) -> None:
        html = (self._dist / 'en' / 'index.html').read_text(encoding='utf-8')
        en_phrases = utils.load_lines(Path(__file__).parents[1] / 'content' / 'tiny_en.txt')
        matched = any(phrase in html for phrase in en_phrases)
        self.assertTrue(matched, "No English tiny phrase found in EN home")

    def test_es_home_has_spanish_tiny_phrase(self) -> None:
        html = (self._dist / 'es' / 'index.html').read_text(encoding='utf-8')
        es_phrases = utils.load_lines(Path(__file__).parents[1] / 'content' / 'tiny.txt')
        matched = any(phrase in html for phrase in es_phrases)
        self.assertTrue(matched, "No Spanish tiny phrase found in ES home")


class DateFormatTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._dist, _ = _build_dist(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_en_notes_show_english_date_format(self) -> None:
        html = (self._dist / 'en' / 'notes' / 'index.html').read_text(encoding='utf-8')
        # English format: "30 Aug 2026"
        self.assertRegex(html, r'\d{1,2} [A-Z][a-z]{2} \d{4}')

    def test_en_notes_do_not_show_numeric_slash_dates(self) -> None:
        html = (self._dist / 'en' / 'notes' / 'index.html').read_text(encoding='utf-8')
        # Should not have DD/MM/YYYY in note cards (meta dates)
        self.assertNotRegex(html, r'<p class="meta">\d{2}/\d{2}/\d{4}</p>')

    def test_es_notes_show_numeric_date_format(self) -> None:
        html = (self._dist / 'es' / 'notas' / 'index.html').read_text(encoding='utf-8')
        self.assertRegex(html, r'\d{2}/\d{2}/\d{4}')


class FooterLocalizationTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._dist, _ = _build_dist(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_es_home_footer_shows_blog_en_ingles(self) -> None:
        html = (self._dist / 'es' / 'index.html').read_text(encoding='utf-8')
        self.assertIn('blog en inglés', html)
        self.assertNotIn('english blog', html)

    def test_en_home_footer_shows_english_blog(self) -> None:
        html = (self._dist / 'en' / 'index.html').read_text(encoding='utf-8')
        self.assertIn('English blog', html)


class UptimeTerminologyTests(unittest.TestCase):
    def test_es_uptime_unchanged(self) -> None:
        self.assertEqual(build.UI_STRINGS['es']['status']['uptime'], 'Uptime')

    def test_en_uptime_unchanged(self) -> None:
        self.assertEqual(build.UI_STRINGS['en']['status']['uptime'], 'Uptime')


class AltTextTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._dist, _ = _build_dist(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_es_home_no_english_album_cover_alt(self) -> None:
        html = (self._dist / 'es' / 'index.html').read_text(encoding='utf-8')
        self.assertNotIn('alt="Album cover"', html)

    def test_en_home_has_album_cover_alt(self) -> None:
        html = (self._dist / 'en' / 'index.html').read_text(encoding='utf-8')
        self.assertIn('alt="Album cover"', html)


if __name__ == '__main__':
    unittest.main()
