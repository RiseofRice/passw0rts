"""
Unit tests for encryption module
"""

import pytest
from cryptography.exceptions import InvalidTag
from passw0rts.core.encryption import EncryptionManager


class TestEncryptionManager:
    """Test cases for EncryptionManager"""

    def test_key_derivation(self):
        """Test key derivation from master password"""
        em = EncryptionManager()
        master_password = "TestMasterPassword123!"

        key = em.derive_key(master_password)

        assert key is not None
        assert len(key) == 32  # 256 bits
        assert em.get_salt() is not None
        assert len(em.get_salt()) == 32

    def test_key_derivation_consistency(self):
        """Test that same password with same salt produces same key"""
        em1 = EncryptionManager()
        master_password = "TestPassword123!"

        key1 = em1.derive_key(master_password)
        salt = em1.get_salt()

        em2 = EncryptionManager()
        key2 = em2.derive_key(master_password, salt)

        assert key1 == key2

    def test_encryption_decryption(self):
        """Test basic encryption and decryption"""
        em = EncryptionManager()
        em.derive_key("MasterPassword123!")

        plaintext = "This is a secret password"
        ciphertext, nonce = em.encrypt(plaintext)

        assert ciphertext != plaintext.encode()
        assert len(nonce) == 12

        decrypted = em.decrypt(ciphertext, nonce)
        assert decrypted == plaintext

    def test_encryption_different_each_time(self):
        """Test that encrypting same plaintext produces different ciphertext"""
        em = EncryptionManager()
        em.derive_key("MasterPassword123!")

        plaintext = "Same text"
        ciphertext1, nonce1 = em.encrypt(plaintext)
        ciphertext2, nonce2 = em.encrypt(plaintext)

        # Different nonces mean different ciphertext
        assert nonce1 != nonce2
        assert ciphertext1 != ciphertext2

        # But both decrypt to same plaintext
        assert em.decrypt(ciphertext1, nonce1) == plaintext
        assert em.decrypt(ciphertext2, nonce2) == plaintext

    def test_base64_encoding(self):
        """Test base64 encoding/decoding"""
        em = EncryptionManager()
        em.derive_key("MasterPassword123!")

        plaintext = "Secret data with special chars: !@#$%^&*()"
        encoded = em.encrypt_to_base64(plaintext)

        assert isinstance(encoded, str)
        assert len(encoded) > 0

        decrypted = em.decrypt_from_base64(encoded)
        assert decrypted == plaintext

    def test_wrong_key_fails(self):
        """Test that decryption fails with wrong key"""
        em1 = EncryptionManager()
        em1.derive_key("CorrectPassword")

        plaintext = "Secret data"
        ciphertext, nonce = em1.encrypt(plaintext)

        em2 = EncryptionManager()
        em2.derive_key("WrongPassword")

        with pytest.raises(InvalidTag):
            em2.decrypt(ciphertext, nonce)

    def test_tampering_detection(self):
        """Test that tampering is detected"""
        em = EncryptionManager()
        em.derive_key("MasterPassword123!")

        plaintext = "Important data"
        ciphertext, nonce = em.encrypt(plaintext)

        # Tamper with ciphertext
        tampered = bytearray(ciphertext)
        tampered[0] ^= 1  # Flip a bit
        tampered = bytes(tampered)

        with pytest.raises(InvalidTag):
            em.decrypt(tampered, nonce)

    def test_encryption_without_key_fails(self):
        """Test that encryption fails without setting key"""
        em = EncryptionManager()

        with pytest.raises(ValueError, match="key not set"):
            em.encrypt("test")

    def test_decryption_without_key_fails(self):
        """Test that decryption fails without setting key"""
        em = EncryptionManager()

        with pytest.raises(ValueError, match="key not set"):
            em.decrypt(b"fake", b"fake")

    def test_clear_sensitive_data(self):
        """Test clearing sensitive data"""
        em = EncryptionManager()
        em.derive_key("MasterPassword123!")

        assert em._key is not None
        assert em._salt is not None

        em.clear()

        assert em._key is None
        assert em._salt is None

    def test_unicode_support(self):
        """Test encryption of unicode characters"""
        em = EncryptionManager()
        em.derive_key("MasterPassword123!")

        plaintext = "Unicode: 你好 мир 🔐 café"
        encoded = em.encrypt_to_base64(plaintext)
        decrypted = em.decrypt_from_base64(encoded)

        assert decrypted == plaintext
