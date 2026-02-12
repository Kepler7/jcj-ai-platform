from chromadb import HttpClient

client = HttpClient(host="chroma", port=8000)
col = client.get_collection("jcj_playbooks_v1")
print("COLLECTION:", col.name)
print("COUNT:", col.count())
