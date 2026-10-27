import asyncio, json, os, sys
import aiohttp.resolver, aiohttp.connector
aiohttp.resolver.DefaultResolver = aiohttp.resolver.ThreadedResolver   # aiodns cannot reach DNS here
aiohttp.connector.DefaultResolver = aiohttp.resolver.ThreadedResolver
import edge_tts
VOICE = sys.argv[1] if len(sys.argv) > 1 else "en-US-AndrewNeural"
async def one(item):
    com = edge_tts.Communicate(item["text"], VOICE, rate="-4%", boundary="SentenceBoundary")
    sents = []
    with open(f"F:/sg_data/video/vo/{item['id']}.mp3", "wb") as f:
        async for ch in com.stream():
            if ch["type"] == "audio":
                f.write(ch["data"])
            elif ch["type"] in ("SentenceBoundary", "WordBoundary"):
                sents.append({"start": ch["offset"] / 1e7, "end": (ch["offset"] + ch["duration"]) / 1e7, "text": ch["text"]})
    return {"id": item["id"], "sentences": sents}
async def main():
    items = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "narration.json"), encoding="utf8"))
    out = [await one(i) for i in items]
    json.dump(out, open("F:/sg_data/video/vo/timing.json", "w", encoding="utf8"), indent=1)
    print(sum(len(i["text"].split()) for i in items), "words")
asyncio.run(main())
