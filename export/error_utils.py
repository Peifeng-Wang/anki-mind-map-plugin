"""Error reporting"""
import traceback


def _print_export_failure(message, exception):
    print(f"{message}: {exception}")
    traceback.print_exc()
