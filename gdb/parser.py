import shlex
import sys
from io import StringIO


def parse_args_safely(parser, args_str):
    """Safely parse arguments using argparse without causing system exit."""

    try:
        # Split the arguments string properly handling quotes
        args_list = shlex.split(args_str.strip()) if args_str.strip() else []

        # Capture stderr to avoid argparse printing to terminal
        old_stderr = sys.stderr
        sys.stderr = StringIO()

        try:
            result = parser.parse_args(args_list)
            return result
        finally:
            # Restore stderr
            error_output = sys.stderr.getvalue()
            sys.stderr = old_stderr
            if error_output:
                print(error_output.strip())

    except SystemExit:
        # argparse calls sys.exit() on error, we catch it and return None
        return None
    except Exception as e:
        print("Error parsing arguments: %s" % str(e))
        return None
