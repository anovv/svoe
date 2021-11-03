
def get_queue_key(exchange: str, data_type: str, symbol: str):
    return f"{exchange}-{data_type}-{symbol}"