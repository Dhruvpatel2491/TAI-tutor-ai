#!/usr/bin/env python3
"""Print a JWT for a given user id using backend.auth.create_jwt_for_user().
Development helper — do NOT use this in production without securing access to the secret.
"""
import argparse
from backend.auth import create_jwt_for_user


def main():
    p = argparse.ArgumentParser(description="Print a JWT for a user id")
    p.add_argument("user_id", help="User id to create token for")
    p.add_argument("--exp", type=int, help="Token lifetime in seconds", default=None)
    args = p.parse_args()
    token = create_jwt_for_user(args.user_id, exp_seconds=args.exp)
    print(token)


if __name__ == "__main__":
    main()
