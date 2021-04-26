import asyncio
from tardis_client import TardisClient, Channel

API_KEY = 'TD.Lgnnny4S9XJdgge-.2saAQyvGTV2T1hv.KOAgHbkOVXFZqvP.yrbCY1PgDD8vT9j.TZNoxTNYhh5hTTl.kb33'

async def replay():
    tardis_client = TardisClient(api_key=API_KEY)

    # replay method returns Async Generator
    # https://rickyhan.com/jekyll/update/2018/01/27/python36.html
    messages = tardis_client.replay(
        exchange="binance",
        from_date="2021-03-01",
        to_date="2021-03-03",
        filters=[Channel(name="trade", symbols=["btcusdt"]), Channel("depth", ["btcusdt"])],
    )

    print(len(messages))

    # async for local_timestamp, message in messages:
    #     # local timestamp is a Python datetime that marks timestamp when given message has been received
    #     # message is a message object as provided by exchange real-time stream
    #     print(message)

def test_tardis():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(replay())
    loop.close()