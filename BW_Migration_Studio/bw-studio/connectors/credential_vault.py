import os
import base64
import hashlib
from cryptography.fernet import Fernet

class CredentialVault:
    """
    Local secret encryption and masking vault.
    Ensures secrets are stored encrypted locally, master key is git-ignored,
    and plain text secrets are NEVER printed or logged.
    """
    def __init__(self, key_file_path=None):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if key_file_path is None:
            self.key_file_path = os.path.join(base_dir, ".master_key")
        else:
            self.key_file_path = key_file_path
        
        self.cipher = self._init_cipher()

    def _init_cipher(self):
        env_key = os.environ.get("MASTER_ENCRYPTION_KEY", "").strip()
        if env_key:
            try:
                return Fernet(env_key.encode('utf-8'))
            except Exception:
                pass

        if os.path.exists(self.key_file_path):
            with open(self.key_file_path, "rb") as f:
                key = f.read().strip()
                if key:
                    return Fernet(key)

        key = Fernet.generate_key()
        try:
            with open(self.key_file_path, "wb") as f:
                f.write(key)
        except Exception:
            pass
        return Fernet(key)

    def encrypt(self, plain_text: str) -> str:
        if not plain_text:
            return ""
        encrypted = self.cipher.encrypt(plain_text.encode('utf-8'))
        return encrypted.decode('utf-8')

    def decrypt(self, encrypted_text: str) -> str:
        if not encrypted_text:
            return ""
        decrypted = self.cipher.decrypt(encrypted_text.encode('utf-8'))
        return decrypted.decode('utf-8')

    @staticmethod
    def mask_secret(value: str) -> str:
        """
        Mask sensitive strings for safe UI display and logging.
        Never reveals the full secret.
        """
        if not value:
            return "NOT_CONFIGURED"
        val = str(value)
        if len(val) <= 4:
            return "********"
        return f"{val[:2]}{'*' * (len(val) - 4)}{val[-2:]}"

    @staticmethod
    def load_env_file(env_path=None):
        """
        Loads .env key-value pairs cleanly without exposing them to system environments.
        """
        if env_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            env_path = os.path.join(base_dir, ".env")

        config = {}
        if not os.path.exists(env_path):
            return config

        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, val = line.split("=", 1)
                    config[key.strip()] = val.strip()
        return config
