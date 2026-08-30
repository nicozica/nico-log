from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from generator import build


class GeneratorBuildTests(unittest.TestCase):
    def test_build_generates_localized_routes_and_metadata(self) -> None:
        root = Path(__file__).parents[1]
        with tempfile.TemporaryDirectory() as temporary:
            output_dir = Path(temporary) / 'dist'
            cache_dir = Path(temporary) / 'cache'

            with patch('generator.build.feeds.fetch_links', return_value=([], 'fallback')):
                with patch('generator.build.feeds.select_preview_links', return_value=[]):
                    with patch('generator.build.weather.fetch_weather', return_value=({'temp_label': '18C', 'description': 'Templado', 'humidity_label': '50%', 'wind_label': '10 km/h', 'forecast': [], 'icon': 'sun'}, 'fallback')):
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

            es_note = output_dir / 'es' / 'cuando-una-herramienta-deja-de-ser-un-experimento' / 'index.html'
            en_note = output_dir / 'en' / 'when-a-tool-stops-being-an-experiment' / 'index.html'
            legacy_note = output_dir / 'notes' / 'cuando-una-herramienta-deja-de-ser-un-experimento' / 'index.html'
            self.assertTrue((output_dir / 'es' / 'index.html').is_file())
            self.assertTrue((output_dir / 'en' / 'index.html').is_file())
            self.assertTrue((output_dir / 'es' / 'notas' / 'index.html').is_file())
            self.assertTrue((output_dir / 'en' / 'notes' / 'index.html').is_file())
            self.assertTrue((output_dir / 'es' / 'noticias' / 'index.html').is_file())
            self.assertTrue((output_dir / 'en' / 'news' / 'index.html').is_file())
            self.assertTrue((output_dir / 'es' / 'acerca' / 'index.html').is_file())
            self.assertTrue((output_dir / 'en' / 'about' / 'index.html').is_file())
            self.assertTrue(es_note.is_file())
            self.assertTrue(en_note.is_file())
            self.assertTrue(legacy_note.is_file())

            es_html = es_note.read_text(encoding='utf-8')
            en_html = en_note.read_text(encoding='utf-8')
            legacy_html = legacy_note.read_text(encoding='utf-8')
            feed_xml = (output_dir / 'notes' / 'rss.xml').read_text(encoding='utf-8')
            root_html = (output_dir / 'index.html').read_text(encoding='utf-8')

            self.assertIn('<html lang="es"', es_html)
            self.assertIn('href="https://www.nico.com.ar/es/cuando-una-herramienta-deja-de-ser-un-experimento/"', es_html)
            self.assertIn('hreflang="en"', es_html)
            self.assertIn('Read in English', es_html)
            self.assertIn('Cuando una herramienta deja de ser un experimento', es_html)

            self.assertIn('<html lang="en"', en_html)
            self.assertIn('href="https://www.nico.com.ar/en/when-a-tool-stops-being-an-experiment/"', en_html)
            self.assertIn('hreflang="es"', en_html)
            self.assertIn('Originally written in Spanish.', en_html)
            self.assertIn('This is a provisional English adaptation of the original Spanish note.', en_html)

            self.assertIn('content="0; url=/es/cuando-una-herramienta-deja-de-ser-un-experimento/"', legacy_html)
            self.assertIn('/es/cuando-una-herramienta-deja-de-ser-un-experimento/', feed_xml)
            self.assertIn('hreflang="x-default"', root_html)
            self.assertIn('/es/', root_html)
            self.assertIn('/en/', root_html)


if __name__ == '__main__':
    unittest.main()
