from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
import json
import logging
import traceback
from config.config import PUBLIC_KEY_PEM, PRIVATE_KEY_PEM

logger = logging.getLogger(__name__)

def load_keys():
    """加载和验证密钥"""
    try:
        # 读取公钥文件内容
        with open(PUBLIC_KEY_PEM, 'rb') as f:
            public_key_data = f.read()
        
        # 读取私钥文件内容
        with open(PRIVATE_KEY_PEM, 'rb') as f:
            private_key_data = f.read()
        
        # 加载公钥
        public_key = serialization.load_pem_public_key(public_key_data)
        logger.info(f"Loaded public key with size: {public_key.key_size}")
        
        # 加载私钥
        private_key = serialization.load_pem_private_key(
            private_key_data,
            password=None
        )
        logger.info(f"Loaded private key with size: {private_key.key_size}")
        
        # 验证密钥对
        test_data = b"test"
        encrypted = public_key.encrypt(
            test_data,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        decrypted = private_key.decrypt(
            encrypted,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        assert decrypted == test_data
        logger.info("Key pair validation successful")
        
        return public_key, private_key
    except Exception as e:
        logger.error(f"Error loading keys: {str(e)}")
        logger.error(traceback.format_exc())
        raise

# 在模块级别加载密钥
PUBLIC_KEY, PRIVATE_KEY = load_keys()

def encrypt_data(data: dict) -> str:
    """使用 RSA 公钥加密数据"""
    try:
        data_bytes = json.dumps(data).encode()
        logger.debug(f"Data to encrypt (bytes): {data_bytes[:100]}...")
        
        encrypted = PUBLIC_KEY.encrypt(
            data_bytes,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return encrypted.hex()
    except Exception as e:
        logger.error(f"Encryption error: {str(e)}")
        logger.error(f"Data: {data}")
        raise

def decrypt_data(encrypted_hex: str) -> dict:
    """使用 RSA 私钥解密数据"""
    try:
        encrypted_bytes = bytes.fromhex(encrypted_hex)
        logger.debug(f"Data to decrypt (hex): {encrypted_hex[:100]}...")
        
        decrypted = PRIVATE_KEY.decrypt(
            encrypted_bytes,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return json.loads(decrypted.decode())
    except Exception as e:
        logger.error(f"Decryption error: {str(e)}")
        logger.error(f"Encrypted hex length: {len(encrypted_hex)}")
        raise 