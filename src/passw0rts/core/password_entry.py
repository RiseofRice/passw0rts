"""
Password entry data model
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
import uuid


def utc_now():
    """Get current UTC time in a timezone-aware manner"""
    return datetime.now(timezone.utc)


class PasswordEntry(BaseModel):
    """
    Represents a single password entry in the password manager.
    """
    
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str = Field(..., min_length=1, description="Title/name of the entry")
    username: Optional[str] = Field(None, description="Username or email")
    password: str = Field(..., min_length=1, description="The password")
    url: Optional[str] = Field(None, description="Associated URL")
    notes: Optional[str] = Field(None, description="Additional notes")
    category: Optional[str] = Field("general", description="Category for organization")
    tags: list[str] = Field(default_factory=list, description="Tags for search")
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return self.model_dump(mode='json')
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PasswordEntry':
        """Create from dictionary"""
        # Handle datetime strings
        if isinstance(data.get('created_at'), str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if isinstance(data.get('updated_at'), str):
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        return cls(**data)
    
    def matches_search(self, query: str) -> bool:
        """
        Check if this entry matches a search query.
        
        Args:
            query: Search query string (case-insensitive)
            
        Returns:
            True if entry matches the query
        """
        query = query.lower()
        searchable_fields = [
            self.title,
            self.username or "",
            self.url or "",
            self.notes or "",
            self.category or "",
            " ".join(self.tags),
        ]
        
        return any(query in field.lower() for field in searchable_fields)
    
    def update_timestamp(self):
        """Update the updated_at timestamp"""
        self.updated_at = utc_now()
