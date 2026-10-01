# ArchScope V4

A research-first architecture discovery prototype inspired by common architecture-library workflows, without copying any publisher's branding or proprietary catalogue.

## Run

Python 3.10+

```bash
pip install flask requests
python app.py
```

Open http://127.0.0.1:5000

## Live search
Create a `.env`/environment variable:

```text
BRAVE_API_KEY=your_key
```

Then run the app. Without the key, the local demonstration catalogue still works.

## V4 architecture
- Project-first catalogue
- Project detail + asset grouping
- Web/image search endpoint
- Drawing/photo/detail classification hook
- Local research board using browser storage
- Source attribution preserved

## Next production steps
- PostgreSQL project/asset schema
- PDF ingestion + page extraction
- Vision model classification
- OCR for drawing labels/dimensions
- Licensed/open image handling
- User accounts and cloud boards
