from __future__ import annotations

import re
import unittest
from pathlib import Path


class NginxRootRoutingTests(unittest.TestCase):
    def test_root_language_regex_recognizes_primary_spanish_tags(self) -> None:
        config = (Path(__file__).parents[1] / 'nginx' / 'nico.com.ar.conf').read_text(encoding='utf-8')
        match = re.search(r"if \(\$http_accept_language ~\* '([^']+)'\)", config)
        self.assertIsNotNone(match)
        pattern = re.compile(match.group(1), re.IGNORECASE)

        cases = {
            'es-AR,es;q=0.9,en;q=0.8': True,
            'es-419,es;q=0.9,en;q=0.8': True,
            'es': True,
            'en-US,en;q=0.9,es;q=0.8': False,
            'fr-FR,fr;q=0.9,es;q=0.8': False,
            '': False,
        }

        for header, expected in cases.items():
            with self.subTest(header=header):
                self.assertEqual(bool(pattern.search(header)), expected)


if __name__ == '__main__':
    unittest.main()
