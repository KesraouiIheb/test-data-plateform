import os



class LocalStorage:
    def save_file(self, local_path: str, target_path: str) -> str:
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"{local_path} does not exist.")
        return local_path
