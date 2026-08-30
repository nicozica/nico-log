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

    def test_published_archive_has_explicit_bilingual_metadata_and_pairing(self) -> None:
        repo_notes_dir = Path(__file__).parents[1] / 'content' / 'notes'
        raw_files = sorted(repo_notes_dir.glob('*.md'))
        self.assertEqual(len(raw_files), 30)
        for path in raw_files:
            raw = path.read_text(encoding='utf-8')
            self.assertIn('note_id:', raw)
            self.assertIn('lang:', raw)
            self.assertIn('slug:', raw)

        loaded = notes.load_notes(repo_notes_dir, site_domain='https://www.nico.com.ar')
        self.assertEqual(len(loaded), 30)
        self.assertEqual(sum(1 for note in loaded if note['language'] == 'es'), 15)
        self.assertEqual(sum(1 for note in loaded if note['language'] == 'en'), 15)
        self.assertEqual(len({(note['note_id'], note['language']) for note in loaded}), len(loaded))
        self.assertEqual(len({(note['language'], note['slug']) for note in loaded}), len(loaded))

        for note_id in {note['note_id'] for note in loaded}:
            langs = {note['language'] for note in loaded if note['note_id'] == note_id}
            self.assertEqual(langs, {'es', 'en'})

        for note in loaded:
            if note['language'] == 'es':
                self.assertIsNotNone(note['translation'])
                self.assertIsNone(note['original'])
            else:
                self.assertIsNotNone(note['original'])
                self.assertIsNotNone(note['translation'])
                self.assertEqual(note['translation']['language'], 'es')


if __name__ == '__main__':
    unittest.main()
