import asyncio
import sys

from async_repository_worker.database import Database


async def main():
    if len(sys.argv) < 2:
        print("Usage: python -m async_repository_worker.search <query>")
        print("Example: python -m async_repository_worker.search python")
        return

    query = sys.argv[1]

    db = Database()
    await db.connect()

    results = await db.search(query, limit=10)

    if not results:
        print(f"No results found for: {query}")
        return

    print(f"\n🔍 Results for '{query}':\n")
    print("-" * 60)

    for repo in results:
        print(f"📦 {repo['full_name']}")
        print(f"   ⭐ Stars: {repo['stars']} | 🍴 Forks: {repo['forks']}")
        if repo.get('language'):
            print(f"   📝 Language: {repo['language']}")
        if repo.get('description'):
            desc = repo['description'][:80]
            print(f"   📄 {desc}...")
        print("-" * 60)

    await db.close()


if __name__ == "__main__":
    asyncio.run(main())