"""Loopback demo CLI; authenticated embedding requires a server verifier adapter."""
import argparse
import uvicorn
from .config import Settings
from .main import create_app


def main(argv=None):
    parser = argparse.ArgumentParser(description='MCIS loopback demonstration service (not production SSO)')
    parser.add_argument('--identity-mode', choices=('local-demo', 'authenticated'), default='local-demo',
                        help='local-demo preserves legacy behavior; authenticated needs a server adapter not available in this CLI')
    args = parser.parse_args(argv)
    if args.identity_mode == 'authenticated':
        parser.error('Authenticated mode has no CLI verifier adapter. Embed create_app(identity_mode="authenticated", identity_verifier=...) with a trusted adapter; no demo fallback was made.')
    st = Settings()
    uvicorn.run(create_app(st, identity_mode=args.identity_mode), host='127.0.0.1', port=st.port, log_level='info')

if __name__ == '__main__':
    main()
