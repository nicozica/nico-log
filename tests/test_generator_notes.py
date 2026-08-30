from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from generator.lib import notes


class GeneratorNotesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.notes_dir = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_note(self, filename: str, content: str) -> None:
        (self.notes_dir / filename).write_text(content, encoding='utf-8')

    def test_pairs_translations_and_localized_paths(self) -> None:
        self.write_note(
            '2026-08-10-nota-es.md',
            """---
title: Nota original
date: 2026-08-10
slug: nota-original
---

Hola mundo.
""",
        )
        self.write_note(
            '2026-08-10-note-en.md',
            """---
note_id: 2026-08-10-nota-es
lang: en
title: Original note
date: 2026-08-10
slug: original-note
---

Hello world.
""",
        )

        loaded = notes.load_notes(self.notes_dir, site_domain='https://www.nico.com.ar')
        spanish = next(note for note in loaded if note['language'] == 'es')
        english = next(note for note in loaded if note['language'] == 'en')

        self.assertEqual(spanish['path'], '/es/nota-original/')
        self.assertEqual(english['path'], '/en/original-note/')
        self.assertEqual(spanish['translation']['path'], '/en/original-note/')
        self.assertEqual(english['original']['path'], '/es/nota-original/')

    def test_missing_translation_keeps_link_empty(self) -> None:
        self.write_note(
            '2026-08-10-nota-es.md',
            """---
title: Nota original
date: 2026-08-10
slug: nota-original
---

Hola mundo.
""",
        )

        loaded = notes.load_notes(self.notes_dir, site_domain='https://www.nico.com.ar')
        spanish = loaded[0]
        self.assertIsNone(spanish['translation'])
        self.assertIsNone(spanish['original'])

    def test_reserved_slug_is_rejected(self) -> None:
        self.write_note(
            '2026-08-10-news.md',
            """---
lang: en
title: Bad
date: 2026-08-10
slug: news
---

Body.
""",
        )

        with self.assertRaises(ValueError):
            notes.load_notes(self.notes_dir, site_domain='https://www.nico.com.ar')

    def test_same_slug_is_allowed_across_languages(self) -> None:
        self.write_note(
            '2026-08-10-nota-es.md',
            """---
title: Igual
date: 2026-08-10
slug: compartido
---

Hola.
""",
        )
        self.write_note(
            '2026-08-10-note-en.md',
            """---
lang: en
title: Same
date: 2026-08-10
slug: compartido
---

Hello.
""",
        )

        loaded = notes.load_notes(self.notes_dir, site_domain='https://www.nico.com.ar')
        self.assertEqual({note['path'] for note in loaded}, {'/es/compartido/', '/en/compartido/'})


if __name__ == '__main__':
    unittest.main()
