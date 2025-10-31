"""
Secure password generator
"""

import secrets
import string


class PasswordGenerator:
    """
    Generates cryptographically secure random passwords.
    """
    
    # Character sets
    LOWERCASE = string.ascii_lowercase
    UPPERCASE = string.ascii_uppercase
    DIGITS = string.digits
    SYMBOLS = "!@#$%^&*()-_=+[]{}|;:,.<>?"
    
    @staticmethod
    def generate(
        length: int = 16,
        use_lowercase: bool = True,
        use_uppercase: bool = True,
        use_digits: bool = True,
        use_symbols: bool = True,
        exclude_ambiguous: bool = False
    ) -> str:
        """
        Generate a secure random password.
        
        Args:
            length: Password length (minimum 8)
            use_lowercase: Include lowercase letters
            use_uppercase: Include uppercase letters
            use_digits: Include digits
            use_symbols: Include symbols
            exclude_ambiguous: Exclude ambiguous characters (O0, l1, etc.)
            
        Returns:
            The generated password
            
        Raises:
            ValueError: If invalid parameters
        """
        if length < 8:
            raise ValueError("Password length must be at least 8 characters")
        
        # Build character set
        charset = ""
        required_chars = []
        
        if use_lowercase:
            chars = PasswordGenerator.LOWERCASE
            if exclude_ambiguous:
                chars = chars.replace('l', '').replace('o', '')
            charset += chars
            if chars:
                required_chars.append(secrets.choice(chars))
        
        if use_uppercase:
            chars = PasswordGenerator.UPPERCASE
            if exclude_ambiguous:
                chars = chars.replace('I', '').replace('O', '')
            charset += chars
            if chars:
                required_chars.append(secrets.choice(chars))
        
        if use_digits:
            chars = PasswordGenerator.DIGITS
            if exclude_ambiguous:
                chars = chars.replace('0', '').replace('1', '')
            charset += chars
            if chars:
                required_chars.append(secrets.choice(chars))
        
        if use_symbols:
            charset += PasswordGenerator.SYMBOLS
            required_chars.append(secrets.choice(PasswordGenerator.SYMBOLS))
        
        if not charset:
            raise ValueError("At least one character type must be selected")
        
        # Generate password ensuring at least one char from each selected type
        remaining_length = length - len(required_chars)
        if remaining_length < 0:
            raise ValueError("Password length is too short for selected requirements")
        
        password_chars = required_chars + [
            secrets.choice(charset) for _ in range(remaining_length)
        ]
        
        # Shuffle to randomize positions
        # Use secrets.SystemRandom for cryptographically secure shuffle
        import random
        rng = random.SystemRandom()
        rng.shuffle(password_chars)
        
        return ''.join(password_chars)
    
    @staticmethod
    def generate_passphrase(word_count: int = 4, separator: str = "-") -> str:
        """
        Generate a passphrase using random words.
        
        Args:
            word_count: Number of words
            separator: Separator between words
            
        Returns:
            The generated passphrase
        """
        # Simple word list (in production, use a larger word list)
        words = [
            "alpha", "bravo", "charlie", "delta", "echo", "foxtrot",
            "golf", "hotel", "india", "juliet", "kilo", "lima",
            "mike", "november", "oscar", "papa", "quebec", "romeo",
            "sierra", "tango", "uniform", "victor", "whiskey", "xray",
            "yankee", "zulu", "cloud", "forest", "mountain", "river",
            "ocean", "desert", "valley", "canyon", "island", "glacier",
            "tiger", "eagle", "wolf", "bear", "lion", "hawk",
            "phoenix", "dragon", "falcon", "panther", "cobra", "viper"
        ]
        
        selected_words = [secrets.choice(words) for _ in range(word_count)]
        return separator.join(selected_words)
    
    @staticmethod
    def estimate_strength(password: str) -> tuple[str, int]:
        """
        Estimate password strength.
        
        Args:
            password: The password to check
            
        Returns:
            Tuple of (strength_label, score) where score is 0-100
        """
        score = 0
        length = len(password)
        
        # Length score (up to 30 points)
        score += min(30, length * 2)
        
        # Character variety (up to 40 points)
        has_lower = any(c.islower() for c in password)
        has_upper = any(c.isupper() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_symbol = any(c in PasswordGenerator.SYMBOLS for c in password)
        
        variety_score = sum([has_lower, has_upper, has_digit, has_symbol]) * 10
        score += variety_score
        
        # Uniqueness (up to 30 points)
        unique_chars = len(set(password))
        uniqueness_ratio = unique_chars / length if length > 0 else 0
        score += int(uniqueness_ratio * 30)
        
        # Determine label
        if score >= 80:
            label = "Strong"
        elif score >= 60:
            label = "Good"
        elif score >= 40:
            label = "Fair"
        else:
            label = "Weak"
        
        return label, min(100, score)
