# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 omsipmxtool contributors
import argparse
import json
import sys
from pathlib import Path
from .pmx import ConversionError, load
from .export import convert


def main():
    parser = argparse.ArgumentParser(description='Experimental PMX -> OpenOMSI O3D/HUM converter')
    sub = parser.add_subparsers(dest='command', required=True)
    inspect = sub.add_parser('inspect', help='List bones, materials and limitations without writing files')
    inspect.add_argument('input', type=Path)
    build = sub.add_parser('convert', help='Create a new standalone content package; never edits the game')
    build.add_argument('input', type=Path)
    build.add_argument('--output', type=Path, required=True)
    build.add_argument('--name', default='CustomDriver')
    build.add_argument('--height', type=float, default=1.75, help='Full mesh height in metres (default 1.75)')
    build.add_argument('--mapping', type=Path, help='JSON object: semantic role -> exact PMX bone name')
    args = parser.parse_args()
    try:
        model = load(args.input)
        if args.command == 'inspect':
            result = {'name': model.name, 'vertices': len(model.vertices),
                      'bones': [{'index': i, 'name': b.name, 'english': b.english, 'parent': b.parent}
                                for i, b in enumerate(model.bones)],
                      'materials': [m.name for m in model.materials], 'textures': model.textures,
                      'warnings': model.warnings}
        else:
            mapping = json.loads(args.mapping.read_text(encoding='utf-8-sig')) if args.mapping else {}
            if not isinstance(mapping, dict):
                raise ConversionError('Mapping must be a JSON object')
            result = convert(model, args.input, args.output, args.name, args.height, mapping)
        # ASCII JSON also works in legacy Windows terminals without encoding errors.
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0
    except (ConversionError, OSError, ValueError) as exc:
        print('Error: ' + str(exc).encode('ascii', 'backslashreplace').decode(), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
