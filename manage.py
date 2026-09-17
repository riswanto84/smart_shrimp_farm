#!/usr/bin/env python

import os
import sys


def main():
    # Paksa Django selalu menggunakan konfigurasi Smart Shrimp Farm.
    os.environ["DJANGO_SETTINGS_MODULE"] = "smart_shrimp_farm.settings"

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Django tidak dapat diimpor. Pastikan virtual environment "
            "Smart Shrimp Farm sudah aktif."
        ) from exc

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()