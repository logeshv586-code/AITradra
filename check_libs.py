try:
    import faiss
    print("faiss found")
except ImportError:
    print("faiss NOT found")

try:
    from sentence_transformers import SentenceTransformer
    print("sentence-transformers found")
except ImportError:
    print("sentence-transformers NOT found")

try:
    import numpy as np
    print("numpy found")
except ImportError:
    print("numpy NOT found")
