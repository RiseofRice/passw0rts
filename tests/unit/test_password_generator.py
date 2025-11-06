"""
Unit tests for password generator
"""

import pytest
from passw0rts.utils.password_generator import PasswordGenerator


class TestPasswordGenerator:
    """Test cases for PasswordGenerator"""

    def test_generate_default(self):
        """Test password generation with defaults"""
        password = PasswordGenerator.generate()

        assert len(password) == 16
        assert any(c.islower() for c in password)
        assert any(c.isupper() for c in password)
        assert any(c.isdigit() for c in password)
        assert any(c in PasswordGenerator.SYMBOLS for c in password)

    def test_generate_custom_length(self):
        """Test password generation with custom length"""
        for length in [8, 12, 20, 32]:
            password = PasswordGenerator.generate(length=length)
            assert len(password) == length

    def test_generate_lowercase_only(self):
        """Test password with only lowercase letters"""
        password = PasswordGenerator.generate(
            length=12,
            use_lowercase=True,
            use_uppercase=False,
            use_digits=False,
            use_symbols=False
        )

        assert len(password) == 12
        assert all(c.islower() for c in password)

    def test_generate_uppercase_only(self):
        """Test password with only uppercase letters"""
        password = PasswordGenerator.generate(
            length=12,
            use_lowercase=False,
            use_uppercase=True,
            use_digits=False,
            use_symbols=False
        )

        assert len(password) == 12
        assert all(c.isupper() for c in password)

    def test_generate_alphanumeric(self):
        """Test alphanumeric password (no symbols)"""
        password = PasswordGenerator.generate(
            length=16,
            use_symbols=False
        )

        assert len(password) == 16
        assert all(c.isalnum() for c in password)

    def test_generate_no_ambiguous(self):
        """Test password without ambiguous characters"""
        password = PasswordGenerator.generate(
            length=20,
            exclude_ambiguous=True
        )

        ambiguous = ['O', '0', 'l', '1', 'I', 'o']
        assert not any(c in ambiguous for c in password)

    def test_generate_minimum_length_validation(self):
        """Test that minimum length is enforced"""
        with pytest.raises(ValueError, match="at least 8"):
            PasswordGenerator.generate(length=7)

    def test_generate_no_character_types(self):
        """Test that at least one character type is required"""
        with pytest.raises(ValueError, match="At least one"):
            PasswordGenerator.generate(
                use_lowercase=False,
                use_uppercase=False,
                use_digits=False,
                use_symbols=False
            )

    def test_generate_randomness(self):
        """Test that generated passwords are random"""
        passwords = [PasswordGenerator.generate() for _ in range(10)]

        # All should be different
        assert len(set(passwords)) == 10

    def test_generate_passphrase(self):
        """Test passphrase generation"""
        passphrase = PasswordGenerator.generate_passphrase()

        words = passphrase.split('-')
        assert len(words) == 4
        assert all(word.isalpha() for word in words)

    def test_generate_passphrase_custom(self):
        """Test passphrase with custom parameters"""
        passphrase = PasswordGenerator.generate_passphrase(
            word_count=6,
            separator="_"
        )

        words = passphrase.split('_')
        assert len(words) == 6

    def test_estimate_strength_weak(self):
        """Test strength estimation for weak password"""
        label, score = PasswordGenerator.estimate_strength("password")

        assert label in ["Weak", "Fair"]
        assert score <= 60  # "password" is short and low variety

    def test_estimate_strength_strong(self):
        """Test strength estimation for strong password"""
        label, score = PasswordGenerator.estimate_strength("xK9#mP2$vL5@qR8!")

        assert label in ["Good", "Strong"]
        assert score >= 60

    def test_estimate_strength_empty(self):
        """Test strength estimation for empty password"""
        label, score = PasswordGenerator.estimate_strength("")

        assert label == "Weak"
        assert score == 0

    def test_estimate_strength_variety(self):
        """Test that variety affects strength"""
        # Only lowercase
        label1, score1 = PasswordGenerator.estimate_strength("abcdefghij")

        # Mixed case and numbers
        label2, score2 = PasswordGenerator.estimate_strength("AbC123XyZ4")

        # Mixed with symbols
        label3, score3 = PasswordGenerator.estimate_strength("AbC!23@XyZ")

        assert score1 < score2 < score3
