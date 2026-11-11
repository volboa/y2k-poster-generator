# Private Y2K Album Poster Generator

Produces three 8 × 10 inch scrapbook poster variations for each row of `albums.csv`, with 2400 × 3000 PNGs tagged 300 DPI and matching PDF exports.

## Browser-only GitHub setup

1. Go to https://github.com/new and create a **Private** repository named `y2k-poster-generator` (no README needed).
2. Download and unzip this starter project. On the GitHub repository page, choose **Add file → Upload files** and upload the contents of the extracted folder, including `.github/workflows/generate.yml`. **Note:** Some browsers hide dotfolders. If so, create `.github/workflows/generate.yml` in GitHub via **Add file → Create new file** and paste the workflow text from the archive.
3. Commit the files to the default branch.
4. Select **Actions** and enable workflows if prompted. Open **Generate private Y2K posters**, then **Run workflow**.
5. Wait for the run to finish. Open the completed run and download `y2k-posters` from **Artifacts**.
6. Unzip the artifact to get three PNGs, three PDFs, and a JSON file recording photo sources.
7. To add more albums, edit `albums.csv` using GitHub's pencil icon and commit. This also triggers generation.

## Optional AI backgrounds

Without any API key, the generator makes original procedural scrapbook textures and uses Openverse photo search. To enable AI-generated decorative backgrounds, add an OpenAI API key as `OPENAI_API_KEY` in **Settings → Secrets and variables → Actions → New repository secret**. This is optional, uses paid API credits, and the code requests only background textures, never impersonated portraits. Check model access and pricing with the provider before enabling. Never paste an API key into `albums.csv` or code.

## Photo sourcing and limitations

The script searches Openverse for real artist photographs. Search results are **not face-verified**; they may be irrelevant, duplicates, low resolution, or wrong subjects. The script downloads up to five candidate images and stores source/attribution metadata in `*-photo-sources.json`. Review the downloaded photos and the credits before using or sharing any output. Open licenses on photos do not automatically clear rights of publicity or trademark issues. The generator **does not perform true background removal**; it makes torn-paper photo cutouts. It does **not** use unauthorized scraping, bypass paywalls, or automatically approve commercial use.

If Openverse returns no usable photographs, the output explicitly says `NO VERIFIED PHOTO` instead of pretending it found an artist portrait. Photo URLs may fail or be rate-limited. Images are selected by search relevance, not verified identity. For a faithful portrait, review source candidates and consider replacing them with photographs you have rights to use.

## Technical details

- Python 3.11, Pillow, ReportLab, requests
- GitHub Actions: workflow dispatch and updates to generator inputs
- 8 × 10 inch output: 2400 × 3000 pixels; PNG metadata 300 DPI; PDF page exactly 8 × 10 inches
- RGB color output. Professional CMYK print production and bleed are not included.
- GitHub Actions artifacts expire after 14 days; download them for long-term storage.
- This is a private repository workflow, not a hosted interactive dashboard.

## Local test (optional)

`pip install -r requirements.txt && python generator.py`
