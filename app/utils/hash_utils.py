import hashlib

def generate_hash(content: bytes):
    return hashlib.md5(content).hexdigest()


def hash_text(text: str):
    return hashlib.sha256(text.encode()).hexdigest()