from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from generator import build


class LocalBuildOfflineTests(unittest.TestCase):
    def test_local_build_uses_offline_runtime_data_only(self) -> None:
        root = Path(__file__).parents[1]
        with tempfile.TemporaryDirectory() as temporary:
            output_dir = Path(temporary) / 'dist'
            cache_dir = Path(temporary) / 'cache'
            env = {
                'NICO_BUILD_LOCAL_ONLY': '1',
            }

            with patch.dict('os.environ', env, clear=False):
                with patch('generator.build.feeds.fetch_links', side_effect=AssertionError('feeds fetch must stay offline')):
                    with patch('generator.build.weather.fetch_weather', wraps=build.weather.fetch_weather) as weather_fetch:
                        with patch('generator.build.status.fetch_status', return_value=({'status': {'source': 'local'}, 'summary': {'metrics_available': False}}, 'local')):
                            with patch('generator.build.now_playing.requests.get', side_effect=AssertionError('now-playing fetch must stay offline')):
                                with patch('generator.build.weather.requests.get', side_effect=AssertionError('weather fetch must stay offline')):
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

            localized_home = (output_dir / 'en' / 'index.html').read_text(encoding='utf-8')
            self.assertIn('Warm Breeze', localized_home)
            self.assertIn('pronóstico en cache', localized_home)
            self.assertTrue(weather_fetch.called)


if __name__ == '__main__':
    unittest.main()
