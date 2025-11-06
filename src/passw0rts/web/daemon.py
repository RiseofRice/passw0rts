"""
Daemon entry point for running passw0rts web server as a background process
"""

import sys
import signal
import argparse
import logging
from pathlib import Path

from passw0rts.web import create_app


# Setup logging
def setup_logging():
    """Configure logging for daemon mode"""
    log_file = Path.home() / ".passw0rts" / "daemon.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logging.info(f"Received signal {signum}, shutting down...")
    sys.exit(0)


def main():
    """Main entry point for the daemon"""
    parser = argparse.ArgumentParser(description='Passw0rts Web Server Daemon')
    parser.add_argument('--host', default='127.0.0.1', help='Host address')
    parser.add_argument('--port', type=int, default=5000, help='Port number')
    parser.add_argument('--storage-path', help='Custom storage path')

    args = parser.parse_args()

    # Setup logging
    setup_logging()

    # Register signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    logging.info(f"Starting Passw0rts web server daemon on {args.host}:{args.port}")

    try:
        # Create and run the Flask app
        app = create_app(storage_path=args.storage_path)

        # Use werkzeug's built-in server (suitable for local/personal use)
        # Note: This is a password manager designed for personal use on trusted local networks.
        # The built-in Flask/werkzeug server is appropriate for this use case.
        # For internet-facing production deployments, consider using gunicorn or waitress.
        app.run(
            host=args.host,
            port=args.port,
            debug=False,
            use_reloader=False,  # Disable reloader in daemon mode
            threaded=True
        )
    except Exception as e:
        logging.error(f"Error running web server: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
