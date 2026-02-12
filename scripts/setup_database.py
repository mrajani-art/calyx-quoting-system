#!/usr/bin/env python3
"""
Database Setup Script — prints the SQL schema for Supabase.
Run this SQL in your Supabase SQL Editor to create all tables.

Usage:
    python scripts/setup_database.py
    python scripts/setup_database.py --execute  (requires Supabase connection)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.data.supabase_client import SCHEMA_SQL


def main():
    if "--execute" in sys.argv:
        print("Executing schema against Supabase...")
        try:
            from src.data.supabase_client import get_client
            client = get_client()
            # Supabase doesn't support raw SQL via the client library,
            # so we print instructions instead
            print("\n⚠  The Supabase Python client doesn't support raw DDL execution.")
            print("   Please copy the SQL below and run it in your Supabase SQL Editor:")
            print("   https://supabase.com/dashboard → SQL Editor\n")
        except Exception as e:
            print(f"Connection failed: {e}")
            print("Printing SQL for manual execution:\n")
    else:
        print("Calyx Quoting System — Database Schema")
        print("=" * 60)
        print("Copy this SQL and run it in your Supabase SQL Editor:")
        print("https://supabase.com/dashboard → SQL Editor")
        print("=" * 60)

    print(SCHEMA_SQL)


if __name__ == "__main__":
    main()
