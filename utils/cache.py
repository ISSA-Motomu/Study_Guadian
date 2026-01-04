import time
from functools import wraps


class SimpleCache:
    def __init__(self, ttl=300):
        self.ttl = ttl
        self.cache = {}

    def get(self, key):
        if key in self.cache:
            val, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                return val
            else:
                del self.cache[key]
        return None

    def set(self, key, value):
        self.cache[key] = (value, time.time())

    def clear(self):
        self.cache = {}


# グローバルキャッシュインスタンス
# 商品リストはあまり変わらないので長め (10分)
shop_items_cache = SimpleCache(ttl=600)

# ジョブリストはステータスが変わるので短め (1分)
job_list_cache = SimpleCache(ttl=60)

# ユーザーの状態管理 (5分)
user_state_cache = SimpleCache(ttl=300)


def cached(cache_instance, key_func=None):
    """
    関数の結果をキャッシュするデコレータ
    :param cache_instance: SimpleCacheのインスタンス
    :param key_func: 引数からキャッシュキーを生成する関数 (省略時は引数なしとみなす)
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if key_func:
                key = key_func(*args, **kwargs)
            else:
                # 引数がない、または固定キーでよい場合
                key = "default_key"

            cached_val = cache_instance.get(key)
            if cached_val is not None:
                # print(f"Cache Hit: {func.__name__} key={key}")
                return cached_val

            # print(f"Cache Miss: {func.__name__} key={key}")
            result = func(*args, **kwargs)
            cache_instance.set(key, result)
            return result

        return wrapper

    return decorator
