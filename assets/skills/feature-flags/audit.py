#!/usr/bin/env python3
import argparse
import datetime
import os
import re
import subprocess
import sys
from collections import defaultdict


def main():
    parser = argparse.ArgumentParser(description='Feature flags audit report')
    parser.add_argument('--port', type=int, default=63514)
    parser.add_argument('--user', default='paulovictor237')
    parser.add_argument('--root', default='.')
    args = parser.parse_args()

    root = os.path.abspath(args.root)
    now = datetime.datetime.now()

    print(f"port={args.port} user={args.user} root={root}", file=sys.stderr)
    print(f"generated_at={now.isoformat(timespec='seconds')}", file=sys.stderr)


if __name__ == '__main__':
    main()
