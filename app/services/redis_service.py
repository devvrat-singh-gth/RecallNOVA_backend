
# app/services/redis_service.py

import os

import redis


REDIS_URL = os.getenv(
    "REDIS_URL",
    "redis://localhost:6379",
)

r = redis.Redis.from_url(
    REDIS_URL,
    decode_responses=True,
    socket_connect_timeout=3,
    socket_timeout=3,
    health_check_interval=30,
)
