from beanie import Document


class TrainFiles(Document):
    file_hash: str
    file_key: str
