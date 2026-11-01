"""Scene Atlas and Visual Transition Discovery Tool.

Analyzes captured screenshots across a DOSBox capture session to detect scene
transitions, cuts, and visual intervals. Generates a scene manifest and transition
ledger to guide reverse-engineering priority.
"""
import argparse
import hashlib
import json
from pathlib import Path

try:
    from PIL import Image, ImageChops, ImageDraw, ImageStat, ImageOps
except ImportError as exc:
    raise SystemExit('Screenshot analysis requires Pillow: python -m pip install Pillow') from exc


def decode_screenshot(path):
    """Compare RGB pixels, including palette colors, rather than encoded bytes."""
    with Image.open(path) as image:
        rgb = image.convert('RGB')
        decoded_hash = hashlib.sha256(
            f'{rgb.width}x{rgb.height}:RGB:'.encode() + rgb.tobytes()
        ).hexdigest()
        sample = rgb.resize((64, 64), Image.Resampling.BOX)
        thumbnail = ImageOps.contain(rgb, (224, 150))
        return rgb.size, decoded_hash, sample, thumbnail


def pixel_delta(previous, current):
    """Normalized mean absolute RGB difference on 64x64 decoded samples."""
    means = ImageStat.Stat(ImageChops.difference(previous, current)).mean
    return round(sum(means) / (3 * 255) * 100, 2)


def write_contact_sheet(entries, thumbnails, output_path):
    columns, cell_width, cell_height = 4, 240, 185
    rows = max(1, (len(entries) + columns - 1) // columns)
    sheet = Image.new('RGB', (columns * cell_width, rows * cell_height), '#f4eddc')
    draw = ImageDraw.Draw(sheet)
    for idx, (entry, thumbnail) in enumerate(zip(entries, thumbnails)):
        x, y = (idx % columns) * cell_width, (idx // columns) * cell_height
        sheet.paste(thumbnail, (x + (cell_width - thumbnail.width) // 2, y + 5))
        elapsed = entry['elapsed_sec']
        time_label = f'{elapsed:.2f}s' if elapsed is not None else 'time unknown'
        draw.text((x + 8, y + 158), f"{entry['capture']} | {time_label}", fill='#392d2b')
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)


def sha256_file(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()


def analyze_session_screenshots(session_dir, output_manifest=None, contact_sheet=None):
    session = Path(session_dir).resolve()
    if not session.is_dir():
        raise SystemExit(f"Session directory not found: {session}")

    manifest_files = sorted(session.glob('capture_*/capture.json'))
    if not manifest_files:
        manifest_files = sorted(session.glob('*/capture.json'))

    entries = []
    thumbnails = []
    warnings = []
    previous = None
    previous_size = None

    for manifest_path in manifest_files:
        cap_dir = manifest_path.parent
        # Look for screenshot image
        screenshot = None
        for ext in ['*.png', '*.bmp', '*.jpg']:
            found = sorted(cap_dir.glob(ext))
            if found:
                screenshot = found[0]
                break

        if not screenshot:
            warnings.append(f'No screenshot in {cap_dir.name}')
            previous = None
            continue

        try:
            size, decoded_hash, sample, thumbnail = decode_screenshot(screenshot)
            file_sha = sha256_file(screenshot)
        except (OSError, ValueError) as exc:
            warnings.append(f'Cannot decode {screenshot.name} in {cap_dir.name}: {exc}')
            previous = None
            continue
        delta = pixel_delta(previous, sample) if previous is not None else None
        dimensions_changed = previous is not None and size != previous_size
        previous, previous_size = sample, size

        # Read capture metadata
        try:
            meta = json.loads(manifest_path.read_text(encoding='utf-8-sig'))
            elapsed_us = meta.get('time', {}).get('process_elapsed_us')
            elapsed = elapsed_us / 1000000.0 if isinstance(elapsed_us, (int, float)) else None
            capture_id = meta.get('capture', cap_dir.name)
        except (OSError, ValueError, TypeError, AttributeError) as exc:
            warnings.append(f'Cannot read metadata in {cap_dir.name}: {exc}')
            elapsed = None
            capture_id = cap_dir.name
        if elapsed is None:
            warnings.append(f'Unknown elapsed time in {cap_dir.name}')

        entries.append({
            'capture': capture_id,
            'elapsed_sec': round(elapsed, 2) if elapsed is not None else None,
            'screenshot_path': str(screenshot.relative_to(session.parent)),
            'sha256': file_sha,
            'decoded_rgb_sha256': decoded_hash,
            'dimensions': list(size),
            'dimensions_changed': dimensions_changed,
            'delta_from_prev_pct': delta
        })
        thumbnails.append(thumbnail)

    # Identify candidate cuts (delta > 35%)
    provisional_scenes = []
    current_scene_start = 0
    scene_id = 1
    candidate_transitions = []

    for idx, entry in enumerate(entries):
        if idx > 0 and (entry['dimensions_changed'] or
                       (entry['delta_from_prev_pct'] is not None and entry['delta_from_prev_pct'] > 35.0)):
            candidate_transitions.append({
                'from_capture': entries[idx - 1]['capture'],
                'to_capture': entry['capture'],
                'start_sec': entries[idx - 1]['elapsed_sec'],
                'end_sec': entry['elapsed_sec'],
                'reason': 'dimensions_changed' if entry['dimensions_changed'] else 'pixel_delta',
                'review_status': 'unreviewed'
            })
            provisional_scenes.append({
                'scene_id': f"S{scene_id:02d}",
                'start_capture': entries[current_scene_start]['capture'],
                'end_capture': entries[idx - 1]['capture'],
                'start_sec': entries[current_scene_start]['elapsed_sec'],
                'end_sec': entries[idx - 1]['elapsed_sec'],
                'sample_count': idx - current_scene_start
            })
            scene_id += 1
            current_scene_start = idx

    if entries and current_scene_start < len(entries):
        provisional_scenes.append({
            'scene_id': f"S{scene_id:02d}",
            'start_capture': entries[current_scene_start]['capture'],
            'end_capture': entries[-1]['capture'],
            'start_sec': entries[current_scene_start]['elapsed_sec'],
            'end_sec': entries[-1]['elapsed_sec'],
            'sample_count': len(entries) - current_scene_start
        })

    atlas = {
        'comparison': {
            'method': 'decoded_rgb_mean_absolute_difference',
            'sample_size': [64, 64],
            'candidate_threshold_pct': 35.0
        },
        'review_status': 'unreviewed',
        'limitations': [
            'Pixel changes flag review candidates, not confirmed scene boundaries; motion and fades can also trigger them.',
            'Sparse screenshots can miss transitions; the last screenshot does not prove program completion.'
        ],
        'warnings': warnings,
        'total_screenshots': len(entries),
        'provisional_scenes_count': len(provisional_scenes),
        'provisional_scenes': provisional_scenes,
        'candidate_transitions': candidate_transitions,
        'entries': entries
    }

    if contact_sheet:
        write_contact_sheet(entries, thumbnails, contact_sheet)
        atlas['contact_sheet_path'] = str(Path(contact_sheet))

    if output_manifest:
        out_path = Path(output_manifest)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(atlas, indent=2), encoding='utf-8')
        print(f"Scene atlas saved to {out_path}")
    else:
        print(json.dumps(atlas, indent=2))

    return atlas


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', required=True, help='Path to capture session directory')
    parser.add_argument('--output', default=None, help='Output JSON manifest path')
    parser.add_argument('--contact-sheet', help='Output review contact sheet (.png or .jpg)')
    args = parser.parse_args()
    analyze_session_screenshots(args.session, args.output, args.contact_sheet)


if __name__ == '__main__':
    main()
