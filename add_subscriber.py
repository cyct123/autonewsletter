#!/usr/bin/env python3
"""
Quick script to add a subscriber to the database.

Usage:
    python add_subscriber.py

Supported channels:
    - pushplus: Uses PUSHPLUS_TOKENS from .env
    - wechat: Uses WECHAT_WEBHOOK_URLS from .env
    - email: Requires email address
    - lark: Uses Lark webhook
"""

import asyncio
import sys
from app.database import AsyncSessionLocal
from app.models.subscriber import Subscriber
from app.config import settings


async def add_subscriber(identifier: str, channel_type: str, preferences: dict = None):
    """Add a new subscriber to the database"""
    async with AsyncSessionLocal() as db:
        # Check if subscriber already exists
        from sqlalchemy import select
        result = await db.execute(
            select(Subscriber).where(Subscriber.identifier == identifier)
        )
        existing = result.scalar_one_or_none()

        if existing:
            print(f"❌ Subscriber already exists: {identifier}")
            return False

        # Create new subscriber
        subscriber = Subscriber(
            identifier=identifier,
            channel_type=channel_type,
            active=True,
            preferences=preferences or {}
        )

        db.add(subscriber)
        await db.commit()
        await db.refresh(subscriber)

        print(f"✅ Subscriber added successfully!")
        print(f"   ID: {subscriber.id}")
        print(f"   Identifier: {subscriber.identifier}")
        print(f"   Channel: {subscriber.channel_type}")
        print(f"   Active: {subscriber.active}")
        return True


async def list_subscribers():
    """List all subscribers"""
    async with AsyncSessionLocal() as db:
        from sqlalchemy import select
        result = await db.execute(select(Subscriber))
        subscribers = result.scalars().all()

        if not subscribers:
            print("📭 No subscribers found.")
            return

        print(f"\n📬 Found {len(subscribers)} subscriber(s):\n")
        for sub in subscribers:
            status = "✅ Active" if sub.active else "❌ Inactive"
            print(f"  {status}")
            print(f"    ID: {sub.id}")
            print(f"    Identifier: {sub.identifier}")
            print(f"    Channel: {sub.channel_type}")
            print(f"    Preferences: {sub.preferences}")
            print()


async def main():
    print("=" * 60)
    print("AutoNewsletter - Add Subscriber")
    print("=" * 60)

    # Check available channels from .env
    print("\n📡 Available channels based on your .env configuration:\n")

    if settings.pushplus_tokens:
        print("  ✅ pushplus - PushPlus tokens configured")
    else:
        print("  ❌ pushplus - No PUSHPLUS_TOKENS in .env")

    if settings.wechat_webhook_urls:
        print("  ✅ wechat - WeChat webhook URLs configured")
    else:
        print("  ❌ wechat - No WECHAT_WEBHOOK_URLS in .env")

    if settings.smtp_host and settings.smtp_user:
        print("  ✅ email - SMTP configured")
    else:
        print("  ❌ email - SMTP not configured in .env")

    print("  ℹ️  lark - Requires Lark webhook URL")

    # List existing subscribers
    await list_subscribers()

    # Interactive mode
    print("\n" + "=" * 60)
    print("Add a new subscriber")
    print("=" * 60)

    channel = input("\nChannel type (pushplus/wechat/email/lark): ").strip().lower()

    if channel not in ["pushplus", "wechat", "email", "lark"]:
        print(f"❌ Invalid channel: {channel}")
        sys.exit(1)

    if channel == "pushplus":
        if not settings.pushplus_tokens:
            print("❌ PUSHPLUS_TOKENS not configured in .env")
            sys.exit(1)
        identifier = input("PushPlus token (or press Enter to use first token from .env): ").strip()
        if not identifier:
            identifier = settings.pushplus_tokens[0]
            print(f"Using token from .env: {identifier[:10]}...")

    elif channel == "wechat":
        if not settings.wechat_webhook_urls:
            print("❌ WECHAT_WEBHOOK_URLS not configured in .env")
            sys.exit(1)
        identifier = input("WeChat webhook URL (or press Enter to use first URL from .env): ").strip()
        if not identifier:
            identifier = settings.wechat_webhook_urls[0]
            print(f"Using webhook from .env: {identifier[:50]}...")

    elif channel == "email":
        if not settings.smtp_host:
            print("⚠️  Warning: SMTP not configured in .env. Email sending may fail.")
        identifier = input("Email address: ").strip()
        if not identifier or "@" not in identifier:
            print("❌ Invalid email address")
            sys.exit(1)

    elif channel == "lark":
        identifier = input("Lark webhook URL: ").strip()
        if not identifier or not identifier.startswith("http"):
            print("❌ Invalid webhook URL")
            sys.exit(1)

    # Optional preferences
    max_items = input("Max items per newsletter (default: 10): ").strip()
    preferences = {}
    if max_items:
        try:
            preferences["maxItemsPerNewsletter"] = int(max_items)
        except ValueError:
            print("⚠️  Invalid number, using default (10)")

    # Add subscriber
    print("\n🔄 Adding subscriber...")
    success = await add_subscriber(identifier, channel, preferences)

    if success:
        print("\n✅ Done! You can now trigger the newsletter:")
        print("   curl -X POST http://localhost:8000/trigger")


if __name__ == "__main__":
    asyncio.run(main())
